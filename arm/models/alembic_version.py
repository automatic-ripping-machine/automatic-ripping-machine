from ui.ui_setup import db


class AlembicVersion(db.Model):
    """
    ARM Database Model - Alembic Version

    Represents the version of the Alembic migration framework in the database.
    The database stores the version number as a string.

    Database Table:
        alembic_version

    Attributes:
        version_num (str): The version number of the Alembic migration framework.
            This serves as the primary key for identifying the Alembic version.

    Relationships:
        None
    """
    __tablename__ = 'alembic_version'

    version_num = db.Column(db.String(36), autoincrement=False, primary_key=True)

    def __init__(self, version=None):
        self.version_num = version

    def __repr__(self):
        return f'<AlembicVersion: {self.version_num}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.version_num
