from flask_login import UserMixin

from ui.ui_setup import db


class User(db.Model, UserMixin):
    """
    ARM Database Model - User

    Holds the user model for ARM, currently ARM only supports a single user.
    The model stores user details such as user ID, email, password hash, and a hash value.

    Database Table:
        user

    Attributes:
        user_id (int): The unique identifier for the user.
        email (str): The email address associated with the user.
        password (str): The hashed password of the user.
        hash (str): Additional hash value associated with the user.

    Relationships:
        None
    """
    __tablename__ = 'user'

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
