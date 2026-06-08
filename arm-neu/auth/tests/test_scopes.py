"""Tests for scope constants and default group definitions."""

from arm_auth.scopes import ALL_SCOPES, DEFAULT_GROUPS, WILDCARD


class TestScopes:
    def test_wildcard_defined(self):
        assert WILDCARD == "*"

    def test_all_scopes_is_set(self):
        assert isinstance(ALL_SCOPES, set)
        assert "jobs:read" in ALL_SCOPES
        assert "jobs:write" in ALL_SCOPES
        assert "users:manage" in ALL_SCOPES
        assert "settings:write" in ALL_SCOPES

    def test_wildcard_not_in_all_scopes(self):
        assert WILDCARD not in ALL_SCOPES


class TestDefaultGroups:
    def test_admin_group_defined(self):
        assert "admin" in DEFAULT_GROUPS
        assert DEFAULT_GROUPS["admin"]["scopes"] == ["*"]

    def test_user_group_defined(self):
        assert "user" in DEFAULT_GROUPS
        user_scopes = DEFAULT_GROUPS["user"]["scopes"]
        assert "jobs:read" in user_scopes
        assert "jobs:write" in user_scopes
        assert "users:manage" not in user_scopes
        assert "settings:write" not in user_scopes

    def test_all_user_scopes_are_valid(self):
        for group_name, group_def in DEFAULT_GROUPS.items():
            for scope in group_def["scopes"]:
                assert scope == WILDCARD or scope in ALL_SCOPES, (
                    f"Group '{group_name}' has unknown scope '{scope}'"
                )
