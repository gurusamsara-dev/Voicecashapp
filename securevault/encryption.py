"""
encryption.py — Double encryption: AES-256 Fernet + ChaCha20-Poly1305

Layer 1: Master-password-derived key via PBKDF2 → Fernet (AES-256-CBC + HMAC-SHA256)
Layer 2: Per-secret ChaCha20-Poly1305 with a random nonce and salt
"""

import os
import base64
import hashlib

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.fernet import Fernet

# ── PBKDF2 parameters ─────────────────────────────────────────────────────────
_PBKDF2_ITERATIONS = 600_000
_KEY_LENGTH = 32  # bytes → 256-bit

# ── Public helpers ─────────────────────────────────────────────────────────────


def derive_fernet_key(master_password: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from *master_password* + *salt* via PBKDF2-HMAC-SHA256.

    Returns the raw 32 bytes (suitable for wrapping in a URL-safe base64 Fernet key).
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LENGTH,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    raw = kdf.derive(master_password.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)  # Fernet expects URL-safe base64


def new_fernet_salt() -> bytes:
    """Return a fresh 16-byte random salt for Fernet key derivation."""
    return os.urandom(16)


def fernet_encrypt(plaintext: bytes, fernet_key: bytes) -> bytes:
    """Encrypt *plaintext* with Fernet (AES-256-CBC + HMAC-SHA256).

    *fernet_key* must be the URL-safe base64-encoded 32-byte key produced by
    :func:`derive_fernet_key`.
    """
    f = Fernet(fernet_key)
    return f.encrypt(plaintext)


def fernet_decrypt(ciphertext: bytes, fernet_key: bytes) -> bytes:
    """Decrypt a Fernet token.  Raises ``cryptography.fernet.InvalidToken`` on failure."""
    f = Fernet(fernet_key)
    return f.decrypt(ciphertext)


# ── ChaCha20-Poly1305 ─────────────────────────────────────────────────────────

def new_chacha_nonce() -> bytes:
    """Return a fresh 12-byte random nonce for ChaCha20-Poly1305."""
    return os.urandom(12)


def new_chacha_salt() -> bytes:
    """Return a fresh 32-byte random salt used to derive the ChaCha20 key."""
    return os.urandom(32)


def _derive_chacha_key(master_password: str, salt: bytes) -> bytes:
    """Derive a 32-byte ChaCha20 key from *master_password* and *salt* via PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LENGTH,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(master_password.encode("utf-8"))


def chacha_encrypt(plaintext: bytes, master_password: str, nonce: bytes, salt: bytes) -> bytes:
    """Encrypt *plaintext* with ChaCha20-Poly1305.

    Returns the raw ciphertext (authenticated, includes the 16-byte Poly1305 tag).
    """
    key = _derive_chacha_key(master_password, salt)
    chacha = ChaCha20Poly1305(key)
    return chacha.encrypt(nonce, plaintext, None)


def chacha_decrypt(ciphertext: bytes, master_password: str, nonce: bytes, salt: bytes) -> bytes:
    """Decrypt a ChaCha20-Poly1305 ciphertext.

    Raises ``cryptography.exceptions.InvalidTag`` on authentication failure.
    """
    key = _derive_chacha_key(master_password, salt)
    chacha = ChaCha20Poly1305(key)
    return chacha.decrypt(nonce, ciphertext, None)


# ── High-level double-encryption interface ────────────────────────────────────

def encrypt_secret(secret: str, master_password: str) -> dict:
    """Double-encrypt *secret* and return all material needed to decrypt it.

    Encryption order:
      1. Fernet (AES-256-CBC + HMAC) with a PBKDF2-derived key → fernet_token
      2. ChaCha20-Poly1305 with a separate PBKDF2-derived key  → chacha_ciphertext

    Returns a dict with keys:
      ``encrypted_key``  – ChaCha20 ciphertext (bytes)
      ``chacha_nonce``   – 12-byte nonce (bytes)
      ``chacha_salt``    – 32-byte salt for ChaCha20 key derivation (bytes)
      ``fernet_salt``    – 16-byte salt for Fernet key derivation (bytes)
    """
    # Layer 1 — Fernet
    fernet_salt = new_fernet_salt()
    fernet_key = derive_fernet_key(master_password, fernet_salt)
    fernet_token = fernet_encrypt(secret.encode("utf-8"), fernet_key)

    # Layer 2 — ChaCha20-Poly1305 wraps the Fernet token
    chacha_nonce = new_chacha_nonce()
    chacha_salt = new_chacha_salt()
    encrypted_key = chacha_encrypt(fernet_token, master_password, chacha_nonce, chacha_salt)

    return {
        "encrypted_key": encrypted_key,
        "chacha_nonce": chacha_nonce,
        "chacha_salt": chacha_salt,
        "fernet_salt": fernet_salt,
    }


def decrypt_secret(
    encrypted_key: bytes,
    chacha_nonce: bytes,
    chacha_salt: bytes,
    fernet_salt: bytes,
    master_password: str,
) -> str:
    """Reverse of :func:`encrypt_secret`.

    Raises on any authentication failure (wrong password, tampered data, etc.).
    Returns the original plaintext string.
    """
    # Layer 2 — undo ChaCha20
    fernet_token = chacha_decrypt(encrypted_key, master_password, chacha_nonce, chacha_salt)

    # Layer 1 — undo Fernet
    fernet_key = derive_fernet_key(master_password, fernet_salt)
    plaintext = fernet_decrypt(fernet_token, fernet_key)

    return plaintext.decode("utf-8")


# ── Verification helper used at login ─────────────────────────────────────────

def verify_master_password(stored_hash: str, master_password: str) -> bool:
    """Return True if SHA-256(master_password) == *stored_hash* (hex string)."""
    candidate = hashlib.sha256(master_password.encode("utf-8")).hexdigest()
    return candidate == stored_hash


def hash_master_password(master_password: str) -> str:
    """Return hex-encoded SHA-256 of *master_password* for storage."""
    return hashlib.sha256(master_password.encode("utf-8")).hexdigest()
