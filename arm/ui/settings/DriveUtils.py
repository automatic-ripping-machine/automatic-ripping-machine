"""
Functions to manage drives
UI Utils
- drives_search
- drives_update
- update_job_status
- job_cleanup
Ripper Utils
- update_drive_job
"""

import dataclasses
import logging

import pyudev

from arm.models import SystemDrives, Job
from arm.ui import app, db


DRIVE_INFORMATION = (
    "DEVNAME",
    "ID_VENDOR_ENC",  # ID_VENDOR (with encoded characters)
    "ID_MODEL_ENC",  # ID_MODEL (with encoded characters)
    "ID_SERIAL_SHORT",
    "ID_SERIAL",
)


@dataclasses.dataclass(order=True)
class DriveInformation:
    """Basic Optical Drive Information from pyudev

    Besides the mount point, this information is considered static per drive.

    @see arm.ripper.makemkv.Drive

    for pyudev fields, see `DRIVE_INFORMATION`
    """
    mount: str
    """Device Mount Point (sort index, dynamic)"""
    # static per drive:
    maker: str
    """Device Manufacturer"""
    model: str
    """Device Model"""
    serial: str
    """Device Serial"""
    name: str
    """Drive Name (Maker+Model+Serial)"""

    def __post_init__(self):
        # handle (encoded characters like \x20)
        self.maker = bytes(self.maker, encoding="utf-8").decode("unicode_escape")
        self.model = bytes(self.model, encoding="utf-8").decode("unicode_escape")


DRIVE_INFORMATION_EXTENDED = (
    "ID_BUS",
    "ID_CDROM_CD",
    "ID_CDROM_DVD",
    "ID_CDROM_BD",
    "ID_REVISION",
    "ID_PATH",
)


@dataclasses.dataclass
class DriveInformationExtended(DriveInformation):
    """Extended Optical Drive Information

    for pyudev fields, see `DRIVE_INFORMATION_EXTENDED`
    """
    # static per drive:
    connection: str
    """Device Bus Connection e.g. usb, ata"""
    read_cd: bool
    """Device can read cd"""
    read_dvd: bool
    """Device can read dvd"""
    read_bd: bool
    """Device can read bluray"""
    # dynamic per drive:
    firmware: str
    """Device Firmware (changes on FW update)"""
    location: str
    """connection of device on hardware (changes on re-plugging)"""

    @staticmethod
    def _convert_bool(value):
        if isinstance(value, (str, int, float, bool)):
            return bool(int(value))
        return False

    def __post_init__(self):
        super().__post_init__()
        self.read_cd = self._convert_bool(self.read_cd)
        self.read_dvd = self._convert_bool(self.read_dvd)
        self.read_bd = self._convert_bool(self.read_bd)


DRIVE_INFORMATION_MEDIUM = (
    "ID_FS_LABEL",
    "ID_CDROM_MEDIA",
    "ID_CDROM_MEDIA_CD",
    "ID_CDROM_MEDIA_DVD",
    "ID_CDROM_MEDIA_BD",
)


@dataclasses.dataclass
class DriveInformationMedium(DriveInformationExtended):
    """Drive Information that changes per disc

    for pyudev fields, see `DRIVE_INFORMATION_MEDIUM`
    """
    disc: str
    """Disc Name (changes)"""
    loaded: bool
    """Device has Medium loaded (changes)"""
    media_cd: bool
    """Medium is CD (changes)"""
    media_dvd: bool
    """Medium is DVD (changes)"""
    media_bd: bool
    """Medium is BluRay (changes)"""

    def __post_init__(self):
        super().__post_init__()
        self.loaded = self._convert_bool(self.loaded)
        self.media_cd = self._convert_bool(self.media_cd)
        self.media_dvd = self._convert_bool(self.media_dvd)
        self.media_bd = self._convert_bool(self.media_bd)


def drives_search():
    """Search the system for optical drives.
    """
    context = pyudev.Context()
    for device in context.list_devices(subsystem="block"):
        if device.properties.get("ID_TYPE") == "cd":
            fields = (
                DRIVE_INFORMATION +
                DRIVE_INFORMATION_EXTENDED +
                DRIVE_INFORMATION_MEDIUM
            )
            yield DriveInformationMedium(*map(device.properties.get, fields))


