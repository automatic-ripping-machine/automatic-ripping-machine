"""Exercise the v7w8x9y0z1 migration end-to-end via alembic.

Seeds a job with imdb_id_auto set but an empty media_metadata_auto
column at the post-u6v7w8x9y0 schema (the legacy triples are already
dropped), patches the network adapter to return a fake legacy dict,
and confirms the migration writes the blob.
"""
import asyncio
import os
import unittest.mock

import pytest
import sqlalchemy as sa

from alembic import command
from alembic.config import Config as AlembicConfig


_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'arm', 'migrations',
)
_BEFORE = 'u6v7w8x9y0'
_AFTER = 'v7w8x9y0z1'


def _make_config(db_path):
    cfg = AlembicConfig()
    cfg.set_main_option('script_location', _MIGRATIONS_DIR)
    cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')
    return cfg


@pytest.fixture
def upgraded_db(tmp_path):
    """Upgrade to the schema right before the backfill migration."""
    db_path = tmp_path / 'test.db'
    cfg = _make_config(str(db_path))
    command.upgrade(cfg, _BEFORE)
    engine = sa.create_engine(f'sqlite:///{db_path}')
    yield cfg, engine
    engine.dispose()


def _insert(engine, job_id, imdb_id, blob=None):
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO job (job_id, status, disctype, imdb_id, imdb_id_auto, media_metadata_auto, guid) "
                "VALUES (:jid, 'success', 'dvd', :imdb, :imdb, :blob, :guid)"
            ),
            {"jid": job_id, "imdb": imdb_id, "blob": blob, "guid": f"g-{job_id}"},
        )


def _fetch_blob(engine, job_id):
    with engine.connect() as conn:
        return conn.execute(
            sa.text("SELECT media_metadata_auto FROM job WHERE job_id = :jid"),
            {"jid": job_id},
        ).scalar()


def test_backfill_writes_blob_for_imdb_only_rows(upgraded_db):
    cfg, engine = upgraded_db
    _insert(engine, 1, "tt7777")

    async def fake(imdb_id):
        return {"poster_url": f"https://api/{imdb_id}.jpg", "video_type": "movie"}

    with unittest.mock.patch("arm.services.metadata.get_details", side_effect=fake):
        command.upgrade(cfg, _AFTER)

    blob = _fetch_blob(engine, 1)
    assert blob is not None
    assert "https://api/tt7777.jpg" in blob


def test_backfill_leaves_existing_blob_untouched(upgraded_db):
    cfg, engine = upgraded_db
    _insert(engine, 2, "tt8888", blob='{"poster_url": "existing"}')

    with unittest.mock.patch("arm.services.metadata.get_details") as m:
        command.upgrade(cfg, _AFTER)
        m.assert_not_called()

    assert _fetch_blob(engine, 2) == '{"poster_url": "existing"}'


def test_backfill_fail_soft_on_network_error(upgraded_db):
    cfg, engine = upgraded_db
    _insert(engine, 3, "tt9999")

    async def boom(imdb_id):
        raise RuntimeError("network down")

    with unittest.mock.patch("arm.services.metadata.get_details", side_effect=boom):
        command.upgrade(cfg, _AFTER)

    assert _fetch_blob(engine, 3) is None  # row left as-is


def test_backfill_fail_soft_on_config_error(upgraded_db):
    cfg, engine = upgraded_db
    _insert(engine, 4, "tt1111")

    from arm.services.metadata import MetadataConfigError

    async def no_key(imdb_id):
        raise MetadataConfigError("no key configured")

    with unittest.mock.patch("arm.services.metadata.get_details", side_effect=no_key):
        command.upgrade(cfg, _AFTER)

    assert _fetch_blob(engine, 4) is None


def test_backfill_handles_empty_adapter_result(upgraded_db):
    cfg, engine = upgraded_db
    _insert(engine, 5, "tt2222")

    async def empty(imdb_id):
        return None

    with unittest.mock.patch("arm.services.metadata.get_details", side_effect=empty):
        command.upgrade(cfg, _AFTER)

    assert _fetch_blob(engine, 5) is None


def test_backfill_no_op_when_nothing_to_do(upgraded_db):
    cfg, engine = upgraded_db
    # No rows inserted - migration should run cleanly and call nothing.

    with unittest.mock.patch("arm.services.metadata.get_details") as m:
        command.upgrade(cfg, _AFTER)
        m.assert_not_called()
