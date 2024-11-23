import logging
import os

import pyudev

from arm.ui import db


class SystemDrives(db.Model):
    """
    Class to hold the system cd/dvd/Blu-ray drive information
    """
    drive_id = db.Column(db.Integer, index=True, primary_key=True)
    name = db.Column(db.String(100))
    type = db.Column(db.String(20))
    mount = db.Column(db.String(100))
    open = db.Column(db.Boolean)
    job_id_current = db.Column(db.Integer, db.ForeignKey("job.job_id"))
    job_id_previous = db.Column(db.Integer, db.ForeignKey("job.job_id"))
    description = db.Column(db.Unicode(200))
    drive_mode = db.Column(db.String(100))

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
        self.drive_mode = "auto"

    def drive_type(self):
        """find the Drive type (CD, DVD, Blu-ray) from the udev values"""
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
        """new job assigned to the drive, update with new job id, and previous job_id"""
        self.job_id_previous = self.job_id_current
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
