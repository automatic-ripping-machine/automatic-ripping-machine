from ui.ui_setup import db


class UISettings(db.Model):
    """
    ARM Database Model - UISettings

    Holds various settings related to the user interface, such as whether to use icons,
    whether to save remote images, the Bootstrap skin, the language preference, refresh intervals
    for index and notifications, and a database limit setting.

    Database Table:
        ui_settings

    Attributes:
        id (int): The unique identifier for the UI settings entry.
        use_icons (bool): Indicates whether to use icons in the user interface.
        save_remote_images (bool): Indicates whether to save remote images.
        bootstrap_skin (str): The selected Bootstrap skin for styling.
        language (str): The language preference for the user interface.
        index_refresh (int): The refresh interval for the index page, in milliseconds.
        database_limit (int): Limit for database entries to display.
        notify_refresh (int): The refresh interval for notifications, in milliseconds

    Relationships:
        None.
    """
    __tablename__ = 'ui_settings'

    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    use_icons = db.Column(db.Boolean)
    save_remote_images = db.Column(db.Boolean)
    bootstrap_skin = db.Column(db.String(64))
    language = db.Column(db.String(4))
    index_refresh = db.Column(db.Integer)
    database_limit = db.Column(db.Integer)
    notify_refresh = db.Column(db.Integer)

    def __init__(self, use_icons=None, save_remote_images=None,
                 bootstrap_skin=None, language=None, index_refresh=None,
                 database_limit=None, notify_refresh=None):
        self.use_icons = use_icons
        self.save_remote_images = save_remote_images
        self.bootstrap_skin = bootstrap_skin
        self.language = language
        self.index_refresh = index_refresh
        self.database_limit = database_limit
        self.notify_refresh = notify_refresh

    def __repr__(self):
        return f'<UISettings {self.id}>'

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
