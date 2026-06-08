"""Shared authentication library for the ARM ecosystem."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("arm-auth")
except PackageNotFoundError:
    # Fallback for development (editable install may not have metadata)
    from pathlib import Path
    __version__ = (Path(__file__).resolve().parent.parent.parent / "VERSION").read_text().strip()

from arm_auth.db import AuthDB, auth_db
from arm_auth.models import User, Group
from arm_auth.passwords import hash_password, verify_password
from arm_auth.scopes import ALL_SCOPES, DEFAULT_GROUPS, WILDCARD
from arm_auth.service import AuthService
from arm_auth.tinyauth.sync import sync_users

__all__ = [
    "AuthDB",
    "auth_db",
    "User",
    "Group",
    "hash_password",
    "verify_password",
    "ALL_SCOPES",
    "DEFAULT_GROUPS",
    "WILDCARD",
    "AuthService",
    "sync_users",
]
