"""Tests for Job model properties and path builders (Phase 2)."""
import os
import uuid


class TestFormattedTitle:
    def test_title_with_year(self, sample_job):
        assert sample_job.formatted_title == "SERIAL_MOM (1994)"

    def test_title_without_year(self, sample_job):
        sample_job.year = ""
        assert sample_job.formatted_title == "SERIAL_MOM"

    def test_manual_title_preferred(self, sample_job):
        sample_job.title_manual = "Serial Mom"
        assert sample_job.formatted_title == "Serial Mom (1994)"

    def test_year_zero_excluded(self, sample_job):
        sample_job.year = "0000"
        assert sample_job.formatted_title == "SERIAL_MOM"

    def test_year_none_excluded(self, sample_job):
        sample_job.year = None
        assert sample_job.formatted_title == "SERIAL_MOM"


class TestTypeSubfolder:
    def test_movie(self, sample_job):
        assert sample_job.type_subfolder == "movies"

    def test_series(self, sample_job):
        sample_job.video_type = "series"
        assert sample_job.type_subfolder == "tv"

    def test_music(self, sample_job):
        sample_job.video_type = "music"
        assert sample_job.type_subfolder == "music"

    def test_unknown_video_disc_lands_in_unidentified(self, sample_job):
        """An unidentified DVD/Blu-ray/UHD routes to UNIDENTIFIED_SUBDIR.
        The operator picks up the rip from the triage bucket, fills in
        metadata, and re-imports; presuming 'movie' on the wire
        misrouted series box-sets and hid misclassification under the
        Movies tree."""
        sample_job.video_type = "unknown"
        sample_job.disctype = "bluray"
        assert sample_job.type_subfolder == "unidentified"

    def test_unknown_dvd_lands_in_unidentified(self, sample_job):
        sample_job.video_type = "unknown"
        sample_job.disctype = "dvd"
        assert sample_job.type_subfolder == "unidentified"

    def test_unknown_uhd_lands_in_unidentified(self, sample_job):
        sample_job.video_type = "unknown"
        sample_job.disctype = "uhd"
        assert sample_job.type_subfolder == "unidentified"

    def test_unknown_data_disc_stays_unidentified(self, sample_job):
        sample_job.video_type = "unknown"
        sample_job.disctype = "data"
        assert sample_job.type_subfolder == "unidentified"

    def test_unknown_blank_disctype_stays_unidentified(self, sample_job):
        sample_job.video_type = "unknown"
        sample_job.disctype = ""
        assert sample_job.type_subfolder == "unidentified"


class TestBuildPaths:
    def test_build_raw_path_uses_guid(self, sample_job):
        """Raw path uses job GUID, not title."""
        expected = f"/home/arm/media/raw/{sample_job.guid}"
        assert sample_job.build_raw_path() == expected

    def test_build_raw_path_independent_of_title(self, sample_job):
        """Changing title does not affect raw path."""
        path_before = sample_job.build_raw_path()
        sample_job.title = "Something Else"
        sample_job.title_auto = "Something Else"
        assert sample_job.build_raw_path() == path_before

    def test_build_raw_path_independent_of_manual_title(self, sample_job):
        """Manual title correction does not affect raw path."""
        path_before = sample_job.build_raw_path()
        sample_job.title_manual = "Serial Mom"
        assert sample_job.build_raw_path() == path_before

    def test_build_transcode_path(self, sample_job):
        assert sample_job.build_transcode_path() == "/home/arm/media/transcode/movies/SERIAL_MOM (1994)"

    def test_build_final_path(self, sample_job):
        assert sample_job.build_final_path() == "/home/arm/media/completed/movies/SERIAL_MOM (1994)"

    def test_build_paths_with_manual_title(self, sample_job):
        sample_job.title_manual = "Serial Mom"
        # raw_path uses GUID (independent of title)
        assert sample_job.build_raw_path() == f"/home/arm/media/raw/{sample_job.guid}"
        # transcode and final use formatted_title (prefers manual)
        assert sample_job.build_transcode_path() == "/home/arm/media/transcode/movies/Serial Mom (1994)"
        assert sample_job.build_final_path() == "/home/arm/media/completed/movies/Serial Mom (1994)"

    def test_build_paths_series(self, sample_job):
        sample_job.video_type = "series"
        assert sample_job.build_transcode_path() == "/home/arm/media/transcode/tv/SERIAL_MOM (1994)"
        assert sample_job.build_final_path() == "/home/arm/media/completed/tv/SERIAL_MOM (1994)"


