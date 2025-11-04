"""
Functions to manage drives
UI Utils
- drives_search
- drives_update
- update_job_status
Ripper Utils
- update_drive_job
"""

import dataclasses
import logging
import re
import pyudev

from arm.models import SystemDrives
from arm.ui import app, db


class MaskSerialMeta(type):
    def __init__(cls, name, bases, class_dict):
        super().__init__(name, bases, class_dict)
        cls._apply_masked_repr()

    def _apply_masked_repr(cls):
        original_repr = cls.__repr__ if hasattr(cls, '__repr__') else object.__repr__

        def masked_repr(self):
            """Mask the serial with asterisks in the repr"""
            repr_str = original_repr(self)
            serial = getattr(self, "serial", None)

            if serial and len(serial) > 6:
                masked = serial[:-6] + "*" * 6
            elif serial:  # shorter than 6 chars
                masked = "*" * len(serial)
            else:  # None or empty
                masked = "UNKNOWN"

            return repr_str.replace(str(serial), masked, 1)

        cls.__repr__ = masked_repr


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
    serial_id: str
    """Drive Serial as id (Maker+Model+Serial)"""

    @staticmethod
    def _decode(value):
        """
        Handle (encoded characters like \x20)
        """
        if isinstance(value, str):
            return bytes(value, encoding="utf-8").decode("unicode_escape")
        if value is None:
            return ""
        return str(value).strip()

    def __post_init__(self):
        self.maker = self._decode(self.maker)
        self.model = self._decode(self.model)


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
        # Allow some of the data to be None
        if value in (None, "", "unknown"):
            return False
        try:
            # Test if we have filled values
            return bool(int(value))
        except (ValueError, TypeError):
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
class DriveInformationMedium(DriveInformationExtended, metaclass=MaskSerialMeta):
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
    """
    Search the system for optical drives and yield DriveInformationMedium objects.

    In a container environment, falls back to treating /dev/sr* as optical drives.
    """
    context = pyudev.Context()
    for device in context.list_devices(subsystem="block"):
        try:
            devnode = device.device_node
            if not devnode:
                continue

            # Ignore loop&nvme devices
            if devnode and (devnode.startswith("/dev/loop") or devnode.startswith("/dev/nvme")):
                # Logging here might not be helpful, unsure yet
                # logging.debug("Ignoring loop/nvme device: %s", devnode)
                continue

            # Log all properties - Helps with debugging if a drive has loaded all properties, or just the base
            logging.debug("Device: %s", devnode)
            for key, value in device.properties.items():
                app.logger.debug("  %s = %s", key, value)

            # Optical drive detection - Try to use ID_TYPE then ID_CDROM but fall back to all drives matching /dev/sr*
            # NOTE: this may be better to check if MAJOR = 11
            # + devname `/dev/sr*` and possibly DEVTYPE as this always means its an optical drive on linux
            # But just the first two MAJOR + devname should be more than enough to verify its a CD/DVD drive
            is_optical = (
                device.properties.get("ID_TYPE") == "cd" or
                device.properties.get("ID_CDROM") == "1" or
                re.match(r"^/dev/sr\d+$", devnode)
            )

            if is_optical:
                logging.info("Optical drive detected: %s", devnode)

                # Try to populate fields, but allow missing values incase the drive hasn't been mounted/activated yet
                fields = (
                    DRIVE_INFORMATION +
                    DRIVE_INFORMATION_EXTENDED +
                    DRIVE_INFORMATION_MEDIUM
                )
                values = [device.properties.get(field) or "" for field in fields]
                yield DriveInformationMedium(*values)

        except Exception as e:
            app.logger.error("Error processing device %s: %s", device, e, exc_info=True)


