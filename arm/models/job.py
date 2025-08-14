import enum
import logging
import os
import psutil
import pyudev
import subprocess
import time

from datetime import datetime as dt
from prettytable import PrettyTable
from sqlalchemy.ext.hybrid import hybrid_property

from arm.ripper import music_brainz
from arm.ui import db
import arm.config.config as cfg

# THESE IMPORTS ARE REQUIRED FOR THE db.Relationships to work
from arm.models.track import Track  # noqa: F401
from arm.models.config import Config  # noqa: F401


class JobState(str, enum.Enum):
    """Possible states for Job.status.

    The origin of the states is getting unclear at this point. Therefore, the
    possible `Job.status` states are defined as fixed enums to handle and group
    them better. Some come from CD, some from DVD ripping.

    Note: The timestamps could also be saved particularily for each step to
          show, for example, the pure transcoding time without the waiting
          time.
    """

    # Job Finished States
    SUCCESS = "success"
    FAILURE = "fail"

    # Manual wait (see job.config.MANUAL_WAIT)
    MANUAL_WAIT_STARTED = "waiting"

    # Job Initialized or Pending
    IDLE = "active"
    """An Idle Job may proceed to ripping or to finished.

    - When initializing a job, the job is set to active
    - After Handbrake finishes, Job is set to active
    - After ABCD finishes, Job is set to active
    """

    # Video Ripping States
    VIDEO_RIPPING = "ripping"
    """Indicate that makemkv is ripping."""
    VIDEO_WAITING = "waiting"
    """Indicate that the job waits for user input or for the next queue slot."""
    VIDEO_INFO = "info"
    """Indicate that the job calls makemkv info"""

    # Audio ripping states
    AUDIO_RIPPING = "ripping"

    # Transcoding states
    TRANSCODE_ACTIVE = "transcoding"
    TRANSCODE_WAITING = "waiting_transcode"


JOB_STATUS_FINISHED = {
    JobState.SUCCESS,
    JobState.FAILURE,
}
JOB_STATUS_RIPPING = {
    JobState.AUDIO_RIPPING,
    JobState.VIDEO_RIPPING,
    JobState.MANUAL_WAIT_STARTED,  # <-- not ripping, but undistinguishable
    JobState.VIDEO_WAITING,
    JobState.VIDEO_INFO,
}
JOB_STATUS_TRANSCODING = {
    JobState.TRANSCODE_ACTIVE,
    JobState.TRANSCODE_WAITING,
}


