"""Tests for arm/services/progress_reader.py - MakeMKV + abcde progress."""
import unittest.mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from arm.services import progress_reader


@pytest.fixture
def progress_dir(tmp_path):
    log_dir = tmp_path / "logs"
    (log_dir / "progress").mkdir(parents=True)
    with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(log_dir)}):
        yield log_dir


class TestRipProgress:
    def test_no_file_returns_none(self, progress_dir):
        result = progress_reader.get_rip_progress(99)
        assert result == {"progress": None, "stage": None, "tracks_ripped": None}

    def test_prgv_during_save_phase(self, progress_dir):
        # Fractional percentage on purpose: real MakeMKV PRGV values rarely land
        # on whole-number percentages, and pydantic int silently coerces 75.0 to
        # 75 while rejecting 33.3 - using a clean number here would have masked
        # the rip_progress int/float contract bug fixed in arm-contracts 67eba7b.
        (progress_dir / "progress" / "1.log").write_text(
            'PRGT:0,0,"Saving to MKV file"\n'
            "PRGV:3333,3333,10000\n"
        )
        result = progress_reader.get_rip_progress(1)
        assert result["progress"] == pytest.approx(33.3)

    def test_prgc_advances_stage_and_tracks(self, progress_dir):
        (progress_dir / "progress" / "2.log").write_text(
            'PRGC:0,2,"Saving to MKV file"\n'
            "PRGV:1000,2000,10000\n"
        )
        result = progress_reader.get_rip_progress(2)
        assert result["stage"] == "Title 3: Saving to MKV file"
        assert result["tracks_ripped"] == 2

    def test_zero_max_skipped(self, progress_dir):
        (progress_dir / "progress" / "3.log").write_text("PRGV:0,0,0\n")
        result = progress_reader.get_rip_progress(3)
        assert result["progress"] is None

    def test_progress_held_when_prgt_transitions_between_titles(self, progress_dir):
        """Folder rips: MakeMKV emits non-'Saving' PRGT between titles while
        PRGC stays on 'Saving to MKV file'. Progress must not go null during
        those windows or the UI flickers to an indeterminate slider.
        """
        (progress_dir / "progress" / "5.log").write_text(
            'PRGT:0,0,"Saving all titles to MKV files"\n'
            'PRGC:0,1,"Saving to MKV file"\n'
            "PRGV:0,640,10000\n"
            'PRGT:0,0,"Analyzing seamless segments"\n'
        )
        result = progress_reader.get_rip_progress(5)
        # Fractional (6.4%) on purpose - exercises the int/float contract path.
        assert result["progress"] == pytest.approx(6.4)

    def test_progress_held_when_prgc_is_saving_without_saving_prgt(self, progress_dir):
        """PRGC alone is enough to identify the rip phase; PRGT can lag."""
        (progress_dir / "progress" / "6.log").write_text(
            'PRGT:0,0,"Processing AV clips"\n'
            'PRGC:0,2,"Saving to MKV file"\n'
            "PRGV:0,128,10000\n"
        )
        result = progress_reader.get_rip_progress(6)
        # Fractional (1.3%) on purpose - exercises the int/float contract path.
        assert result["progress"] == pytest.approx(1.3)

    def test_oserror_on_open_returns_default(self, progress_dir, monkeypatch):
        target = progress_dir / "progress" / "4.log"
        target.write_text("PRGV:1,1,2\n")

        import builtins
        real_open = builtins.open

        def boom(path, *a, **kw):
            if str(path).endswith("4.log"):
                raise OSError("nope")
            return real_open(path, *a, **kw)

        monkeypatch.setattr(builtins, "open", boom)
        result = progress_reader.get_rip_progress(4)
        assert result == {"progress": None, "stage": None, "tracks_ripped": None}

    def test_traversal_returns_none(self, progress_dir):
        # _safe_log_path coerces to None for paths escaping LOGPATH
        result = progress_reader._safe_log_path("..", "..", "etc", "passwd")
        assert result is None


