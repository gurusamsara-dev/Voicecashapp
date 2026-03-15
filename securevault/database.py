"""
database.py — SQLite CRUD for SecureVault.

All values written to disk are already encrypted by the caller.
This module never handles plaintext secrets.
"""

import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional

# Default database path (can be overridden via environment variable)
_DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".securevault", "vault.db")


def _get_db_path() -> str:
    return os.environ.get("SECUREVAULT_DB", _DEFAULT_DB_PATH)


def ensure_db_dir() -> None:
    """Create the database directory if it does not exist."""
    db_path = _get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row-factory set to :class:`sqlite3.Row`."""
    ensure_db_dir()
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they do not already exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_meta (
                id      INTEGER PRIMARY KEY CHECK (id = 1),
                pw_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                description   TEXT    NOT NULL,
                category      TEXT    NOT NULL DEFAULT 'General',
                encrypted_key BLOB    NOT NULL,
                chacha_nonce  BLOB    NOT NULL,
                chacha_salt   BLOB    NOT NULL,
                fernet_salt   BLOB    NOT NULL,
                date_added    TEXT    NOT NULL
            )
        """)
        conn.commit()


# ── Master-password hash ──────────────────────────────────────────────────────

def set_master_password_hash(pw_hash: str) -> None:
    """Persist the master-password hash (first-run setup)."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO vault_meta (id, pw_hash) VALUES (1, ?)",
            (pw_hash,),
        )
        conn.commit()


def get_master_password_hash() -> Optional[str]:
    """Return the stored master-password hash, or *None* if not yet set."""
    with get_connection() as conn:
        row = conn.execute("SELECT pw_hash FROM vault_meta WHERE id = 1").fetchone()
        return row["pw_hash"] if row else None


# ── CRUD operations ───────────────────────────────────────────────────────────

def add_secret(
    description: str,
    category: str,
    encrypted_key: bytes,
    chacha_nonce: bytes,
    chacha_salt: bytes,
    fernet_salt: bytes,
) -> int:
    """Insert a new encrypted secret and return its row id."""
    date_added = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO secrets
                (description, category, encrypted_key, chacha_nonce, chacha_salt, fernet_salt, date_added)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (description, category, encrypted_key, chacha_nonce, chacha_salt, fernet_salt, date_added),
        )
        conn.commit()
        return cur.lastrowid


def get_all_secrets(order_by: str = "date_added DESC") -> list:
    """Return all rows (as :class:`sqlite3.Row` objects) ordered by *order_by*."""
    allowed = {
        "date_added DESC", "date_added ASC",
        "description ASC", "description DESC",
        "category ASC", "category DESC",
    }
    if order_by not in allowed:
        order_by = "date_added DESC"
    with get_connection() as conn:
        return conn.execute(f"SELECT * FROM secrets ORDER BY {order_by}").fetchall()


def get_secret_by_id(secret_id: int) -> Optional[sqlite3.Row]:
    """Return the row for *secret_id*, or *None* if not found."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM secrets WHERE id = ?", (secret_id,)
        ).fetchone()


def search_secrets(query: str) -> list:
    """Return rows whose description or category contains *query* (case-insensitive)."""
    pattern = f"%{query}%"
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT * FROM secrets
            WHERE description LIKE ? OR category LIKE ?
            ORDER BY date_added DESC
            """,
            (pattern, pattern),
        ).fetchall()


def delete_secret(secret_id: int) -> None:
    """Permanently delete the row with *secret_id*."""
    with get_connection() as conn:
        conn.execute("DELETE FROM secrets WHERE id = ?", (secret_id,))
        conn.commit()


# ── Backup / export ───────────────────────────────────────────────────────────

def export_backup(path: str) -> None:
    """Copy the live database to *path* as an encrypted-at-rest backup."""
    src_conn = get_connection()
    try:
        dst_conn = sqlite3.connect(path)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()


def import_backup(path: str) -> None:
    """Overwrite the live database with the backup at *path*."""
    ensure_db_dir()
    src_conn = sqlite3.connect(path)
    try:
        dst_conn = get_connection()
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()
