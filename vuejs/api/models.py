"""
Hold all models for ARM
"""
import datetime
import os
import subprocess
import logging
import time
from typing import Any

import psutil
import platform
import re

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.types import String, Integer, DateTime, Boolean, Text, BigInteger
from sqlalchemy import ForeignKey, Unicode, Float

from prettytable import PrettyTable
from database import Base

hidden_attribs = ("OMDB_API_KEY", "EMBY_USERID", "EMBY_PASSWORD",
                  "EMBY_API_KEY", "PB_KEY", "IFTTT_KEY", "PO_KEY",
                  "PO_USER_KEY", "PO_APP_KEY", "ARM_API_KEY",
                  "TMDB_API_KEY", "_sa_instance_state")
HIDDEN_VALUE = "<hidden>"


class Job(Base):
    __tablename__ = "job"
    """
    Job Class hold most of the details for each job
    connects to track, config
    """
    job_id = Column(Integer, primary_key=True, index=True)
    arm_version = Column(String(256))
    crc_id = Column(String(256))
    logfile = Column(String(256))
    start_time = Column(DateTime)
    stop_time = Column(DateTime)
    job_length = Column(String(256))
    status = Column(String(256))
    stage = Column(String(256))
    no_of_titles = Column(Integer)
    title = Column(String(256))
    title_auto = Column(String(256))
    title_manual = Column(String(256))
    year = Column(String(256))
    year_auto = Column(String(256))
    year_manual = Column(String(256))
    video_type = Column(String(256))
    video_type_auto = Column(String(256))
    video_type_manual = Column(String(256))
    imdb_id = Column(String(256))
    imdb_id_auto = Column(String(256))
    imdb_id_manual = Column(String(256))
    poster_url = Column(String(256))
    poster_url_auto = Column(String(256))
    poster_url_manual = Column(String(256))
    devpath = Column(String(256))
    mountpoint = Column(String(256))
    hasnicetitle = Column(Boolean)
    errors = Column(Text)
    disctype = Column(String(256))  # dvd/bluray/data/music/unknown
    label = Column(String(256))
    path = Column(String(256))
    ejected = Column(Boolean)
    updated = Column(Boolean)
    pid = Column(BigInteger)
    pid_hash = Column(BigInteger)
    tracks = relationship('Track', backref='job', uselist=True)
    config = relationship('Config', backref="job", uselist=False)

    def __init__(self, devpath, *args: Any, **kwargs: Any):
        """Return a disc object"""
        super().__init__(*args, **kwargs)
        self.devpath = devpath
        self.mountpoint = "/mnt" + devpath
        self.hasnicetitle = False
        self.video_type = "unknown"
        self.ejected = False
        self.updated = False
        self.parse_udev()
        self.get_pid()
        self.stage = str(round(time.time() * 100))

        if self.disctype == "dvd" and not self.label:
            logging.info("No disk label Available. Trying lsdvd")
            command = f"lsdvd {devpath} | grep 'Disc Title' | cut -d ' ' -f 3-"
            lsdvdlbl = str(subprocess.check_output(command, shell=True).strip(), 'utf-8')
            self.label = lsdvdlbl

    def __str__(self):
        """Returns a string of the object"""

        return_string = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            return_string = return_string + "(" + str(attr) + "=" + str(value) + ") "

        return return_string

    def __repr__(self):
        return f'<Job {self.label}>'

    def parse_udev(self):
        """Parse udev for properties of current disc"""
        self.disctype = "unknown"

    def get_pid(self):
        """
        Get the jobs process id
        :return: None
        """
        pid = os.getpid()
        process_id = psutil.Process(pid)
        self.pid = pid
        self.pid_hash = hash(process_id)

    def get_disc_type(self, found_hvdvd_ts):
        """
        Checks/corrects the current disc-type
        :param found_hvdvd_ts:  gets pushed in from utils - saves importing utils
        :return: None
        """
        if self.disctype == "music":
            logging.debug("Disc is music.")
            # self.label = music_brainz.main(self)
        elif os.path.isdir(self.mountpoint + "/VIDEO_TS"):
            logging.debug(f"Found: {self.mountpoint}/VIDEO_TS")
            self.disctype = "dvd"
        elif os.path.isdir(self.mountpoint + "/video_ts"):
            logging.debug(f"Found: {self.mountpoint}/video_ts")
            self.disctype = "dvd"
        elif os.path.isdir(self.mountpoint + "/BDMV"):
            logging.debug(f"Found: {self.mountpoint}/BDMV")
            self.disctype = "bluray"
        elif os.path.isdir(self.mountpoint + "/HVDVD_TS"):
            logging.debug(f"Found: {self.mountpoint}/HVDVD_TS")
            # do something here
        elif found_hvdvd_ts:
            logging.debug("Found file: HVDVD_TS")
            # do something here too
        else:
            logging.debug("Did not find valid dvd/bd files. Changing disc-type to 'data'")
            self.disctype = "data"

    def identify_audio_cd(self):
        """
        Get the title for audio cds to use for the logfile name.

        Needs the job class passed into it so it can be forwarded to mb

        return - only the logfile - setup_logging() adds the full path
        """
        # # Use the music label if we can find it - defaults to music_cd.log
        # #disc_id = music_brainz.get_disc_id(self)
        # logging.debug(f"music_id: {disc_id}")
        # mb_title = music_brainz.get_title(disc_id, self)
        # logging.debug(f"mm_title: {mb_title}")
        #
        # if mb_title == "not identified":
        #     self.label = self.title = "not identified"
        #     logfile = "music_cd.log"
        #     new_log_file = f"music_cd_{round(time.time() * 100)}.log"
        # else:
        #     logfile = f"{mb_title}.log"
        #     new_log_file = f"{mb_title}_{round(time.time() * 100)}.log"
        #
        # temp_log_full = os.path.join(cfg.arm_config['LOGPATH'], logfile)
        # logfile = new_log_file if os.path.isfile(temp_log_full) else logfile
        return "logfile"

    def pretty_table(self):
        """Returns a string of the prettytable"""
        pretty_table = PrettyTable()
        pretty_table.field_names = ["Config", "Value"]
        pretty_table._max_width = {"Config": 50, "Value": 60}
        for attr, value in self.__dict__.items():
            if attr == "config":
                pretty_table.add_row([str(attr), str(value.pretty_table())])
            else:
                pretty_table.add_row([str(attr), str(value)])
        return str(pretty_table.get_string())

    def get_d(self):
        """
        Return a dict of class - exclude the _sa_instance_state
        :return: dict containing all attribs from class
        """
        return_dict = {}
        for key, value in self.__dict__.items():
            if '_sa_instance_state' not in key:
                return_dict[str(key)] = str(value)
        return return_dict

    def eject(self):
        """Eject disc if it hasn't previously been ejected"""
        if not self.ejected:
            self.ejected = True
            try:
                # This might always return true
                if bool(os.system("umount " + self.devpath)):
                    logging.debug(f"Unmounted disc {self.devpath}")
                else:
                    logging.debug(f"Failed to unmount {self.devpath}")
                if bool(os.system("eject -sv " + self.devpath)):
                    logging.debug(f"Ejected disc {self.devpath}")
                else:
                    logging.debug(f"Failed to eject {self.devpath}")
            except Exception as error:
                logging.debug(f"{self.devpath} couldn't be ejected {error}")


