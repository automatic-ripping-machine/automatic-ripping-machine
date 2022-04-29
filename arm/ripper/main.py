#!/usr/bin/env python3
"""
The main runner for Automatic Ripping Machine

For help please visit https://github.com/automatic-ripping-machine/automatic-ripping-machine
"""
import sys
import argparse  # noqa: E402
import os  # noqa: E402
import logging  # noqa: E402
import time  # noqa: E402
import datetime  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import getpass  # noqa E402
import pyudev  # noqa: E402

sys.path.append("/opt/arm")

from arm.ripper import logger, utils, makemkv, handbrake, identify  # noqa: E402
from arm.config.config import cfg  # noqa: E402
from arm.models.models import Job, Config  # noqa: E402
from arm.ui import app, db  # noqa E402

NOTIFY_TITLE = "ARM notification"
PROCESS_COMPLETE = " processing complete. "


def entry():
    """ Entry to program, parses arguments"""
    parser = argparse.ArgumentParser(description='Process disc using ARM')
    parser.add_argument('-d', '--devpath', help='Devpath', required=True)

    return parser.parse_args()


def log_udev_params(dev_path):
    """log all udev parameters"""

    logging.debug("******************* Logging udev attributes *******************")
    context = pyudev.Context()
    device = pyudev.Devices.from_device_file(context, dev_path)
    for key, value in device.items():
        logging.debug(key + ":" + value)
    logging.debug("******************* End udev attributes *******************")


def log_arm_params(job):
    """log all entry parameters"""

    # log arm parameters
    logging.info("******************* Logging ARM variables *******************")
    for key in ("devpath", "mountpoint", "title", "year", "video_type",
                "hasnicetitle", "label", "disctype"):
        logging.info(f"{key}: {str(getattr(job, key))}")
    logging.info("******************* End of ARM variables *******************")

    logging.info("******************* Logging config parameters *******************")
    for key in ("SKIP_TRANSCODE", "MAINFEATURE", "MINLENGTH", "MAXLENGTH",
                "VIDEOTYPE", "MANUAL_WAIT", "MANUAL_WAIT_TIME", "RIPMETHOD",
                "MKV_ARGS", "DELRAWFILES", "HB_PRESET_DVD", "HB_PRESET_BD",
                "HB_ARGS_DVD", "HB_ARGS_BD", "RAW_PATH", "TRANSCODE_PATH",
                "COMPLETED_PATH", "EXTRAS_SUB", "EMBY_REFRESH", "EMBY_SERVER",
                "EMBY_PORT", "NOTIFY_RIP", "NOTIFY_TRANSCODE",
                "MAX_CONCURRENT_TRANSCODES"):
        logging.info(f"{key.lower()}: {str(cfg.get(key, '<not given>'))}")
    logging.info("******************* End of config parameters *******************")


