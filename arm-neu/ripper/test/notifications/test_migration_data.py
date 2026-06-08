"""Test the data-migration step: legacy Config row -> channel rows,
then legacy columns dropped."""
import os

import sqlalchemy as sa

from alembic import command
from alembic.config import Config as AlembicConfig


_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'arm', 'migrations',
)


def _make_config(db_path):
    cfg = AlembicConfig()
    cfg.set_main_option('script_location', _MIGRATIONS_DIR)
    cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')
    return cfg


def _seed_legacy_config(db_path: str):
    """Upgrade to the pre-data-migration head, then insert a legacy
    Config row with notification fields populated. job_id is the PK."""
    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        conn.execute(sa.text(
            "INSERT INTO job (job_id, title, status, guid) "
            "VALUES (1, 'seed-job', 'success', 'test-guid-0001')"
        ))
        conn.execute(sa.text(
            "INSERT INTO config (job_id, PB_KEY, IFTTT_KEY, IFTTT_EVENT, "
            "PO_USER_KEY, PO_APP_KEY, NOTIFY_RIP, NOTIFY_TRANSCODE) "
            "VALUES (1, 'pbtoken', 'iftkey', 'evt', 'po_u', 'po_a', 1, 1)"
        ))
        conn.commit()
    engine.dispose()


def test_data_migration_creates_channels_from_legacy_config(tmp_path):
    db_path = str(tmp_path / "test.db")
    cfg = _make_config(db_path)
    command.upgrade(cfg, "w8x9y0z1a2")
    _seed_legacy_config(db_path)
    command.upgrade(cfg, "x9y0z1a2b3")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT name, type FROM notification_channel")
        ).fetchall()
    engine.dispose()
    names = {r[0] for r in rows}
    assert "Pushbullet (migrated)" in names
    assert "IFTTT (migrated)" in names
    assert "Pushover (migrated)" in names


def test_data_migration_drops_legacy_columns(tmp_path):
    db_path = str(tmp_path / "test.db")
    cfg = _make_config(db_path)
    command.upgrade(cfg, "x9y0z1a2b3")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    insp = sa.inspect(engine)
    config_cols = {c["name"] for c in insp.get_columns("config")}
    # Dropped columns must not be present.
    for legacy in (
        "PB_KEY", "IFTTT_KEY", "IFTTT_EVENT",
        "PO_USER_KEY", "PO_APP_KEY",
        "NOTIFY_RIP", "NOTIFY_TRANSCODE",
    ):
        assert legacy not in config_cols, (
            f"legacy column {legacy!r} still present"
        )
    # Non-notification columns are intentionally kept.
    assert "ARM_CHECK_UDF" in config_cols
    engine.dispose()


def test_data_migration_idempotent_on_empty_config(tmp_path):
    """Running the migration on a fresh DB with no Config row is a no-op
    that doesn't crash."""
    db_path = str(tmp_path / "test.db")
    cfg = _make_config(db_path)
    command.upgrade(cfg, "x9y0z1a2b3")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        count = conn.execute(
            sa.text("SELECT COUNT(*) FROM notification_channel")
        ).scalar()
    engine.dispose()
    assert count == 0
