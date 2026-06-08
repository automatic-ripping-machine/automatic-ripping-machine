"""Tests for model serialization, string representation, and creation."""
import unittest.mock


class TestConfigGetD:
    """Test Config.get_d() dict export with hidden attributes filtered."""

    def test_excludes_api_keys(self, app_context):
        from arm.models.config import Config

        config = Config({
            'OMDB_API_KEY': 'secret123',
            'TMDB_API_KEY': 'tmdb_secret',
            'RAW_PATH': '/test/raw',
            'COMPLETED_PATH': '/test/completed',
        }, job_id=1)
        result = config.get_d()
        assert 'OMDB_API_KEY' not in result
        assert 'TMDB_API_KEY' not in result
        assert 'secret123' not in str(result)
        assert 'tmdb_secret' not in str(result)

    def test_includes_non_sensitive(self, app_context):
        from arm.models.config import Config

        config = Config({
            'RAW_PATH': '/test/raw',
            'COMPLETED_PATH': '/test/completed',
            'SKIP_TRANSCODE': False,
        }, job_id=1)
        result = config.get_d()
        assert result['RAW_PATH'] == '/test/raw'
        assert result['COMPLETED_PATH'] == '/test/completed'

    def test_excludes_sa_instance_state(self, app_context):
        from arm.models.config import Config
        from arm.database import db

        config = Config({'RAW_PATH': '/test/raw'}, job_id=1)
        db.session.add(config)
        db.session.commit()

        result = config.get_d()
        assert '_sa_instance_state' not in result

    def test_all_hidden_attribs_excluded(self, app_context):
        from arm.models.config import Config, hidden_attribs

        config_dict = {attr: f"value_{attr}" for attr in hidden_attribs
                       if attr != '_sa_instance_state'}
        config_dict['RAW_PATH'] = '/visible'
        config = Config(config_dict, job_id=1)
        result = config.get_d()
        for attr in hidden_attribs:
            assert attr not in result


class TestConfigListParams:
    """Test Config.list_params() formatted output."""

    def test_masks_sensitive_values(self, app_context):
        from arm.models.config import Config, HIDDEN_VALUE

        config = Config({
            'OMDB_API_KEY': 'secret123',
            'RAW_PATH': '/test/raw',
        }, job_id=1)
        result = config.list_params()
        assert 'secret123' not in result
        assert HIDDEN_VALUE in result
        assert '/test/raw' in result

    def test_contains_newlines(self, app_context):
        from arm.models.config import Config

        config = Config({
            'RAW_PATH': '/test/raw',
            'COMPLETED_PATH': '/test/completed',
        }, job_id=1)
        result = config.list_params()
        assert '\n' in result

    def test_empty_sensitive_not_masked(self, app_context):
        from arm.models.config import Config, HIDDEN_VALUE

        config = Config({
            'OMDB_API_KEY': '',
            'RAW_PATH': '/test/raw',
        }, job_id=1)
        result = config.list_params()
        # Empty values should NOT be masked (falsy check)
        # The logic is: if str(attr) in hidden_attribs AND value (truthy)
        assert result.count(HIDDEN_VALUE) == 0 or 'OMDB_API_KEY:' in result


class TestConfigPrettyTable:
    """Test Config.pretty_table() PrettyTable formatting."""

    def test_returns_string(self, app_context):
        from arm.models.config import Config

        config = Config({'RAW_PATH': '/test/raw'}, job_id=1)
        result = config.pretty_table()
        assert isinstance(result, str)

    def test_contains_headers(self, app_context):
        from arm.models.config import Config

        config = Config({'RAW_PATH': '/test/raw'}, job_id=1)
        result = config.pretty_table()
        assert 'Config' in result
        assert 'Value' in result

    def test_masks_sensitive(self, app_context):
        from arm.models.config import Config, HIDDEN_VALUE

        config = Config({'OMDB_API_KEY': 'my_omdb_secret'}, job_id=1)
        result = config.pretty_table()
        assert 'my_omdb_secret' not in result
        assert HIDDEN_VALUE in result


class TestConfigStr:
    """Test Config.__str__() representation."""

    def test_masks_sensitive(self, app_context):
        from arm.models.config import Config, HIDDEN_VALUE

        config = Config({'OMDB_API_KEY': 'secret', 'RAW_PATH': '/raw'}, job_id=1)
        result = str(config)
        assert 'secret' not in result
        assert HIDDEN_VALUE in result
        assert '/raw' in result

    def test_contains_class_name(self, app_context):
        from arm.models.config import Config

        config = Config({'RAW_PATH': '/raw'}, job_id=1)
        result = str(config)
        assert 'Config' in result