def drives_update(startup=False):
    """
    scan the system for new cd/dvd/Blu-ray drives and update the database

    - `serial_id` is assumed persistent/unique.
    - `mount` point may change for USB devices

    on system startup, clear all mdisc (MakeMKV disc index) values.
    """
    drive_count = SystemDrives.query.count()

    # Mark all drives as stale
    for db_drive in SystemDrives.query.all():
        db_drive.stale = True
        if startup:
            db_drive.mdisc = None
    db.session.commit()

    # Update drive information:
    system_drives = sorted(drives_search())
    if len(system_drives) < 1:
        logging.error(f"We Cant find any system drives!. {system_drives}")
    for drive in system_drives:  # sorted by mount point
        logging.debug(f"Drive info: {drive}")
        # Retrieve the drive matching `drive.serial_id` from the database or
        # create a new entry if it doesn't exist. Since `drive.serial_id` *may*
        # not be unique, we update only the first drive that misses the mdisc
        # value and was not updated prior to this branch. The result is sorted
        # by mount points to update only the drive with the alphabetically
        # first mount point.  If no `drive.serial_id` is found (e.g. on first
        # run), take the pre-existing mount point and update the serial_id
        # there.
        query = (
            SystemDrives
            .query
            .filter_by(serial_id=drive.serial_id, stale=True)
            .order_by(SystemDrives.mount)
        )
        if db_drive := query.first():
            app.logger.debug("Update drive '%s' by serial.", drive.serial_id)
        elif db_drive := SystemDrives.query.filter_by(mount=drive.mount).first():
            app.logger.debug("Update drive '%s' by mount path.", drive.mount)
        else:
            msg = "Create a new drive entity in the database for '%s' on '%s'."
            app.logger.debug(msg, drive.serial_id, drive.mount)
            db_drive = SystemDrives()
            db_drive.name = drive.serial_id
            db.session.add(db_drive)
        db_drive.update(drive)
        db.session.commit()  # needed to get drive_id for new entities
        db_drive.debug(logger=app.logger)

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
        db.session.commit()

    # remove and log stale mount points
    stale_count = 0
    for stale_drive in SystemDrives.query.filter_by(stale=True).all():
        msg = "Drive '%s' on '%s' is not available."
        app.logger.warning(msg, stale_drive.serial_id, stale_drive.mount)
        if stale_drive.processing:
            app.logger.warning(f"Drive '{stale_drive.mount}' has an active job and might be blocked.")
            stale_drive.stale = False
        else:
            stale_drive.mount = ""
            stale_drive.location = ""
            stale_drive.mdisc = None
            stale_count += 1
        db.session.commit()
        stale_drive.debug(logger=app.logger)
    if stale_count > 0:
        app.logger.info("%d drives are unavailable.", stale_count)

    return drive_count - SystemDrives.query.count()


def update_job_status():
    """
    Check the drive job status
    """
    drives = SystemDrives.query.all()
    for drive in drives:
        # Check if the current job is using the drive, if not remove job from drive.
        if drive.processing and drive.job_current.ripping_finished:
            # Note: it is not generally safe to release the job by any means.
            # "transcoding" jobs may also use the drive so an
            logging.info(f"A job is currently running on drive '{drive.name}'")
            if drive.job_current.finished:
                logging.warning(f"Releasing job from drive '{drive.name}'")
                drive.release_current_job()
                db.session.commit()
                continue
            logging.debug("If you want to release the job from the drive, press eject.")

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
    Called when removing a job from the database.

    Note: This makes sure that the job_id is not associated with any of the
          drives.  If keep the job_id associated with the drives, new job_ids
          with the same number are generated by the database messing up our
          association for future jobs.
    """
    for drive in SystemDrives.query.filter_by(job_id_current=job_id):
        drive.job_id_current = None
        app.logger.debug(f"Current Job {job_id} cleared from drive {drive.mount}")
    for drive in SystemDrives.query.filter_by(job_id_previous=job_id):
        drive.job_id_previous = None
        app.logger.debug(f"Current Job {job_id} cleared from drive {drive.mount}")
    db.session.commit()


def update_drive_job(job):
    """
    Function to take the current job task and update the associated drive ID into the database
    """
    drive = SystemDrives.query.filter_by(mount=job.devpath).first()
    drive.new_job(job.job_id)
    app.logger.debug(f"Updating Drive: ['{drive.serial_id}'|'{drive.mount}']"
                     f" Current Job: [{drive.job_id_current}]"
                     f" Previous Job: [{drive.job_id_previous}]")
    try:
        db.session.commit()
        logging.debug("Database update with new Job ID to associated drive")
    except Exception as error:  # noqa: E722
        logging.error(f"Failed to update the database with the associated drive. {error}")


def update_tray_status(drives):
    for drive in drives:
        drive.tray_status()


def get_drives():
    """
    Wrapper around SystemDrives Database
    """
    return SystemDrives.query.order_by(SystemDrives.name, SystemDrives.description, SystemDrives.serial_id).all()
