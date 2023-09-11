"""
Functions to manage drives
UI Utils
- drives_search
- drives_update
- drives_check_status
- drive_status_debug
- job_cleanup
Ripper Utils
- update_drive_job
"""

import pyudev
import re
import logging
from models import SystemDrives, Job


def drives_search():
    """
    Search the system for any drives
    """
    udev_drives = []

    context = pyudev.Context()

    for device in context.list_devices(subsystem='block'):
        regexoutput = re.search(r'(\/dev\/sr\d{1,2})', device.device_node)
        if regexoutput:
            logging.info(f"regex output: {regexoutput.group()}")
            udev_drives.append(regexoutput.group())

    if len(udev_drives) > 0:
        logging.info(f"System disk scan, found {len(udev_drives)} drives for ARM")
        for disk in udev_drives:
            logging.info(f"disk: {disk}")
    else:
        logging.info("System disk scan, no drives attached to ARM server")

    return udev_drives


def drives_update(db):
    """
    scan the system for new cd/dvd/Blu-ray drives
    """
    udev_drives = drives_search()
    new_count = 0

    # Get the number of current drives in the database
    drive_count = db.query(SystemDrives).count()

    for drive_mount in udev_drives:
        # Check drive doesn't already exist
        if not db.query(SystemDrives).filter_by(mount=drive_mount).first():
            # New drive, set previous job to none
            last_job = None
            new_count += 1

            # Create new disk (name, type, mount, open, job id, previos job id, description )
            db_drive = SystemDrives(f"Drive {drive_count + new_count}",
                                    drive_mount, None, last_job, "Classic burner")
            logging.info("****** Drive Information ******")
            logging.info(f"Name: {db_drive.name}")
            logging.info(f"Type: {db_drive.type}")
            logging.info(f"Mount: {db_drive.mount}")
            logging.info("****** End Drive Information ******")
            db.add(db_drive)
            db.commit()

    if new_count > 0:
        logging.info(f"Added {new_count} drives for ARM.")
    else:
        logging.info("No new drives found on the system.")

    return new_count


def drives_check_status(db):
    """
    Check the drive job status
    """
    drives = db.query(SystemDrives).all()
    if not drives or len(drives) < 1:
        drives_update(db)
    for drive in drives:
        # Check if the current job is active, if not remove current job_current id
        if drive.job_id_current is not None and drive.job_id_current > 0 and drive.job_current is not None:
            if drive.job_current.status == "success" or drive.job_current.status == "fail":
                drive.job_finished()
                db.session.commit()

        # Catch if a user has removed database entries and the previous job doesn't exist
        if drive.job_previous is not None and drive.job_previous.status is None:
            drive.job_id_previous = None
            db.session.commit()

        # logging.info the drive debug status
        drive_status_debug(drive)

    # Requery data to ensure current pending job status change
    drives = db.query(SystemDrives).all()

    return drives


def drive_status_debug(drive):
    """
    Report the current drive status (debug)
    """
    logging.info("*********")
    logging.info(f"Name: {drive.name}")
    logging.info(f"Type: {drive.type}")
    logging.info(f"Mount: {drive.mount}")
    logging.info(f"Open: {drive.open}")
    logging.info(f"Job Current: {drive.job_id_current}")
    if drive.job_id_current and drive.job_current is not None:
        logging.info(f"Job - Status: {drive.job_current.status}")
        logging.info(f"Job - Type: {drive.job_current.video_type}")
        logging.info(f"Job - Title: {drive.job_current.title}")
        logging.info(f"Job - Year: {drive.job_current.year}")
    logging.info(f"Job Previous: {drive.job_id_previous}")
    if drive.job_id_previous and drive.job_previous is not None:
        logging.info(f"Job - Status: {drive.job_previous.status}")
        logging.info(f"Job - Type: {drive.job_previous.video_type}")
        logging.info(f"Job - Title: {drive.job_previous.title}")
        logging.info(f"Job - Year: {drive.job_previous.year}")
    logging.info("*********")


def job_cleanup(job_id):
    """
    Function called when removing a job from the database, removing the data in the previous job field
    """
    job = Job.query.filter_by(job_id=job_id).first()
    drive = SystemDrives.query.filter_by(mount=job.devpath).first()
    drive.job_id_previous = None
    logging.info(f"Job {job.job_id} cleared from drive {drive.mount} previous")