def drives_update():
    """
    scan the system for new cd/dvd/Blu-ray drives and update the database

    - `name` is assumed persistent/unique.
    - `mount` point may change for USB devices
    """
    drive_count = SystemDrives.query.count()

    # Mark all drives as stale
    for db_drive in SystemDrives.query.all():
        db_drive.location = ""
        db_drive.stale = True
        db_drive.mdisc = None  # ToDo: Mdisc should not be updated every time the settings page is shown.
        db.session.add(db_drive)
    db.session.commit()

    # Update drive information:
    for drive in sorted(drives_search()):  # sorted by mount point
        app.logger.debug(drive)
        # Retrieve the drive matching `drive.name` from the
        # database or create a new entry if it doesn't exist. Since
        # `drive.name` *may* not be unique, we update only the first drive that
        # misses the mdisc value and was not updated prior to this branch. The
        # result is sorted by mount points to update only the drive with the
        # alphabetically first mount point.
        # If no `drive.name` is found (e.g. on first run), take the pre-existing
        # mount point and update the name there.
        query = (
            SystemDrives
            .query
            .filter_by(name=drive.name, stale=True)
            .order_by(SystemDrives.mount)
        )
        if db_drive := query.first():
            app.logger.debug("Update drive '%s' by serial.", drive.name)
        elif db_drive := SystemDrives.query.filter_by(mount=drive.mount).first():
            app.logger.debug("Update drive '%s' by mount path.", drive.mount)
        else:
            msg = "Create a new drive entity in the database for '%s' on '%s'."
            app.logger.debug(msg, drive.name, drive.mount)
            db_drive = SystemDrives()
        db_drive.update(drive)
        db.session.add(db_drive)
        db.session.commit()  # needed to get drive_id for new entities

        # Remove conflicting mount points in database to ensure that we have
        # a set of unique mount points entries.
        conflicting_drives = (
            SystemDrives
            .query
            .filter(
                SystemDrives.drive_id != db_drive.drive_id,
                SystemDrives.mount == db_drive.mount,
            )
        )
        for conflicting_drive in conflicting_drives.all():
            conflicting_drive.mount = ""
            db.session.add(conflicting_drive)
        db.session.commit()

    # remove and log stale mount points
    stale_count = 0
    for stale_drive in SystemDrives.query.filter_by(stale=True).all():
        msg = "Drive '%s' on '%s' is not available."
        app.logger.debug(msg, stale_drive.name, stale_drive.mount)
        stale_drive.mount = ""
        stale_count += 1
        db.session.add(stale_drive)
        db.session.commit()
    if stale_count > 0:
        app.logger.info("%d drives are unavailable.", stale_count)

    return drive_count - SystemDrives.query.count()


def update_job_status():
    """
    Check the drive job status
    """
    drives = SystemDrives.query.all()
    for drive in drives:
        # Check if the current job is active, if not remove current job_current id
        if drive.job_id_current is not None and drive.job_id_current > 0 and drive.job_current is not None:
            if drive.job_current.status in ("success", "fail"):
                drive.job_finished()
                db.session.commit()

        # Catch if a user has removed database entries and the previous job doesn't exist
        if drive.job_previous is not None and drive.job_previous.status is None:
            drive.job_id_previous = None
            db.session.commit()

        # Check if drive mode is Null (default)
        if drive.drive_mode is None:
            drive.drive_mode = "auto"
            db.session.commit()

        app.logger.debug("Drive Mode: %s", drive.drive_mode)


def job_cleanup(job_id):
    """
    Function called when removing a job from the database, removing the data in the previous job field
    """
    job = Job.query.filter_by(job_id=job_id).first()
    drive = SystemDrives.query.filter_by(mount=job.devpath).first()
    drive.job_id_previous = None
    app.logger.debug(f"Job {job.job_id} cleared from drive {drive.mount} previous")


def update_drive_job(job):
    """
    Function to take the current job task and update the associated drive ID into the database
    """
    drive = SystemDrives.query.filter_by(mount=job.devpath).first()
    drive.new_job(job.job_id)
    app.logger.debug(f"Updating Drive: ['{drive.name}'|'{drive.mount}']"
                     f" Current Job: [{drive.job_id_current}]"
                     f" Previous Job: [{drive.job_id_previous}]")
    try:
        db.session.commit()
        logging.debug("Database update with new Job ID to associated drive")
    except Exception as error:  # noqa: E722
        logging.error(f"Failed to update the database with the associated drive. {error}")


def get_drives():
    """
    Wrapper around SystemDrives Database
    """
    return SystemDrives.query.order_by(SystemDrives.mount).all()
