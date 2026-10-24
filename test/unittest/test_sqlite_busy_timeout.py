"""SQLite locking between the ripper processes and the UI (#500, #1840)"""
import sqlite3

import pytest
from sqlalchemy import event, text

from arm.ui import app, db
import arm.ui.utils as ui_utils
import arm.ripper.utils as ripper_utils
from arm.models.track import Track


@pytest.fixture
def app_db():
    with app.app_context():
        db.create_all()
        db.engine.dispose()
        yield db
        db.session.rollback()
        db.engine.dispose()


@pytest.fixture
def short_busy_timeout(app_db):
    """Make a locked write fail after 50ms instead of 30s so the retry path runs quickly"""
    def set_timeout(dbapi_conn, *_):
        dbapi_conn.execute("PRAGMA busy_timeout = 50")
    event.listen(app_db.engine, "checkout", set_timeout)
    yield app_db
    event.remove(app_db.engine, "checkout", set_timeout)


@pytest.fixture
def lock_holder(app_db):
    """A second connection (another ARM process) holding the write lock until sleep() is called"""
    conn = sqlite3.connect(app_db.engine.url.database, isolation_level=None)
    sleeps = []

    def fake_sleep(_seconds):
        sleeps.append(_seconds)
        if conn.in_transaction:
            conn.execute("COMMIT")
    yield conn, sleeps, fake_sleep
    if conn.in_transaction:
        conn.execute("ROLLBACK")
    conn.close()


def make_track():
    return Track(1, "1", 100, "16:9", 24.0, False, "MakeMKV", "base", "file.mkv")


def stored_status(app_db, track_id):
    conn = sqlite3.connect(app_db.engine.url.database)
    try:
        return conn.execute("SELECT status FROM track WHERE track_id = ?", (track_id,)).fetchone()[0]
    finally:
        conn.close()


def test_engine_waits_30s_for_a_locked_database(app_db):
    assert app_db.session.execute(text("PRAGMA busy_timeout")).scalar() == 30000


@pytest.mark.parametrize("module", [ripper_utils, ui_utils], ids=["ripper", "ui"])
def test_database_updater_retries_after_locked_commit(short_busy_timeout, lock_holder, monkeypatch, module):
    track = make_track()
    db.session.add(track)
    db.session.commit()
    conn, sleeps, fake_sleep = lock_holder
    if module is ripper_utils:
        monkeypatch.setattr(ripper_utils.time, "sleep", fake_sleep)
    else:
        monkeypatch.setattr(ui_utils, "sleep", fake_sleep)
    conn.execute("BEGIN IMMEDIATE")

    assert module.database_updater({"status": "ripped"}, track, wait_time=3) is True
    assert len(sleeps) == 1
    assert stored_status(db, track.track_id) == "ripped"


def test_database_adder_retries_after_locked_commit(short_busy_timeout, lock_holder, monkeypatch):
    conn, sleeps, fake_sleep = lock_holder
    monkeypatch.setattr(ripper_utils.time, "sleep", fake_sleep)
    conn.execute("BEGIN IMMEDIATE")
    track = make_track()

    assert ripper_utils.database_adder(track) is True
    assert len(sleeps) == 1
    assert track.track_id is not None
