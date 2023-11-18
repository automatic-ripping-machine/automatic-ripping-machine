from flask_login import UserMixin

from arm.ui import db


class User(db.Model, UserMixin):
    """
    Class to hold admin users
    """
    user_id = db.Column(db.Integer, index=True, primary_key=True)
    email = db.Column(db.String(64))
    password = db.Column(db.String(128))
    hash = db.Column(db.String(256))

    def __init__(self, email=None, password=None, hashed=None):
        self.email = email
        self.password = password
        self.hash = hashed

    def __repr__(self):
        """ Return users name """
        return f'<User {self.email}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.email

    def get_id(self):
        """ Return users id """
        return self.user_id
