"""
ARM UI Test - Models

Model:
    Notifications

Tests:
    setup_test_data - Fixture for setting up test data
    test_create_notifications - Test creating a new Notifications record
    test_query_notifications - Test querying an existing Notifications record
"""
import pytest

from ui.ui_setup import db
from models.notifications import Notifications  # Model under test


@pytest.fixture
def setup_test_data():
    """ Fixture for setting up test data """
    # Create a sample Notification instance for testing
    notification = Notifications("Test Notification",
                                 "This is a test message")
    db.session.add(notification)
    db.session.commit()

    yield notification  # Allow test execution to proceed

    # Clean up (rollback changes)
    db.session.rollback()


def test_create_notifications(setup_test_data):
    """ Test creating a new Notifications record """
    title = "New Notification"
    message = "A new notification message"
    notification = Notifications(title, message)

    db.session.add(notification)
    db.session.commit()

    # Ensure the record exists
    assert notification.id is not None


def test_query_notifications(setup_test_data):
    """ Test querying an existing Notifications record """
    notification = Notifications.query.first()

    # Assert each attribute value against values loaded in setup_test_data
    assert notification.title == "Test Notification"
    assert notification.message == "This is a test message"
    assert notification.seen is False  # 'seen' should be False initially
    assert notification.cleared is False  # 'cleared' should be False initially
