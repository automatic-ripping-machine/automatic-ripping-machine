import enum
import logging
import os
import psutil
import pyudev
import time

from datetime import datetime as dt
from prettytable import PrettyTable
from sqlalchemy.ext.hybrid import hybrid_property

from arm.ripper import music_brainz
from arm.database import db
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

    # Disc identification phase
    IDENTIFYING = "identifying"
    """Indicate that ARM is identifying the disc (reading label, querying APIs)."""

    # Job identified and ready to rip
    IDLE = "ready"
    """Job has been identified and is ready to proceed to ripping."""

    # Video Ripping States
    VIDEO_RIPPING = "ripping"
    """Indicate that makemkv is ripping."""
    VIDEO_WAITING = "waiting"
    """Indicate that the job waits for user input or for the next queue slot."""
    VIDEO_INFO = "info"
    """Indicate that the job calls makemkv info"""

    # Audio ripping states
    AUDIO_RIPPING = "ripping"

    # Post-rip states
    COPYING = "copying"
    """Indicate that ripped files are being moved to shared/network storage."""
    EJECTING = "ejecting"
    """Indicate that the disc is being ejected from the drive."""

    # Transcoding states
    TRANSCODE_ACTIVE = "transcoding"
    TRANSCODE_WAITING = "waiting_transcode"


