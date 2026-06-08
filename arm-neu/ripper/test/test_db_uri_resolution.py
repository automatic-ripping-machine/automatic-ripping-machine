"""Tests for arm.config.config.get_db_uri() DSN selection."""
import os
import unittest.mock


def test_get_db_uri_returns_sqlite_default_when_no_overrides():
    """With no env var and no arm.yaml DATABASE_URL key, returns
    sqlite:///<DBFILE> for backwards compatibility."""
    import arm.config.config as cfg
    # Ensure no env override
    with unittest.mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop('ARM_DATABASE_URL', None)
        # Snapshot+restore arm_config so this test doesn't pollute siblings
        original = cfg.arm_config.get('DATABASE_URL')
        cfg.arm_config.pop('DATABASE_URL', None)
        try:
            uri = cfg.get_db_uri()
        finally:
            if original is not None:
                cfg.arm_config['DATABASE_URL'] = original
    assert uri == 'sqlite:///' + cfg.arm_config['DBFILE']


def test_get_db_uri_uses_arm_yaml_key_when_set():
    """A DATABASE_URL key in arm.yaml takes precedence over the sqlite default."""
    import arm.config.config as cfg
    with unittest.mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop('ARM_DATABASE_URL', None)
        original = cfg.arm_config.get('DATABASE_URL')
        cfg.arm_config['DATABASE_URL'] = 'postgresql+psycopg://yaml:yaml@yamlhost/yamldb'
        try:
            uri = cfg.get_db_uri()
        finally:
            if original is None:
                cfg.arm_config.pop('DATABASE_URL', None)
            else:
                cfg.arm_config['DATABASE_URL'] = original
    assert uri == 'postgresql+psycopg://yaml:yaml@yamlhost/yamldb'


def test_get_db_uri_env_var_wins_over_arm_yaml():
    """ARM_DATABASE_URL env var beats arm.yaml DATABASE_URL key."""
    import arm.config.config as cfg
    original = cfg.arm_config.get('DATABASE_URL')
    cfg.arm_config['DATABASE_URL'] = 'postgresql+psycopg://yaml:yaml@yamlhost/yamldb'
    try:
        with unittest.mock.patch.dict(
            os.environ,
            {'ARM_DATABASE_URL': 'postgresql+psycopg://env:env@envhost/envdb'},
        ):
            uri = cfg.get_db_uri()
    finally:
        if original is None:
            cfg.arm_config.pop('DATABASE_URL', None)
        else:
            cfg.arm_config['DATABASE_URL'] = original
    assert uri == 'postgresql+psycopg://env:env@envhost/envdb'


def test_get_db_uri_empty_string_overrides_treated_as_unset():
    """Empty string env var or empty arm.yaml value should not be honored
    (avoids the foot-gun where someone unsets via empty string and gets
    a malformed sqlite URI)."""
    import arm.config.config as cfg
    original = cfg.arm_config.get('DATABASE_URL')
    cfg.arm_config['DATABASE_URL'] = ''  # explicitly empty
    try:
        with unittest.mock.patch.dict(os.environ, {'ARM_DATABASE_URL': ''}):
            uri = cfg.get_db_uri()
    finally:
        if original is None:
            cfg.arm_config.pop('DATABASE_URL', None)
        else:
            cfg.arm_config['DATABASE_URL'] = original
    assert uri == 'sqlite:///' + cfg.arm_config['DBFILE']
