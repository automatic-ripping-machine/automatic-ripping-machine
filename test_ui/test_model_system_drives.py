"""
ARM UI Test - Models

Model:
    System Drives

Tests:
    setup_test_data - Fixture for setting up test data
    test_create_system_drives - Test creating a new System Drives record
    test_query_system_drives - Test querying an existing System Drives record
"""
import pytest

from ui.ui_setup import db
from models.system_drives import SystemDrives   # Model under test
from models.job import Job                      # Required relational support


@pytest.fixture
def setup_test_data():
    """ Fixture for setting up test data """
    # Create a sample Job instance to use for job_id_current and job_id_previous
    job_previous = Job("/dev/sr0")
    job_current = Job("/dev/sr0")

    db.session.add(job_current)
    db.session.add(job_previous)
    db.session.commit()

    # Create a sample SystemDrives instance for testing
    system_drive = SystemDrives("System Drive 1",
                                "/dev/sr0",
                                job_current.job_id,
                                job_previous.job_id,
                                "Super Fast Magic Burner",
                                "CD/DVD/BluRay")

    db.session.add(system_drive)
    db.session.commit()

    yield system_drive  # Allow test execution to proceed

    # Clean up (rollback changes)
    db.session.rollback()


def test_create_system_drives(setup_test_data):
    """ Test creating a new System Drives record """
    # Create a sample Job instance to use for job_id_current and job_id_previous
    job_previous = setup_test_data.job_current
    job_current = Job("/dev/sr10")

    db.session.add(job_current)
    db.session.commit()

    system_drive = SystemDrives("System Drive 2",
                                "/dev/sr2",
                                job_current.job_id,
                                job_previous.job_id,
                                "Sloooooow drive",
                                "CD")

    db.session.add(system_drive)
    db.session.commit()

    # Ensure the record exists
    assert system_drive.drive_id is not None


def test_query_system_drives(setup_test_data):
    """ Test querying an existing System Drives record """
    drive = setup_test_data.drive_id
    system_drive = SystemDrives.query.filter_by(drive_id=drive).first()
    # system_drive = SystemDrives.query.first()

    # Assert for values retrieved from the database
    assert system_drive is not None
    assert system_drive.name == "System Drive 1"
    assert system_drive.type == "CD/DVD/BluRay"
    assert system_drive.mount == "/dev/sr0"
    assert system_drive.open is False
    assert system_drive.job_id_current == setup_test_data.job_current.job_id
    assert system_drive.job_id_previous == setup_test_data.job_previous.job_id
    assert system_drive.description == "Super Fast Magic Burner"
