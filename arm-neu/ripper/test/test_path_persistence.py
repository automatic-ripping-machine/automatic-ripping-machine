"""Tests for path persistence at computation sites (Phase 3)."""


class TestPathPersistence:
    def test_raw_path_persisted(self, app_context, sample_job):
        """After setting raw_path, it should be in the DB."""
        _, db = app_context
        from arm.ripper.utils import database_updater

        database_updater({'raw_path': '/home/arm/media/raw/SERIAL_MOM'}, sample_job)

        db.session.refresh(sample_job)
        assert sample_job.raw_path == '/home/arm/media/raw/SERIAL_MOM'

    def test_raw_path_unchanged_after_title_correction(self, app_context, sample_job):
        """After manual title correction, raw_path must retain original dir name."""
        _, db = app_context
        from arm.ripper.utils import database_updater

        # Set raw_path with auto-detected title
        database_updater({'raw_path': '/home/arm/media/raw/SERIAL_MOM'}, sample_job)

        # User corrects title
        database_updater({
            'title': 'Serial Mom',
            'title_manual': 'Serial Mom',
            'path': '/home/arm/media/completed/movies/Serial Mom (1994)'
        }, sample_job)

        db.session.refresh(sample_job)
        # raw_path still points to original auto-detected directory
        assert sample_job.raw_path == '/home/arm/media/raw/SERIAL_MOM'
        # but final path uses corrected title
        assert sample_job.path == '/home/arm/media/completed/movies/Serial Mom (1994)'

    def test_transcode_path_persisted(self, app_context, sample_job):
        _, db = app_context
        from arm.ripper.utils import database_updater

        database_updater(
            {'transcode_path': '/home/arm/media/transcode/movies/SERIAL_MOM (1994)'},
            sample_job,
        )

        db.session.refresh(sample_job)
        assert sample_job.transcode_path == '/home/arm/media/transcode/movies/SERIAL_MOM (1994)'

    def test_transcode_path_updated_on_skip_transcode(self, app_context, sample_job):
        """When SKIP_TRANSCODE swaps transcode_path to raw, DB should reflect it."""
        _, db = app_context
        from arm.ripper.utils import database_updater

        # Initial transcode path
        database_updater(
            {'transcode_path': '/home/arm/media/transcode/movies/SERIAL_MOM (1994)'},
            sample_job,
        )
        # SKIP_TRANSCODE swaps to raw path
        database_updater({'transcode_path': '/home/arm/media/raw/SERIAL_MOM'}, sample_job)

        db.session.refresh(sample_job)
        assert sample_job.transcode_path == '/home/arm/media/raw/SERIAL_MOM'

    def test_all_paths_persisted_together(self, app_context, sample_job):
        """Test persisting all three paths at once (as arm_ripper does)."""
        _, db = app_context
        from arm.ripper.utils import database_updater

        database_updater({
            'path': '/home/arm/media/completed/movies/SERIAL_MOM (1994)',
            'transcode_path': '/home/arm/media/transcode/movies/SERIAL_MOM (1994)',
        }, sample_job)

        database_updater({'raw_path': '/home/arm/media/raw/SERIAL_MOM'}, sample_job)

        db.session.refresh(sample_job)
        assert sample_job.path == '/home/arm/media/completed/movies/SERIAL_MOM (1994)'
        assert sample_job.transcode_path == '/home/arm/media/transcode/movies/SERIAL_MOM (1994)'
        assert sample_job.raw_path == '/home/arm/media/raw/SERIAL_MOM'
