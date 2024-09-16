from models.arm_models import ARMModel
from ui.ui_setup import db


class Config(ARMModel):
    """
    ARM Database Model - Config

    Represents configuration settings for each job.
    This class stores configuration settings for each job, which may vary between jobs.
    It includes various settings related to job execution, file paths, permissions,
    media processing parameters, external service credentials, and notification preferences.

    Database Table:
        config

    Attributes:
        CONFIG_ID (int): The unique identifier for the configuration.
        job_id (int): The identifier of the job associated with this configuration.
        ARM_CHECK_UDF (bool): Indicates whether to check UDF when using ARM.
        GET_VIDEO_TITLE (bool): Indicates whether to fetch video titles.
        SKIP_TRANSCODE (bool): Indicates whether to skip transcoding.
        VIDEOTYPE (str): Type of video.
        MINLENGTH (str): Minimum length.
        MAXLENGTH (str): Maximum length.
        MANUAL_WAIT (bool): Indicates whether to manually wait.
        MANUAL_WAIT_TIME (int): Time to wait manually.
        RAW_PATH (str): Path for raw files.
        TRANSCODE_PATH (str): Path for transcoded files.
        COMPLETED_PATH (str): Path for completed files.
        EXTRAS_SUB (str): Subtitle for extras.
        INSTALLPATH (str): Installation path.
        LOGPATH (str): Log path.
        LOGLEVEL (str): Log level.
        LOGLIFE (int): Log life.
        DBFILE (str): Database file.
        WEBSERVER_IP (str): Web server IP address.
        WEBSERVER_PORT (int): Web server port.
        UI_BASE_URL (str): Base URL for the user interface.
        SET_MEDIA_PERMISSIONS (bool): Indicates whether to set media permissions.
        CHMOD_VALUE (int): CHMOD value.
        SET_MEDIA_OWNER (bool): Indicates whether to set media owner.
        CHOWN_USER (str): User for CHOWN.
        CHOWN_GROUP (str): Group for CHOWN.
        RIPMETHOD (str): RIP method.
        MKV_ARGS (str): Arguments for MKV.
        DELRAWFILES (bool): Indicates whether to delete raw files.
        HASHEDKEYS (bool): Indicates whether to use hashed keys.
        HB_PRESET_DVD (str): Handbrake preset for DVD.
        HB_PRESET_BD (str): Handbrake preset for Blu-ray.
        DEST_EXT (str): Destination extension.
        HANDBRAKE_CLI (str): Handbrake CLI.
        MAINFEATURE (bool): Indicates whether to select the main feature.
        HB_ARGS_DVD (str): Arguments for Handbrake DVD.
        HB_ARGS_BD (str): Arguments for Handbrake Blu-ray.
        EMBY_REFRESH (bool): Indicates whether to refresh Emby.
        EMBY_SERVER (str): Emby server.
        EMBY_PORT (str): Emby port.
        EMBY_CLIENT (str): Emby client.
        EMBY_DEVICE (str): Emby device.
        EMBY_DEVICEID (str): Emby device ID.
        EMBY_USERNAME (str): Emby username.
        EMBY_USERID (str): Emby user ID.
        EMBY_PASSWORD (str): Emby password.
        EMBY_API_KEY (str): Emby API key.
        NOTIFY_RIP (bool): Indicates whether to notify on rip.
        NOTIFY_TRANSCODE (bool): Indicates whether to notify on transcoding.
        PB_KEY (str): Pushbullet key.
        IFTTT_KEY (str): IFTTT key.
        IFTTT_EVENT (str): IFTTT event.
        PO_USER_KEY (str): PO user key.
        PO_APP_KEY (str): PO app key.
        OMDB_API_KEY (str): OMDB API key.

    Relationships:
        None
    """
    __tablename__ = "config"

    hidden_attribs: tuple = ("OMDB_API_KEY", "EMBY_USERID", "EMBY_PASSWORD",
                             "EMBY_API_KEY", "PB_KEY", "IFTTT_KEY", "PO_KEY",
                             "PO_USER_KEY", "PO_APP_KEY", "ARM_API_KEY",
                             "TMDB_API_KEY", "_sa_instance_state")
    HIDDEN_VALUE: str = "<hidden>"

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

    def __init__(self, c, job_id: int):
        self.__dict__.update(c)
        self.job_id = job_id

    # TODO: remove outside model definition
    # def pretty_table(self):
    #     """Returns a string of the PrettyTable"""
    #     pretty_table = PrettyTable()
    #     pretty_table.field_names = ["Config", "Value"]
    #     pretty_table._max_width = {"Config": 20, "Value": 30}
    #     for attr, value in self.__dict__.items():
    #         if str(attr) in hidden_attribs and value:
    #             value = HIDDEN_VALUE
    #         pretty_table.add_row([str(attr), str(value)])
    #     return str(pretty_table.get_string())
    # def get_d(self):
    #     """
    #     Return a dict of class - exclude any sensitive info
    #     :return: dict containing all attribs from class
    #     """
    #     return_dict = {}
    #     for key, value in self.__dict__.items():
    #         if str(key) not in hidden_attribs:
    #             return_dict[str(key)] = str(value)
    #     return return_dict