class Track(Base):
    __tablename__ = "track"

    """ Holds all the individual track details for each job """
    track_id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('job.job_id'))
    track_number = Column(String(4))
    length = Column(Integer)
    aspect_ratio = Column(String(20))
    fps = Column(Float)
    main_feature = Column(Boolean)
    basename = Column(String(256))
    filename = Column(String(256))
    orig_filename = Column(String(256))
    new_filename = Column(String(256))
    ripped = Column(Boolean)
    status = Column(String(32))
    error = Column(Text)
    source = Column(String(32))

    def __init__(self, job_id, track_number, length, aspect_ratio, fps, main_feature, source, basename, filename,
                 *args: Any, **kwargs: Any):
        """Return a track object"""
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.track_number = track_number
        self.length = length
        self.aspect_ratio = aspect_ratio
        self.fps = fps
        self.main_feature = main_feature
        self.source = source
        self.basename = basename
        self.filename = filename
        self.ripped = False

    def __repr__(self):
        return f'<Track {self.track_number}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.track_number

    def get_d(self):
        """
        Return a dict of class - exclude the _sa_instance_state
        :return: dict containing all attribs from class
        """
        return_dict = {}
        for key, value in self.__dict__.items():
            if '_sa_instance_state' not in key:
                return_dict[str(key)] = str(value)
        return return_dict


