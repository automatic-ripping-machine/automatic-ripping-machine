"""
ARM UI Test Configuration
Setup and define the test fixtures for ARM UI tests.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'arm')))
from ui import create_app           # noqa: E402
from models.db_setup import db      # noqa: E402


@pytest.fixture(scope='session')
def test_app():
    """
    ARM UI Test Configuration

    Setup and define the test app environment
    """
    # Load Flask with Test Config
    flask_app = create_app('testing')

    # Only run if the db is connecting to arm_testing
    if not flask_app.config["MYSQL_DATABASE"] == "arm_testing":
        print("Testing not running with the 'testing' environment config")
        exit(1)

    return flask_app


@pytest.fixture(scope='session')
def test_client(test_app):
    """
    ARM UI Test Configuration

    Provide a flask test client instance
    """
    # Create a test client using the Flask application configured for testing
    with test_app.test_client() as testing_client:
        # Establish an application context
        with test_app.app_context():
            yield testing_client  # this is where the testing happens!


@pytest.fixture(scope='session')
def init_db(test_app):
    """
    ARM UI Test Configuration

    Provide a database instance
    """
    with test_app.app_context():
        db.create_all()

    yield db                # Provide db to pytest session

    with test_app.app_context():
        # Roll back and release every session first - leaked transactions
        # (e.g. from tests erroring mid-fixture) otherwise hold MySQL
        # metadata locks and db.drop_all() hangs indefinitely.
        db.session.rollback()
        db.session.close_all()
        db.drop_all()       # Drop all tables after testing