class TestMusicProgress:
    def test_no_logfile(self, progress_dir):
        result = progress_reader.get_music_progress(None, 10)
        assert result["progress"] is None
        assert result["stage"] is None

    def test_missing_file(self, progress_dir):
        result = progress_reader.get_music_progress("nonexistent.log", 10)
        assert result["progress"] is None

    def test_parses_abcde_phases(self, progress_dir):
        # 2 of 7 tracks = ~28.57% - fractional on purpose so we exercise the
        # int-vs-float contract path on music_progress (same trap as
        # rip_progress, see arm-contracts 67eba7b).
        (progress_dir / "music.log").write_text(
            "Grabbing track 1: foo\n"
            "Grabbing track 2: bar\n"
            "Encoding track 1 of 7\n"
            "Encoding track 2 of 7\n"
            "Tagging track 1 of 7\n"
        )
        result = progress_reader.get_music_progress("music.log", 7)
        assert result["tracks_total"] == 7
        assert result["tracks_ripped"] == 2  # encoding count
        assert result["progress"] == pytest.approx(28.6)
        assert "tagging track 2" in result["stage"]

    def test_empty_log_returns_default(self, progress_dir):
        (progress_dir / "music.log").write_text("nothing here\n")
        result = progress_reader.get_music_progress("music.log", 5)
        assert result["progress"] is None

    def test_falls_back_to_seen_count_when_total_zero(self, progress_dir):
        (progress_dir / "music.log").write_text("Grabbing track 1: foo\n")
        result = progress_reader.get_music_progress("music.log", 0)
        assert result["tracks_total"] == 1

    def test_grabbing_only_is_ripping_phase(self, progress_dir):
        """Only Grabbing seen (no Encoding/Tagging yet) -> phase is 'ripping'."""
        (progress_dir / "music.log").write_text("Grabbing track 1: foo\n")
        result = progress_reader.get_music_progress("music.log", 5)
        assert "ripping track 1" in result["stage"]

    def test_encoding_without_tagging_is_encoding_phase(self, progress_dir):
        """Encoding seen but no Tagging yet -> phase is 'encoding'."""
        (progress_dir / "music.log").write_text(
            "Grabbing track 1: foo\n"
            "Encoding track 1 of 5\n"
        )
        result = progress_reader.get_music_progress("music.log", 5)
        assert "encoding track 1" in result["stage"]

    def test_oserror_on_open_returns_default(self, progress_dir, monkeypatch):
        target = progress_dir / "music.log"
        target.write_text("Grabbing track 1: foo\n")

        import builtins
        real_open = builtins.open

        def boom(path, *a, **kw):
            if "music.log" in str(path):
                raise OSError("nope")
            return real_open(path, *a, **kw)

        monkeypatch.setattr(builtins, "open", boom)
        result = progress_reader.get_music_progress("music.log", 5)
        assert result["progress"] is None


class TestProgressStateEndpoint:
    @pytest.fixture
    def jobs_client(self, progress_dir, app_context):
        from arm.api.v1.jobs import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as c:
            yield c, progress_dir

    def test_endpoint_includes_realtime_keys(self, jobs_client, sample_job):
        client, log_dir = jobs_client
        # Fractional percentage (12.3%) on purpose: real MakeMKV PRGV values
        # rarely produce whole-number percentages. Using clean values like
        # 50.0 here masked the rip_progress int-vs-float contract bug fixed
        # in arm-contracts 67eba7b - pydantic int silently coerces 50.0 to 50
        # but rejects 12.3 with int_from_float, which tanked /progress-state
        # in production once the parser produced fractional values.
        (log_dir / "progress" / f"{sample_job.job_id}.log").write_text(
            'PRGT:0,0,"Saving to MKV file"\n'
            "PRGV:0,1230,10000\n"
        )
        resp = client.get(f"/api/v1/jobs/{sample_job.job_id}/progress-state")
        assert resp.status_code == 200
        body = resp.json()
        assert body["rip_progress"] == pytest.approx(12.3)
        assert body["rip_stage"] is None  # no PRGC, name was "Saving"
        # Pre-existing keys still present
        assert body["disctype"] == "bluray"
        assert body["logfile"] == "test.log"
        assert "track_counts" in body
        # Music keys present (None for video disc)
        assert body["music_progress"] is None

    def test_endpoint_with_no_progress_file(self, jobs_client, sample_job):
        client, _ = jobs_client
        resp = client.get(f"/api/v1/jobs/{sample_job.job_id}/progress-state")
        assert resp.status_code == 200
        body = resp.json()
        assert body["rip_progress"] is None
        assert body["tracks_ripped_realtime"] is None
        assert body["music_progress"] is None

    def test_missing_job_404(self, jobs_client):
        client, _ = jobs_client
        resp = client.get("/api/v1/jobs/99999/progress-state")
        assert resp.status_code == 404