class Job(db.Model):
    """
    Job Class hold most of the details for each job
    connects to track, config
    """
    job_id = db.Column(db.Integer, primary_key=True)
    arm_version = db.Column(db.String(20))
    crc_id = db.Column(db.String(63))
    logfile = db.Column(db.String(256))
    start_time = db.Column(db.DateTime)
    stop_time = db.Column(db.DateTime)
    job_length = db.Column(db.String(12))
    status = db.Column(db.String(32))
    """Now that we have JobState, we should migrate this column.
    status = db.Column(
        db.Enum(JobState, name="job_state_enum", native_enum=False, validate_strings=True),
        nullable=False
    )
    """
    stage = db.Column(db.String(63))
    no_of_titles = db.Column(db.Integer)
    title = db.Column(db.String(256))
    title_auto = db.Column(db.String(256))
    title_manual = db.Column(db.String(256))
    year = db.Column(db.String(4))
    year_auto = db.Column(db.String(4))
    year_manual = db.Column(db.String(4))
    video_type = db.Column(db.String(20))
    video_type_auto = db.Column(db.String(20))
    video_type_manual = db.Column(db.String(20))
    imdb_id = db.Column(db.String(15))
    imdb_id_auto = db.Column(db.String(15))
    imdb_id_manual = db.Column(db.String(15))
    poster_url = db.Column(db.String(256))
    poster_url_auto = db.Column(db.String(256))
    poster_url_manual = db.Column(db.String(256))
    devpath = db.Column(db.String(15))
    mountpoint = db.Column(db.String(20))
    hasnicetitle = db.Column(db.Boolean)
    errors = db.Column(db.Text)
    disctype = db.Column(db.String(20))  # dvd/bluray/data/music/unknown
    label = db.Column(db.String(256))
    path = db.Column(db.String(256))
    ejected = db.Column(db.Boolean)
    updated = db.Column(db.Boolean)
    pid = db.Column(db.Integer)
    pid_hash = db.Column(db.Integer)
    is_iso = db.Column(db.Boolean)
    manual_start = db.Column(db.Boolean)
    manual_mode = db.Column(db.Boolean)
    tracks = db.relationship('Track', backref='job', lazy='dynamic')
    config = db.relationship('Config', uselist=False, backref="job")

    def __init__(self, devpath):
        """Return a disc object"""
        self.devpath = devpath
        self.mountpoint = "/mnt" + devpath
        self.hasnicetitle = False
        self.video_type = "unknown"
        self.ejected = False
        self.updated = False
        if cfg.arm_config['VIDEOTYPE'] != "auto":
            self.video_type = cfg.arm_config['VIDEOTYPE']
        self.parse_udev()
        self.get_pid()
        self.stage = str(round(time.time() * 100))
        self.manual_start = False
        self.manual_mode = False
        self.has_track_99 = False

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
        context = pyudev.Context()
        device = pyudev.Devices.from_device_file(context, self.devpath)
        self.disctype = "unknown"

        for key, value in device.items():
            logging.debug(f"pyudev: {key}: {value}")
            if key == "ID_FS_LABEL":
                self.label = value
                if value == "iso9660":
                    self.disctype = "data"
            elif key == "ID_CDROM_MEDIA_BD":
                self.disctype = "bluray"
            elif key == "ID_CDROM_MEDIA_DVD":
                self.disctype = "dvd"
            elif key == "ID_CDROM_MEDIA_TRACK_COUNT_AUDIO":
                self.disctype = "music"
            else:
                continue

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
            self.label = music_brainz.main(self)
        elif (os.path.isdir(self.mountpoint + "/AUDIO_TS")
              and len(os.listdir(self.mountpoint + "/AUDIO_TS")) > 0) \
            or (os.path.isdir(self.mountpoint + "/audio_ts")
                and len(os.listdir(self.mountpoint + "/audio_ts")) > 0):
            logging.debug(f"Found: {self.mountpoint}/AUDIO_TS")
            self.disctype = "data"
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
        # Use the music label if we can find it - defaults to music_cd.log
        disc_id = music_brainz.get_disc_id(self)
        logging.debug(f"music_id: {disc_id}")
        mb_title = music_brainz.get_title(disc_id, self)
        logging.debug(f"mm_title: {mb_title}")

        if mb_title == "not identified":
            self.label = self.title = "not identified"
            logfile = "music_cd.log"
            new_log_file = f"music_cd_{round(time.time() * 100)}.log"
        else:
            logfile = f"{mb_title}.log"
            new_log_file = f"{mb_title}_{round(time.time() * 100)}.log"

        temp_log_full = os.path.join(cfg.arm_config['LOGPATH'], logfile)
        logfile = new_log_file if os.path.isfile(temp_log_full) else logfile
        return logfile

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
        """Eject disc if it hasn't previously been ejected
        """
        if self.ejected:
            logging.debug("The drive associated with this job has already been ejected.")
            return
        if self.drive is None:
            logging.warning("No drive was backpopulated with this job!")
            return
        if not cfg.arm_config['AUTO_EJECT']:
            logging.info("Skipping auto eject")
            self.drive.release_current_job()  # release job without ejecting
            return
        # release job from drive after ejecting
        if (error := self.drive.eject(method="eject", logger=logging)) is not None:
            logging.debug(f"{self.devpath} couldn't be ejected: {error}")
        self.ejected = True

    @hybrid_property
    def finished(self):
        return JobState(self.status) in JOB_STATUS_FINISHED

    @finished.expression
    def finished(cls):
        return cls.status.in_([js.value for js in JOB_STATUS_FINISHED])

    @property
    def idle(self):
        return JobState(self.status) == JobState.IDLE

    @property
    def ripping(self):
        return JobState(self.status) in JOB_STATUS_RIPPING

    @property
    def run_time(self):
        return abs(dt.now() - self.start_time).total_seconds()

    @property
    def ripping_finished(self):
        """Indicates that the ripping process has finished.

        Note: This usually means that we are transcoding and the drive is not
              currently used.
        """
        if self.finished:
            logging.info("Job is finished.")
            return True
        if not self.ripping:
            logging.info("Job is not ripping.")
            return True
        if self.drive is None:
            logging.info("No drive was backpopulated with this job!")
            return True
        if self.ejected:
            logging.info(f"Drive {self.devpath} was ejected. No ripping process active.")
            return True
        logging.info(f"Job is ripping {self.devpath}.")
        return False
