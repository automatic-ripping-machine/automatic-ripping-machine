"""
ARM UI Test - Models

Model:
    System Info

Tests:
    setup_test_data - Fixture for setting up test data
    test_create_system_info - Test creating a new System Info record
    test_query_system_info - Test querying an existing System Info record
"""
import pytest

from ui.ui_setup import db
from models.system_info import SystemInfo       # Model under test


@pytest.fixture
def setup_test_data():
    """ Fixture for setting up test data """
    # Create a sample SystemInfo instance for testing
    system_info = SystemInfo("Test Server",
                             "Test server description")

    db.session.add(system_info)
    db.session.commit()

    yield system_info  # Allow test execution to proceed

    # Clean up (rollback changes)
    db.session.rollback()


def test_create_system_info(setup_test_data):
    """ Test creating a new SystemInfo record """
    # Create a sample SystemInfo instance for testing
    system_info = SystemInfo("Test Server",
                             "Test server description")

    db.session.add(system_info)
    db.session.commit()

    # Ensure the record exists
    assert system_info.id is not None


def test_query_system_info(setup_test_data):
    """ Test querying an existing SystemInfo record """
    system_info = SystemInfo.query.first()

    # Assert for values retrieved from the database
    assert system_info is not None
    assert system_info.name == "Test Server"
    assert system_info.description == "Test server description"
