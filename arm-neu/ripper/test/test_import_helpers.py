"""Tests for shared import helpers extracted from folder.py + iso.py.

Covers:
- arm.ripper.import_prescan.prescan_and_wait (background thread body)
- arm.ripper.import_prescan.auto_disable_short_tracks (track filter)
- arm.api.v1._import_helpers.apply_request_metadata_to_job (ORM populate)
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class TestApplyRequestMetadataToJob:
    """apply_request_metadata_to_job(job, req): populate optional fields."""

    def _req(self, **kwargs):
        defaults = dict(
            title="Movie",
            year=None,
            video_type="movie",
            imdb_id=None,
            poster_url=None,
            multi_title=False,
            season=None,
            disc_number=None,
            disc_total=None,
        )
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_applies_required_title_and_video_type(self):
        from arm.api.v1._import_helpers import apply_request_metadata_to_job

        job = MagicMock()
        req = self._req(title="Inception", video_type="movie")
        apply_request_metadata_to_job(job, req)

        assert job.title == "Inception"
        assert job.title_auto == "Inception"
        assert job.video_type == "movie"
        assert job.multi_title is False

    def test_applies_year_when_present(self):
        from arm.api.v1._import_helpers import apply_request_metadata_to_job

        job = MagicMock()
        req = self._req(year="2010")
        apply_request_metadata_to_job(job, req)

        assert job.year == "2010"
        assert job.year_auto == "2010"

    def test_skips_year_when_absent(self):
        from arm.api.v1._import_helpers import apply_request_metadata_to_job

        # Use real attribute to detect "not assigned"
        job = SimpleNamespace()
        req = self._req(year=None)
        apply_request_metadata_to_job(job, req)

        assert not hasattr(job, "year") or job.year is None
        assert not hasattr(job, "year_auto") or job.year_auto is None

    def test_applies_imdb_and_poster_when_present(self):
        from arm.api.v1._import_helpers import apply_request_metadata_to_job

        job = MagicMock()
        req = self._req(imdb_id="tt1375666", poster_url="https://x/p.jpg")
        apply_request_metadata_to_job(job, req)

        assert job.imdb_id == "tt1375666"
        # poster_url now goes through set_metadata_auto with a MediaMetadata.
        job.set_metadata_auto.assert_called_once()
        meta_arg = job.set_metadata_auto.call_args.args[0]
        assert meta_arg.poster_url == "https://x/p.jpg"

    def test_skips_imdb_and_poster_when_absent(self):
        from arm.api.v1._import_helpers import apply_request_metadata_to_job

        job = SimpleNamespace()
        req = self._req(imdb_id=None, poster_url=None)
        apply_request_metadata_to_job(job, req)

        # SimpleNamespace doesn't auto-create attrs, so a successful skip
        # leaves these unset (no AttributeError on hasattr).
        assert not hasattr(job, "imdb_id") or job.imdb_id is None
        # poster_url no longer flows through a job attribute - it goes
        # through set_metadata_auto, which isn't on a bare SimpleNamespace.
        assert not hasattr(job, "set_metadata_auto")

    def test_applies_season_disc_number_disc_total(self):
        from arm.api.v1._import_helpers import apply_request_metadata_to_job

        job = MagicMock()
        req = self._req(season=2, disc_number=3, disc_total=5)
        apply_request_metadata_to_job(job, req)

        assert job.season == "2"
        assert job.season_manual == "2"
        assert job.disc_number == 3
        assert job.disc_total == 5

    def test_skips_disc_fields_when_none(self):
        from arm.api.v1._import_helpers import apply_request_metadata_to_job

        job = SimpleNamespace()
        req = self._req(season=None, disc_number=None, disc_total=None)
        apply_request_metadata_to_job(job, req)

        assert not hasattr(job, "season")
        assert not hasattr(job, "disc_number")
        assert not hasattr(job, "disc_total")

    def test_applies_multi_title_true(self):
        from arm.api.v1._import_helpers import apply_request_metadata_to_job

        job = MagicMock()
        req = self._req(multi_title=True)
        apply_request_metadata_to_job(job, req)

        assert job.multi_title is True


class TestAutoDisableShortTracks:
    """auto_disable_short_tracks lives in arm.ripper.import_prescan."""

    def test_disables_tracks_below_minlength(self):
        from arm.ripper.import_prescan import auto_disable_short_tracks

        short = MagicMock(length=30, enabled=True, process=True)
        long_ = MagicMock(length=3000, enabled=True, process=True)
        job = MagicMock()
        job.tracks = [short, long_]

        count = auto_disable_short_tracks(job, minlength=120)

        assert count == 1
        assert short.enabled is False
        # process must also flip to False so kick_off_import_rip's
        # post-rip deselection filter discards the output file.
        assert short.process is False
        assert long_.enabled is True
        assert long_.process is True

    def test_skips_tracks_with_none_length(self):
        from arm.ripper.import_prescan import auto_disable_short_tracks

        unknown = MagicMock(length=None, enabled=True)
        job = MagicMock()
        job.tracks = [unknown]

        count = auto_disable_short_tracks(job, minlength=120)
        assert count == 0
        assert unknown.enabled is True


class TestPrescanAndWait:
    """prescan_and_wait runs the background thread body."""

    @patch("arm.ripper.import_prescan.db")
    @patch("arm.ripper.import_prescan.Job")
    def test_success_transitions_to_manual_paused(self, mock_job_cls, mock_db):
        from arm.ripper.import_prescan import prescan_and_wait

        mock_job = MagicMock()
        mock_job.job_id = 42
        track1 = MagicMock(length=3000, enabled=True)
        mock_job.tracks = [track1]
        mock_job_cls.query.get.return_value = mock_job

        with patch("arm.ripper.makemkv.prep_mkv") as mock_prep, \
             patch("arm.ripper.makemkv.prescan_track_info") as mock_prescan:
            prescan_and_wait(42)

        mock_prep.assert_called_once()
        mock_prescan.assert_called_once_with(mock_job)
        assert mock_job.status == "manual_paused"
        mock_db.session.commit.assert_called()
        mock_db.session.remove.assert_called_once()

    @patch("arm.ripper.import_prescan.db")
    @patch("arm.ripper.import_prescan.Job")
    def test_failure_still_transitions(self, mock_job_cls, mock_db):
        from arm.ripper.import_prescan import prescan_and_wait

        mock_job = MagicMock()
        mock_job.job_id = 7
        mock_job.errors = None
        mock_job_cls.query.get.return_value = mock_job

        with patch("arm.ripper.makemkv.prep_mkv"), \
             patch(
                 "arm.ripper.makemkv.prescan_track_info",
                 side_effect=RuntimeError("boom"),
             ):
            prescan_and_wait(7)

        assert mock_job.status == "manual_paused"
        assert "Prescan failed" in mock_job.errors
        assert "boom" in mock_job.errors
        mock_db.session.remove.assert_called_once()

    @patch("arm.ripper.import_prescan.db")
    @patch("arm.ripper.import_prescan.Job")
    def test_job_not_found_cleans_session(self, mock_job_cls, mock_db):
        from arm.ripper.import_prescan import prescan_and_wait

        mock_job_cls.query.get.return_value = None

        # Should not raise
        prescan_and_wait(123)

        mock_db.session.commit.assert_not_called()
        mock_db.session.remove.assert_called_once()