def check_fstab():
    """
    Check the fstab entries to see if ARM has been set up correctly
    :return: None
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


def skip_transcode(job, final_directory, raw_path, hb_out_path):
    """
    Section to follow when Skip transcoding is enabled exit when finished
    :param job: current Job
    :param final_directory: final directory
    :param raw_path: RAW_PATH
    :return: sys.exit()
    """
    logging.info("SKIP_TRANSCODE is true.  Moving raw mkv files.")
    logging.info("NOTE: Identified main feature may not be actual main feature")
    files = os.listdir(raw_path)

    if job.video_type == "movie":
        skip_transcode_movie(files, job, raw_path)
    else:
        # if video_type is not movie, then move everything
        logging.debug(f"Video type: {job.video_type}")
        for file in files:
            utils.move_files(raw_path, file, job, True)

    # remove raw files, if specified in config
    if cfg["DELRAWFILES"]:
        logging.info("Removing raw files")
        shutil.rmtree(raw_path)
        shutil.rmtree(hb_out_path)

    utils.set_permissions(final_directory)
    utils.notify(job, NOTIFY_TITLE, str(job.title) + PROCESS_COMPLETE)

    logging.info("ARM processing complete")
    utils.database_updater({'status': "success"}, job)
    job.eject()
    sys.exit()


def skip_transcode_movie(files, job, raw_path):
    """
    only ran if job is a movie find the largest file use it as mainfeature\n\n
    :param files: os.listdir(RAW_PATH)
    :param job: Current job
    :param raw_path: RAW_PATH of ripped mkv files (mkvoutpath)
    :return: None
    """
    logging.debug(f"Videotype: {job.video_type}")
    # if video_type is movie, then move the biggest title to media_dir
    # move the rest of the files to the extras' folder
    # find largest filesize
    logging.debug("Finding largest file")
    largest_file_name = utils.find_largest_file(files, raw_path)
    # largest_file_name should be the largest file
    logging.debug(f"Largest file is: {largest_file_name}")
    temp_path = os.path.join(raw_path, largest_file_name)
    if os.stat(temp_path).st_size <= 1:  # sanity check for filesize
        logging.debug(f"{raw_path} is empty or very small size. - Folder size: {os.stat(temp_path).st_size}")
    for file in files:
        # move main into main folder
        # move others into extras folder
        if file == largest_file_name:
            # largest movie
            utils.move_files(raw_path, file, job, True)
        else:
            # If mainfeature is enabled skip to the next file
            if job.config.MAINFEATURE:
                logging.debug(f"MAINFEATURE IS {job.config.MAINFEATURE} - Skipping move of {file}")
                continue
            # Other/extras
            if str(cfg["EXTRAS_SUB"]).lower() != "none":
                utils.move_files(raw_path, file, job, False)
            else:
                logging.info(f"Not moving extra: \"{file}\" - Sub folder is not set or named incorrectly")


def main(logfile, job):
    """main disc processing function"""
    logging.info("Starting Disc identification")
    identify.identify(job)
    # Check db for entries matching the crc and successful
    have_dupes, crc_jobs = utils.job_dupe_check(job)
    logging.debug(f"Value of have_dupes: {have_dupes}")

    utils.notify_entry(job)
    # Check if user has manual wait time enabled
    utils.check_for_wait(job, config)

    log_arm_params(job)
    check_fstab()
    # Set job.stage with a random timestamp, so we can sync all ts with one job
    utils.database_updater({'stage': str(round(time.time() * 100))}, job)
    # Entry point for dvd/bluray
    if job.disctype in ["dvd", "bluray"]:
        type_sub_folder = utils.convert_job_type(job.video_type)
        # We need to check/construct the final path, and the transcode path
        if job.year and job.year != "0000" and job.year != "":
            hb_out_path = os.path.join(cfg["TRANSCODE_PATH"], str(type_sub_folder), f"{job.title} ({job.year})")
            final_directory = os.path.join(cfg["COMPLETED_PATH"], str(type_sub_folder), f"{job.title} ({job.year})")
        else:
            hb_out_path = os.path.join(cfg["TRANSCODE_PATH"], str(type_sub_folder), str(job.title))
            final_directory = os.path.join(cfg["COMPLETED_PATH"], str(type_sub_folder), str(job.title))
        # Check folders for already ripped jobs -> creates folder
        hb_out_path = utils.check_for_dupe_folder(have_dupes, hb_out_path, job)
        # If dupes rips is disabled this might kill the run
        final_directory = utils.check_for_dupe_folder(have_dupes, final_directory, job)
        # Update the job.path with the final directory
        utils.database_updater({'path': final_directory}, job)
        # Save poster image from disc if enabled
        utils.save_disc_poster(final_directory, job)

        logging.info(f"Processing files to: {hb_out_path}")
        mkvoutpath = None
        hb_in_path = str(job.devpath)
        # entry point for bluray
        #  or dvd with (not MAINFEATURE and RIPMETHOD mkv)
        if job.disctype == "bluray" or (not cfg["MAINFEATURE"] and cfg["RIPMETHOD"] == "mkv"):
            # Run MakeMKV and get path to output
            job.status = "ripping"
            db.session.commit()
            try:
                mkvoutpath = makemkv.makemkv(logfile, job)
            except Exception as mkv_error:  # noqa: E722
                logging.error(f"MakeMKV did not complete successfully.  Exiting ARM! "
                              f"Error: {mkv_error}")
                raise

            if mkvoutpath is None:
                logging.error("MakeMKV did not complete successfully.  Exiting ARM!")
                job.status = "fail"
                db.session.commit()
                sys.exit()
            if cfg["NOTIFY_RIP"]:
                utils.notify(job, NOTIFY_TITLE, f"{job.title} rip complete. Starting transcode. ")

            # Entry point for not transcoding
            if cfg["SKIP_TRANSCODE"] and cfg["RIPMETHOD"] == "mkv":
                skip_transcode(job, final_directory, mkvoutpath, hb_out_path)
            # point HB to the path MakeMKV ripped to
            hb_in_path = mkvoutpath

        # Update db with transcoding status
        utils.database_updater({'status': "transcoding"}, job)
        # Begin transcoding section
        if job.disctype == "bluray" and cfg["RIPMETHOD"] == "mkv" \
                or job.disctype == "dvd" and (not cfg["MAINFEATURE"] and cfg["RIPMETHOD"] == "mkv"):
            handbrake.handbrake_mkv(hb_in_path, hb_out_path, logfile, job)
        elif job.video_type == "movie" and cfg["MAINFEATURE"] and job.hasnicetitle:
            handbrake.handbrake_main_feature(hb_in_path, hb_out_path, logfile, job)
            job.eject()
        else:
            handbrake.handbrake_all(hb_in_path, hb_out_path, logfile, job)
            job.eject()

        # check if there is a new title and change all filenames
        db.session.refresh(job)
        logging.debug(f"New Title is {job.title}")

        # Move to final folder
        tracks = job.tracks.filter_by(ripped=True)  # .order_by(job.tracks.length.desc())
        if job.video_type == "series":
            for track in tracks:
                utils.move_files(hb_out_path, track.filename, job, True)
        else:
            for track in tracks:
                if tracks.count() == 1:
                    utils.move_files(hb_out_path, track.filename, job, True)
                else:
                    # If source is MakeMKV we know the mainfeature will be wrong let skip_transcode_movie handle it
                    if track.source == "MakeMKV":
                        skip_transcode_movie(os.listdir(hb_out_path), job, hb_out_path)
                        break
                    # If HandBrake was used we can pass track.main_feature
                    utils.move_files(hb_out_path, track.filename, job, track.main_feature)

        # Movie the movie poster if we have one
        utils.move_movie_poster(final_directory, hb_out_path)
        # Scan emby if arm.yaml requires it
        utils.scan_emby()
        # Set permissions if arm.yaml requires it
        utils.set_permissions(final_directory)
        # If set in the arm.yaml remove the raw files
        utils.delete_raw_files(hb_in_path, hb_out_path, mkvoutpath)
        # report errors if any
        if cfg["NOTIFY_TRANSCODE"]:
            if job.errors:
                errlist = ', '.join(job.errors)
                utils.notify(job, NOTIFY_TITLE,
                             f" {job.title} processing completed with errors. "
                             f"Title(s) {errlist} failed to complete. ")
                logging.info(f"Transcoding completed with errors.  Title(s) {errlist} failed to complete. ")
            else:
                utils.notify(job, NOTIFY_TITLE, str(job.title) + PROCESS_COMPLETE)

        logging.info("ARM processing complete")

    elif job.disctype == "music":
        if utils.rip_music(job, logfile):
            utils.notify(job, NOTIFY_TITLE, f"Music CD: {job.label} {PROCESS_COMPLETE}")
            utils.scan_emby()
            # This shouldn't be needed. but to be safe
            job.status = "success"
            db.session.commit()
        else:
            logging.info("Music rip failed.  See previous errors.  Exiting. ")
            job.status = "fail"
            db.session.commit()
        job.eject()

    elif job.disctype == "data":
        logging.info("Disc identified as data")
        if utils.rip_data(job):
            utils.notify(job, NOTIFY_TITLE, f"Data disc: {job.label} copying complete. ")
        else:
            logging.info("Data rip failed.  See previous errors.  Exiting.")
        job.eject()

    else:
        logging.info("Couldn't identify the disc type. Exiting without any action.")


if __name__ == "__main__":
    # Make sure all directories are fully setup
    utils.arm_setup()
    args = entry()
    devpath = "/dev/" + args.devpath
    job = Job(devpath)
    logfile = logger.setup_logging(job)
    # Exit if drive isn't ready
    if utils.get_cdrom_status(devpath) != 4:
        logging.info("Drive appears to be empty or is not ready.  Exiting ARM.")
        sys.exit()
    # Don't put out anything if we are using the empty.log NAS_[0-9].log or NAS1_[0-9].log
    if logfile.find("empty.log") != -1 or re.search(r"(NAS|NAS1)_\d+\.log", logfile) is not None:
        sys.exit()
    # Check the db is current, if not update it
    utils.check_db_version(cfg['INSTALLPATH'], cfg['DBFILE'])
    # Sometimes drives trigger twice this stops multi runs from 1 udev trigger
    utils.duplicate_run_check(devpath)

    logging.info(f"Starting ARM processing at {datetime.datetime.now()}")

    # put in db
    job.status = "active"
    job.start_time = datetime.datetime.now()
    utils.database_adder(job)

    time.sleep(1)
    # Add the job.config to db
    config = Config(cfg, job_id=job.job_id)
    utils.database_adder(config)

    # Log version number
    with open(os.path.join(cfg["INSTALLPATH"], 'VERSION')) as version_file:
        version = version_file.read().strip()
    utils.get_git_commit()
    logging.info(f"ARM version: {version}")
    job.arm_version = version
    logging.info(("Python version: " + sys.version).replace('\n', ""))
    logging.info(f"User is: {getpass.getuser()}")
    # Delete old log files
    logger.clean_up_logs(cfg["LOGPATH"], cfg["LOGLIFE"])
    logging.info(f"Job: {job.label}")  # This will sometimes be none
    # Check for zombie jobs and update status to failed
    utils.clean_old_jobs()
    log_udev_params(devpath)

    try:
        main(logfile, job)
    except Exception as error:
        logging.exception("A fatal error has occurred and ARM is exiting.  See traceback below for details.")
        utils.notify(job, NOTIFY_TITLE, "ARM encountered a fatal error processing "
                                        f"{job.title}. Check the logs for more details. {error}")
        job.status = "fail"
        job.errors = str(error)
        job.eject()
    else:
        job.status = "success"
    finally:
        job.stop_time = datetime.datetime.now()
        job_length = job.stop_time - job.start_time
        minutes, seconds = divmod(job_length.seconds + job_length.days * 86400, 60)
        hours, minutes = divmod(minutes, 60)
        job.job_length = f'{hours:d}:{minutes:02d}:{seconds:02d}'
        db.session.commit()
