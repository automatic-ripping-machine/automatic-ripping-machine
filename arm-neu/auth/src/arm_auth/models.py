"""SQLAlchemy models for the auth system."""

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from arm_auth.db import Base


class UserGroup(Base):
    """Many-to-many association between users and groups."""

    __tablename__ = "auth_user_group"

    user_id = Column(Integer, ForeignKey("auth_user.id", ondelete="CASCADE"), primary_key=True)
    group_id = Column(Integer, ForeignKey("auth_group.id", ondelete="CASCADE"), primary_key=True)


class User(Base):
    """An authenticated user."""

    __tablename__ = "auth_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    groups = relationship("Group", secondary="auth_user_group", back_populates="users")

    @property
    def all_scopes(self) -> set[str]:
        """Return the union of all scopes from all groups."""
        scopes = set()
        for group in self.groups:
            scopes.update(group.scope_list)
        return scopes

    def has_scope(self, scope: str) -> bool:
        """Check if user has a specific scope (or wildcard)."""
        all_scopes = self.all_scopes
        return "*" in all_scopes or scope in all_scopes

    def __repr__(self):
        return f"<User {self.username!r}>"


class Group(Base):
    """A named group with a set of permission scopes."""

    __tablename__ = "auth_group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    scopes = Column(Text, nullable=False)  # JSON array: ["jobs:read", "jobs:write"]

    users = relationship("User", secondary="auth_user_group", back_populates="groups")

    @property
    def scope_list(self) -> list[str]:
        """Parse the JSON scopes string into a list."""
        try:
            return json.loads(self.scopes)
        except (json.JSONDecodeError, TypeError):
            return []

    @scope_list.setter
    def scope_list(self, value: list[str]):
        self.scopes = json.dumps(value)

    def __repr__(self):
        return f"<Group {self.name!r}>"