class TestPatternEngineIntegration:
    """Test that structured fields activate the naming pattern engine."""

    # --- Music ---

    def test_music_formatted_title_uses_pattern(self, sample_job):
        """With artist+album set, formatted_title uses the music title pattern."""
        from arm_contracts import MediaMetadata
        sample_job.video_type = "music"
        sample_job.set_metadata_auto(MediaMetadata(artist="The Beatles", album="Abbey Road"))
        sample_job.year = "1969"
        assert sample_job.formatted_title == "The Beatles - Abbey Road"

    def test_music_folder_path_uses_pattern(self, sample_job):
        """With artist+album set, build_final_path uses the music folder pattern."""
        from arm_contracts import MediaMetadata
        sample_job.video_type = "music"
        sample_job.set_metadata_auto(MediaMetadata(artist="The Beatles", album="Abbey Road"))
        sample_job.year = "1969"
        path = sample_job.build_final_path()
        assert path == os.path.join(
            "/home/arm/media/completed", "music",
            "The Beatles", "Abbey Road (1969)"
        )

    def test_music_transcode_path_uses_pattern(self, sample_job):
        from arm_contracts import MediaMetadata
        sample_job.video_type = "music"
        sample_job.set_metadata_auto(MediaMetadata(artist="Pink Floyd", album="The Wall"))
        sample_job.year = "1979"
        path = sample_job.build_transcode_path()
        assert path == os.path.join(
            "/home/arm/media/transcode", "music",
            "Pink Floyd", "The Wall (1979)"
        )

    def test_music_manual_artist_preferred(self, sample_job):
        """Manual artist overrides auto-detected artist."""
        from arm_contracts import MediaMetadata
        sample_job.video_type = "music"
        sample_job.set_metadata_auto(MediaMetadata(artist="beatles", album="Help"))
        sample_job.set_metadata_manual(MediaMetadata(artist="The Beatles"))
        assert sample_job.formatted_title == "The Beatles - Help"

    def test_music_falls_back_without_structured_fields(self, sample_job):
        """Without artist/album, music falls back to Title (Year)."""
        sample_job.video_type = "music"
        sample_job.title = "Pink Floyd The Dark Side of the Moon"
        sample_job.year = "1973"
        assert sample_job.formatted_title == "Pink Floyd The Dark Side of the Moon (1973)"

    # --- Series ---

    def test_series_formatted_title_uses_pattern(self, sample_job):
        """With season+episode set, formatted_title uses the TV title pattern."""
        sample_job.video_type = "series"
        sample_job.title = "Breaking Bad"
        sample_job.season = "1"
        sample_job.episode = "3"
        assert sample_job.formatted_title == "Breaking Bad S01E03"

    def test_series_folder_path_uses_pattern(self, sample_job):
        """With season set, build_final_path uses the TV folder pattern."""
        sample_job.video_type = "series"
        sample_job.title = "Breaking Bad"
        sample_job.season = "2"
        path = sample_job.build_final_path()
        assert path == os.path.join(
            "/home/arm/media/completed", "tv",
            "Breaking Bad", "Season 02"
        )

    def test_series_falls_back_without_season(self, sample_job):
        """Without season/episode, series falls back to Title (Year)."""
        sample_job.video_type = "series"
        sample_job.title = "SERIAL_MOM"
        sample_job.year = "1994"
        assert sample_job.formatted_title == "SERIAL_MOM (1994)"

    def test_series_manual_season_preferred(self, sample_job):
        """Manual season overrides auto-detected season."""
        sample_job.video_type = "series"
        sample_job.title = "Lost"
        sample_job.season = "1"
        sample_job.season_manual = "3"
        sample_job.episode = "5"
        assert sample_job.formatted_title == "Lost S03E05"

    # --- Movies always use pattern (just need title) ---

    def test_movie_still_uses_pattern(self, sample_job):
        """Movies use the pattern engine (default pattern matches old behavior)."""
        sample_job.video_type = "movie"
        sample_job.title = "Inception"
        sample_job.year = "2010"
        assert sample_job.formatted_title == "Inception (2010)"

    # --- Raw path never uses pattern ---

    def test_raw_path_unaffected_by_structured_fields(self, sample_job):
        """build_raw_path always uses GUID, never the pattern engine."""
        from arm_contracts import MediaMetadata
        sample_job.video_type = "music"
        sample_job.set_metadata_auto(MediaMetadata(
            artist="The Beatles",
            album="Abbey Road",
        ))
        sample_job.title_auto = "Beatles Abbey Road"
        assert sample_job.build_raw_path() == f"/home/arm/media/raw/{sample_job.guid}"


