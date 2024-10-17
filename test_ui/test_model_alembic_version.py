"""
ARM UI Test - Models

Model:
    Alembic Version

Tests:
    setup_test_data - Fixture for setting up test data
    test_create_alembic_version - Test creating a new AlembicVersion record
    test_query_alembic_version - Test querying an existing AlembicVersion record
"""
import pytest

from ui.ui_setup import db
from models.alembic_version import AlembicVersion


@pytest.fixture
def setup_test_data(init_db):
    """ Fixture for setting up test data """
    # Setup Alembic Version with sample data for testing
    if not AlembicVersion.query.filter_by(version_num='12345').first():
        arm_alembic_version = AlembicVersion('12345')
        db.session.add(arm_alembic_version)
        db.session.commit()

    yield  # Allow test execution to proceed

    # Clean up (rollback changes)
    db.session.rollback()


def test_create_alembic_version(setup_test_data):
    """ Test creating a new AlembicVersion record """
    arm_alembic_version = AlembicVersion('67890')
    db.session.add(arm_alembic_version)
    db.session.commit()

    # Ensure the Config record exists
    assert arm_alembic_version.version_num is not None


def test_query_alembic_version(setup_test_data):
    """ Test querying an existing AlembicVersion record """
    arm_alembic_version = AlembicVersion.query.first()

    # Ensure the record exists
    assert arm_alembic_version is not None

    # Assert each attribute value against values loaded in test_create_alembic_version
    assert arm_alembic_version.version_num == '12345'
