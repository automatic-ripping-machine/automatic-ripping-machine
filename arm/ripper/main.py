#!/usr/bin/env python3
"""
The main runner for Automatic Ripping Machine

For help please visit https://github.com/uprightbass360/automatic-ripping-machine-neu
"""
import argparse  # noqa: E402
import logging  # noqa: E402
import sys
import time  # noqa: E402
import datetime  # noqa: E402
import re  # noqa: E402
from argparse import Namespace
from importlib.util import find_spec
from pathlib import Path
from signal import signal, SIGTERM
from typing import Optional

import pyudev  # noqa: E402

# If the arm module can't be found, add the folder this file is in to PYTHONPATH
# This is a bad workaround for non-existent packaging
if find_spec("arm") is None:
    sys.path.append(str(Path(__file__).parents[2]))

import arm.config.config as cfg  # noqa E402
from arm.models.config import Config  # noqa: E402
from arm.models.job import Job, JobState  # noqa: E402
from arm.models.system_drives import CDS, SystemDrives  # noqa: E402
from arm.database import db  # noqa E402
import arm.constants as constants  # noqa E402
from arm.ripper import (arm_ripper, identify, logger,  # noqa: E402
                        music_brainz, utils)
from arm.ripper.ARMInfo import ARMInfo  # noqa E402
from arm.services import drives as drive_utils  # noqa E402

# Initialise standalone database (no Flask)
db.init_engine('sqlite:///' + cfg.arm_config['DBFILE'])

job: Optional[Job] = None
args: Optional[Namespace] = None
log_file: Optional[str] = None


def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Process disc using ARM')
    parser.add_argument('-d', '--devpath', help='Devpath', required=True)
    parser.add_argument(
        "--syslog",
        help="Log to /dev/log",
        required=False,
        default=True,
        action=argparse.BooleanOptionalAction,
    )
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
    for key in ("MAINFEATURE", "MINLENGTH", "MAXLENGTH",
                "VIDEOTYPE", "MANUAL_WAIT", "MANUAL_WAIT_TIME", "RIPMETHOD",
                "MKV_ARGS", "DELRAWFILES", "RAW_PATH", "TRANSCODE_PATH",
                "COMPLETED_PATH", "EXTRAS_SUB", "EMBY_REFRESH", "EMBY_SERVER",
                "EMBY_PORT", "NOTIFY_RIP", "NOTIFY_TRANSCODE",
                "MAX_CONCURRENT_MAKEMKVINFO"):
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


def main():
    """main disc processing function"""
    global log_file

    logging.info("Starting Disc identification")
    identify.identify(job)

    # Re-initialize job log now that identification has resolved the label
    log_file = logger.setup_job_log(job)
    job.status = JobState.IDLE.value
    db.session.commit()

    # Check db for entries matching the crc and successful
    have_dupes = utils.job_dupe_check(job)
    logging.debug(f"Value of have_dupes: {have_dupes}")

    utils.notify_entry(job)
    # Check if user has manual wait time enabled
    utils.check_for_wait(job)

    log_arm_params(job)
    check_fstab()

    # Ripper type assessment for the various media types
    # Type: dvd/bluray/bluray4k
    if job.disctype in ["dvd", "bluray", "bluray4k"]:
        arm_ripper.rip_visual_media(have_dupes, job, log_file, job.has_track_99)

    # Type: Music
    elif job.disctype == "music":
        # Try to recheck music disc for auto ident
        music_brainz.main(job)
        if utils.rip_music(job, log_file):
            utils.notify(job, constants.NOTIFY_TITLE, f"Music CD: {job.title} {constants.PROCESS_COMPLETE}")
            utils.scan_emby()
            # This shouldn't be needed. but to be safe
            job.status = JobState.SUCCESS.value
            db.session.commit()
        else:
            logging.critical("Music rip failed.  See previous errors.  Exiting. ")
            job.status = JobState.FAILURE.value
            db.session.commit()

    # Type: Data
    elif job.disctype == "data":
        logging.info("Disc identified as data")
        if utils.rip_data(job):
            utils.notify(job, constants.NOTIFY_TITLE, f"Data disc: {job.label} copying complete. ")
        else:
            logging.critical("Data rip failed.  See previous errors.  Exiting.")

    # Type: undefined
    else:
        logging.critical("Couldn't identify the disc type. Exiting without any action.")


