"""Regression: music-rip failure paths must write a valid TrackStatus
member into ``Track.status``.

Background
----------
Before TrackStatus.failed existed, the abcde wrapper's ``TimeoutError``
and ``subprocess.CalledProcessError`` branches in ``utils.rip_music``
called a workaround helper (``_update_music_tracks_ripped_only``) that
only flipped ``ripped`` to False and left ``status`` at its prior value
(typically 'pending'). That was a deliberate workaround for the missing
TrackStatus member.

With ``TrackStatus.failed`` shipped in arm_contracts v2.0.0, the failure
branches now call ``_update_music_tracks(job, ripped=False,
status=TrackStatus.failed.value)`` directly. This test pins:

* both abcde failure modes (TimeoutError, CalledProcessError) finish
  cleanly (no raised LookupError, function returns False),
* per-track ``status`` is set to ``TrackStatus.failed.value``,
* ``ripped`` is False.
"""
import os
import tempfile
import unittest.mock

import pytest

import arm.config.config as cfg
from arm.database import db
from arm.models.job import Job
from arm.models.config import Config
from arm.models.track import Track
from arm.ripper import utils
from arm_contracts.enums import TrackStatus


# ---------------------------------------------------------------------------
# Local fixtures (mirrors test_music_rip.music_job to avoid cross-file coupling)
# ---------------------------------------------------------------------------

@pytest.fixture
def music_job(app_context):
    """Create a Job with disctype='music' and the minimal attributes needed
    to exercise utils.rip_music()."""
    _, _ = app_context

    with unittest.mock.patch.object(Job, 'parse_udev'), \
         unittest.mock.patch.object(Job, 'get_pid'):
        job = Job('/dev/sr0')

    job.arm_version = "test"
    job.crc_id = ""
    job.logfile = "music_cd.log"
    job.start_time = None
    job.stop_time = None
    job.job_length = ""
    job.status = 'audio_ripping'
    job.stage = "170750493000"
    job.no_of_titles = 0
    job.title = "DARK_SIDE"
    job.title_auto = "DARK_SIDE"
    job.title_manual = None
    job.year = ""
    job.year_auto = ""
    job.year_manual = None
    job.video_type = "unknown"
    job.video_type_auto = "unknown"
    job.video_type_manual = None
    job.imdb_id = ""
    job.imdb_id_auto = ""
    job.imdb_id_manual = None
    job.poster_url = ""
    job.poster_url_auto = ""
    job.poster_url_manual = None
    job.devpath = "/dev/sr0"
    job.mountpoint = "/mnt/dev/sr0"
    job.hasnicetitle = False
    job.errors = None
    job.disctype = "music"
    job.label = "DARK_SIDE"
    job.path = None
    job.raw_path = None
    job.transcode_path = None
    job.ejected = False
    job.updated = False
    job.pid = os.getpid()
    job.pid_hash = 0
    job.is_iso = False

    db.session.add(job)
    db.session.flush()

    config = Config({
        'RAW_PATH': '/home/arm/media/raw',
        'TRANSCODE_PATH': '/home/arm/media/transcode',
        'COMPLETED_PATH': '/home/arm/media/completed',
        'LOGPATH': tempfile.mkdtemp(prefix='arm_test_logs_'),
        'EXTRAS_SUB': 'extras',
        'MINLENGTH': '600',
        'MAXLENGTH': '99999',
        'MAINFEATURE': False,
        'RIPMETHOD': 'mkv',
        'NOTIFY_RIP': True,
        'NOTIFY_TRANSCODE': True,
        'WEBSERVER_PORT': 8080,
    }, job.job_id)

    db.session.add(config)
    db.session.commit()
    db.session.refresh(job)
    return job


def _seed_tracks(job, count=3):
    """Insert ``count`` Track rows for ``job``. Each row is left at the
    Track.__init__ default of status='pending', ripped=False."""
    tracks = []
    for i in range(1, count + 1):
        t = Track(
            job_id=job.job_id,
            track_number=str(i),
            length=180,
            aspect_ratio="n/a",
            fps=0.1,
            main_feature=False,
            source="MusicBrainz",
            basename=f"{i:02d} - Track {i}.flac",
            filename=f"{i:02d} - Track {i}.flac",
        )
        db.session.add(t)
        tracks.append(t)
    db.session.commit()
    return tracks


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------

