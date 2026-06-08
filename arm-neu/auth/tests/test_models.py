"""Tests for auth SQLAlchemy models."""

import pytest

from arm_auth.db import AuthDB
from arm_auth.models import User, Group, UserGroup


class TestUserModel:
    def test_create_user(self, auth_db):
        with auth_db.session() as s:
            user = User(
                username="admin",
                email="admin@arm.local",
                password_hash="$2b$12$fakehash",
            )
            s.add(user)
            s.flush()
            assert user.id is not None
            assert user.active is True
            assert user.created_at is not None

    def test_username_unique(self, auth_db):
        with auth_db.session() as s:
            s.add(User(username="admin", password_hash="hash1"))
            s.flush()
        with pytest.raises(Exception):
            with auth_db.session() as s:
                s.add(User(username="admin", password_hash="hash2"))

    def test_user_repr(self, auth_db):
        with auth_db.session() as s:
            user = User(username="admin", password_hash="hash")
            s.add(user)
            s.flush()
            assert "admin" in repr(user)


class TestGroupModel:
    def test_create_group(self, auth_db):
        with auth_db.session() as s:
            group = Group(name="admin", scopes='["*"]')
            s.add(group)
            s.flush()
            assert group.id is not None

    def test_group_name_unique(self, auth_db):
        with auth_db.session() as s:
            s.add(Group(name="admin", scopes='["*"]'))
            s.flush()
        with pytest.raises(Exception):
            with auth_db.session() as s:
                s.add(Group(name="admin", scopes='["*"]'))

    def test_scope_list_property(self, auth_db):
        with auth_db.session() as s:
            group = Group(name="user", scopes='["jobs:read","jobs:write"]')
            s.add(group)
            s.flush()
            assert group.scope_list == ["jobs:read", "jobs:write"]

    def test_scope_list_wildcard(self, auth_db):
        with auth_db.session() as s:
            group = Group(name="admin", scopes='["*"]')
            s.add(group)
            s.flush()
            assert group.scope_list == ["*"]


class TestScopeListSetter:
    def test_scope_list_setter(self, auth_db):
        with auth_db.session() as s:
            group = Group(name="custom", scopes='[]')
            s.add(group)
            s.flush()
            group.scope_list = ["a", "b"]
            s.flush()
            assert group.scopes == '["a", "b"]'


class TestUserNoGroups:
    def test_user_no_groups_empty_scopes(self, auth_db):
        with auth_db.session() as s:
            user = User(username="lonely", password_hash="hash")
            s.add(user)
            s.flush()
            assert user.all_scopes == set()
            assert user.has_scope("x") is False


class TestUserGroupRelationship:
    def test_assign_user_to_group(self, auth_db):
        with auth_db.session() as s:
            user = User(username="admin", password_hash="hash")
            group = Group(name="admin", scopes='["*"]')
            s.add(user)
            s.add(group)
            s.flush()
            user.groups.append(group)
            s.flush()
            assert group in user.groups
            assert user in group.users

    def test_user_all_scopes(self, auth_db):
        with auth_db.session() as s:
            user = User(username="viewer", password_hash="hash")
            g1 = Group(name="readers", scopes='["jobs:read","logs:read"]')
            g2 = Group(name="writers", scopes='["jobs:write"]')
            s.add_all([user, g1, g2])
            s.flush()
            user.groups.extend([g1, g2])
            s.flush()
            scopes = user.all_scopes
            assert scopes == {"jobs:read", "logs:read", "jobs:write"}

    def test_user_all_scopes_wildcard(self, auth_db):
        with auth_db.session() as s:
            user = User(username="admin", password_hash="hash")
            group = Group(name="admin", scopes='["*"]')
            s.add_all([user, group])
            s.flush()
            user.groups.append(group)
            s.flush()
            assert user.all_scopes == {"*"}

    def test_user_has_scope(self, auth_db):
        with auth_db.session() as s:
            user = User(username="viewer", password_hash="hash")
            group = Group(name="readers", scopes='["jobs:read"]')
            s.add_all([user, group])
            s.flush()
            user.groups.append(group)
            s.flush()
            assert user.has_scope("jobs:read") is True
            assert user.has_scope("jobs:write") is False

    def test_user_has_scope_wildcard(self, auth_db):
        with auth_db.session() as s:
            user = User(username="admin", password_hash="hash")
            group = Group(name="admin", scopes='["*"]')
            s.add_all([user, group])
            s.flush()
            user.groups.append(group)
            s.flush()
            assert user.has_scope("anything") is True

    def test_cascade_delete_user(self, auth_db):
        with auth_db.session() as s:
            user = User(username="temp", password_hash="hash")
            group = Group(name="g", scopes='["*"]')
            s.add_all([user, group])
            s.flush()
            user.groups.append(group)
            s.flush()
            user_id = user.id
            s.delete(user)
            s.flush()
            count = s.query(UserGroup).filter_by(user_id=user_id).count()
            assert count == 0
