from models.arm_models import ARMModel
from ui.ui_setup import db


class SystemDrives(ARMModel):
    """
    ARM Database Model - System Drives

    This class holds information about CD/DVD/Blu-ray drives installed in the system,
    including drive ID, name, type, mount point, open status, current and previous job associations,
    and a description.

    Database Table:
        system_drives

    Attributes:
        drive_id (int): The unique identifier for the drive.
        name (str): The name of the drive.
        type (str): The type of the drive (e.g., CD, DVD, Blu-ray).
        mount (str): The mount point of the drive.
        open (bool): Indicates whether the drive tray is open.
        job_id_current (int): The ID of the current job associated with the drive.
        job_id_previous (int): The ID of the previous job associated with the drive.
        description (str): Description of the drive.

    Relationships:
        job_current (relationship): Relationship to the current job associated with the drive.
        job_previous (relationship): Relationship to the previous job associated with the drive.
    """
    __tablename__ = 'system_drives'

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

    def __init__(self, name: str, mount: str, job: int, job_previous: int, description: str, type: str):
        self.name = name
        self.mount = mount
        self.open = False
        self.job_id_current = job
        self.job_id_previous = job_previous
        self.description = description
        self.type = type

    # TODO: this is a flask dataclass and should not contain functions, remove to a new class or function file
    # def drive_type(self):
    #     """find the Drive type (CD, DVD, Blu-ray) from the udev values"""
    #     context = pyudev.Context()
    #     device = pyudev.Devices.from_device_file(context, self.mount)
    #     temp = ""
    #
    #     for key, value in device.items():
    #         if key == "ID_CDROM" and value:
    #             temp += "CD"
    #         elif key == "ID_CDROM_DVD" and value:
    #             temp += "/DVD"
    #         elif key == "ID_CDROM_BD" and value:
    #             temp += "/BluRay"
    #     self.type = temp
    #
    # def new_job(self, job_id):
    #     """new job assigned to the drive, update with new job id, and previous job_id"""
    #     self.job_id_previous = self.job_id_current
    #     self.job_id_current = job_id
    #
    # def job_finished(self):
    #     """update Job IDs between current and previous jobs"""
    #     self.job_id_previous = self.job_id_current
    #     self.job_id_current = None
    #     # eject drive (not implemented, as job.eject() declared in a lot of places)
    #     # self.open_close()
    #
    # def open_close(self):
    #     """Open or Close the drive"""
    #     if self.open:
    #         # If open, then close the drive
    #         try:
    #             os.system("eject -tv " + self.mount)
    #             self.open = False
    #         except Exception as error:
    #             logging.debug(f"{self.mount} unable to be closed {error}")
    #     else:
    #         # if closed, open/eject the drive
    #         if self.job_id_current:
    #             logging.debug(f"{self.mount} unable to eject - current job [{self.job_id_current}] is in progress.")
    #         else:
    #             try:
    #                 # eject the drive
    #                 # eject returns 0 for successful, 1 for failure
    #                 if not bool(os.system("eject -v " + self.mount)):
    #                     logging.debug(f"Ejected disc {self.mount}")
    #                 else:
    #                     logging.debug(f"Failed to eject {self.mount}")
    #                 self.open = True
    #             except Exception as error:
    #                 logging.debug(f"{self.mount} couldn't be ejected {error}")
