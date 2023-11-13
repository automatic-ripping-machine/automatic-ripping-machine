from arm.ui import db


class AlembicVersion(db.Model):
    """
    Class to hold the A.R.M db version
    """
    version_num = db.Column(db.String(36), autoincrement=False, primary_key=True)

    def __init__(self, version=None):
        self.version_num = version

    def __repr__(self):
        return f'<AlembicVersion: {self.version_num}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.version_num
