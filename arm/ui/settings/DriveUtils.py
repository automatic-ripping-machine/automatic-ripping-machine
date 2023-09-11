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
from arm.models import models
from arm.database import db


def drives_search():
    """
    Search the system for any drives
    """
    udev_drives = []

    context = pyudev.Context()

    for device in context.list_devices(subsystem='block'):
        regexoutput = re.search(r'(\/dev\/sr\d{1,2})', device.device_node)
        if regexoutput:
            logging.debug(f"regex output: {regexoutput.group()}")
            udev_drives.append(regexoutput.group())

    if len(udev_drives) > 0:
        logging.info(f"System disk scan, found {len(udev_drives)} drives for ARM")
        for disk in udev_drives:
            logging.debug(f"disk: {disk}")
    else:
        logging.info("System disk scan, no drives attached to ARM server")

    return udev_drives


def drives_update():
    """
    scan the system for new cd/dvd/Blu-ray drives
    """
    udev_drives = drives_search()
    i = 1
    new_count = 0

    # Get the number of current drives in the database
    drive_count = models.SystemDrives.query.count()

    for drive_mount in udev_drives:
        # Check drive doesn't already exist
        if not models.SystemDrives.query.filter_by(mount=drive_mount).first():
            # New drive, set previous job to none
            last_job = None
            new_count += 1

            # Create new disk (name, type, mount, open, job id, previos job id, description )
            db_drive = models.SystemDrives(f"Drive {drive_count + new_count}",
                                           drive_mount, None, last_job, "Classic burner")
            logging.debug("****** Drive Information ******")
            logging.debug(f"Name: {db_drive.name}")
            logging.debug(f"Type: {db_drive.type}")
            logging.debug(f"Mount: {db_drive.mount}")
            logging.debug("****** End Drive Information ******")
            db.session.add(db_drive)
            db.session.commit()
            i += 1
        else:
            i += 1

    if new_count > 0:
        logging.info(f"Added {new_count} drives for ARM.")
    else:
        logging.info("No new drives found on the system.")

    return new_count


def drives_check_status():
    """
    Check the drive job status
    """
    drives = models.SystemDrives.query.all()
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

        # Print the drive debug status
        drive_status_debug(drive)

    # Requery data to ensure current pending job status change
    drives = models.SystemDrives.query.all()

    return drives


def drive_status_debug(drive):
    """
    Report the current drive status (debug)
    """
    logging.debug("*********")
    logging.debug(f"Name: {drive.name}")
    logging.debug(f"Type: {drive.type}")
    logging.debug(f"Mount: {drive.mount}")
    logging.debug(f"Open: {drive.open}")
    logging.debug(f"Job Current: {drive.job_id_current}")
    if drive.job_id_current and drive.job_current is not None:
        logging.debug(f"Job - Status: {drive.job_current.status}")
        logging.debug(f"Job - Type: {drive.job_current.video_type}")
        logging.debug(f"Job - Title: {drive.job_current.title}")
        logging.debug(f"Job - Year: {drive.job_current.year}")
    logging.debug(f"Job Previous: {drive.job_id_previous}")
    if drive.job_id_previous and drive.job_previous is not None:
        logging.debug(f"Job - Status: {drive.job_previous.status}")
        logging.debug(f"Job - Type: {drive.job_previous.video_type}")
        logging.debug(f"Job - Title: {drive.job_previous.title}")
        logging.debug(f"Job - Year: {drive.job_previous.year}")
    logging.debug("*********")


def job_cleanup(job_id):
    """
    Function called when removing a job from the database, removing the data in the previous job field
    """
    job = models.Job.query.filter_by(job_id=job_id).first()
    drive = models.SystemDrives.query.filter_by(mount=job.devpath).first()
    drive.job_id_previous = None
    logging.debug(f"Job {job.job_id} cleared from drive {drive.mount} previous")


def update_drive_job(job):
    """
    Function to take current job task and update the associated drive ID into the database
    """
    drive = models.SystemDrives.query.filter_by(mount=job.devpath).first()
    drive.new_job(job.job_id)
    logging.debug(f"Updating drive [{job.devpath}] current job, with id [{job.job_id}]")
    try:
        db.session.commit()
        logging.debug("Database update with new Job ID to associated drive")
    except Exception as error:  # noqa: E722
        logging.error(f"Failed to update the database with the associated drive. {error}")