def setup():
    global job
    global args
    global log_file

    def signal_handler(_signal, _frame_type):
        raise utils.RipperException("Received SIGTERM")

    # Handle SIGTERM so we can exit gracefully. Without this, no except: or finally: blocks are
    # run and the program exits immediately, potentially leaving the database in an invalid state.
    signal(SIGTERM, signal_handler)

    # Get arguments from arg parser
    args = entry()
    devpath = f"/dev/{args.devpath}"
    # Setup base logger - will log to <log directory>/arm.log, syslog & stdout
    # This will catch any permission errors
    arm_log = logger.create_early_logger(syslog=args.syslog)
    # Make sure all directories are fully setup
    utils.arm_setup(arm_log)

    # Auto-migrate database schema if out of date (before any DB queries)
    from arm.services.config import check_db_version
    try:
        check_db_version(cfg.arm_config['INSTALLPATH'], cfg.arm_config['DBFILE'])
    except Exception as e:
        # Migration may fail if another ripper process is migrating concurrently.
        # Re-check: if DB is now current (other process succeeded), continue.
        from arm.services.config import arm_alembic_get, arm_db_get
        head = arm_alembic_get()
        current = arm_db_get()
        if current and current.version_num == head:
            logging.info("Migration failed but DB is current (migrated by another process).")
        else:
            raise utils.RipperException(
                f"Database migration failed and schema is still outdated "
                f"(head={head}, db={current.version_num if current else 'unknown'}): {e}"
            ) from e

    drive = SystemDrives.query.filter_by(mount=devpath).first()
    if drive is None:
        # Drive may have reconnected on a different device node — re-detect.
        logging.info(f"No drive record for {devpath}, re-scanning drives...")
        drive_utils.drives_update()
        drive = SystemDrives.query.filter_by(mount=devpath).first()
    if drive is None:
        logging.info(f"Drive {devpath} not found after re-scan. Exiting gracefully.")
        return False

    # With some drives and some disks, there is a race condition between creating the Job()
    # below and the drive being ready, so give it a chance to get ready (observed with LG SP80NB80)
    drive_ready_timeout = int(cfg.arm_config.get('DRIVE_READY_TIMEOUT', 60))
    poll_interval = 2
    max_polls = max(drive_ready_timeout // poll_interval, 1)
    no_disc_threshold = max_polls // 2  # >50% of timeout with NO_DISC → exit gracefully
    no_disc_count = 0
    drive_is_ready = False

    for num in range(1, max_polls + 1):
        drive.tray_status()
        if drive.ready:
            drive_is_ready = True
            break
        state_name = drive.tray.name if drive.tray else "UNKNOWN"
        if drive.tray == CDS.NO_DISC:
            no_disc_count += 1
        logging.info(
            f"[{num}/{max_polls}] Drive [{drive.mount}] not ready "
            f"(state: {state_name}). Waiting {poll_interval}s"
        )
        if no_disc_count > no_disc_threshold:
            logging.info(
                f"Drive [{drive.mount}] reported NO_DISC for majority of "
                f"checks ({no_disc_count}/{num}). Exiting gracefully."
            )
            return False
        time.sleep(poll_interval)

    if not drive_is_ready:
        state_name = drive.tray.name if drive.tray else "UNKNOWN"
        logging.info(
            f"Timed out waiting for drive [{drive.mount}] to be ready "
            f"after {drive_ready_timeout}s (last state: {state_name}). "
            f"Exiting gracefully."
        )
        return False

    # ARM Job starts
    # Create new job
    job = Job(devpath)

    # Capture and report the ARM Info
    arminfo = ARMInfo(cfg.arm_config["INSTALLPATH"], cfg.arm_config['DBFILE'])
    job.arm_version = arminfo.arm_version
    arminfo.get_values()

    # Sometimes drives trigger twice this stops multi runs from 1 udev trigger
    utils.duplicate_run_check(devpath)

    logging.info(f"************* Starting ARM processing at {datetime.datetime.now()} *************")
    # Set job status and start time
    job.status = JobState.IDENTIFYING.value
    job.start_time = datetime.datetime.now()
    utils.database_adder(job)

    # Setup logging — must happen after job is persisted (job_id assigned) and
    # arm_version is set, because music CDs trigger a MusicBrainz lookup here
    # that needs both values.
    log_file = logger.setup_job_log(job)
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

    try:
        # Delete old log files
        logger.clean_up_logs(cfg.arm_config["LOGPATH"], cfg.arm_config["LOGLIFE"])
    except Exception as error:
        logging.error(error, exc_info=True)

    logging.info(f"Job: {job.label}")  # This will sometimes be none
    # Check for zombie jobs and update status to 'failed'
    utils.clean_old_jobs()
    # Log all params/attribs from the drive
    log_udev_params(devpath)
    return True


if __name__ == "__main__":
    job = None
    try:
        ready = setup()
        if not ready:
            # Drive not ready or no disc — exit cleanly without error
            sys.exit(0)
        main()
    except Exception as error:
        logging.critical("A fatal error has occurred and ARM is exiting.")
        print_stacktrace = (
            logging.getLogger().getEffectiveLevel() == logging.DEBUG
            or not isinstance(error, utils.RipperException)
        )
        logging.critical(error, exc_info=(error if print_stacktrace else None),)

        if job:
            utils.notify(
                job,
                constants.NOTIFY_TITLE,
                f"ARM encountered a fatal error processing {job.title}. "
                f"Check the logs for more details. {error}"
            )
        else:
            utils.notify(
                job,
                constants.NOTIFY_TITLE,
                f"ARM encountered a fatal error during job setup."
                f"Check the logs for more details. {error}"
            )
        if job:
            job.status = JobState.FAILURE.value
            job.errors = str(error)
        # Possibly add cleanup section here for failed job files
    else:
        if job:
            # If external transcoder is configured and this was a video disc,
            # mark as waiting_transcode — the transcoder callback will set
            # the final status (success/fail) when it finishes.
            if (job.disctype in ("dvd", "bluray", "bluray4k")
                    and cfg.arm_config.get("TRANSCODER_URL")):
                job.status = JobState.TRANSCODE_WAITING.value
            else:
                job.status = JobState.SUCCESS.value
    finally:
        if job:
            job.eject()  # each job stores its eject status, so it is safe to call.
            job.stop_time = datetime.datetime.now()
            job_length = job.stop_time - job.start_time if job.start_time else 0
            minutes, seconds = divmod(job_length.seconds + job_length.days * 86400, 60)
            hours, minutes = divmod(minutes, 60)
            job.job_length = f'{hours:d}:{minutes:02d}:{seconds:02d}'
        db.session.commit()
