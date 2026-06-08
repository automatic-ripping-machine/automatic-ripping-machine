"""Auth service — CRUD operations for users and groups."""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from arm_auth.db import AuthDB
from arm_auth.models import User, Group
from arm_auth.passwords import hash_password, verify_password
from arm_auth.scopes import DEFAULT_GROUPS

logger = logging.getLogger(__name__)

# Pre-computed dummy hash for constant-time username enumeration prevention
_DUMMY_HASH = hash_password("arm-auth-dummy-init")


@dataclass
class GroupInfo:
    """Plain data copy of a Group, safe to use outside a DB session."""
    id: int
    name: str
    scopes: list[str]


@dataclass
class UserInfo:
    """Plain data copy of a User, safe to use outside a DB session."""
    id: int
    username: str
    email: str | None
    password_hash: str
    active: bool
    groups: list[GroupInfo] = field(default_factory=list)

    @property
    def all_scopes(self) -> set[str]:
        scopes = set()
        for g in self.groups:
            scopes.update(g.scopes)
        return scopes

    def has_scope(self, scope: str) -> bool:
        all_scopes = self.all_scopes
        return "*" in all_scopes or scope in all_scopes


class AuthService:
    """High-level operations for managing auth users and groups."""

    def __init__(self, db: AuthDB):
        self.db = db

    @staticmethod
    def _to_info(user: User) -> UserInfo:
        """Copy user and groups into plain dataclasses (session-safe)."""
        return UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            password_hash=user.password_hash,
            active=user.active,
            groups=[
                GroupInfo(id=g.id, name=g.name, scopes=g.scope_list)
                for g in user.groups
            ],
        )

    def seed_defaults(self):
        """Create default groups if they don't exist."""
        with self.db.session() as s:
            for name, definition in DEFAULT_GROUPS.items():
                existing = s.query(Group).filter_by(name=name).first()
                if existing is None:
                    group = Group(name=name, scopes=json.dumps(definition["scopes"]))
                    s.add(group)
                    logger.info("Seeded default group: %s", name)

    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        group_name: str = "user",
    ) -> UserInfo:
        """Create a new user with a hashed password and group assignment."""
        # Validate username
        username = username.strip()
        if not username:
            raise ValueError("Username cannot be empty")
        if len(username) > 150:
            raise ValueError("Username too long (max 150 characters)")
        if ":" in username or "\n" in username or "\x00" in username:
            raise ValueError("Username contains invalid characters (: newline or null)")

        # Validate password
        if not password:
            raise ValueError("Password cannot be empty")
        if len(password.encode("utf-8")) > 72:
            raise ValueError("Password too long (max 72 bytes — bcrypt limitation)")

        with self.db.session() as s:
            existing = s.query(User).filter_by(username=username).first()
            if existing is not None:
                raise ValueError(f"User '{username}' already exists")

            group = s.query(Group).filter_by(name=group_name).first()
            if group is None:
                raise ValueError(f"Group '{group_name}' does not exist")

            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
            )
            user.groups.append(group)
            s.add(user)
            s.flush()
            s.refresh(user)
            return self._to_info(user)

    def list_users(self) -> list[UserInfo]:
        """Return all users with their groups loaded."""
        with self.db.session() as s:
            users = s.query(User).all()
            return [self._to_info(u) for u in users]

    def get_user(self, username: str) -> Optional[UserInfo]:
        """Look up a user by username."""
        with self.db.session() as s:
            user = s.query(User).filter_by(username=username).first()
            if user is None:
                return None
            return self._to_info(user)

    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        group_name: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> UserInfo:
        """Update a user's email, group, or active status."""
        with self.db.session() as s:
            user = s.get(User, user_id)
            if user is None:
                raise ValueError(f"User ID {user_id} not found")
            if email is not None:
                user.email = email
            if active is not None:
                user.active = active
            if group_name is not None:
                group = s.query(Group).filter_by(name=group_name).first()
                if group is None:
                    raise ValueError(f"Group '{group_name}' does not exist")
                user.groups.clear()
                user.groups.append(group)
            s.flush()
            s.refresh(user)
            return self._to_info(user)

    def update_password(self, user_id: int, new_password: str):
        """Change a user's password."""
        with self.db.session() as s:
            user = s.get(User, user_id)
            if user is None:
                raise ValueError(f"User ID {user_id} not found")
            user.password_hash = hash_password(new_password)

    def delete_user(self, user_id: int):
        """Delete a user. Prevents deleting the last admin."""
        with self.db.session() as s:
            user = s.get(User, user_id)
            if user is None:
                raise ValueError(f"User ID {user_id} not found")

            if any(g.name == "admin" for g in user.groups):
                admin_group = s.query(Group).filter_by(name="admin").first()
                if admin_group and len(admin_group.users) <= 1:
                    raise ValueError("Cannot delete the last admin user")

            s.delete(user)

    def verify_credentials(self, username: str, password: str) -> Optional[UserInfo]:
        """Verify username + password. Returns user if valid, None otherwise."""
        with self.db.session() as s:
            user = s.query(User).filter_by(username=username, active=True).first()
            if user is None:
                verify_password("dummy", _DUMMY_HASH)
                return None
            if not verify_password(password, user.password_hash):
                return None
            return self._to_info(user)
