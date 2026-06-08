"""Bcrypt password hashing.

Uses bcrypt's self-contained hash format ($2b$12$...) which embeds
the salt. No separate salt column needed.
"""

import bcrypt


def hash_password(password: str, rounds: int = 12) -> str:
    """Hash a password with bcrypt. Returns a self-contained hash string."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
