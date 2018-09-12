import os
import pyudev
from armui import db


# class Disc(db.Model):
#     crc_id = db.Column(db.String(63), primary_key=True)
#     disctype = db.Column(db.String(20))  #dvd/bluray/data/music/unknown
#     label = db.Column(db.String(256))
#     ejected = db.Column(db.Boolean)
#     jobs = db.relationship('Job', backref='disc', lazy='dynamic')

#     def __init__(self, crc_id):
#         self.eject = False
#         self.parse_udev()

#     def parse_udev(self):
#         """Parse udev for properties of current disc"""

#         # print("Entering disc")
#         context = pyudev.Context()
#         device = pyudev.Devices.from_device_file(context, self.devpath)
#         self.disctype = "unknown"
#         for key, value in device.items():
#             if key == "ID_FS_LABEL":
#                 self.label = value
#                 if value == "iso9660":
#                     self.disctype = "data"
#             elif key == "ID_CDROM_MEDIA_BD":
#                 self.disctype = "bluray"
#             elif key == "ID_CDROM_MEDIA_DVD":
#                 self.disctype = "dvd"
#             elif key == "ID_CDROM_MEDIA_TRACK_COUNT_AUDIO":
#                 self.disctype = "music"
#             else:
#                 pass

#     def __repr__(self):
#         return '<Disc CRC {}>'.format(self.crc_id) 


class Job(db.Model):
    job_id = db.Column(db.Integer, primary_key=True)
    arm_version = db.Column(db.String(20))
    crc_id = db.Column(db.String(63))
    logfile = db.Column(db.String(256))
    disc = db.Column(db.String(63), db.ForeignKey('disc.crc_id'))
    start_time = db.Column(db.DateTime)
    stop_time = db.Column(db.DateTime)
    job_length = db.Column(db.Integer)
    status = db.Column(db.String(32))
    video_type = db.Column(db.String(20))
    title = db.Column(db.String(256))
    year = db.Column(db.Integer)
    new_title = db.Column(db.String(256))
    new_year = db.Column(db.Integer)
    devpath = db.Column(db.String(15))
    mountpoint = db.Column(db.String(20))
    hasnicetitle = db.Column(db.Boolean)
    errors = db.Column(db.Text)
    disctype = db.Column(db.String(20))  # dvd/bluray/data/music/unknown
    label = db.Column(db.String(256))
    ejected = db.Column(db.Boolean)

    def __init__(self, devpath):
        """Return a disc object"""
        self.devpath = devpath
        self.mountpoint = "/mnt" + devpath
        # self.title = ""
        # self.year = ""
        # self.video_type = ""
        self.hasnicetitle = False
        # self.label = ""
        # self.disctype = ""
        self.ejected = False
        # self.errors = []

        self.parse_udev()

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


# class Movie(db.Model):
#     movid_id = db.Column(db.Integer, primary_key=True)
#     imdb_id = db.Column(db.String(256))
#     title = db.Column(db.String(256))
#     year = db.Column(db.Integer)
#     title_ms = db.Column(db.String(256))
#     title_omdb_id = db.Column(db.String(20))

#     def __repr__(self):
#         return '<Movie {}>'.format(self.label) 