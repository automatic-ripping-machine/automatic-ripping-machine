#!/usr/bin/env python3
import sys
import os
import logging
import subprocess
import time
import shlex

from arm.config.config import cfg
from arm.ripper import utils  # noqa: E402
from arm.ui import db  # noqa: F401, E402


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
    Rip Blu-rays with MakeMKV\n\n

    :param logfile: Location of logfile to redirect MakeMKV logs to
    :param job: job object
    :return: path to ripped files.
    """

    # confirm MKV is working, beta key hasn't expired
    prep_mkv()
    logging.info(f"Starting MakeMKV rip. Method is {cfg['RIPMETHOD']}")
    # get MakeMKV disc number
    logging.debug("Getting MakeMKV disc number")
    cmd = f"makemkvcon -r info disc:9999  |grep {job.devpath} |grep -oP '(?<=:).*?(?=,)'"
    try:
        mdisc = subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
        logging.info(f"MakeMKV disc number: {mdisc.strip()}")
    except subprocess.CalledProcessError as mdisc_error:
        raise MakeMkvRuntimeError(mdisc_error)

    # get filesystem in order
    rawpath = setup_rawpath(job, os.path.join(str(cfg["RAW_PATH"]), str(job.title)))

    # rip bluray
    if cfg["RIPMETHOD"] == "backup" and job.disctype == "bluray":
        # backup method
        cmd = f'makemkvcon backup --decrypt {cfg["MKV_ARGS"]} ' \
              f'-r disc:{mdisc.strip()} {shlex.quote(rawpath)}>> {logfile}'
        logging.info("Backup up disc")
        run_makemkv(cmd)
    elif cfg["RIPMETHOD"] == "mkv" or job.disctype == "dvd":
        # mkv method
        get_track_info(mdisc, job)

        # if no maximum length, process the whole disc in one command
        if int(cfg["MAXLENGTH"]) > 99998:
            cmd = 'makemkvcon mkv {0} -r --progress=-stdout --messages=-stdout dev:{1} all {2} --minlength={3}>> {4}'.format(
                cfg["MKV_ARGS"],
                job.devpath,
                shlex.quote(rawpath),
                cfg["MINLENGTH"],
                logfile
            )
            run_makemkv(cmd)
        else:
            process_tracks(job, logfile, rawpath)
    else:
        logging.info("I'm confused what to do....  Passing on MakeMKV")

    job.eject()
    logging.info(f"Exiting MakeMKV processing with return value of: {rawpath}")
    return rawpath


def process_tracks(job, logfile, rawpath):
    """
    For processing single tracks from MakeMKV
    :param job: job object
    :param str logfile: path of logfile
    :param str rawpath:
    :return:
    """
    # process one track at a time based on track length
    for track in job.tracks:
        if track.length < int(cfg["MINLENGTH"]):
            # too short
            logging.info(f"Track #{track.track_number} of {job.no_of_titles}. Length ({track.length}) "
                         f"is less than minimum length ({cfg['MINLENGTH']}).  Skipping")
        elif track.length > int(cfg["MAXLENGTH"]):
            # too long
            logging.info(f"Track #{track.track_number} of {job.no_of_titles}. "
                         f"Length ({track.length}) is greater than maximum length ({cfg['MAXLENGTH']}).  "
                         "Skipping")
        else:
            # just right
            logging.info(f"Processing track #{track.track_number} of {(job.no_of_titles - 1)}. "
                         f"Length is {track.length} seconds.")
            filepathname = os.path.join(rawpath, track.filename)
            logging.info(f"Ripping title {track.track_number} to {shlex.quote(filepathname)}")

            cmd = 'makemkvcon mkv {0} -r --progress=-stdout --messages=-stdout' \
                  'dev:{1} {2} {3} --minlength={4}>> {5}'.format(cfg["MKV_ARGS"],
                                                                 job.devpath,
                                                                 str(track.track_number),
                                                                 shlex.quote(rawpath),
                                                                 cfg["MINLENGTH"],
                                                                 logfile
                                                                 )
            run_makemkv(cmd)


def setup_rawpath(job, rawpath):
    """
    Checks if we need to create path and does so if needed\n\n
    :param job:
    :param rawpath:
    :return: rawpath
    """

    logging.info(f"Destination is {rawpath}")
    if not os.path.exists(rawpath):
        try:
            os.makedirs(rawpath)
        except OSError:
            err = f"Couldn't create the base file path: {rawpath} Probably a permissions error"
            logging.debug(err)
    else:
        logging.info(f"{rawpath} exists.  Adding timestamp.")
        ts = round(time.time() * 100)
        rawpath = os.path.join(str(cfg["RAW_PATH"]), f"{job.title}_{ts}")
        logging.info(f"rawpath is {rawpath}")
        try:
            os.makedirs(rawpath)
        except OSError:
            err = f"Couldn't create the base file path: {rawpath} Probably a permissions error"
            sys.exit(err)
    return rawpath


def prep_mkv():
    """Make sure the MakeMKV key is up-to-date

    Parameters:
        job: job object\n
    Raises:
        RuntimeError
    """
    
    try:
        logging.info("Updating MakeMKV key...")
        update_cmd = "/bin/bash /opt/arm/scripts/update_key.sh"
        subprocess.run(update_cmd, capture_output=True, shell=True, check=True)  # noqa: F841
    except subprocess.CalledProcessError as update_err:
        err = f"Error updating MakeMKV key, return code: {update_err.returncode}"
        logging.error(err)
        raise RuntimeError(err)


def get_track_info(mdisc, job):
    """
    Use MakeMKV to get track info and update Track class

    :param mdisc: MakeMKV disc number
    :param job: Job instance
    :return: None
    """

    logging.info("Using MakeMKV to get information on all the tracks on the disc.  This will take a few minutes...")

    cmd = f'makemkvcon -r --progress=-stdout --messages=-stdout --cache=1 info disc:{mdisc}'
    logging.debug(f"Sending command: {cmd}")
    try:
        mkv = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True
        ).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as mdisc_error:
        raise MakeMkvRuntimeError(mdisc_error)

    track = 0
    fps = float(0)
    aspect = ""
    seconds = 0
    filename = ""

    for line in mkv:
        if line.split(":")[0] in ("MSG", "TCOUNT", "CINFO", "TINFO", "SINFO"):
            line_split = line.split(":", 1)
            msg_type = line_split[0]
            msg = line_split[1].split(",")
            line_track = int(msg[0])

            if msg_type == "TCOUNT":
                titles = int(line_split[1].strip())
                logging.info(f"Found {titles} titles")
                utils.database_updater({'no_of_titles': titles}, job)
            if msg_type == "TINFO":
                if track != line_track:
                    if line_track == int(0):
                        pass
                    else:
                        utils.put_track(job, track, seconds, aspect, fps, False, "makemkv", filename)
                    track = line_track

                if msg[1] == "27":
                    filename = msg[3].replace('"', '').strip()

            if msg_type == "TINFO" and msg[1] == "9":
                len_hms = msg[3].replace('"', '').strip()
                h, m, s = len_hms.split(':')
                seconds = int(h) * 3600 + int(m) * 60 + int(s)

            if msg_type == "SINFO" and msg[1] == "0":
                if msg[2] == "20":
                    aspect = msg[4].replace('"', '').strip()
                elif msg[2] == "21":
                    fps = msg[4].split()[0]
                    fps = fps.replace('"', '').strip()
                    fps = float(fps)

    utils.put_track(job, track, seconds, aspect, fps, False, "makemkv", filename)


def run_makemkv(cmd):
    """
    Run MakeMKV with the command passed to the function.

    Parameters:
        cmd: the command to be run
    Raises:
        MakeMkvRuntimeError
    """

    logging.debug(f"Ripping with the following command: {cmd}")
    try:
        subprocess.run(cmd, capture_output=True, shell=True, check=True)  # noqa: F841
    except subprocess.CalledProcessError as mkv_error:
        raise MakeMkvRuntimeError(mkv_error)