class TestStructuredFieldColumns:
    """Test the surviving structured columns (season/episode).

    artist/album/poster_url columns were retired by the
    media_metadata_columns migration; their replacements live in the
    media_metadata JSON blob and are covered by test_job_media_metadata.py.
    """

    def test_season_episode_columns_persist(self, sample_job, app_context):
        from arm.database import db
        sample_job.season = "3"
        sample_job.season_auto = "3"
        sample_job.episode = "12"
        sample_job.episode_auto = "12"
        sample_job.episode_manual = "13"
        db.session.commit()
        db.session.refresh(sample_job)
        assert sample_job.season == "3"
        assert sample_job.episode == "12"
        assert sample_job.episode_manual == "13"

    def test_columns_nullable(self, sample_job, app_context):
        """Surviving structured fields default to None."""
        from arm.database import db
        db.session.refresh(sample_job)
        assert sample_job.season is None
        assert sample_job.episode is None


class TestJobGuid:
    def test_new_job_has_guid(self, sample_job):
        """Every job gets a UUID4 guid at creation."""
        assert sample_job.guid is not None
        parsed = uuid.UUID(sample_job.guid)
        assert parsed.version == 4

    def test_guid_is_unique_per_job(self, app_context):
        """Two jobs get different GUIDs."""
        from arm.models.job import Job
        import unittest.mock
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job1 = Job('/dev/sr0')
            job2 = Job('/dev/sr1')
        assert job1.guid != job2.guid

    def test_folder_job_has_guid(self, app_context, tmp_path):
        """Folder-import jobs also get GUIDs."""
        from arm.models.job import Job
        job = Job.from_folder(str(tmp_path / "test"), 'dvd')
        assert job.guid is not None
        parsed = uuid.UUID(job.guid)
        assert parsed.version == 4


class TestTypeSubfolderConfigurable:
    """type_subfolder reads MOVIES_SUBDIR/TV_SUBDIR/AUDIO_SUBDIR/UNIDENTIFIED_SUBDIR
    from arm.yaml and falls back to legacy defaults when unset.

    These tests monkeypatch cfg.arm_config to override individual keys; the
    monkeypatch fixture reverses the change at teardown so other tests are
    unaffected.
    """

    def test_movies_custom(self, sample_job, monkeypatch):
        import arm.config.config as cfg
        monkeypatch.setitem(cfg.arm_config, "MOVIES_SUBDIR", "Movies/0.Rips")
        sample_job.video_type = "movie"
        assert sample_job.type_subfolder == "Movies/0.Rips"

    def test_tv_custom(self, sample_job, monkeypatch):
        import arm.config.config as cfg
        monkeypatch.setitem(cfg.arm_config, "TV_SUBDIR", "TV/0.Rips")
        sample_job.video_type = "series"
        assert sample_job.type_subfolder == "TV/0.Rips"

    def test_audio_custom(self, sample_job, monkeypatch):
        import arm.config.config as cfg
        monkeypatch.setitem(cfg.arm_config, "AUDIO_SUBDIR", "Music/0.Rips")
        sample_job.video_type = "music"
        assert sample_job.type_subfolder == "Music/0.Rips"

    def test_unidentified_custom(self, sample_job, monkeypatch):
        """Truly-unidentifiable rips (no video disctype) honor UNIDENTIFIED_SUBDIR."""
        import arm.config.config as cfg
        monkeypatch.setitem(cfg.arm_config, "UNIDENTIFIED_SUBDIR", "0.Inbox")
        sample_job.video_type = "unknown"
        sample_job.disctype = "data"  # not dvd/bluray/uhd
        assert sample_job.type_subfolder == "0.Inbox"

    def test_build_final_path_uses_custom_movies_subdir(self, sample_job, monkeypatch):
        import arm.config.config as cfg
        monkeypatch.setitem(cfg.arm_config, "MOVIES_SUBDIR", "Movies/0.Rips")
        sample_job.video_type = "movie"
        # sample_job already has title="SERIAL_MOM", year="1994" from the fixture.
        # Path prefix matches the existing TestBuildPaths assertions (the
        # sample_job fixture patches sample_job.config.COMPLETED_PATH to
        # "/home/arm/media/completed", overriding test_arm.yaml).
        assert sample_job.build_final_path() == \
            "/home/arm/media/completed/Movies/0.Rips/SERIAL_MOM (1994)"

    def test_build_transcode_path_uses_custom_tv_subdir(self, sample_job, monkeypatch):
        import arm.config.config as cfg
        monkeypatch.setitem(cfg.arm_config, "TV_SUBDIR", "TV/0.Rips")
        sample_job.video_type = "series"
        assert sample_job.build_transcode_path() == \
            "/home/arm/media/transcode/TV/0.Rips/SERIAL_MOM (1994)"
