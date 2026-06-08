"""Tests for config utilities (arm/config/config_utils.py)."""


class TestArmYamlTestBool:
    """Test arm_yaml_test_bool() YAML value formatting."""

    def test_true_value(self):
        from arm.config.config_utils import arm_yaml_test_bool
        result = arm_yaml_test_bool("MAINFEATURE", "True")
        assert result == "MAINFEATURE: true\n"

    def test_false_value(self):
        from arm.config.config_utils import arm_yaml_test_bool
        result = arm_yaml_test_bool("MAINFEATURE", "False")
        assert result == "MAINFEATURE: false\n"

    def test_case_insensitive_true(self):
        from arm.config.config_utils import arm_yaml_test_bool
        result = arm_yaml_test_bool("NOTIFY_RIP", "TRUE")
        assert result == "NOTIFY_RIP: true\n"

    def test_case_insensitive_false(self):
        from arm.config.config_utils import arm_yaml_test_bool
        result = arm_yaml_test_bool("NOTIFY_RIP", "FALSE")
        assert result == "NOTIFY_RIP: false\n"

    def test_webserver_ip_no_quotes(self):
        from arm.config.config_utils import arm_yaml_test_bool
        result = arm_yaml_test_bool("WEBSERVER_IP", "192.168.1.100")
        assert result == "WEBSERVER_IP: 192.168.1.100\n"

    def test_string_value_quoted(self):
        from arm.config.config_utils import arm_yaml_test_bool
        result = arm_yaml_test_bool("RAW_PATH", "/home/arm/media/raw")
        assert result == 'RAW_PATH: "/home/arm/media/raw"\n'

    def test_string_with_quotes_escaped(self):
        from arm.config.config_utils import arm_yaml_test_bool
        result = arm_yaml_test_bool("TITLE", 'He said "hello"')
        assert '\\"' in result
        assert "TITLE:" in result

    def test_empty_string(self):
        from arm.config.config_utils import arm_yaml_test_bool
        result = arm_yaml_test_bool("BASH_SCRIPT", "")
        assert result == 'BASH_SCRIPT: ""\n'


def _full_comments():
    """Build a complete ARM_CFG_GROUPS dict (all keys required at call time)."""
    return {
        'ARM_CFG_GROUPS': {
            'DIR_SETUP': '# Directory Setup',
            'WEB_SERVER': '# Web Server',
            'FILE_PERMS': '# File Permissions',
            'MAKE_MKV': '# MakeMKV',
            'EMBY': '# Emby',
            'EMBY_ADDITIONAL': '# Emby Additional',
            'NOTIFY_PERMS': '# Notifications',
            'APPRISE': '# Apprise',
        }
    }


class TestArmYamlCheckGroups:
    """Test arm_yaml_check_groups() comment section insertion."""

    def test_known_key_returns_comment(self):
        from arm.config.config_utils import arm_yaml_check_groups
        result = arm_yaml_check_groups(_full_comments(), 'COMPLETED_PATH')
        assert '# Directory Setup' in result

    def test_unknown_key_returns_empty(self):
        from arm.config.config_utils import arm_yaml_check_groups
        result = arm_yaml_check_groups(_full_comments(), 'UNKNOWN_KEY')
        assert result == ""

    def test_webserver_ip_returns_web_server(self):
        from arm.config.config_utils import arm_yaml_check_groups
        result = arm_yaml_check_groups(_full_comments(), 'WEBSERVER_IP')
        assert '# Web Server' in result


class TestBuildArmCfgStrip:
    """Test that build_arm_cfg strips whitespace from values (#1684)."""

    def test_key_value_stripped(self):
        from arm.services.config import build_arm_cfg
        comments = _full_comments()
        comments['ARM_CFG_GROUPS']['BEGIN'] = '# ARM config'
        form_data = {
            'MAKEMKV_PERMA_KEY': '  T-abc123xyz  ',
        }
        result = build_arm_cfg(form_data, comments)
        assert 'T-abc123xyz' in result
        assert '  T-abc123xyz' not in result

    def test_normal_value_unchanged(self):
        from arm.services.config import build_arm_cfg
        comments = _full_comments()
        comments['ARM_CFG_GROUPS']['BEGIN'] = '# ARM config'
        form_data = {
            'RAW_PATH': '/home/arm/media/raw',
        }
        result = build_arm_cfg(form_data, comments)
        assert '/home/arm/media/raw' in result
