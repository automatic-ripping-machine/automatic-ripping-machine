import datetime

from ui.ui_setup import db


class Notifications(db.Model):
    """
    ARM Database Model - Notifications

    Each notification has an ID, a boolean indicating if it has been seen,
    the time when it was triggered, the time when it was dismissed (if dismissed),
    a title, a message, a boolean indicating if it has been cleared,
    the time when it was cleared, and a difference time property (None by default).

    Database Table:
        notifications

    Attributes:
        id (int): The unique identifier for the notification.
        seen (bool): Indicates if the notification has been seen.
        trigger_time (datetime): The time when the notification was triggered.
        dismiss_time (datetime): The time when the notification was dismissed.
        title (str): The title of the notification.
        message (str): The content/message of the notification.
        cleared (bool): Indicates if the notification has been cleared.
        cleared_time (datetime): The time when the notification was cleared.
        diff_time (None): Difference time property, initialized as None.

    Relationships:
        None
    """
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    seen = db.Column(db.Boolean)
    trigger_time = db.Column(db.DateTime)
    dismiss_time = db.Column(db.DateTime)
    title = db.Column(db.String(256))
    message = db.Column(db.Text)
    diff_time = None
    cleared = db.Column(db.Boolean, default=False, nullable=False)
    cleared_time = db.Column(db.DateTime)

    def __init__(self, title: str = None, message: str = None):
        self.seen = False
        self.trigger_time = datetime.datetime.now()
        self.title = title
        self.message = message

    def __repr__(self):
        return f'<Notification {self.id}>'

    def __str__(self):
        """Returns a string of the object"""

        return_string = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            return_string = return_string + "(" + str(attr) + "=" + str(value) + ") "

        return return_string

    def get_d(self):
        """ Returns a dict of the object"""
        return_dict = {}
        for key, value in self.__dict__.items():
            if '_sa_instance_state' not in key:
                return_dict[str(key)] = str(value)
        return return_dict
