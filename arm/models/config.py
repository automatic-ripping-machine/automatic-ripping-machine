from prettytable import PrettyTable

from arm.ui import db


hidden_attribs = ("OMDB_API_KEY", "EMBY_USERID", "EMBY_PASSWORD",
                  "EMBY_API_KEY", "PB_KEY", "IFTTT_KEY", "PO_KEY",
                  "PO_USER_KEY", "PO_APP_KEY", "ARM_API_KEY",
                  "TMDB_API_KEY", "_sa_instance_state")
HIDDEN_VALUE = "<hidden>"


class Config(db.Model):
    """ Holds all the config settings for each job
    as these may change between each job """
    CONFIG_ID = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.job_id'))
    ARM_CHECK_UDF = db.Column(db.Boolean)
    GET_VIDEO_TITLE = db.Column(db.Boolean)
    SKIP_TRANSCODE = db.Column(db.Boolean)
    VIDEOTYPE = db.Column(db.String(25))
    MINLENGTH = db.Column(db.String(6))
    MAXLENGTH = db.Column(db.String(6))
    MANUAL_WAIT = db.Column(db.Boolean)
    MANUAL_WAIT_TIME = db.Column(db.Integer)
    RAW_PATH = db.Column(db.String(255))
    TRANSCODE_PATH = db.Column(db.String(255))
    COMPLETED_PATH = db.Column(db.String(255))
    EXTRAS_SUB = db.Column(db.String(255))
    INSTALLPATH = db.Column(db.String(255))
    LOGPATH = db.Column(db.String(255))
    LOGLEVEL = db.Column(db.String(255))
    LOGLIFE = db.Column(db.Integer)
    DBFILE = db.Column(db.String(255))
    WEBSERVER_IP = db.Column(db.String(25))
    WEBSERVER_PORT = db.Column(db.Integer)
    UI_BASE_URL = db.Column(db.String(128))
    SET_MEDIA_PERMISSIONS = db.Column(db.Boolean)
    CHMOD_VALUE = db.Column(db.Integer)
    SET_MEDIA_OWNER = db.Column(db.Boolean)
    CHOWN_USER = db.Column(db.String(50))
    CHOWN_GROUP = db.Column(db.String(50))
    RIPMETHOD = db.Column(db.String(25))
    MKV_ARGS = db.Column(db.String(25))
    DELRAWFILES = db.Column(db.Boolean)
    HASHEDKEYS = db.Column(db.Boolean)
    HB_PRESET_DVD = db.Column(db.String(256))
    HB_PRESET_BD = db.Column(db.String(256))
    DEST_EXT = db.Column(db.String(10))
    HANDBRAKE_CLI = db.Column(db.String(25))
    FFMPEG_PRE_FILE_ARGS = db.Column(db.String(512))
    FFMPEG_POST_FILE_ARGS = db.Column(db.String(512))
    FFMPEG_CLI = db.Column(db.String(256))
    FFMPEG_LOCAL = db.Column(db.String(256))
    USE_FFMPEG = db.Column(db.Boolean)
    MAINFEATURE = db.Column(db.Boolean)
    HB_ARGS_DVD = db.Column(db.String(256))
    HB_ARGS_BD = db.Column(db.String(256))
    EMBY_REFRESH = db.Column(db.Boolean)
    EMBY_SERVER = db.Column(db.String(25))
    EMBY_PORT = db.Column(db.String(6))
    EMBY_CLIENT = db.Column(db.String(25))
    EMBY_DEVICE = db.Column(db.String(50))
    EMBY_DEVICEID = db.Column(db.String(128))
    EMBY_USERNAME = db.Column(db.String(50))
    EMBY_USERID = db.Column(db.String(128))
    EMBY_PASSWORD = db.Column(db.String(128))
    EMBY_API_KEY = db.Column(db.String(64))
    NOTIFY_RIP = db.Column(db.Boolean)
    NOTIFY_TRANSCODE = db.Column(db.Boolean)
    PB_KEY = db.Column(db.String(64))
    IFTTT_KEY = db.Column(db.String(64))
    IFTTT_EVENT = db.Column(db.String(25))
    PO_USER_KEY = db.Column(db.String(64))
    PO_APP_KEY = db.Column(db.String(64))
    OMDB_API_KEY = db.Column(db.String(64))

    def __init__(self, c, job_id):
        self.__dict__.update(c)
        self.job_id = job_id

    def __str__(self):
        """Returns a string of the object"""
        return_string = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            if str(attr) in hidden_attribs and value:
                value = HIDDEN_VALUE
            return_string = return_string + "(" + str(attr) + "=" + str(value) + ") "

        return return_string

    def list_params(self):
        """Returns a string of the object"""
        return_string = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            if return_string:
                return_string = return_string + "\n"
            if str(attr) in hidden_attribs and value:
                value = HIDDEN_VALUE
            return_string = return_string + str(attr) + ":" + str(value)

        return return_string

    def pretty_table(self):
        """Returns a string of the PrettyTable"""
        pretty_table = PrettyTable()
        pretty_table.field_names = ["Config", "Value"]
        pretty_table._max_width = {"Config": 20, "Value": 30}
        for attr, value in self.__dict__.items():
            if str(attr) in hidden_attribs and value:
                value = HIDDEN_VALUE
            pretty_table.add_row([str(attr), str(value)])
        return str(pretty_table.get_string())

    def get_d(self):
        """
        Return a dict of class - exclude any sensitive info
        :return: dict containing all attribs from class
        """
        return_dict = {}
        for key, value in self.__dict__.items():
            if str(key) not in hidden_attribs:
                return_dict[str(key)] = str(value)
        return return_dict
