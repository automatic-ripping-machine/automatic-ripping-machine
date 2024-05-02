"""
ARM UI Test - Models

Model:
    Job

Tests:
    setup_test_data - Fixture for setting up test data
    test_create_job - Test creating a new Job record
    test_job_attributes - Test Job model attributes
"""
import pytest
from datetime import datetime

from ui.ui_setup import db
from models.job import Job          # Model under test
from models.track import Track      # Required relational support
from test_model_config import setup_test_data as setup_config   # Required relational support


@pytest.fixture
def setup_test_data(setup_config):
    """ Fixture for setting up test data """
    # Create a sample Track associated with the job
    track = Track(1,
                  "1",
                  10140,
                  "1.43:1",
                  60.0,
                  True,
                  "MakeMKV",
                  "Interstellar",
                  "track1.mkv")
    db.session.add(track)
    db.session.commit()

    # Create a sample Job instance for testing
    job = Job(devpath="/dev/cdrom")
    job.arm_version = "1.2.3"
    job.crc_id = "ABC123"
    job.logfile = "/var/log/job.log"
    job.start_time = datetime(2024, 5, 3, 12, 30, 0)  # May 3, 2024, 12:30:00
    job.stop_time = datetime(2024, 5, 3, 14, 0, 0)  # May 3, 2024, 14:00:00
    job.job_length = "1.5 hours"
    job.status = "completed"
    job.stage = "processing"
    job.no_of_titles = 1
    job.title = "Interstellar"
    job.title_auto = "Interstellar"
    job.title_manual = "Interstellar_manual"
    job.year = "2014"
    job.year_auto = "2014"
    job.year_manual = "2000"
    job.video_type = "movie"
    job.video_type_auto = "movie"
    job.video_type_manual = "movie"
    job.imdb_id = "tt0816692"
    job.imdb_id_auto = "tt0816692"
    job.imdb_id_manual = "tt1234567"
    job.poster_url = "https://example.com/poster.jpg"
    job.poster_url_auto = "https://example.com/poster.jpg"
    job.poster_url_manual = "https://manual.com/poster.jpg"
    job.label = "Blu-ray Disc"
    job.path = "/media/disc"
    job.ejected = False
    job.updated = False
    job.pid = 123456789
    job.pid_hash = 987654321
    job.tracks.append(track)    # link to track table
    # job.config - pulled in with setup_config

    # Add the job to the database session
    db.session.add(job)
    db.session.commit()

    yield job  # Allow test execution to proceed

    # Clean up (rollback changes)
    db.session.rollback()


def test_create_job(setup_test_data):
    """ Test creating a new Job record """
    # Create a sample Track associated with the job
    track = Track(1,
                  "1",
                  10140,
                  "1.43:1",
                  60.0,
                  True,
                  "MakeMKV",
                  "Interstellar",
                  "track1.mkv")
    db.session.add(track)
    db.session.commit()

    # Create a sample Job instance for testing
    job = Job(devpath="/dev/sr10")
    job.arm_version = "3.0.0"
    job.crc_id = "123DEF"
    job.logfile = "/var/log/insert.log"
    job.start_time = datetime(2024, 5, 3, 12, 30, 0)  # May 3, 2024, 12:30:00
    job.stop_time = datetime(2024, 5, 3, 14, 0, 0)  # May 3, 2024, 14:00:00
    job.job_length = "60"
    job.status = "completed"
    job.stage = "processing"
    job.no_of_titles = 2
    job.title = "Wyrmwood: Road of the Dead"
    job.title_auto = "Wyrmwood: Road of the Dead"
    job.title_manual = "Wyrmwood: Road of the Dead_manual"
    job.year = "2014"
    job.year_auto = "2014"
    job.year_manual = "2014"
    job.video_type = "movie"
    job.video_type_auto = "movie"
    job.video_type_manual = "movie"
    job.imdb_id = "tt2535470"
    job.imdb_id_auto = "tt2535470"
    job.imdb_id_manual = "tt1234567"
    job.poster_url = "https://example.com/poster.jpg"
    job.poster_url_auto = "https://example.com/poster.jpg"
    job.poster_url_manual = "https://manual.com/poster.jpg"
    job.label = "Blu-ray Disc"
    job.path = "/media/disc"
    job.ejected = False
    job.updated = False
    job.pid = 123456789
    job.pid_hash = 987654321
    job.tracks.append(track)  # link to track table
    # job.config - pulled in with setup_config

    # Add the job to the database session
    db.session.add(job)
    db.session.commit()

    # Ensure the record exists
    assert job.job_id is not None


def test_job_attributes(setup_test_data):
    """ Test Job model attributes """
    job = setup_test_data

    # Assert each attribute value
    assert job.devpath == "/dev/cdrom"
    assert job.arm_version == "1.2.3"
    assert job.crc_id == "ABC123"
    assert job.logfile == "/var/log/job.log"
    assert job.start_time == datetime(2024, 5, 3, 12, 30, 0)
    assert job.stop_time == datetime(2024, 5, 3, 14, 0, 0)
    assert job.job_length == "1.5 hours"
    assert job.status == "completed"
    assert job.stage == "processing"
    assert job.no_of_titles == 1
    assert job.title == "Interstellar"
    assert job.title_auto == "Interstellar"
    assert job.title_manual == "Interstellar_manual"
    assert job.year == "2014"
    assert job.year_auto == "2014"
    assert job.year_manual == "2000"
    assert job.video_type == "movie"
    assert job.video_type_auto == "movie"
    assert job.video_type_manual == "movie"
    assert job.imdb_id == "tt0816692"
    assert job.imdb_id_auto == "tt0816692"
    assert job.imdb_id_manual == "tt1234567"
    assert job.poster_url == "https://example.com/poster.jpg"
    assert job.poster_url_auto == "https://example.com/poster.jpg"
    assert job.poster_url_manual == "https://manual.com/poster.jpg"
    assert job.label == "Blu-ray Disc"
    assert job.path == "/media/disc"
    assert job.ejected is False
    assert job.updated is False
    assert job.pid == 123456789
    assert job.pid_hash == 987654321
    # No test for job.tracks
    # No test for job.config
