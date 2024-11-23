#!/usr/bin/env python3
"""
Main file for dealing with connecting to MakeMKV and handling errors
"""
import os
import logging
import subprocess
import shlex
from time import sleep

from arm.models.track import Track
from arm.ripper import utils  # noqa: E402
from arm.ui import db  # noqa: F401, E402
import arm.config.config as cfg  # noqa E402
from arm.ripper.utils import notify


class MakeMkvRuntimeError(RuntimeError):
    """Exception raised when a CalledProcessError is thrown during execution of a `makemkvcon` command.

    Attributes:
        message: the explanation of the error
    """

    def __init__(self, error):
        self.message = f"Call to MakeMKV failed with code: {error.returncode} ({error.output})"
        logging.error(self.message)
        raise super().__init__(self.message)


def makemkv(logfile, job):
    """
    Rip Blu-rays/DVDs with MakeMKV\n\n

    :param logfile: Location of logfile to redirect MakeMKV logs to
    :param job: job object
    :return: path to ripped files.
    """

    # Get drive mode for the current drive
    mode = utils.get_drive_mode(job.devpath)
    logging.info(f"Job running in {mode} mode")

    # confirm MKV is working, beta key hasn't expired
    prep_mkv(logfile)
    logging.info(f"Starting MakeMKV rip. Method is {job.config.RIPMETHOD}")
    # get MakeMKV disc number
    logging.debug("Getting MakeMKV disc number")
    cmd = f"makemkvcon -r info disc:9999 | grep {job.devpath} | grep -oP '(?<=:).*?(?=,)'"
    logging.debug(f"Using command: {cmd}")
    try:
        mdisc = subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
        logging.info(f"MakeMKV disc number: {mdisc.strip()}")
        logging.debug(f"Disk raw number: {mdisc}")
    except subprocess.CalledProcessError as mdisc_error:
        raise MakeMkvRuntimeError(mdisc_error) from mdisc_error

    # get filesystem in order
    rawpath = setup_rawpath(job, os.path.join(str(job.config.RAW_PATH), str(job.title)))
    logging.info(f"Processing files to: {rawpath}")
    # Rip bluray
    if (job.config.RIPMETHOD == "backup" or job.config.RIPMETHOD == "backup_dvd") and job.disctype == "bluray":
        # backup method
        cmd = f'makemkvcon backup --decrypt {job.config.MKV_ARGS} --minlength={job.config.MINLENGTH}' \
              f'--progress={os.path.join(job.config.LOGPATH, "progress", str(job.job_id))}.log ' \
              f'--messages=-stdout ' \
              f'-r disc:{mdisc.strip()} {shlex.quote(rawpath)}'
        logging.info("Backing up disc")
        run_makemkv(cmd, logfile)
    # Rip Blu-ray without enhanced protection or dvd disc
    elif job.config.RIPMETHOD == "mkv" or job.disctype == "dvd":
        get_track_info(mdisc, job)
        if job.config.MAINFEATURE:
            logging.info("Trying to find mainfeature")
            track = Track.query.filter_by(job_id=job.job_id).order_by(Track.length.desc()).first()
            rip_mainfeature(job, track, logfile, rawpath)

        # Run if mode is manual, user selects tracks
        elif mode == 'manual':
            # Set job status to waiting
            job.status = "waiting"
            db.session.commit()
            # Alert User tracks are ready and wait, waits for 30 minutes
            job_state = manual_wait(job)
            # Process Tracks
            if job_state:
                # Response from user provided, process requested tracks
                process_single_tracks(job, logfile, rawpath, mode)
            else:
                # Notify User, no action was taken
                title = "ARM is Sad - Job Abandoned"
                message = "You left me alone in the cold and dark, I forgot who I was. Your job has been abandoned."
                notify(job, title, message)

                # Setting rawpath to None to set the job as failed when returning to arm_ripper
                rawpath = None

        # if no maximum length, process the whole disc in one command
        elif int(job.config.MAXLENGTH) > 99998:
            cmd = f'makemkvcon mkv {job.config.MKV_ARGS} -r ' \
                  f'--progress={os.path.join(job.config.LOGPATH, "progress", str(job.job_id))}.log ' \
                  f'--messages=-stdout ' \
                  f'dev:{job.devpath} all {shlex.quote(rawpath)} --minlength={job.config.MINLENGTH}'
            run_makemkv(cmd, logfile)
        else:
            process_single_tracks(job, logfile, rawpath, 'auto')
    else:
        logging.info("I'm confused what to do....  Passing on MakeMKV")

    job.eject()
    logging.info(f"Exiting MakeMKV processing with return value of: {rawpath}")
    return rawpath


