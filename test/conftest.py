"""Pytest conftest - mock heavy system dependencies before ARM imports."""
import sys
import os
import types
from unittest.mock import MagicMock

# Mock system-level modules that require native libraries or system config
_MOCKED_MODULES = [
    'discid',
    'discid.disc',
    'discid.libdiscid',
]

for mod_name in _MOCKED_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Create a minimal arm.config.config module before any ARM code imports it.
# This avoids loading /etc/arm/config/arm.yaml which doesn't exist in test envs.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_minimal_arm_config = {
    'INSTALLPATH': _project_root + '/',
    'DBFILE': '/tmp/arm_test.db',
    'LOGLEVEL': 'DEBUG',
    'DISABLE_LOGIN': True,
    'COMPLETED_PATH': '/tmp/arm_completed',
    'RAW_PATH': '/tmp/arm_raw',
    'TRANSCODE_PATH': '/tmp/arm_transcode',
    'MEDIA_DIR': '/tmp/arm_media',
    'ARMPATH': _project_root + '/',
    'RAWPATH': '/tmp/arm_raw',
    'USE_DISC_LABEL_FOR_TV': False,
    'GROUP_TV_DISCS_UNDER_SERIES': False,
    'EXTRAS_SUB': 'extras',
    'DEST_EXT': 'mkv',
}

# Pre-populate arm.config and arm.config.config in sys.modules
_config_mod = types.ModuleType('arm.config.config')
_config_mod.arm_config = _minimal_arm_config
_config_mod.arm_config_path = '/tmp/arm.yaml'
_config_mod.abcde_config = ''
_config_mod.apprise_config = {}

_config_pkg = types.ModuleType('arm.config')
_config_pkg.config = _config_mod

# Also mock config_utils used by config.py
_config_utils = types.ModuleType('arm.config.config_utils')
_config_utils.arm_yaml_check_groups = MagicMock(return_value='')
_config_utils.arm_yaml_test_bool = MagicMock(return_value='')

sys.modules['arm.config'] = _config_pkg
sys.modules['arm.config.config'] = _config_mod
sys.modules['arm.config.config_utils'] = _config_utils
