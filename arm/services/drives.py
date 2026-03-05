"""
Drive management services — extracted from arm/ui/settings/DriveUtils.py.

All app.logger calls replaced with standard logging.
Dataclasses and constants moved here from DriveUtils.py.
"""
import dataclasses
import logging
import re
import time

import pyudev

from arm.models import SystemDrives
from arm.database import db

log = logging.getLogger(__name__)


# ── Drive information dataclasses ─────────────────────────────────────────


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
    """
    context = pyudev.Context()
    for device in context.list_devices(subsystem="block"):
        try:
            devnode = device.device_node
            if not devnode:
                continue

            if devnode and (devnode.startswith("/dev/loop") or devnode.startswith("/dev/nvme")):
                continue

            logging.debug("Device: %s", devnode)
            for key, value in device.properties.items():
                log.debug("  %s = %s", key, value)

            is_optical = (
                device.properties.get("ID_TYPE") == "cd" or
                device.properties.get("ID_CDROM") == "1" or
                re.match(r"^/dev/sr\d+$", devnode)
            )

            if is_optical:
                logging.info("Optical drive detected: %s", devnode)

                fields = (
                    DRIVE_INFORMATION +
                    DRIVE_INFORMATION_EXTENDED +
                    DRIVE_INFORMATION_MEDIUM
                )
                values = [device.properties.get(field) or "" for field in fields]
                yield DriveInformationMedium(*values)

        except Exception as e:
            log.error("Error processing device %s: %s", device, e, exc_info=True)


def _detect_drives(startup):
    """Search for system drives, retrying at startup for udev to settle."""
    system_drives = sorted(drives_search())
    if startup and not system_drives:
        for attempt in range(1, 4):
            delay = attempt * 5
            logging.info(
                "No drives detected at startup (attempt %d/3). "
                "Retrying in %ds for udev to settle...", attempt, delay,
            )
            time.sleep(delay)
            system_drives = sorted(drives_search())
            if system_drives:
                break
    return system_drives


def _find_or_create_drive(drive):
    """Find an existing DB drive matching the detected drive, or create a new one."""
    if drive.serial_id:
        db_drive = (SystemDrives.query
                    .filter_by(serial_id=drive.serial_id, stale=True)
                    .order_by(SystemDrives.mount).first())
        if db_drive:
            log.debug("Update drive '%s' by serial.", drive.serial_id)
            return db_drive
    if drive.location:
        db_drive = SystemDrives.query.filter_by(location=drive.location, stale=True).first()
        if db_drive:
            log.debug("Update drive '%s' by location '%s'.", drive.serial_id, drive.location)
            return db_drive
    db_drive = SystemDrives.query.filter_by(mount=drive.mount).first()
    if db_drive:
        log.debug("Update drive '%s' by mount path.", drive.mount)
        return db_drive
    log.debug("Create a new drive entity in the database for '%s' on '%s'.",
              drive.serial_id, drive.mount)
    db_drive = SystemDrives()
    db_drive.name = drive.serial_id or ""
    db.session.add(db_drive)
    return db_drive


def _cleanup_stale_drives():
    """Clear stale drives that have no active jobs. Returns count of unavailable drives."""
    stale_count = 0
    for stale_drive in SystemDrives.query.filter_by(stale=True).all():
        log.warning("Drive '%s' on '%s' is not available.", stale_drive.serial_id, stale_drive.mount)
        if stale_drive.processing:
            log.warning(f"Drive '{stale_drive.mount}' has an active job and might be blocked.")
            stale_drive.stale = False
        else:
            stale_drive.mount = ""
            stale_drive.location = ""
            stale_drive.mdisc = None
            stale_count += 1
        db.session.commit()
        stale_drive.debug(logger=log)
    return stale_count


def drives_update(startup=False):
    """
    scan the system for new cd/dvd/Blu-ray drives and update the database
    """
    drive_count = SystemDrives.query.count()

    # Mark non-processing drives as stale.  Drives with an active job keep
    # stale=False so a rescan triggered by *another* drive's re-enumeration
    # can never blank the mount of a drive that is mid-rip.
    for db_drive in SystemDrives.query.all():
        if db_drive.processing:
            db_drive.stale = False
            log.debug("Skipping stale mark for active drive '%s' on '%s'",
                       db_drive.serial_id, db_drive.mount)
        else:
            db_drive.stale = True
        if startup:
            db_drive.mdisc = None
    db.session.commit()

    system_drives = _detect_drives(startup)
    if not system_drives:
        logging.error(f"We Cant find any system drives!. {system_drives}")

    for drive in system_drives:
        logging.debug(f"Drive info: {drive}")
        db_drive = _find_or_create_drive(drive)
        db_drive.update(drive)
        db.session.commit()
        db_drive.debug(logger=log)

        for conflicting_drive in SystemDrives.query.filter(
            SystemDrives.drive_id != db_drive.drive_id,
            SystemDrives.mount == db_drive.mount,
        ).all():
            if conflicting_drive.processing:
                log.warning("Mount conflict on '%s': drive '%s' has active job, skipping blank",
                            db_drive.mount, conflicting_drive.serial_id)
            else:
                conflicting_drive.mount = ""
        db.session.commit()

    stale_count = _cleanup_stale_drives()
    if stale_count > 0:
        log.info("%d drives are unavailable.", stale_count)

    return drive_count - SystemDrives.query.count()


def update_job_status():
    """
    Check the drive job status
    """
    drives = SystemDrives.query.all()
    for drive in drives:
        if drive.processing and drive.job_current.ripping_finished:
            logging.info(f"A job is currently running on drive '{drive.name}'")
            if drive.job_current.finished:
                logging.warning(f"Releasing job from drive '{drive.name}'")
                drive.release_current_job()
                db.session.commit()
                continue
            logging.debug("If you want to release the job from the drive, press eject.")

        if drive.job_previous is not None and drive.job_previous.status is None:
            drive.job_id_previous = None
            db.session.commit()

        if drive.drive_mode is None:
            drive.drive_mode = "auto"
            db.session.commit()

        log.debug("Drive Mode: %s", drive.drive_mode)


def job_cleanup(job_id):
    """
    Called when removing a job from the database.
    """
    for drive in SystemDrives.query.filter_by(job_id_current=job_id):
        drive.job_id_current = None
        log.debug(f"Current Job {job_id} cleared from drive {drive.mount}")
    for drive in SystemDrives.query.filter_by(job_id_previous=job_id):
        drive.job_id_previous = None
        log.debug(f"Current Job {job_id} cleared from drive {drive.mount}")
    db.session.commit()


def update_drive_job(job):
    """
    Function to take the current job task and update the associated drive ID into the database
    """
    drive = SystemDrives.query.filter_by(mount=job.devpath).first()
    if drive is None:
        logging.warning(f"No drive found in database for {job.devpath}. "
                        "Job will continue but drive association may fail.")
        return
    drive.new_job(job.job_id)
    log.debug(f"Updating Drive: ['{drive.serial_id}'|'{drive.mount}']"
              f" Current Job: [{drive.job_id_current}]"
              f" Previous Job: [{drive.job_id_previous}]")
    try:
        db.session.commit()
        logging.debug("Database update with new Job ID to associated drive")
    except Exception as error:
        logging.error(f"Failed to update the database with the associated drive. {error}")


def update_tray_status(drives):
    for drive in drives:
        drive.tray_status()


def get_drives():
    """
    Wrapper around SystemDrives Database
    """
    return SystemDrives.query.order_by(SystemDrives.name, SystemDrives.description, SystemDrives.serial_id).all()


def clear_drive_job(job_id):
    """Alias for job_cleanup for backward compat."""
    return job_cleanup(job_id)
