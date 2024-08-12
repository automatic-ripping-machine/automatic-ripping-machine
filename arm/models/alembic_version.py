from models.arm_models import ARMModel
from ui.ui_setup import db


class AlembicVersion(ARMModel):
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

    def __init__(self, version: str = None):
        self.version_num = version
