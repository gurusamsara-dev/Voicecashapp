"""
utils.py — Helper functions for SecureVault.

Covers:
  - Secure random key generation
  - Input validation
  - Miscellaneous formatting helpers
"""

import os
import re
import string
import secrets
from typing import Optional


# ── Random key generator ──────────────────────────────────────────────────────

_ALPHABET_FULL = string.ascii_letters + string.digits + string.punctuation


def generate_random_key(
    length: int = 32,
    use_symbols: bool = True,
    use_digits: bool = True,
    use_upper: bool = True,
    use_lower: bool = True,
) -> str:
    """Generate a cryptographically secure random key.

    Parameters
    ----------
    length:
        Number of characters in the generated key (default 32).
    use_symbols:
        Include punctuation / symbols.
    use_digits:
        Include decimal digits.
    use_upper:
        Include uppercase ASCII letters.
    use_lower:
        Include lowercase ASCII letters.

    Returns
    -------
    str
        A random key string.

    Raises
    ------
    ValueError
        If no character set is selected or *length* < 1.
    """
    if length < 1:
        raise ValueError("Key length must be at least 1.")

    alphabet = ""
    if use_lower:
        alphabet += string.ascii_lowercase
    if use_upper:
        alphabet += string.ascii_uppercase
    if use_digits:
        alphabet += string.digits
    if use_symbols:
        alphabet += string.punctuation

    if not alphabet:
        raise ValueError("At least one character class must be selected.")

    return "".join(secrets.choice(alphabet) for _ in range(length))


# ── Input validation ─────────────────────────────────────────────────────────

def validate_description(description: str) -> Optional[str]:
    """Return an error message string if *description* is invalid, else ``None``."""
    if not description or not description.strip():
        return "Description cannot be empty."
    if len(description.strip()) > 200:
        return "Description must be 200 characters or fewer."
    return None


def validate_secret(secret: str) -> Optional[str]:
    """Return an error message string if *secret* is invalid, else ``None``."""
    if not secret:
        return "Secret cannot be empty."
    return None


def validate_category(category: str) -> Optional[str]:
    """Return an error message string if *category* is invalid, else ``None``."""
    if not category or not category.strip():
        return "Category cannot be empty."
    if len(category.strip()) > 100:
        return "Category must be 100 characters or fewer."
    return None


def validate_master_password(password: str) -> Optional[str]:
    """Enforce basic master-password policy.

    Returns an error message string if *password* fails, else ``None``.
    A new vault password must be at least 8 characters.
    """
    if not password:
        return "Master password cannot be empty."
    if len(password) < 8:
        return "Master password must be at least 8 characters."
    return None


# ── Formatting helpers ────────────────────────────────────────────────────────

def format_date(iso_date: str) -> str:
    """Return a human-friendly date string from an ISO-format date/datetime string."""
    try:
        from datetime import datetime
        dt = datetime.strptime(iso_date[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_date or "—"


def truncate(text: str, max_length: int = 60) -> str:
    """Truncate *text* to *max_length* characters, appending '…' if shortened."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


# ── Categories ────────────────────────────────────────────────────────────────

DEFAULT_CATEGORIES = [
    "General",
    "API Key",
    "Password",
    "SSH Key",
    "Token",
    "Certificate",
    "Database",
    "Other",
]
