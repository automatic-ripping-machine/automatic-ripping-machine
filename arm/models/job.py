# import logging
# import os
# import psutil
# import pyudev
# import subprocess
import time

# from prettytable import PrettyTable
# from arm.ripper import music_brainz
from ui.ui_setup import db
# import arm.config.config as cfg

# ARM Model relationship imports, required for db.Relationships to work
from models.track import Track  # noqa: F401
from models.config import Config  # noqa: F401


class Job(db.Model):
    """
    ARM Database Model - Job

    This class represents a job in the ARM (Automated Ripping Machine) system,
    storing details about each job's execution, including job ID, ARM version,
    CRC ID, logfile path, start and stop times, job length, status, stage,
    number of titles, title information, video type, IMDb ID, poster URL,
    device path, mount point, error details, disc type, label, path,
    and related tracks and configuration.

    Database Table:
        job

    Attributes:
        job_id (int): The unique identifier for the job.
        arm_version (str): The version of the Automated Ripping Machine (ARM) used for the job.
        crc_id (str): CRC ID associated with the job.
        logfile (str): Path to the logfile for the job.
        start_time (DateTime): The start time of the job.
        stop_time (DateTime): The stop time of the job.
        job_length (str): Length or duration of the job.
        status (str): Current status of the job.
        stage (str): Current stage of the job.
        no_of_titles (int): Number of titles processed in the job.
        title (str): Title information associated with the job.
        title_auto (str): Automatically detected title information.
        title_manual (str): Manually specified title information.
        year (str): Year associated with the job.
        year_auto (str): Automatically detected year.
        year_manual (str): Manually specified year.
        video_type (str): Video type of the job.
        video_type_auto (str): Automatically detected video type.
        video_type_manual (str): Manually specified video type.
        imdb_id (str): IMDb ID associated with the job.
        imdb_id_auto (str): Automatically detected IMDb ID.
        imdb_id_manual (str): Manually specified IMDb ID.
        poster_url (str): URL to the poster image associated with the job.
        poster_url_auto (str): Automatically detected poster URL.
        poster_url_manual (str): Manually specified poster URL.
        devpath (str): Device path for the job.
        mountpoint (str): Mount point for the job.
        hasnicetitle (bool): Indicates if the job has a "nice" title.
        errors (str): Details of any errors encountered during the job.
        disctype (str): Type of disc (DVD/Blu-ray/data/music/unknown).
        label (str): Label associated with the job.
        path (str): Path associated with the job.
        ejected (bool): Indicates if the disc was ejected after the job.
        updated (bool): Indicates if the job information has been updated.
        pid (int): Process ID (PID) associated with the job.
        pid_hash (int): Hashed process ID (PID) associated with the job.
        tracks (relationship): Relationship to associated tracks.
        config (relationship): Relationship to associated configuration settings.

    Relationships:
        tracks (relationship): Relationship to associated tracks.
        config (relationship): Relationship to associated configuration settings.
        system_drives (relationship): Relationship to associated system drives.

    """

    __tablename__ = 'job'

    job_id = db.Column(db.Integer, primary_key=True)
    arm_version = db.Column(db.String(256))
    crc_id = db.Column(db.String(256))
    logfile = db.Column(db.String(256))
    start_time = db.Column(db.DateTime)
    stop_time = db.Column(db.DateTime)
    job_length = db.Column(db.String(256))
    status = db.Column(db.String(256))
    stage = db.Column(db.String(256))
    no_of_titles = db.Column(db.Integer)
    title = db.Column(db.String(256))
    title_auto = db.Column(db.String(256))
    title_manual = db.Column(db.String(256))
    year = db.Column(db.String(256))
    year_auto = db.Column(db.String(256))
    year_manual = db.Column(db.String(256))
    video_type = db.Column(db.String(256))
    video_type_auto = db.Column(db.String(256))
    video_type_manual = db.Column(db.String(256))
    imdb_id = db.Column(db.String(256))
    imdb_id_auto = db.Column(db.String(256))
    imdb_id_manual = db.Column(db.String(256))
    poster_url = db.Column(db.String(256))
    poster_url_auto = db.Column(db.String(256))
    poster_url_manual = db.Column(db.String(256))
    devpath = db.Column(db.String(256))
    mountpoint = db.Column(db.String(256))
    hasnicetitle = db.Column(db.Boolean)
    errors = db.Column(db.Text)
    disctype = db.Column(db.String(256))  # dvd/bluray/data/music/unknown
    label = db.Column(db.String(256))
    path = db.Column(db.String(256))
    ejected = db.Column(db.Boolean)
    updated = db.Column(db.Boolean)
    pid = db.Column(db.BigInteger)
    pid_hash = db.Column(db.BigInteger)
    tracks = db.relationship('Track', backref='job', lazy='dynamic')
    config = db.relationship('Config', uselist=False, backref="job")

    def __init__(self, devpath: str):
        self.devpath = devpath
        self.mountpoint = "/mnt" + devpath
        self.hasnicetitle = False
        self.video_type = "unknown"
        self.ejected = False
        self.updated = False
        self.stage = str(round(time.time() * 100))

        # TODO: avoid importing config, pass the value
        # if cfg.arm_config['VIDEOTYPE'] != "auto":
        #     self.video_type = cfg.arm_config['VIDEOTYPE']
        # self.parse_udev()     # TODO: remove or pass in values
        # self.get_pid()        # TODO: remove or pass in values

        # TODO: remove or pass in values
        # if self.disctype == "dvd" and not self.label:
        #     logging.info("No disk label Available. Trying lsdvd")
        #     command = f"lsdvd {devpath} | grep 'Disc Title' | cut -d ' ' -f 3-"
        #     lsdvdlbl = str(subprocess.check_output(command, shell=True).strip(), 'utf-8')
        #     self.label = lsdvdlbl

    def __str__(self):
        """Returns a string of the object"""

        return_string = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            return_string = return_string + "(" + str(attr) + "=" + str(value) + ") "

        return return_string

    def __repr__(self):
        return f'<Job {self.label}>'

    # TODO: remove code from model, move to class or function
    # def parse_udev(self):
    #     """Parse udev for properties of current disc"""
    #     context = pyudev.Context()
    #     device = pyudev.Devices.from_device_file(context, self.devpath)
    #     self.disctype = "unknown"
    #
    #     for key, value in device.items():
    #         logging.debug(f"pyudev: {key}: {value}")
    #         if key == "ID_FS_LABEL":
    #             self.label = value
    #             if value == "iso9660":
    #                 self.disctype = "data"
    #         elif key == "ID_CDROM_MEDIA_BD":
    #             self.disctype = "bluray"
    #         elif key == "ID_CDROM_MEDIA_DVD":
    #             self.disctype = "dvd"
    #         elif key == "ID_CDROM_MEDIA_TRACK_COUNT_AUDIO":
    #             self.disctype = "music"
    #         else:
    #             continue
    #
    # def get_pid(self):
    #     """
    #     Get the jobs process id
    #     :return: None
    #     """
    #     pid = os.getpid()
    #     process_id = psutil.Process(pid)
    #     self.pid = pid
    #     self.pid_hash = hash(process_id)
    #
    # def get_disc_type(self, found_hvdvd_ts):
    #     """
    #     Checks/corrects the current disc-type
    #     :param found_hvdvd_ts:  gets pushed in from utils - saves importing utils
    #     :return: None
    #     """
    #     if self.disctype == "music":
    #         logging.debug("Disc is music.")
    #         self.label = music_brainz.main(self)
    #     elif os.path.isdir(self.mountpoint + "/VIDEO_TS"):
    #         logging.debug(f"Found: {self.mountpoint}/VIDEO_TS")
    #         self.disctype = "dvd"
    #     elif os.path.isdir(self.mountpoint + "/video_ts"):
    #         logging.debug(f"Found: {self.mountpoint}/video_ts")
    #         self.disctype = "dvd"
    #     elif os.path.isdir(self.mountpoint + "/BDMV"):
    #         logging.debug(f"Found: {self.mountpoint}/BDMV")
    #         self.disctype = "bluray"
    #     elif os.path.isdir(self.mountpoint + "/HVDVD_TS"):
    #         logging.debug(f"Found: {self.mountpoint}/HVDVD_TS")
    #         # do something here
    #     elif found_hvdvd_ts:
    #         logging.debug("Found file: HVDVD_TS")
    #         # do something here too
    #     else:
    #         logging.debug("Did not find valid dvd/bd files. Changing disc-type to 'data'")
    #         self.disctype = "data"
    #
    # def identify_audio_cd(self):
    #     """
    #     Get the title for audio cds to use for the logfile name.
    #
    #     Needs the job class passed into it so it can be forwarded to mb
    #
    #     return - only the logfile - setup_logging() adds the full path
    #     """
    #     # Use the music label if we can find it - defaults to music_cd.log
    #     disc_id = music_brainz.get_disc_id(self)
    #     logging.debug(f"music_id: {disc_id}")
    #     mb_title = music_brainz.get_title(disc_id, self)
    #     logging.debug(f"mm_title: {mb_title}")
    #
    #     if mb_title == "not identified":
    #         self.label = self.title = "not identified"
    #         logfile = "music_cd.log"
    #         new_log_file = f"music_cd_{round(time.time() * 100)}.log"
    #     else:
    #         logfile = f"{mb_title}.log"
    #         new_log_file = f"{mb_title}_{round(time.time() * 100)}.log"
    #
    #     temp_log_full = os.path.join(cfg.arm_config['LOGPATH'], logfile)
    #     logfile = new_log_file if os.path.isfile(temp_log_full) else logfile
    #     return logfile
    #
    # def pretty_table(self):
    #     """Returns a string of the prettytable"""
    #     pretty_table = PrettyTable()
    #     pretty_table.field_names = ["Config", "Value"]
    #     pretty_table._max_width = {"Config": 50, "Value": 60}
    #     for attr, value in self.__dict__.items():
    #         if attr == "config":
    #             pretty_table.add_row([str(attr), str(value.pretty_table())])
    #         else:
    #             pretty_table.add_row([str(attr), str(value)])
    #     return str(pretty_table.get_string())
    #
    # def get_d(self):
    #     """
    #     Return a dict of class - exclude the _sa_instance_state
    #     :return: dict containing all attribs from class
    #     """
    #     return_dict = {}
    #     for key, value in self.__dict__.items():
    #         if '_sa_instance_state' not in key:
    #             return_dict[str(key)] = str(value)
    #     return return_dict
    #
    # def eject(self):
    #     """Eject disc if it hasn't previously been ejected"""
    #     if not cfg.arm_config['AUTO_EJECT']:
    #         logging.info("Skipping auto eject")
    #         return
    #     if not self.ejected:
    #         self.ejected = True
    #         try:
    #             # This might always return true
    #             if bool(os.system("umount " + self.devpath)):
    #                 logging.debug(f"Unmounted disc {self.devpath}")
    #             else:
    #                 logging.debug(f"Failed to unmount {self.devpath}")
    #             if bool(os.system("eject -sv " + self.devpath)):
    #                 logging.debug(f"Ejected disc {self.devpath}")
    #             else:
    #                 logging.debug(f"Failed to eject {self.devpath}")
    #         except Exception as error:
    #             logging.debug(f"{self.devpath} couldn't be ejected {error}")