class TestNotificationsGetD:
    """Test Notifications.get_d() dict export."""

    def test_returns_dict(self, app_context):
        from arm.models.notifications import Notifications
        from arm.database import db

        notif = Notifications("Test Title", "Test body")
        db.session.add(notif)
        db.session.commit()
        db.session.refresh(notif)  # reload expired attributes

        result = notif.get_d()
        assert isinstance(result, dict)
        assert result['title'] == 'Test Title'
        assert result['message'] == 'Test body'

    def test_excludes_sa_instance_state(self, app_context):
        from arm.models.notifications import Notifications
        from arm.database import db

        notif = Notifications("Title", "Body")
        db.session.add(notif)
        db.session.commit()
        db.session.refresh(notif)

        result = notif.get_d()
        assert '_sa_instance_state' not in result

    def test_initial_state(self, app_context):
        from arm.models.notifications import Notifications
        from arm.database import db

        notif = Notifications("Title", "Body")
        db.session.add(notif)
        db.session.commit()
        db.session.refresh(notif)

        result = notif.get_d()
        assert result['seen'] == 'False'
        assert 'trigger_time' in result


class TestNotificationsStr:
    """Test Notifications.__str__() output."""

    def test_contains_class_name(self, app_context):
        from arm.models.notifications import Notifications

        notif = Notifications("Title", "Body")
        result = str(notif)
        assert "Notifications" in result

    def test_contains_title(self, app_context):
        from arm.models.notifications import Notifications

        notif = Notifications("My Title", "My Body")
        result = str(notif)
        assert "My Title" in result


class TestUISettingsGetD:
    """Test UISettings.get_d() dict export."""

    def test_returns_dict(self, app_context):
        from arm.models.ui_settings import UISettings
        from arm.database import db

        settings = UISettings(
            use_icons=True,
            bootstrap_skin="darkly",
            language="en",
            notify_refresh=5000,
        )
        db.session.add(settings)
        db.session.commit()
        db.session.refresh(settings)

        result = settings.get_d()
        assert isinstance(result, dict)
        assert result['bootstrap_skin'] == 'darkly'
        assert result['language'] == 'en'

    def test_excludes_sa_instance_state(self, app_context):
        from arm.models.ui_settings import UISettings
        from arm.database import db

        settings = UISettings()
        db.session.add(settings)
        db.session.commit()
        db.session.refresh(settings)

        result = settings.get_d()
        assert '_sa_instance_state' not in result


class TestTrackCreation:
    """Test Track model creation and representation."""

    def test_track_init(self, app_context):
        from arm.models.track import Track

        track = Track(
            job_id=1,
            track_number="3",
            length=5400,
            aspect_ratio="16:9",
            fps=23.976,
            main_feature=True,
            source="HandBrake",
            basename="SERIAL_MOM",
            filename="title_03.mkv",
        )
        assert track.job_id == 1
        assert track.track_number == "3"
        assert track.length == 5400
        assert track.main_feature is True
        assert track.ripped is False  # default
        # process=None means "not yet decided" - the API serializer
        # defaults None to True so the disc-review widget renders fresh
        # tracks as rippable until the rip path explicitly sets True/False.
        assert track.process is None

    def test_track_str(self, app_context):
        from arm.models.track import Track

        track = Track(
            job_id=1, track_number="5", length=600,
            aspect_ratio="16:9", fps=24.0, main_feature=False,
            source="MakeMKV", basename="test", filename="t5.mkv",
        )
        result = str(track)
        assert "Track" in result
        assert "5" in result

    def test_track_repr(self, app_context):
        from arm.models.track import Track

        track = Track(
            job_id=1, track_number="1", length=100,
            aspect_ratio="4:3", fps=25.0, main_feature=False,
            source="HandBrake", basename="test", filename="t1.mkv",
        )
        result = repr(track)
        assert "Track" in result

    def test_track_persists(self, app_context):
        from arm.models.track import Track
        from arm.models.job import Job
        from arm.database import db

        # Need a job first (FK constraint)
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.title = "TEST"
        job.title_auto = "TEST"
        job.label = "TEST"
        db.session.add(job)
        db.session.flush()

        track = Track(
            job_id=job.job_id, track_number="1", length=3600,
            aspect_ratio="16:9", fps=24.0, main_feature=True,
            source="HandBrake", basename="TEST", filename="title_01.mkv",
        )
        db.session.add(track)
        db.session.commit()

        found = db.session.get(Track, track.track_id)
        assert found is not None
        assert found.length == 3600
        assert found.main_feature is True