JOB_STATUS_FINISHED = {
    JobState.SUCCESS,
    JobState.FAILURE,
}
JOB_STATUS_RIPPING = {
    JobState.IDENTIFYING,
    JobState.AUDIO_RIPPING,
    JobState.VIDEO_RIPPING,
    JobState.MANUAL_WAIT_STARTED,  # <-- not ripping, but undistinguishable
    JobState.VIDEO_WAITING,
    JobState.VIDEO_INFO,
    JobState.COPYING,
    JobState.EJECTING,
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
    disctype = db.Column(db.String(20))  # dvd/bluray/bluray4k/data/music/unknown
    label = db.Column(db.String(256))
    path = db.Column(db.String(256))
    raw_path = db.Column(db.String(256))
    transcode_path = db.Column(db.String(256))
    # Music structured fields
    artist = db.Column(db.String(256))
    artist_auto = db.Column(db.String(256))
    artist_manual = db.Column(db.String(256))
    album = db.Column(db.String(256))
    album_auto = db.Column(db.String(256))
    album_manual = db.Column(db.String(256))
    # TV structured fields
    season = db.Column(db.String(10))
    season_auto = db.Column(db.String(10))
    season_manual = db.Column(db.String(10))
    episode = db.Column(db.String(10))
    episode_auto = db.Column(db.String(10))
    episode_manual = db.Column(db.String(10))
    transcode_overrides = db.Column(db.Text, nullable=True)  # JSON dict of per-job transcode settings
    multi_title = db.Column(db.Boolean, default=False)
    disc_number = db.Column(db.Integer, nullable=True)
    disc_total = db.Column(db.Integer, nullable=True)
    tvdb_id = db.Column(db.Integer, nullable=True)
    ejected = db.Column(db.Boolean)
    updated = db.Column(db.Boolean)
    pid = db.Column(db.Integer)
    pid_hash = db.Column(db.Integer)
    is_iso = db.Column(db.Boolean)
    source_type = db.Column(db.String(16), default="disc", nullable=False, server_default="disc")
    source_path = db.Column(db.String(1024), nullable=True)
    manual_start = db.Column(db.Boolean)
    manual_pause = db.Column(db.Boolean)
    manual_mode = db.Column(db.Boolean)
    wait_start_time = db.Column(db.DateTime, nullable=True)
    tracks = db.relationship('Track', backref='job', lazy='dynamic')
    config = db.relationship('Config', uselist=False, backref="job")

    def __init__(self, devpath, _skip_hardware=False):
        """Return a disc object"""
        self.devpath = devpath
        self.mountpoint = ""
        self.hasnicetitle = False
        self.video_type = "unknown"
        self.ejected = False
        self.updated = False
        if cfg.arm_config.get('VIDEOTYPE', 'auto') != "auto":
            self.video_type = cfg.arm_config['VIDEOTYPE']
        if not _skip_hardware:
            self.parse_udev()
            self.get_pid()
        self.stage = ""
        self.manual_start = False
        self.manual_pause = False
        self.manual_mode = False
        self.has_track_99 = False

    @classmethod
    def from_folder(cls, source_path: str, disctype: str):
        """Create a Job from a folder path, bypassing udev/drive detection."""
        job = cls(
            devpath=None,
            _skip_hardware=True,
        )
        job.source_type = "folder"
        job.source_path = source_path
        job.disctype = disctype
        job.start_time = dt.now()
        job.is_iso = False
        if cfg.arm_config.get('VIDEOTYPE', 'auto') != "auto":
            job.video_type = cfg.arm_config['VIDEOTYPE']
        return job

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
            # UHD Blu-rays use AACS2 and have a /CERTIFICATE/id.bdmv file
            if os.path.isfile(self.mountpoint + "/CERTIFICATE/id.bdmv"):
                logging.debug(f"Found: {self.mountpoint}/CERTIFICATE/id.bdmv — UHD Blu-ray")
                self.disctype = "bluray4k"
            else:
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

        # Create placeholder tracks from the disc TOC so the UI can
        # display track durations during the manual-wait period.
        music_brainz.create_toc_tracks(self, disc_id)

        mb_title = music_brainz.get_title(disc_id, self)
        logging.debug(f"mm_title: {mb_title}")

        if mb_title == "not identified":
            self.label = self.title = mb_title
            return "music_cd"
        else:
            return mb_title

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
        self.drive.eject()
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

    @property
    def makemkv_source(self) -> str:
        """Return the MakeMKV source string for this job."""
        if self.source_type == "folder":
            return f"file:{self.source_path}"
        return f"dev:{self.devpath}"

    @property
    def is_folder_import(self) -> bool:
        """Return True if this job was created from a folder import."""
        return self.source_type == "folder"

    @property
    def type_subfolder(self):
        """Map video_type to filesystem subfolder: movies/tv/music/unidentified."""
        if self.video_type == "movie":
            return "movies"
        elif self.video_type == "series":
            return "tv"
        elif self.video_type == "music":
            return "music"
        return "unidentified"

    def _pattern_fields_available(self):
        """Check if the structured fields needed for pattern rendering are populated.
        Movies: always available (just need title).
        Music: need artist or album.
        Series: need season or episode.
        """
        if self.video_type == 'music':
            return bool(
                getattr(self, 'artist', None) or getattr(self, 'artist_manual', None)
                or getattr(self, 'album', None) or getattr(self, 'album_manual', None)
            )
        elif self.video_type == 'series':
            return bool(
                getattr(self, 'season', None) or getattr(self, 'season_manual', None)
                or getattr(self, 'episode', None) or getattr(self, 'episode_manual', None)
            )
        return True

    @property
    def formatted_title(self):
        """Title formatted for filesystem paths, using pattern engine if available.
        Falls back to 'Title (Year)' or 'Title'."""
        if self._pattern_fields_available():
            try:
                from arm.ripper.naming import render_title
                result = render_title(self, cfg.arm_config)
                if result:
                    return result
            except Exception:
                pass
        title = self.title_manual if self.title_manual else self.title
        if self.year and self.year != "0000" and self.year != "":
            return f"{title} ({self.year})"
        return f"{title}"

    def build_raw_path(self):
        """Compute the raw rip directory path.
        Uses title_auto (original auto-detected title) to match the actual
        directory on disk, even after manual title correction."""
        return os.path.join(str(self.config.RAW_PATH), str(self.title_auto or self.title))

    def build_transcode_path(self):
        """Compute the transcode output directory path, using folder pattern."""
        if self._pattern_fields_available():
            try:
                from arm.ripper.naming import render_folder
                folder = render_folder(self, cfg.arm_config)
                if folder:
                    return os.path.join(self.config.TRANSCODE_PATH, self.type_subfolder, folder)
            except Exception:
                pass
        return os.path.join(self.config.TRANSCODE_PATH, self.type_subfolder, self.formatted_title)

    def build_final_path(self):
        """Compute the final completed media directory path, using folder pattern.

        For TV series with USE_DISC_LABEL_FOR_TV enabled, uses disc label-based
        folder naming (e.g. "Breaking_Bad_S1D1").  When GROUP_TV_DISCS_UNDER_SERIES
        is also enabled, adds a parent series folder level.
        """
        from arm.ripper.utils import get_tv_folder_name, get_tv_series_parent_folder

        # TV series disc label naming overrides the normal pipeline
        if self.video_type == "series" and getattr(self.config, 'USE_DISC_LABEL_FOR_TV', False):
            folder = get_tv_folder_name(self)
            if not folder:
                folder = self.formatted_title
            if getattr(self.config, 'GROUP_TV_DISCS_UNDER_SERIES', False):
                parent = get_tv_series_parent_folder(self)
                return os.path.join(self.config.COMPLETED_PATH, self.type_subfolder, parent, folder)
            return os.path.join(self.config.COMPLETED_PATH, self.type_subfolder, folder)

        if self._pattern_fields_available():
            try:
                from arm.ripper.naming import render_folder
                folder = render_folder(self, cfg.arm_config)
                if folder:
                    return os.path.join(self.config.COMPLETED_PATH, self.type_subfolder, folder)
            except Exception:
                pass
        return os.path.join(self.config.COMPLETED_PATH, self.type_subfolder, self.formatted_title)