def rip_mainfeature(job, track, logfile, rawpath):
    """
    Find and rip only the main feature when using Blu-rays
    """
    logging.info(f"Processing track #{track.track_number} as mainfeature. "
                 f"Length is {track.length} seconds.")
    filepathname = os.path.join(rawpath, track.filename)
    logging.info(f"Ripping title {track.track_number} to {shlex.quote(filepathname)}")
    cmd = f'makemkvcon mkv {job.config.MKV_ARGS} -r' \
          f' --progress={os.path.join(job.config.LOGPATH, "progress", str(job.job_id))}.log' \
          f' --messages=-stdout ' \
          f'dev:{job.devpath} {track.track_number} {shlex.quote(rawpath)} ' \
          f'--minlength={job.config.MINLENGTH}'
    # Possibly update db to say track was ripped
    run_makemkv(cmd, logfile)


def process_single_tracks(job, logfile, rawpath, mode: str):
    """
    For processing single tracks from MakeMKV one at a time
    :param job: job object
    :param str logfile: path of logfile
    :param str rawpath:
    :param str mode: drive mode (auto or manual)
    :return:
    """
    # process one track at a time based on track length
    for track in job.tracks:
        # Process single track automatically based on start and finish times
        if mode == 'auto':
            if track.length < int(job.config.MINLENGTH):
                # too short
                logging.info(f"Track #{track.track_number} of {job.no_of_titles}. Length ({track.length}) "
                             f"is less than minimum length ({job.config.MINLENGTH}).  Skipping")
                track.process = False

            elif track.length > int(job.config.MAXLENGTH):
                # too long
                logging.info(f"Track #{track.track_number} of {job.no_of_titles}. "
                             f"Length ({track.length}) is greater than maximum length ({job.config.MAXLENGTH}).  "
                             "Skipping")
                track.process = False
            else:
                # track is just right
                track.process = True

        # Rip the track if the user has set it to rip, or in auto mode and the time is good
        if track.process:
            logging.info(f"Processing track #{track.track_number} of {(job.no_of_titles - 1)}. "
                         f"Length is {track.length} seconds.")
            filepathname = os.path.join(rawpath, track.filename)
            logging.info(f"Ripping title {track.track_number} to {shlex.quote(filepathname)}")

            cmd = f'makemkvcon mkv {job.config.MKV_ARGS} -r ' \
                  f'--progress={os.path.join(job.config.LOGPATH, "progress", str(job.job_id))}.log ' \
                  f'--messages=-stdout ' \
                  f'dev:{job.devpath} {track.track_number} {shlex.quote(rawpath)}'
            run_makemkv(cmd, logfile)


def setup_rawpath(job, raw_path):
    """
    Checks if we need to create path and does so if needed\n\n
    :param job:
    :param raw_path:
    :return: raw_path
    """

    logging.info(f"Destination is {raw_path}")
    if not os.path.exists(raw_path):
        try:
            os.makedirs(raw_path)
        except OSError:
            err = f"Couldn't create the base file path: {raw_path}. Probably a permissions error"
            logging.error(err)
    else:
        logging.info(f"{raw_path} exists.  Adding timestamp.")
        raw_path = os.path.join(str(job.config.RAW_PATH), f"{job.title}_{job.stage}")
        logging.info(f"raw_path is {raw_path}")
        try:
            os.makedirs(raw_path)
        except OSError:
            err = f"Couldn't create the base file path: {raw_path}. Probably a permissions error"
            raise OSError(err) from OSError
    return raw_path