class Config(Base):
    __tablename__ = "config"
    """ Holds all the config settings for each job
    as these may change between each job """
    CONFIG_ID = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('job.job_id'))
    ARM_CHECK_UDF = Column(Boolean)
    GET_VIDEO_TITLE = Column(Boolean)
    SKIP_TRANSCODE = Column(Boolean)
    VIDEOTYPE = Column(String(25))
    MINLENGTH = Column(String(6))
    MAXLENGTH = Column(String(6))
    MANUAL_WAIT = Column(Boolean)
    MANUAL_WAIT_TIME = Column(Integer)
    RAW_PATH = Column(String(255))
    TRANSCODE_PATH = Column(String(255))
    COMPLETED_PATH = Column(String(255))
    EXTRAS_SUB = Column(String(255))
    INSTALLPATH = Column(String(255))
    LOGPATH = Column(String(255))
    LOGLEVEL = Column(String(255))
    LOGLIFE = Column(Integer)
    DBFILE = Column(String(255))
    WEBSERVER_IP = Column(String(25))
    WEBSERVER_PORT = Column(Integer)
    SET_MEDIA_PERMISSIONS = Column(Boolean)
    CHMOD_VALUE = Column(Integer)
    SET_MEDIA_OWNER = Column(Boolean)
    CHOWN_USER = Column(String(50))
    CHOWN_GROUP = Column(String(50))
    RIPMETHOD = Column(String(25))
    MKV_ARGS = Column(String(25))
    DELRAWFILES = Column(Boolean)
    HASHEDKEYS = Column(Boolean)
    HB_PRESET_DVD = Column(String(256))
    HB_PRESET_BD = Column(String(256))
    DEST_EXT = Column(String(10))
    HANDBRAKE_CLI = Column(String(25))
    MAINFEATURE = Column(Boolean)
    HB_ARGS_DVD = Column(String(256))
    HB_ARGS_BD = Column(String(256))
    EMBY_REFRESH = Column(Boolean)
    EMBY_SERVER = Column(String(25))
    EMBY_PORT = Column(String(6))
    EMBY_CLIENT = Column(String(25))
    EMBY_DEVICE = Column(String(50))
    EMBY_DEVICEID = Column(String(128))
    EMBY_USERNAME = Column(String(50))
    EMBY_USERID = Column(String(128))
    EMBY_PASSWORD = Column(String(128))
    EMBY_API_KEY = Column(String(64))
    NOTIFY_RIP = Column(Boolean)
    NOTIFY_TRANSCODE = Column(Boolean)
    PB_KEY = Column(String(64))
    IFTTT_KEY = Column(String(64))
    IFTTT_EVENT = Column(String(25))
    PO_USER_KEY = Column(String(64))
    PO_APP_KEY = Column(String(64))
    OMDB_API_KEY = Column(String(64))

    def __init__(self, c, job_id, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
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
        Return a dict of class - exclude the any sensitive info
        :return: dict containing all attribs from class
        """
        return_dict = {}
        for key, value in self.__dict__.items():
            if str(key) not in hidden_attribs:
                return_dict[str(key)] = str(value)
        return return_dict


class User(Base):
    __tablename__ = "user"
    """
    Class to hold admin users
    """
    user_id = Column(Integer, index=True, primary_key=True)
    username = Column(String(64))
    password = Column(String(128))
    hash = Column(String(256))
    disabled = Column(Boolean)

    def __init__(self, username=None, password=None, hashed=None, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.username = username
        self.password = password
        self.hash = hashed
        self.disabled = False

    def __repr__(self):
        """ Return users name """
        return f'<User {self.username}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.username

    def get_id(self):
        """ Return users id """
        return self.user_id


class AlembicVersion(Base):
    __tablename__ = "alembic_version"
    """
    Class to hold the A.R.M db version
    """
    version_num = Column(String(36), autoincrement=False, primary_key=True)

    def __init__(self, version=None, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.version_num = version

    def __repr__(self):
        return f'<AlembicVersion: {self.version_num}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.version_num


class UISettings(Base):
    __tablename__ = "ui_settings"
    """
    Class to hold the A.R.M ui settings
    """
    id = Column(Integer, autoincrement=True, primary_key=True)
    use_icons = Column(Boolean)
    save_remote_images = Column(Boolean)
    bootstrap_skin = Column(String(64))
    language = Column(String(4))
    index_refresh = Column(Integer)
    database_limit = Column(Integer)
    notify_refresh = Column(Integer)

    def __init__(self, use_icons=None, save_remote_images=None, bootstrap_skin=None, language=None, index_refresh=None,
                 database_limit=None, notify_refresh=None, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
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


class Notifications(Base):
    __tablename__ = "notifications"
    """
    Class to hold the A.R.M notifications
    """
    id = Column(Integer, autoincrement=True, primary_key=True)
    seen = Column(Boolean)
    trigger_time = Column(DateTime)
    dismiss_time = Column(DateTime)
    title = Column(String(256))
    message = Column(Text)
    diff_time = None
    cleared = Column(Boolean, default=False, nullable=False)
    cleared_time = Column(DateTime)

    def __init__(self, title=None, message=None, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
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


class SystemInfo(Base):
    __tablename__ = "system_info"
    """
    Class to hold the system (server) information
    """
    id = Column(Integer, index=True, primary_key=True)
    name = Column(String(100))
    cpu = Column(String(20))
    description = Column(Unicode(200))
    mem_total = Column(Float())

    def __init__(self, name="ARM Server", description="Automatic Ripping Machine main server", *args: Any,
                 **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.get_cpu_info()
        self.get_memory()
        self.name = name
        self.description = description

    def get_cpu_info(self):
        """
        function to collect and return some cpu info
        ideally want to return {name} @ {speed} Ghz
        """
        self.cpu = "Unknown"
        if platform.system() == "Windows":
            self.cpu = platform.processor()
        elif platform.system() == "Darwin":
            self.cpu = subprocess.check_output(['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]).strip()
        elif platform.system() == "Linux":
            command = "cat /proc/cpuinfo"
            fulldump = str(subprocess.check_output(command, shell=True).strip())
            # Take any float trailing "MHz", some whitespace, and a colon.
            speeds = re.search(r"\\nmodel name\\t:.*?GHz\\n", fulldump)
            if speeds:
                # We have intel CPU
                speeds = str(speeds.group())
                speeds = speeds.replace('\\n', ' ')
                speeds = speeds.replace('\\t', ' ')
                speeds = speeds.replace('model name :', '')
                self.cpu = speeds
            # AMD CPU
            amd_name_full = re.search(r"model name\\t: (.*?)\\n", fulldump)
            if amd_name_full:
                amd_name = amd_name_full.group(1)
                amd_mhz = re.search(r"cpu MHz(?:\\t)*: ([.0-9]*)\\n", fulldump)  # noqa: W605
                if amd_mhz:
                    amd_ghz = round(float(amd_mhz.group(1)) / 1000, 2)  # this is a good idea
                    self.cpu = str(amd_name) + " @ " + str(amd_ghz) + " GHz"
            # ARM64 CPU
            arm_cpu = re.search(r"\\nmodel name\\t:(.*?)\\n", fulldump)
            if arm_cpu:
                self.cpu = str(arm_cpu.group(1))[:19]
        else:
            self.cpu = "N/A"

    def get_memory(self):
        """ get the system total memory """
        try:
            memory = psutil.virtual_memory()
            self.mem_total = round(memory.total / 1073741824, 1)
        except EnvironmentError:
            self.mem_total = 0

    def get_d(self):
        """ Returns a dict of the object"""
        return_dict = {}
        for key, value in self.__dict__.items():
            if '_sa_instance_state' not in key:
                return_dict[str(key)] = str(value)
        return return_dict


class SystemDrives(Base):
    __tablename__ = "system_drives"
    """
    Class to hold the system cd/dvd/blueray drive information
    """
    drive_id = Column(Integer, index=True, primary_key=True)
    name = Column(String(100))
    type = Column(String(20))
    mount = Column(String(100))
    open = Column(Boolean)
    job_id_current = Column(Integer, ForeignKey("job.job_id"))
    job_id_previous = Column(Integer, ForeignKey("job.job_id"))
    description = Column(Unicode(200))

    # relationship - join current and previous jobs to the jobs table
    job_current = relationship("Job", backref="Current", foreign_keys=[job_id_current])
    job_previous = relationship("Job", backref="Previous", foreign_keys=[job_id_previous])

    def __init__(self, name, mount, job, job_previous, description, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.name = name
        self.mount = mount
        self.open = False
        self.job_id_current = job
        self.job_id_previous = job_previous
        self.description = description
        self.drive_type()

    def drive_type(self):
        """find the Drive type (CD, DVD, Blueray) from the udev values"""
        temp = ""
        self.type = temp

    def new_job(self, job_id):
        """new job assigned to the drive, add the job id"""
        self.job_id_current = job_id

    def job_finished(self):
        """update Job IDs between current and previous jobs"""
        self.job_id_previous = self.job_id_current
        self.job_id_current = None
        # eject drive (not implemented, as job.eject() declared in a lot of places)
        # self.open_close()

    def open_close(self):
        """Open or Close the drive"""
        if self.open:
            # If open, then close the drive
            try:
                os.system("eject -tv " + self.mount)
                self.open = False
            except Exception as error:
                logging.debug(f"{self.mount} unable to be closed {error}")
        else:
            # if closed, open/eject the drive
            if self.job_id_current:
                logging.debug(f"{self.mount} unable to eject - current job [{self.job_id_current}] is in progress.")
            else:
                try:
                    # eject the drive
                    # eject returns 0 for successful, 1 for failure
                    if not bool(os.system("eject -v " + self.mount)):
                        logging.debug(f"Ejected disc {self.mount}")
                    else:
                        logging.debug(f"Failed to eject {self.mount}")
                    self.open = True
                except Exception as error:
                    logging.debug(f"{self.mount} couldn't be ejected {error}")

    def get_d(self):
        """ Returns a dict of the object"""
        return_dict = {}
        for key, value in self.__dict__.items():
            if '_sa_instance_state' not in key:
                return_dict[str(key)] = str(value)
            if "job_previous" in key:
                return_dict[str(key)] = {'fucked': value.get_d()}
        return return_dict


class AppriseConfig(Base):
    __tablename__ = "apprise_config"
    """
    Class to hold the apprise config
    """
    id = Column(Integer, autoincrement=True, primary_key=True)
    BOXCAR_KEY = Column(String(256))
    BOXCAR_SECRET = Column(String(256))
    DISCORD_WEBHOOK_ID = Column(String(256))
    DISCORD_TOKEN = Column(String(256))
    FAAST_TOKEN = Column(String(256))
    FLOCK_TOKEN = Column(String(256))
    GITTER_TOKEN = Column(String(256))
    GITTER_ROOM = Column(String(256))
    GOTIFY_TOKEN = Column(String(256))
    GOTIFY_HOST = Column(String(256))
    GROWL_HOST = Column(String(256))
    GROWL_PASS = Column(String(256))
    JOIN_API = Column(String(256))
    JOIN_DEVICE = Column(String(256))
    KODI_HOST = Column(String(256))
    KODI_PORT = Column(String(256))
    KODI_USER = Column(String(256))
    KODI_PASS = Column(String(256))
    KUMULOS_API = Column(String(256))
    KUMULOS_SERVERKEY = Column(String(256))
    LAMETRIC_MODE = Column(String(256))
    LAMETRIC_API = Column(Text)
    LAMETRIC_HOST = Column(Text)
    LAMETRIC_APP_ID = Column(Text)
    LAMETRIC_TOKEN = Column(Text)
    MAILGUN_DOMAIN = Column(Text)
    MAILGUN_USER = Column(Text)
    MAILGUN_APIKEY = Column(Text)
    MATRIX_HOST = Column(Text)
    MATRIX_USER = Column(Text)
    MATRIX_PASS = Column(Text)
    MATRIX_TOKEN = Column(Text)
    MSTEAMS_TOKENA = Column(Text)
    MSTEAMS_TOKENB = Column(Text)
    MSTEAMS_TOKENC = Column(Text)
    NEXTCLOUD_HOST = Column(Text)
    NEXTCLOUD_ADMINUSER = Column(Text)
    NEXTCLOUD_ADMINPASS = Column(Text)
    NEXTCLOUD_NOTIFY_USER = Column(Text)
    NOTICA_TOKEN = Column(Text)
    NOTIFICO_PROJECTID = Column(Text)
    NOTIFICO_MESSAGEHOOK = Column(Text)
    OFFICE365_TENANTID = Column(Text)
    OFFICE365_ACCOUNTEMAIL = Column(Text)
    OFFICE365_CLIENT_ID = Column(Text)
    OFFICE365_CLIENT_SECRET = Column(Text)
    POPCORN_API = Column(Text)
    POPCORN_EMAIL = Column(Text)
    POPCORN_PHONENO = Column(Text)
    PROWL_API = Column(Text)
    PROWL_PROVIDERKEY = Column(Text)
    PUSHJET_HOST = Column(Text)
    PUSHJET_SECRET = Column(Text)
    PUSH_API = Column(Text)
    PUSHED_APP_KEY = Column(Text)
    PUSHED_APP_SECRET = Column(Text)
    PUSHSAFER_KEY = Column(Text)
    ROCKETCHAT_HOST = Column(Text)
    ROCKETCHAT_USER = Column(Text)
    ROCKETCHAT_PASS = Column(String(256))
    ROCKETCHAT_WEBHOOK = Column(String(256))
    RYVER_ORG = Column(String(256))
    RYVER_TOKEN = Column(String(256))
    SENDGRID_API = Column(String(256))
    SENDGRID_FROMMAIL = Column(String(256))
    SIMPLEPUSH_API = Column(String(256))
    SLACK_TOKENA = Column(Text)
    SLACK_TOKENB = Column(Text)
    SLACK_TOKENC = Column(String(256))
    SLACK_CHANNEL = Column(String(256))
    SPARKPOST_API = Column(String(256))
    SPARKPOST_HOST = Column(String(256))
    SPARKPOST_USER = Column(String(256))
    SPARKPOST_EMAIL = Column(String(256))
    SPONTIT_API = Column(String(256))
    SPONTIT_USER_ID = Column(String(256))
    TELEGRAM_BOT_TOKEN = Column(String(256))
    TELEGRAM_CHAT_ID = Column(String(256))
    TWIST_EMAIL = Column(String(256))
    TWIST_PASS = Column(String(256))
    XBMC_HOST = Column(String(256))
    XBMC_PORT = Column(String(256))
    XBMC_USER = Column(String(256))
    XBMC_PASS = Column(String(256))
    XMPP_HOST = Column(String(256))
    XMPP_PASS = Column(String(256))
    XMPP_USER = Column(String(256))
    WEBEX_TEAMS_TOKEN = Column(String(256))
    ZILUP_CHAT_TOKEN = Column(String(256))
    ZILUP_CHAT_BOTNAME = Column(String(256))
    ZILUP_CHAT_ORG = Column(String(256))

    def __init__(self, config_name=None, config_value=None, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.config_name = config_name
        self.config_value = config_value

    def __repr__(self):
        return f'<AppriseConfig: {self.__dict__}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " +  str(self.__dict__)

class RipperConfig(Base):
    __tablename__ = "ripper_config"
    """
    Class to hold the ripper config
    """
    id = Column(Integer, autoincrement=True, primary_key=True , default=0)
    ARM_NAME = Column(String(256))
    ARM_CHILDREN = Column(String(256))
    PREVENT_99 = Column(Boolean)
    ARM_CHECK_UDF = Column(Boolean)
    UMASK = Column(String(256))
    GET_VIDEO_TITLE = Column(Boolean)
    ARM_API_KEY = Column(String(256))
    DISABLE_LOGIN = Column(Boolean)
    SKIP_TRANSCODE = Column(Boolean)
    VIDEOTYPE = Column(String(256))
    MINLENGTH = Column(Integer)
    MAXLENGTH = Column(Integer)
    MANUAL_WAIT = Column(Boolean)
    MANUAL_WAIT_TIME = Column(Integer)
    DATE_FORMAT = Column(String(256))
    ALLOW_DUPLICATES = Column(Boolean)
    MAX_CONCURRENT_TRANSCODES = Column(Integer)
    DATA_RIP_PARAMETERS = Column(String(256))
    METADATA_PROVIDER = Column(String(256))
    GET_AUDIO_TITLE = Column(String(256))
    RIP_POSTER = Column(Boolean)
    ABCDE_CONFIG_FILE = Column(String(256))
    RAW_PATH = Column(String(256))
    TRANSCODE_PATH = Column(String(256))
    COMPLETED_PATH = Column(String(256))
    EXTRAS_SUB = Column(String(256))
    INSTALLPATH = Column(String(256))
    LOGPATH = Column(String(256))
    LOGLEVEL = Column(String(256))
    LOGLIFE = Column(Integer)
    DBFILE = Column(String(256))
    WEBSERVER_IP = Column(String(256))
    WEBSERVER_PORT = Column(Integer)
    SET_MEDIA_PERMISSIONS = Column(Boolean)
    CHMOD_VALUE = Column(Integer)
    SET_MEDIA_OWNER = Column(Boolean)
    CHOWN_USER = Column(String(256))
    CHOWN_GROUP = Column(String(256))
    MAKEMKV_PERMA_KEY = Column(String(256))
    RIPMETHOD = Column(String(256))
    RIPMETHOD_DVD = Column(String(256))
    RIPMETHOD_BR = Column(String(256))
    MKV_ARGS = Column(String(256))
    DELRAWFILES = Column(Boolean)
    HB_PRESET_DVD = Column(String(256))
    HB_PRESET_BD = Column(String(256))
    DEST_EXT = Column(String(256))
    HANDBRAKE_CLI = Column(String(256))
    HANDBRAKE_LOCAL = Column(String(256))
    MAINFEATURE = Column(Boolean)
    HB_ARGS_DVD = Column(String(256))
    HB_ARGS_BD = Column(String(256))
    EMBY_REFRESH = Column(Boolean)
    EMBY_SERVER = Column(String(256))
    EMBY_PORT = Column(Integer)
    EMBY_CLIENT = Column(String(256))
    EMBY_DEVICE = Column(String(256))
    EMBY_DEVICEID = Column(String(256))
    EMBY_USERNAME = Column(String(256))
    EMBY_USERID = Column(String(256))
    EMBY_PASSWORD = Column(String(256))
    EMBY_API_KEY = Column(String(256))
    NOTIFY_RIP = Column(Boolean)
    NOTIFY_TRANSCODE = Column(Boolean)
    NOTIFY_JOBID = Column(Boolean)
    PB_KEY = Column(String(256))
    IFTTT_KEY = Column(String(256))
    IFTTT_EVENT = Column(String(256))
    PO_USER_KEY = Column(String(256))
    PO_APP_KEY = Column(String(256))
    OMDB_API_KEY = Column(String(256))
    TMDB_API_KEY = Column(String(256))
    JSON_URL = Column(String(256))
    APPRISE = Column(String(256))
    

    def __init__(self, config_name=None, config_value=None, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.config_name = config_name
        self.config_value = config_value


    def __repr__(self):
        return f'<RipperConfig: {self.__dict__}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + str(self.__dict__)