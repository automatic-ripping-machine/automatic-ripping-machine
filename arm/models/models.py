import os
import pyudev
import psutil
from arm.ui import db
from arm.config.config import cfg  # noqa: E402


class Job(db.Model):
    job_id = db.Column(db.Integer, primary_key=True)
    arm_version = db.Column(db.String(20))
    crc_id = db.Column(db.String(63))
    logfile = db.Column(db.String(256))
    disc = db.Column(db.String(63))
    start_time = db.Column(db.DateTime)
    stop_time = db.Column(db.DateTime)
    job_length = db.Column(db.String(12))
    status = db.Column(db.String(32))
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
    ejected = db.Column(db.Boolean)
    updated = db.Column(db.Boolean)
    pid = db.Column(db.Integer)
    pid_hash = db.Column(db.Integer)
    tracks = db.relationship('Track', backref='job', lazy='dynamic')

    def __init__(self, devpath):
        """Return a disc object"""
        self.devpath = devpath
        self.mountpoint = "/mnt" + devpath
        self.hasnicetitle = False
        self.video_type = "unknown"
        self.ejected = False
        self.updated = False
        if cfg['VIDEOTYPE'] != "auto":
            self.video_type = cfg['VIDEOTYPE']

        self.parse_udev()
        self.get_pid()

    def parse_udev(self):
        """Parse udev for properties of current disc"""

        # print("Entering disc")
        context = pyudev.Context()
        device = pyudev.Devices.from_device_file(context, self.devpath)
        self.disctype = "unknown"
        for key, value in device.items():
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
                pass

    def get_pid(self):
        pid = os.getpid()
        p = psutil.Process(pid)
        self.pid = pid
        self.pid_hash = hash(p)

    def __str__(self):
        """Returns a string of the object"""

        s = self.__class__.__name__ + ": "
        for attr, value in self.__dict__.items():
            s = s + "(" + str(attr) + "=" + str(value) + ") "

        return s

    def __repr__(self):
        return '<Job {}>'.format(self.label)

    def eject(self):
        """Eject disc if it hasn't previously been ejected"""

        # print("Value is " + str(self.ejected))
        if not self.ejected:
            os.system("eject " + self.devpath)
            self.ejected = True


class Track(db.Model):
    track_id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.job_id'))
    track_number = db.Column(db.String(4))
    length = db.Column(db.Integer)
    aspect_ratio = db.Column(db.String(20))
    blocks = db.Column(db.Integer)
    fps = db.Column(db.Float)
    main_feature = db.Column(db.Boolean)
    basename = db.Column(db.String(256))
    filename = db.Column(db.String(256))
    orig_filename = db.Column(db.String(256))
    new_filename = db.Column(db.String(256))
    ripped = db.Column(db.Boolean)

    def __init__(self, job_id, track_number, length, aspect_ratio, blocks, fps, main_feature, basename, filename, orig_filename):
        """Return a track object"""
        self.job_id = job_id
        self.track_number = track_number
        self.length = length
        self.aspect_ratio = aspect_ratio
        self.blocks = blocks
        self.fps = fps
        self.main_feature = main_feature
        self.basename = basename
        self.filename = filename
        self.orig_filename = orig_filename
        self.ripped = False

    def __repr__(self):
        return '<Post {}>'.format(self.track_number)
