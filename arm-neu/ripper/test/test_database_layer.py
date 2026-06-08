"""Tests for database layer (standalone SQLAlchemy)."""


class TestDatabaseLayer:
    def test_import_from_arm_database(self):
        """arm.database.db should be importable."""
        from arm.database import db
        assert db is not None

    def test_init_db_creates_tables(self, app_context):
        """init_engine + create_all should set up tables."""
        from arm.models.job import Job
        assert Job.query.all() == []

    def test_models_use_shared_db(self, app_context):
        """All models should use the shared db instance."""
        from arm.database import db
        from arm.models.job import Job
        from arm.models.notifications import Notifications
        from arm.models.track import Track
        from arm.models.user import User

        # All model classes should reference the same db metadata
        assert Job.metadata is db.metadata
        assert Notifications.metadata is db.metadata
        assert Track.metadata is db.metadata
        assert User.metadata is db.metadata
