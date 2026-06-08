"""Tests for _apply_track_phases and _stream_abcde_output in arm.ripper.utils."""
import os
import tempfile
import unittest.mock

import pytest

from arm.ripper.utils import _apply_track_phases, _stream_abcde_output, put_track


class TestApplyTrackPhases:
    """Test _apply_track_phases() updates track status based on abcde phases."""

    def test_grabbing_sets_ripping(self, app_context, sample_job):
        from arm.database import db

        put_track(sample_job, 1, 180, 'n/a', 0.1, False, 'TOC', 'Track 1.flac')
        put_track(sample_job, 2, 200, 'n/a', 0.1, False, 'TOC', 'Track 2.flac')
        db.session.commit()

        _apply_track_phases(sample_job, grabbing={1}, encoding=set(), tagging=set())

        from arm.models.track import Track
        tracks = Track.query.filter_by(job_id=sample_job.job_id).order_by(Track.track_number).all()
        assert tracks[0].status == "ripping"
        assert tracks[1].status == "pending"  # not in grabbing set

    def test_encoding_sets_encoding_not_ripped(self, app_context, sample_job):
        """Encoding sets status but does NOT mark ripped — that only
        happens after tagging (the final step)."""
        from arm.database import db

        put_track(sample_job, 1, 180, 'n/a', 0.1, False, 'TOC', 'Track 1.flac')
        db.session.commit()

        _apply_track_phases(sample_job, grabbing={1}, encoding={1}, tagging=set())

        from arm.models.track import Track
        t = Track.query.filter_by(job_id=sample_job.job_id).first()
        assert t.status == "encoding"
        assert not t.ripped

    def test_tagging_sets_success(self, app_context, sample_job):
        from arm.database import db

        put_track(sample_job, 1, 180, 'n/a', 0.1, False, 'TOC', 'Track 1.flac')
        db.session.commit()

        _apply_track_phases(sample_job, grabbing={1}, encoding={1}, tagging={1})

        from arm.models.track import Track
        t = Track.query.filter_by(job_id=sample_job.job_id).first()
        assert t.status == "success"
        assert t.ripped is True

    def test_no_change_when_already_correct(self, app_context, sample_job):
        """If status already matches, no commit should happen."""
        from arm.database import db

        put_track(sample_job, 1, 180, 'n/a', 0.1, False, 'TOC', 'Track 1.flac')
        db.session.commit()

        # Set to success first
        _apply_track_phases(sample_job, grabbing={1}, encoding={1}, tagging={1})
        # Call again — no change needed
        with unittest.mock.patch.object(db.session, 'commit') as mock_commit:
            _apply_track_phases(sample_job, grabbing={1}, encoding={1}, tagging={1})
            mock_commit.assert_not_called()

    def test_invalid_track_number_skipped(self, app_context, sample_job):
        """Tracks with non-numeric track_number are silently skipped."""
        from arm.database import db
        from arm.models.track import Track

        t = Track(sample_job.job_id, 'abc', 180, 'n/a', 0.1, False, 'TOC', '', 'Track.flac')
        db.session.add(t)
        db.session.commit()

        # Should not raise
        _apply_track_phases(sample_job, grabbing={1}, encoding=set(), tagging=set())

    def test_db_error_rolls_back(self, app_context, sample_job):
        """DB errors are caught and rolled back."""
        from arm.database import db

        with unittest.mock.patch('arm.ripper.utils.Track.query') as mock_q:
            mock_q.filter_by.side_effect = Exception("DB error")
            _apply_track_phases(sample_job, grabbing={1}, encoding=set(), tagging=set())
            # Should not raise

    def test_multiple_tracks_mixed_phases(self, app_context, sample_job):
        from arm.database import db

        put_track(sample_job, 1, 180, 'n/a', 0.1, False, 'TOC', 'Track 1.flac')
        put_track(sample_job, 2, 200, 'n/a', 0.1, False, 'TOC', 'Track 2.flac')
        put_track(sample_job, 3, 220, 'n/a', 0.1, False, 'TOC', 'Track 3.flac')
        db.session.commit()

        _apply_track_phases(
            sample_job,
            grabbing={1, 2, 3},
            encoding={1, 2},
            tagging={1},
        )

        from arm.models.track import Track
        tracks = {
            int(t.track_number): t
            for t in Track.query.filter_by(job_id=sample_job.job_id).all()
        }
        assert tracks[1].status == "success"
        assert tracks[2].status == "encoding"
        assert tracks[3].status == "ripping"


class TestStreamAbcdeOutput:
    """Test _stream_abcde_output() reads stdout and updates tracks."""

    def test_parses_all_three_phases(self, app_context, sample_job):
        from arm.database import db

        put_track(sample_job, 1, 180, 'n/a', 0.1, False, 'TOC', 'Track 1.flac')
        db.session.commit()

        proc = unittest.mock.MagicMock()
        proc.stdout = iter([
            "Grabbing track 1: some info\n",
            "Encoding track 1 of 5\n",
            "Tagging track 1 of 5\n",
        ])

        errors = _stream_abcde_output(proc, sample_job)

        from arm.models.track import Track
        t = Track.query.filter_by(job_id=sample_job.job_id).first()
        assert t.status == "success"
        assert t.ripped is True
        assert errors == []

    def test_collects_error_lines(self, app_context, sample_job):
        proc = unittest.mock.MagicMock()
        proc.stdout = iter([
            "Starting rip\n",
            "[ERROR] Unable to read disc\n",
            "Finished\n",
        ])

        errors = _stream_abcde_output(proc, sample_job)
        assert len(errors) == 1
        assert "[ERROR] Unable to read disc" in errors[0]

    def test_empty_stdout(self, app_context, sample_job):
        """Empty stdout returns no errors."""
        proc = unittest.mock.MagicMock()
        proc.stdout = iter([])

        errors = _stream_abcde_output(proc, sample_job)
        assert errors == []


class TestPutTrackTitle:
    """Test that put_track() sets the title kwarg on the Track."""

    def test_title_kwarg_sets_track_title(self, app_context, sample_job):
        from arm.database import db
        from arm.models.track import Track

        put_track(sample_job, 1, 180, 'n/a', 0.1, False, 'MusicBrainz',
                  '01 - Speak to Me.flac', title='Speak to Me')
        db.session.commit()

        t = Track.query.filter_by(job_id=sample_job.job_id).first()
        assert t.title == 'Speak to Me'
        assert t.filename == '01 - Speak to Me.flac'

    def test_no_title_kwarg_leaves_none(self, app_context, sample_job):
        from arm.database import db
        from arm.models.track import Track

        put_track(sample_job, 1, 180, 'n/a', 0.1, False, 'TOC', 'Track 1.flac')
        db.session.commit()

        t = Track.query.filter_by(job_id=sample_job.job_id).first()
        assert t.title is None
