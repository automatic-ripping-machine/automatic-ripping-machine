"""
ARM UI Test - Models

Model:
    Config

Tests:
    setup_test_data - Fixture for setting up test data
    test_create_config - Test creating a new Config record
    test_query_config - Test querying an existing Config record
"""
import pytest

from ui.ui_setup import db
from models.config import Config        # Model under test
from models.job import Job              # Required relational support


# Fixture to setup test data
@pytest.fixture
def setup_test_data(init_db):
    """ Fixture for setting up test data """
    # Create a sample Job record
    test_job = Job("/dev/sr0")
    db.session.add(test_job)
    db.session.commit()

    # Create sample Config data for testing
    arm_config = Config(
        {
            "ARM_CHECK_UDF": True,
            "GET_VIDEO_TITLE": False,
            "SKIP_TRANSCODE": True,
            "VIDEOTYPE": "Movie",
            "MINLENGTH": "120",
            "MAXLENGTH": "180",
            "WEBSERVER_IP": "192.168.1.100",
            "WEBSERVER_PORT": 5000,
            "UI_BASE_URL": "http://localhost:5000",
            "SET_MEDIA_PERMISSIONS": True,
            "CHMOD_VALUE": 644,
            "SET_MEDIA_OWNER": True,
            "CHOWN_USER": "user",
            "CHOWN_GROUP": "group",
            "RIPMETHOD": "MKV",
            "MKV_ARGS": "--preset=fast",
            "DELRAWFILES": False,
            "HASHEDKEYS": True,
            "HB_PRESET_DVD": "High Profile",
            "HB_PRESET_BD": "1080p30",
            "DEST_EXT": "mkv",
            "HANDBRAKE_CLI": "/usr/bin/HandBrakeCLI",
            "MAINFEATURE": True,
            "HB_ARGS_DVD": "--preset=DVD",
            "HB_ARGS_BD": "--preset=Blu-ray",
            "EMBY_REFRESH": False,
            "EMBY_SERVER": "emby.example.com",
            "EMBY_PORT": "8096",
            "EMBY_CLIENT": "Chrome",
            "EMBY_DEVICE": "PC",
            "EMBY_DEVICEID": "123456",
            "EMBY_USERNAME": "user",
            "EMBY_USERID": "7890",
            "EMBY_PASSWORD": "password",
            "EMBY_API_KEY": "api_key",
            "NOTIFY_RIP": True,
            "NOTIFY_TRANSCODE": False,
            "PB_KEY": "pushbullet_key",
            "IFTTT_KEY": "ifttt_key",
            "IFTTT_EVENT": "event",
            "PO_USER_KEY": "user_key",
            "PO_APP_KEY": "app_key",
            "OMDB_API_KEY": "omdb_key"
        }, test_job.job_id
    )

    db.session.add(arm_config)
    db.session.commit()

    yield  # Allow test execution to proceed

    # Clean up (rollback changes)
    db.session.rollback()


