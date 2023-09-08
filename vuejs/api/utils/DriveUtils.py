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

from arm.ui import app, db
from arm.models import models


def drives_search():
    """
    Search the system for any drives
    """
    udev_drives = []

    context = pyudev.Context()

    for device in context.list_devices(subsystem='block'):
        regexoutput = re.search(r'(\/dev\/sr\d{1,2})', device.device_node)
        if regexoutput:
            app.logger.debug(f"regex output: {regexoutput.group()}")
            udev_drives.append(regexoutput.group())

    if len(udev_drives) > 0:
        app.logger.info(f"System disk scan, found {len(udev_drives)} drives for ARM")
        for disk in udev_drives:
            app.logger.debug(f"disk: {disk}")
    else:
        app.logger.info("System disk scan, no drives attached to ARM server")

    return udev_drives


def drives_update():
    """
    scan the system for new cd/dvd/Blu-ray drives
    """
    udev_drives = drives_search()
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
            app.logger.debug("****** Drive Information ******")
            app.logger.debug(f"Name: {db_drive.name}")
            app.logger.debug(f"Type: {db_drive.type}")
            app.logger.debug(f"Mount: {db_drive.mount}")
            app.logger.debug("****** End Drive Information ******")
            db.session.add(db_drive)
            db.session.commit()
            db_drive = None

    if new_count > 0:
        app.logger.info(f"Added {new_count} drives for ARM.")
    else:
        app.logger.info("No new drives found on the system.")

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

        # Catch if a user has removed database entries and the previous job doesnt exist
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
    app.logger.debug("*********")
    app.logger.debug(f"Name: {drive.name}")
    app.logger.debug(f"Type: {drive.type}")
    app.logger.debug(f"Mount: {drive.mount}")
    app.logger.debug(f"Open: {drive.open}")
    app.logger.debug(f"Job Current: {drive.job_id_current}")
    if drive.job_id_current and drive.job_current is not None:
        app.logger.debug(f"Job - Status: {drive.job_current.status}")
        app.logger.debug(f"Job - Type: {drive.job_current.video_type}")
        app.logger.debug(f"Job - Title: {drive.job_current.title}")
        app.logger.debug(f"Job - Year: {drive.job_current.year}")
    app.logger.debug(f"Job Previous: {drive.job_id_previous}")
    if drive.job_id_previous and drive.job_previous is not None:
        app.logger.debug(f"Job - Status: {drive.job_previous.status}")
        app.logger.debug(f"Job - Type: {drive.job_previous.video_type}")
        app.logger.debug(f"Job - Title: {drive.job_previous.title}")
        app.logger.debug(f"Job - Year: {drive.job_previous.year}")
    app.logger.debug("*********")


def job_cleanup(job_id):
    """
    Function called when removing a job from the database, removing the data in the previous job field
    """
    job = models.Job.query.filter_by(job_id=job_id).first()
    drive = models.SystemDrives.query.filter_by(mount=job.devpath).first()
    drive.job_id_previous = None
    app.logger.debug(f"Job {job.job_id} cleared from drive {drive.mount} previous")


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
