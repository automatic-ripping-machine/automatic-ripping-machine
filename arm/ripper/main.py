#!/usr/bin/env python3
"""
The main runner for Automatic Ripping Machine

For help please visit https://github.com/automatic-ripping-machine/automatic-ripping-machine
"""
import sys
import argparse  # noqa: E402
import os  # noqa: E402
import logging  # noqa: E402
import logging.handlers  # noqa: E402
import time  # noqa: E402
import datetime  # noqa: E402
import re  # noqa: E402
import getpass  # noqa E402
import pyudev  # noqa: E402
import psutil  # noqa E402

# set the PATH to /opt/arm so we can handle imports properly
sys.path.append("/opt/arm")

from arm.ripper import logger, utils, identify, arm_ripper, music_brainz  # noqa: E402
import arm.config.config as cfg  # noqa E402
from arm.models.config import Config  # noqa: E402
from arm.models.job import Job  # noqa: E402
from arm.models.system_drives import SystemDrives  # noqa: E402
from arm.ui import app, db, constants  # noqa E402
from arm.ui.settings import DriveUtils as drive_utils # noqa E402
import arm.config.config as cfg  # noqa E402
from arm.ripper.ARMInfo import ARMInfo  # noqa E402


def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Process disc using ARM')
    parser.add_argument('-d', '--devpath', help='Devpath', required=True)
    parser.add_argument('-p', '--protection', help='Does disc have 99 track protection', required=False)
    return parser.parse_args()


def log_udev_params(dev_path):
    """log all udev parameters"""

    logging.debug("******************* Logging udev attributes *******************")
    context = pyudev.Context()
    device = pyudev.Devices.from_device_file(context, dev_path)
    for key, value in device.items():
        logging.debug(f"{key}:{value}")
    logging.debug("******************* End udev attributes *******************")


def log_arm_params(job):
    """log all entry parameters"""

    # log arm parameters
    logging.info("******************* Logging ARM variables *******************")
    for key in ("devpath", "mountpoint", "title", "year", "video_type",
                "hasnicetitle", "label", "disctype", "manual_start"):
        logging.info(f"{key}: {str(getattr(job, key))}")
    logging.info("******************* End of ARM variables *******************")

    logging.info("******************* Logging config parameters *******************")
    for key in ("SKIP_TRANSCODE", "MAINFEATURE", "MINLENGTH", "MAXLENGTH",
                "VIDEOTYPE", "MANUAL_WAIT", "MANUAL_WAIT_TIME", "RIPMETHOD",
                "MKV_ARGS", "DELRAWFILES", "HB_PRESET_DVD", "HB_PRESET_BD",
                "HB_ARGS_DVD", "HB_ARGS_BD", "RAW_PATH", "TRANSCODE_PATH",
                "COMPLETED_PATH", "EXTRAS_SUB", "EMBY_REFRESH", "EMBY_SERVER",
                "EMBY_PORT", "NOTIFY_RIP", "NOTIFY_TRANSCODE",
                "MAX_CONCURRENT_TRANSCODES", "MAX_CONCURRENT_MAKEMKVINFO"):
        logging.info(f"{key.lower()}: {str(cfg.arm_config.get(key, '<not given>'))}")
    logging.info("******************* End of config parameters *******************")


def check_fstab():
    """
    Check the fstab entries to see if ARM has been set up correctly
    :return: None

    # todo: remove this from the ripper and add into the ARM UI with a warning
    """
    logging.info("Checking for fstab entry.")
    with open('/etc/fstab', 'r') as fstab:
        lines = fstab.readlines()
        for line in lines:
            # Now grabs the real uncommented fstab entry
            if re.search("^" + job.devpath, line):
                logging.info(f"fstab entry is: {line.rstrip()}")
                return
    logging.error("No fstab entry found.  ARM will likely fail.")


def main(logfile, job, protection=0):
    """main disc processing function"""
    logging.info("Starting Disc identification")
    identify.identify(job)

    # Check db for entries matching the crc and successful
    have_dupes = utils.job_dupe_check(job)
    logging.debug(f"Value of have_dupes: {have_dupes}")

    utils.notify_entry(job)
    # Check if user has manual wait time enabled
    utils.check_for_wait(job)

    log_arm_params(job)
    check_fstab()

    # Ripper type assessment for the various media types
    # Type: dvd/bluray
    if job.disctype in ["dvd", "bluray"]:
        arm_ripper.rip_visual_media(have_dupes, job, logfile, protection)

    # Type: Music
    elif job.disctype == "music":
        # Try to recheck music disc for auto ident
        music_brainz.main(job)
        if utils.rip_music(job, logfile):
            utils.notify(job, constants.NOTIFY_TITLE, f"Music CD: {job.title} {constants.PROCESS_COMPLETE}")
            utils.scan_emby()
            # This shouldn't be needed. but to be safe
            job.status = "success"
            db.session.commit()
        else:
            logging.info("Music rip failed.  See previous errors.  Exiting. ")
            job.status = "fail"
            db.session.commit()
        job.eject()

    # Type: Data
    elif job.disctype == "data":
        logging.info("Disc identified as data")
        if utils.rip_data(job):
            utils.notify(job, constants.NOTIFY_TITLE, f"Data disc: {job.label} copying complete. ")
        else:
            logging.info("Data rip failed.  See previous errors.  Exiting.")
        job.eject()

    # Type: undefined
    else:
        logging.info("Couldn't identify the disc type. Exiting without any action.")


