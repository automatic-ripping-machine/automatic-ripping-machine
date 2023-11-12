"""
Hold all models for ARM
"""
import datetime
import os
import subprocess
import logging
import time
import pyudev
import psutil
import platform
import re

from prettytable import PrettyTable
from flask_login import LoginManager, current_user, login_user, UserMixin  # noqa: F401
from arm.ripper import music_brainz
from arm.ui import db
import arm.config.config as cfg
from arm.models.job import Job

class AlembicVersion(db.Model):
    """
    Class to hold the A.R.M db version
    """
    version_num = db.Column(db.String(36), autoincrement=False, primary_key=True)

    def __init__(self, version=None):
        self.version_num = version

    def __repr__(self):
        return f'<AlembicVersion: {self.version_num}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.version_num


class UISettings(db.Model):
    """
    Class to hold the A.R.M ui settings
    """
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


class Notifications(db.Model):
    """
    Class to hold the A.R.M notifications
    """
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    seen = db.Column(db.Boolean)
    trigger_time = db.Column(db.DateTime)
    dismiss_time = db.Column(db.DateTime)
    title = db.Column(db.String(256))
    message = db.Column(db.String(256))
    diff_time = None
    cleared = db.Column(db.Boolean, default=False, nullable=False)
    cleared_time = db.Column(db.DateTime)

    def __init__(self, title=None, message=None):
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


class SystemInfo(db.Model):
    """
    Class to hold the system (server) information
    """
    id = db.Column(db.Integer, index=True, primary_key=True)
    name = db.Column(db.String(100))
    cpu = db.Column(db.String(20))
    description = db.Column(db.Unicode(200))
    mem_total = db.Column(db.Float())

    def __init__(self, name="ARM Server", description="Automatic Ripping Machine main server"):
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


class SystemDrives(db.Model):
    """
    Class to hold the system cd/dvd/blueray drive information
    """
    drive_id = db.Column(db.Integer, index=True, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(20))
    mount = db.Column(db.String(100))
    open = db.Column(db.Boolean)
    job_id_current = db.Column(db.Integer, db.ForeignKey("job.job_id"))
    job_id_previous = db.Column(db.Integer, db.ForeignKey("job.job_id"))
    description = db.Column(db.Unicode(200))

    # relationship - join current and previous jobs to the jobs table
    job_current = db.relationship("Job", backref="Current", foreign_keys=[job_id_current])
    job_previous = db.relationship("Job", backref="Previous", foreign_keys=[job_id_previous])

    def __init__(self, name, mount, job, job_previous, description):
        self.name = name
        self.mount = mount
        self.open = False
        self.job_id_current = job
        self.job_id_previous = job_previous
        self.description = description
        self.drive_type()

    def drive_type(self):
        """find the Drive type (CD, DVD, Blueray) from the udev values"""
        context = pyudev.Context()
        device = pyudev.Devices.from_device_file(context, self.mount)
        temp = ""

        for key, value in device.items():
            if key == "ID_CDROM" and value:
                temp += "CD"
            elif key == "ID_CDROM_DVD" and value:
                temp += "/DVD"
            elif key == "ID_CDROM_BD" and value:
                temp += "/BluRay"
        self.type = temp

    def new_job(self, job_id):
        """new job assigned to the drive, add the job id"""
        self.job_id_current = job_id

    def job_finished(self):
        """update Job IDs between current and previous jobs"""
        self.job_id_previous = self.job_id_current
        self.job_id_current = None
        # eject drive (not implemented, as job.eject() decleared in a lot of places)
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
