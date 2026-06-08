"""Verify columns reject out-of-band values at the SQLAlchemy boundary."""
import unittest.mock
import pytest
from sqlalchemy.exc import StatementError


def _make_bare_job(devpath="/dev/sr0"):
    """Create a Job bypassing udev/PID lookup (mirrors sample_job fixture)."""
    from arm.models.job import Job
    with unittest.mock.patch.object(Job, 'parse_udev'), \
         unittest.mock.patch.object(Job, 'get_pid'):
        return Job(devpath)


def test_job_status_rejects_unknown_value(app_context):
    from arm.database import db
    job = _make_bare_job()
    job.status = "totally-not-a-state"
    db.session.add(job)
    with pytest.raises((StatementError, ValueError, LookupError)):
        db.session.flush()
    db.session.rollback()


def test_job_source_type_rejects_unknown(app_context):
    from arm.database import db
    job = _make_bare_job()
    job.status = "ready"
    job.source_type = "carrier-pigeon"
    db.session.add(job)
    with pytest.raises((StatementError, ValueError, LookupError)):
        db.session.flush()
    db.session.rollback()


def test_track_status_rejects_unknown(app_context):
    from arm.database import db
    from arm.models.track import Track
    job = _make_bare_job()
    job.status = "ready"
    db.session.add(job)
    db.session.flush()
    track = Track(
        job_id=job.job_id, track_number="1", length=0, aspect_ratio="",
        fps=0.0, main_feature=False, source="x", basename="b", filename="f",
    )
    track.status = "transcode_failed: this is the old prefix smell"
    db.session.add(track)
    with pytest.raises((StatementError, ValueError, LookupError)):
        db.session.flush()
    db.session.rollback()


def test_config_ripmethod_rejects_unknown(app_context):
    from arm.database import db
    from arm.models.config import Config
    c = Config({}, job_id=None)
    c.RIPMETHOD = "rsync"
    db.session.add(c)
    with pytest.raises((StatementError, ValueError, LookupError)):
        db.session.flush()
    db.session.rollback()


def test_config_ripmethod_accepts_backup_dvd(app_context):
    """Regression: backup_dvd was rejected by the API but accepted by the
    ripper before the enum extraction. Now both sides use the enum."""
    from arm.database import db
    from arm.models.config import Config
    c = Config({}, job_id=None)
    c.RIPMETHOD = "backup_dvd"
    db.session.add(c)
    db.session.flush()  # must not raise
    db.session.rollback()


def test_config_ripmethod_accepts_all_three(app_context):
    """All three RipMethod values must be persistable."""
    from arm.database import db
    from arm.models.config import Config
    for value in ("mkv", "backup", "backup_dvd"):
        c = Config({}, job_id=None)
        c.RIPMETHOD = value
        db.session.add(c)
        db.session.flush()  # must not raise
        db.session.rollback()


def test_track_skip_reason_rejects_unknown(app_context):
    from arm.database import db
    from arm.models.track import Track
    job = _make_bare_job()
    job.status = "ready"
    db.session.add(job)
    db.session.flush()
    track = Track(
        job_id=job.job_id, track_number="1", length=0, aspect_ratio="",
        fps=0.0, main_feature=False, source="x", basename="b", filename="f",
    )
    track.skip_reason = "obviously_not_a_reason"
    db.session.add(track)
    with pytest.raises((StatementError, ValueError, LookupError)):
        db.session.flush()
    db.session.rollback()


def test_track_skip_reason_accepts_below_main_feature(app_context):
    """below_main_feature is reserved in the SkipReason enum but has no
    arm-neu writer yet; make sure the column accepts it for forward
    compatibility."""
    from arm.database import db
    from arm.models.track import Track
    job = _make_bare_job()
    job.status = "ready"
    db.session.add(job)
    db.session.flush()
    track = Track(
        job_id=job.job_id, track_number="1", length=0, aspect_ratio="",
        fps=0.0, main_feature=False, source="x", basename="b", filename="f",
    )
    track.skip_reason = "below_main_feature"
    db.session.add(track)
    db.session.flush()  # must not raise
    db.session.rollback()
