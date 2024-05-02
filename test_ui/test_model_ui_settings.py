"""
ARM UI Test - Models

Model:
    UI Settings

Tests:
    setup_test_data - Fixture for setting up test data
    test_create_ui_settings - Test creating a new UI Settings record
    test_query_ui_settings - Test querying an existing UI Settings record
"""
import pytest

from ui.ui_setup import db
from models.ui_settings import UISettings  # Model under test


@pytest.fixture
def setup_test_data():
    """ Fixture for setting up UISettings test data """
    # Create a sample UISettings instance for testing
    ui_settings = UISettings(True,
                             True,
                             "dark",
                             "en",
                             3000,
                             100,
                             5000)

    db.session.add(ui_settings)
    db.session.commit()

    yield ui_settings  # Allow test execution to proceed

    # Clean up (rollback changes)
    db.session.rollback()


def test_create_ui_settings(setup_test_data):
    """Test creating a new UI Settings record"""
    # Create a sample UI Settings instance for testing
    ui_settings = UISettings(True,
                             True,
                             "dark",
                             "en",
                             3000,
                             100,
                             5000)

    db.session.add(ui_settings)
    db.session.commit()

    # Ensure the record exists
    assert ui_settings.id is not None


def test_query_ui_settings(setup_test_data):
    """ Test querying an existing UISettings record """
    ui_settings = UISettings.query.first()

    # Assert for values retrieved from the database
    assert ui_settings is not None
    assert ui_settings.use_icons is True
    assert ui_settings.save_remote_images is True
    assert ui_settings.bootstrap_skin == "dark"
    assert ui_settings.language == "en"
    assert ui_settings.index_refresh == 3000
    assert ui_settings.database_limit == 100
    assert ui_settings.notify_refresh == 5000