def prep_mkv(logfile):
    """Make sure the MakeMKV key is up-to-date

    Parameters:
        logfile: Location of logfile to redirect MakeMKV logs to
    Raises:
        RuntimeError
    """
    try:
        logging.info("Updating MakeMKV key...")
        update_cmd = "/bin/bash /opt/arm/scripts/update_key.sh"

        # if MAKEMKV_PERMA_KEY is populated
        if cfg.arm_config['MAKEMKV_PERMA_KEY'] is not None and cfg.arm_config['MAKEMKV_PERMA_KEY'] != "":
            logging.debug("MAKEMKV_PERMA_KEY populated, using that...")
            # add MAKEMKV_PERMA_KEY as an argument to the command
            update_cmd = f"{update_cmd} {cfg.arm_config['MAKEMKV_PERMA_KEY']}"

        subprocess.run(f"{update_cmd} >> {logfile}", capture_output=True, shell=True, check=True)
    except subprocess.CalledProcessError as update_err:
        err = f"Error updating MakeMKV key, return code: {update_err.returncode}"
        logging.error(err)
        raise RuntimeError(err) from update_err


def get_track_info(mdisc, job):
    """
    Use MakeMKV to get track info and update Track class

    :param mdisc: MakeMKV disc number
    :param job: Job instance
    :return: None

    .. note:: For help with MakeMKV codes:
    https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/MakeMKV-Codes
    """

    logging.info("Using MakeMKV to get information on all the tracks on the disc. This will take a few minutes...")

    cmd = f'makemkvcon -r --progress={os.path.join(job.config.LOGPATH, "progress", str(job.job_id))}.log ' \
          f'--messages=-stdout --minlength={job.config.MINLENGTH} ' \
          f'--cache=1 info disc:{mdisc}'
    logging.debug(f"Sending command: {cmd}")
    try:
        mkv = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True
        ).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as mdisc_error:
        raise MakeMkvRuntimeError(mdisc_error) from mdisc_error

    track = 0
    fps = float(0)
    aspect = ""
    seconds = 0
    filename = ""
    for line in mkv:
        # MSG:3028 - track was added (contains total length and chapter length)
        # MSG:3025 - too short - track was skipped
        # MSG:2003 - read error
        if line.split(":")[0] in ("MSG", "TCOUNT", "CINFO", "TINFO", "SINFO"):
            line_split = line.split(":", 1)
            msg_type = line_split[0]
            msg = line_split[1].split(",")
            line_track = int(msg[0])
            # Total track count
            if msg_type == "TCOUNT":
                logging.info(f"Found {line_split[1].strip()} titles")
                utils.database_updater({'no_of_titles': int(line_split[1].strip())}, job)
            # Title info add track and get filename
            if msg_type == "TINFO":
                filename, track = add_track_filename(aspect, filename, fps, job,
                                                     line_track, msg, seconds, track)
            # Title length
            seconds = find_track_length(msg, msg_type, seconds)
            # Aspect ratio and fps
            aspect, fps = find_aspect_fps(aspect, msg, msg_type, fps)
    # If we haven't already added any tracks add one with what we have
    utils.put_track(job, track, seconds, aspect, str(fps), False, "MakeMKV", filename)


def find_track_length(msg, msg_type, seconds):
    """
    Find the track length from TINFO msg from MakeMKV\n
    :param msg: current MakeMKV line split by ','
    :param msg_type: the message type from MakeMKV
    :param seconds: length in seconds of file
    :return: seconds of file
    """
    if msg_type == "TINFO" and msg[1] == "9":
        len_hms = msg[3].replace('"', '').strip()
        hour, mins, secs = len_hms.split(':')
        seconds = int(hour) * 3600 + int(mins) * 60 + int(secs)
    return seconds