def test_create_config(setup_test_data):
    """ Test creating a new Config record """
    # Create a sample Job record
    test_job = Job("/dev/sr0")
    db.session.add(test_job)
    db.session.commit()

    new_config = Config({
        "ARM_CHECK_UDF": False,
        "GET_VIDEO_TITLE": True,
        "SKIP_TRANSCODE": False,
        "VIDEOTYPE": "TV Show",
        "MINLENGTH": "30",
        "MAXLENGTH": "60",
        "WEBSERVER_IP": "192.168.1.200",
        "WEBSERVER_PORT": 8080,
        "UI_BASE_URL": "http://localhost:8080",
        "SET_MEDIA_PERMISSIONS": False,
        "CHMOD_VALUE": 755,
        "SET_MEDIA_OWNER": False,
        "CHOWN_USER": "admin",
        "CHOWN_GROUP": "admin",
        "RIPMETHOD": "ISO",
        "MKV_ARGS": "--preset=medium",
        "DELRAWFILES": True,
        "HASHEDKEYS": False,
        "HB_PRESET_DVD": "Standard",
        "HB_PRESET_BD": "720p30",
        "DEST_EXT": "mp4",
        "HANDBRAKE_CLI": "/usr/bin/HandBrake",
        "MAINFEATURE": False,
        "HB_ARGS_DVD": "--preset=Low Quality",
        "HB_ARGS_BD": "--preset=720p",
        "EMBY_REFRESH": True,
        "EMBY_SERVER": "emby.test.com",
        "EMBY_PORT": "8090",
        "EMBY_CLIENT": "Firefox",
        "EMBY_DEVICE": "Laptop",
        "EMBY_DEVICEID": "987654",
        "EMBY_USERNAME": "test_user",
        "EMBY_USERID": "1234",
        "EMBY_PASSWORD": "test_password",
        "EMBY_API_KEY": "test_api_key",
        "NOTIFY_RIP": False,
        "NOTIFY_TRANSCODE": True,
        "PB_KEY": "test_pushbullet_key",
        "IFTTT_KEY": "test_ifttt_key",
        "IFTTT_EVENT": "test_event",
        "PO_USER_KEY": "test_user_key",
        "PO_APP_KEY": "test_app_key",
        "OMDB_API_KEY": "test_omdb_key"
    }, test_job.job_id)

    db.session.add(new_config)
    db.session.commit()

    # Ensure the record exists
    assert new_config.CONFIG_ID is not None


def test_query_config(setup_test_data):
    """ Test querying an existing Config record """
    arm_config = Config.query.first()

    # Ensure the record exists
    assert arm_config is not None

    # Assert each attribute value against values loaded in test_create_config
    assert arm_config.ARM_CHECK_UDF is True
    assert arm_config.GET_VIDEO_TITLE is False
    assert arm_config.SKIP_TRANSCODE is True
    assert arm_config.VIDEOTYPE == "Movie"
    assert arm_config.MINLENGTH == "120"
    assert arm_config.MAXLENGTH == "180"
    assert arm_config.WEBSERVER_IP == "192.168.1.100"
    assert arm_config.WEBSERVER_PORT == 5000
    assert arm_config.UI_BASE_URL == "http://localhost:5000"
    assert arm_config.SET_MEDIA_PERMISSIONS is True
    assert arm_config.CHMOD_VALUE == 644
    assert arm_config.SET_MEDIA_OWNER is True
    assert arm_config.CHOWN_USER == "user"
    assert arm_config.CHOWN_GROUP == "group"
    assert arm_config.RIPMETHOD == "MKV"
    assert arm_config.MKV_ARGS == "--preset=fast"
    assert arm_config.DELRAWFILES is False
    assert arm_config.HASHEDKEYS is True
    assert arm_config.HB_PRESET_DVD == "High Profile"
    assert arm_config.HB_PRESET_BD == "1080p30"
    assert arm_config.DEST_EXT == "mkv"
    assert arm_config.HANDBRAKE_CLI == "/usr/bin/HandBrakeCLI"
    assert arm_config.MAINFEATURE is True
    assert arm_config.HB_ARGS_DVD == "--preset=DVD"
    assert arm_config.HB_ARGS_BD == "--preset=Blu-ray"
    assert arm_config.EMBY_REFRESH is False
    assert arm_config.EMBY_SERVER == "emby.example.com"
    assert arm_config.EMBY_PORT == "8096"
    assert arm_config.EMBY_CLIENT == "Chrome"
    assert arm_config.EMBY_DEVICE == "PC"
    assert arm_config.EMBY_DEVICEID == "123456"
    assert arm_config.EMBY_USERNAME == "user"
    assert arm_config.EMBY_USERID == "7890"
    assert arm_config.EMBY_PASSWORD == "password"
    assert arm_config.EMBY_API_KEY == "api_key"
    assert arm_config.NOTIFY_RIP is True
    assert arm_config.NOTIFY_TRANSCODE is False
    assert arm_config.PB_KEY == "pushbullet_key"
    assert arm_config.IFTTT_KEY == "ifttt_key"
    assert arm_config.IFTTT_EVENT == "event"
    assert arm_config.PO_USER_KEY == "user_key"
    assert arm_config.PO_APP_KEY == "app_key"
    assert arm_config.OMDB_API_KEY == "omdb_key"
