"""
ARM UI Test - Models

Model:
    User

Tests:
    setup_test_data - Fixture for setting up test data
    test_create_user - Test creating a new user record
    test_query_user - Test querying an existing user record
"""
import pytest

from ui.ui_setup import db
from models.user import User       # Model under test


@pytest.fixture
def setup_test_data():
    """ Fixture for setting up User test data """
    # Create a sample User instance for testing
    user = User("test@example.com",
                "password123",
                "hashed_value")

    db.session.add(user)
    db.session.commit()

    yield user  # Allow test execution to proceed

    # Clean up (rollback changes)
    db.session.rollback()


def test_create_user(setup_test_data):
    """Test creating a new user record"""
    # Create a sample User instance for testing
    user = User("test@example.com",
                "password123",
                "hashed_value")

    db.session.add(user)
    db.session.commit()

    # Ensure the record exists
    assert user.user_id is not None


def test_query_user(setup_test_data):
    """ Test querying an existing User record """
    user = User.query.filter_by(email="test@example.com").first()

    # Assert for values retrieved from the database
    assert user is not None
    assert user.email == "test@example.com"
    assert user.password == "password123"
    assert user.hash == "hashed_value"