def find_aspect_fps(aspect, msg, msg_type, fps):
    """
    Search current line and find the file's aspect ratio and fps if msg_type is SINFO\n
    :param str aspect: aspect ratio (stored as float but db wants string)
    :param msg: current MakeMKV line split by ','
    :param msg_type: the message type from MakeMKV
    :param float fps: fps of file
    :return: [aspect, fps]

    .. note::
           aspect.msg - ['0', '0', '20', '0', '"16:9"']\n
           fps.msg - ['0', '0', '21', '0', '"25"']\n
    """
    if msg_type == "SINFO" and msg[1] == "0":
        if msg[2] == "20":
            # aspect comes wrapped in "" remove them
            aspect = msg[4].replace('"', '').strip()
        elif msg[2] == "21":
            fps = msg[4].split()[0]
            fps = fps.replace('"', '').strip()
            fps = float(fps)
    return aspect, fps


def add_track_filename(aspect, filename, fps, job, line_track, msg, seconds, track):
    """
    Only add tracks that weren't previously added ? Also finds filename and removes quotes around it\n
    :param aspect: Aspect ratio of file
    :param filename: Filename of file
    :param fps: FPS of file
    :param job: Job the track belongs to
    :param line_track: e.g TINFO: **3** ,8,0,"2"
    :param msg: current line from MakeMKV split into array
    :param int seconds: Length of track
    :param track: Track number of current file
    :return: [filename, track]
    """
    if track != line_track:
        if line_track != int(0):
            utils.put_track(job, track, seconds, aspect, fps, False, "MakeMKV", filename)
        track = line_track
    if msg[1] == "27":
        filename = msg[3].replace('"', '').strip()
    return filename, track


def run_makemkv(cmd, logfile):
    """
    Run MakeMKV with the command passed to the function.

    Parameters:
        cmd: the command to be run
        logfile: Location of logfile to redirect MakeMKV logs to
    Raises:
        MakeMkvRuntimeError
    """

    logging.debug(f"Ripping with the following command: {cmd}")
    try:
        # need to check output for '0 titles saved'
        subprocess.run(f"{cmd} >> {logfile}", capture_output=True, shell=True, check=True)
    except subprocess.CalledProcessError as mkv_error:
        raise MakeMkvRuntimeError(mkv_error) from mkv_error


def manual_wait(job) -> bool:
    """
    Pause execution to allow for user interaction and monitor job readiness.

    This function initiates a manual wait mode for a specified job, notifying the user
    to configure job parameters within a set time limit. The function sends periodic
    reminders and checks the job's readiness state. If the job is set to `manual_start`
    before the timeout, it exits early; otherwise, it continues until time expires.

    Parameters:
        job (Job): An instance of the job to monitor, which includes attributes
                   such as `job_id` and `manual_start` indicating job readiness.

    Returns:
        bool: `True` if the user sets the job to ready (`manual_start` is enabled)
              within the wait time, otherwise `False`.

    Notes:
        - The function checks in one minute intervals for state changes
        - A reminder is sent every 10 minutes.
        - A final notification is sent when one minute is left, warning of potential
          cancellation.
    """
    user_ready = False
    wait_time: int = 30

    title = "Manual Mode Activated!"
    message = f"ARM has taken it's hands off the wheels. You have {wait_time} minutes to set the job."
    notify(job, title, message)

    # Wait for the user to set the files and then start
    title = "Waiting for input on job!"
    for i in range(wait_time, 0, -1):
        # Wait for a minute
        sleep(60)

        # Refresh job data
        db.session.refresh(job)
        logging.debug(f"Wait time logging: [{i}] mins - Ready: [{job.manual_start}]")

        # Check the job state (true once ready)
        if job.manual_start:
            user_ready = True
            title = "The Wait is Over"
            message = "Thanks for not forgetting me, I am now processing your job."
            notify(job, title, message)
            break
        else:
            # If nothing has happened, remind the user every 5 minutes
            if i % 5 == 0 and i != wait_time:
                body = f"Don't forget me, I need your help to continue doing ARM things!. You have {i} minutes."
                notify(job, title, body)

            if i == 1:
                body = "ARM is about to cancel this job!!! You have less than 1 minute left!"
                notify(job, title, body)

    return user_ready