if __name__ == "__main__":
    # Setup base logger - will log to /var/log/arm.log, /home/arm/logs/arm.log & stdout
    # This will catch any permission errors
    arm_log = logger.create_logger("ARM", logging.DEBUG, True, True, True)
    # Make sure all directories are fully setup
    utils.arm_setup(arm_log)
    # Get arguments from arg parser
    args = entry()
    devpath = f"/dev/{args.devpath}"
    drive = SystemDrives.query.filter_by(mount=devpath).one()  # unique mounts

    # With some drives and some disks, there is a race condition between creating the Job()
    # below and the drive being ready, so give it a chance to get ready (observed with LG SP80NB80)
    ready_count = 1
    for num in range(1, 11):
        if drive.ready:
            break
        time.sleep(1)
        msg = f"[{num} of 10] Drive [{drive.mount}] appears to be empty or is not ready. Waiting 1s"
        logging.info(msg)
    else:
        # This should really never trigger now as arm_wrapper should be taking care of this.
        msg = f"Failed to wait for drive ready (ioctl tray status: {drive.tray})."
        logging.info(msg)
        arm_log.info(msg)
        sys.exit()

    # ARM Job starts
    # Create new job
    job = Job(devpath)
    # Setup logging
    log_file = logger.setup_logging(job)

    # Don't put out anything if we are using the empty.log NAS_[0-9].log or NAS1_[0-9].log
    if log_file.find("empty.log") != -1 or re.search(r"(NAS|NAS1)_\d+\.log", log_file) is not None:
        arm_log.info("ARM is trying to write a job to the empty.log, or NAS**.log")
        sys.exit()

    # Capture and report the ARM Info
    arminfo = ARMInfo(cfg.arm_config["INSTALLPATH"], cfg.arm_config['DBFILE'])
    job.arm_version = arminfo.arm_version
    arminfo.get_values()

    # Sometimes drives trigger twice this stops multi runs from 1 udev trigger
    utils.duplicate_run_check(devpath)

    logging.info(f"************* Starting ARM processing at {datetime.datetime.now()} *************")
    if args.protection:
        logging.warning("Found 99 Track protection system - Job may fail!")
    # Set job status and start time
    job.status = "active"
    job.start_time = datetime.datetime.now()
    utils.database_adder(job)
    # Sleep to lower chances of db locked - unlikely to be needed
    time.sleep(1)
    # Associate the job with the drive in the database
    drive_utils.update_drive_job(job)
    # Add the job.config to db
    config = Config(cfg.arm_config, job_id=job.job_id)  # noqa: F811
    # Check if the drive mode is set to manual, and load to the job config for later use
    logging.debug(f"drive_mode: {drive.drive_mode}")
    if drive.drive_mode == 'manual':
        job.manual_mode = True
        db.session.commit()
    else:
        job.manual_mode = False
        db.session.commit()
    utils.database_adder(config)
    # Log version number
    with open(os.path.join(cfg.arm_config["INSTALLPATH"], 'VERSION')) as version_file:
        version = version_file.read().strip()

    # Delete old log files
    logger.clean_up_logs(cfg.arm_config["LOGPATH"], cfg.arm_config["LOGLIFE"])
    logging.info(f"Job: {job.label}")  # This will sometimes be none
    # Check for zombie jobs and update status to 'failed'
    utils.clean_old_jobs()
    # Log all params/attribs from the drive
    log_udev_params(devpath)

    try:
        main(log_file, job, args.protection)
    except Exception as error:
        logging.error(error, exc_info=True)
        logging.error("A fatal error has occurred and ARM is exiting.  See traceback below for details.")
        utils.notify(job, constants.NOTIFY_TITLE, "ARM encountered a fatal error processing "
                                                  f"{job.title}. Check the logs for more details. {error}")
        job.status = "fail"
        job.errors = str(error)
        job.eject()
        # Possibly add cleanup section here for failed job files
    else:
        job.status = "success"
    finally:
        job.stop_time = datetime.datetime.now()
        job_length = job.stop_time - job.start_time
        minutes, seconds = divmod(job_length.seconds + job_length.days * 86400, 60)
        hours, minutes = divmod(minutes, 60)
        job.job_length = f'{hours:d}:{minutes:02d}:{seconds:02d}'
        db.session.commit()