class TestMusicFailureMarksTracksFailed:
    """The abcde failure branches MUST mark per-track status as
    ``TrackStatus.failed``. Prior to v2.0.0 of arm_contracts there was no
    failed member and the code routed through a ripped-only workaround;
    now the workaround is retired and the failed status is the source of
    truth at the track level."""

    def test_called_process_error_marks_tracks_failed(
        self, music_job, tmp_path
    ):
        """Non-zero abcde exit -> CalledProcessError branch -> calls
        ``_update_music_tracks(job, ripped=False, status='failed')``."""
        tracks = _seed_tracks(music_job)
        music_job.config.LOGPATH = str(tmp_path)
        logfile = "abcde_test.log"

        mock_proc = unittest.mock.MagicMock()
        mock_proc.poll.return_value = 1
        mock_proc.wait.return_value = 1
        mock_proc.returncode = 1
        mock_proc.stdout = iter([])

        with unittest.mock.patch.dict(cfg.arm_config, {
                'ABCDE_CONFIG_FILE': '/nonexistent',
            }), \
             unittest.mock.patch('subprocess.Popen', return_value=mock_proc), \
             unittest.mock.patch(
                 'arm.ripper.utils._update_music_tracks'
             ) as mock_with_status:
            result = utils.rip_music(music_job, logfile)

        assert result is False
        # The fixed code path now calls _update_music_tracks with the
        # generic failed status. Find at least one such call.
        failed_calls = [
            c for c in mock_with_status.call_args_list
            if c.kwargs.get('status') == TrackStatus.failed.value
            and c.kwargs.get('ripped') is False
        ]
        assert failed_calls, (
            f"Expected at least one _update_music_tracks call with "
            f"status='failed' and ripped=False, got: "
            f"{mock_with_status.call_args_list!r}"
        )
        # And NO call should pass a bare 'fail' (the JobState string,
        # which is not a TrackStatus member).
        for call in mock_with_status.call_args_list:
            assert call.kwargs.get('status') != 'fail', \
                f"_update_music_tracks called with bare 'fail': {call!r}"

    def test_timeout_error_marks_tracks_failed(
        self, music_job, tmp_path
    ):
        """abcde stall -> TimeoutError branch -> calls
        ``_update_music_tracks(job, ripped=False, status='failed')``."""
        tracks = _seed_tracks(music_job)
        music_job.config.LOGPATH = str(tmp_path)
        logfile = "abcde_test.log"

        mock_proc = unittest.mock.MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.returncode = None
        mock_proc.stdout = iter([])

        with unittest.mock.patch.dict(cfg.arm_config, {
                'ABCDE_CONFIG_FILE': '/nonexistent',
            }), \
             unittest.mock.patch('subprocess.Popen', return_value=mock_proc), \
             unittest.mock.patch(
                 'arm.ripper.utils._stream_abcde_output',
                 side_effect=TimeoutError("CD rip stalled - simulated"),
             ), \
             unittest.mock.patch(
                 'arm.ripper.utils._update_music_tracks'
             ) as mock_with_status:
            result = utils.rip_music(music_job, logfile)

        assert result is False
        failed_calls = [
            c for c in mock_with_status.call_args_list
            if c.kwargs.get('status') == TrackStatus.failed.value
            and c.kwargs.get('ripped') is False
        ]
        assert failed_calls, (
            f"Expected at least one _update_music_tracks call with "
            f"status='failed' and ripped=False, got: "
            f"{mock_with_status.call_args_list!r}"
        )
        for call in mock_with_status.call_args_list:
            assert call.kwargs.get('status') != 'fail', \
                f"_update_music_tracks called with bare 'fail': {call!r}"


class TestUpdateMusicTracksFailedStatus:
    """Direct unit test: _update_music_tracks with TrackStatus.failed
    actually persists to the DB without raising the LookupError that
    used to break the buggy ``status='fail'`` path before TrackStatus
    grew the failed member."""

    def test_helper_persists_failed_status(self, music_job):
        tracks = _seed_tracks(music_job, count=2)

        # Sanity: starting state is the constructor default.
        for t in tracks:
            assert t.status == TrackStatus.pending.value

        # Should set status='failed' and ripped=False on all tracks.
        utils._update_music_tracks(
            music_job, ripped=False, status=TrackStatus.failed.value,
        )

        for t in tracks:
            db.session.refresh(t)
            assert t.status == TrackStatus.failed.value
            assert t.ripped is False
