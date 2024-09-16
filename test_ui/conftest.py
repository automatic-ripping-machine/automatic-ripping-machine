"""
ARM UI Test Configuration
Setup and define the test fixtures for ARM UI tests.
"""
import os
import pytest

from ui import create_app
from ui.ui_setup import db


@pytest.fixture(scope='session')
def test_app():
    """
    ARM UI Test Configuration

    Setup and define the test app environment
    """
    # Set the Testing configuration prior to creating the Flask application
    os.environ['MYSQL_IP'] = '127.0.0.1'
    os.environ['MYSQL_USER'] = 'arm'
    os.environ['MYSQL_PASSWORD'] = 'example'

    flask_app = create_app('testing')

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
        db.create_all()     # Create tables for testing
        yield db            # Provide db to pytest session

        db.session.remove()
        db.drop_all()  # Drop all tables after testing
