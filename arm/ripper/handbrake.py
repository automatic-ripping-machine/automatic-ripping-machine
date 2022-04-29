#!/usr/bin/env python3
# Handbrake processing of dvd/bluray

import sys
import os
import logging
import subprocess
import re
import shlex
# Added for sleep check/ transcode limits
import time  # noqa: F401
import datetime  # noqa: F401
import psutil  # noqa: F401

from arm.ripper import utils
from arm.ui import app, db  # noqa E402
from arm.config.config import cfg

PROCESS_COMPLETE = "Handbrake processing complete"


def handbrake_mainfeature(srcpath, basepath, logfile, job):
    """process dvd with mainfeature enabled.\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    job = Job object\n

    Returns nothing
    """
    logging.info("Starting DVD Movie Mainfeature processing")
    logging.debug("Handbrake starting: ")
    logging.debug("\n\r" + job.pretty_table())

    utils.database_updater({'status': "waiting_transcode"}, job)
    # TODO: send a notification that jobs are waiting ?
    utils.sleep_check_process("HandBrakeCLI", int(cfg["MAX_CONCURRENT_TRANSCODES"]))
    logging.debug("Setting job status to 'transcoding'")
    utils.database_updater({'status': "transcoding"}, job)
    filename = os.path.join(basepath, job.title + "." + cfg["DEST_EXT"])
    filepathname = os.path.join(basepath, filename)
    logging.info(f"Ripping title Mainfeature to {shlex.quote(filepathname)}")

    get_track_info(srcpath, job)

    track = job.tracks.filter_by(main_feature=True).first()
    if track is None:
        msg = "No main feature found by Handbrake. Turn MAINFEATURE to false in arm.yml and try again."
        logging.error(msg)
        raise RuntimeError(msg)

    track.filename = track.orig_filename = filename
    db.session.commit()

    if job.disctype == "dvd":
        hb_args = cfg["HB_ARGS_DVD"]
        hb_preset = cfg["HB_PRESET_DVD"]
    elif job.disctype == "bluray":
        hb_args = cfg["HB_ARGS_BD"]
        hb_preset = cfg["HB_PRESET_BD"]

    cmd = 'nice {0} -i {1} -o {2} --main-feature --preset "{3}" {4} >> {5} 2>&1'.format(
        cfg["HANDBRAKE_CLI"],
        shlex.quote(srcpath),
        shlex.quote(filepathname),
        hb_preset,
        hb_args,
        logfile
    )

    logging.debug(f"Sending command: {cmd}")

    try:
        subprocess.check_output(cmd, shell=True).decode("utf-8")
        logging.info("Handbrake call successful")
        track.status = "success"
    except subprocess.CalledProcessError as hb_error:
        err = f"Call to handbrake failed with code: {hb_error.returncode}({hb_error.output})"
        logging.error(err)
        track.status = "fail"
        track.error = err
        job.status = "fail"
        db.session.commit()
        sys.exit(err)

    logging.info(PROCESS_COMPLETE)
    logging.debug("\n\r" + job.pretty_table())
    track.ripped = True
    db.session.commit()


def handbrake_all(srcpath, basepath, logfile, job):
    """Process all titles on the dvd\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    job = Disc object\n

    Returns nothing
    """

    # Wait until there is a spot to transcode
    job.status = "waiting_transcode"
    db.session.commit()
    utils.sleep_check_process("HandBrakeCLI", int(cfg["MAX_CONCURRENT_TRANSCODES"]))
    job.status = "transcoding"
    db.session.commit()
    logging.info("Starting BluRay/DVD transcoding - All titles")

    if job.disctype == "dvd":
        hb_args = cfg["HB_ARGS_DVD"]
        hb_preset = cfg["HB_PRESET_DVD"]
    elif job.disctype == "bluray":
        hb_args = cfg["HB_ARGS_BD"]
        hb_preset = cfg["HB_PRESET_BD"]

    get_track_info(srcpath, job)

    logging.debug(f"Total number of tracks is {job.no_of_titles}")

    for track in job.tracks:

        if track.length < int(cfg["MINLENGTH"]):
            # too short
            logging.info(f"Track #{track.track_number} of {job.no_of_titles}. "
                         f"Length ({track.length}) is less than minimum length ({cfg['MINLENGTH']}).  Skipping")
        elif track.length > int(cfg["MAXLENGTH"]):
            # too long
            logging.info(f"Track #{track.track_number} of {job.no_of_titles}. "
                         f"Length ({track.length}) is greater than maximum length ({cfg['MAXLENGTH']}).  Skipping")
        else:
            # just right
            logging.info(f"Processing track #{track.track_number} of {job.no_of_titles}. "
                         f"Length is {track.length} seconds.")

            filename = "title_" + str.zfill(str(track.track_number), 2) + "." + cfg["DEST_EXT"]
            filepathname = os.path.join(basepath, filename)

            logging.info(f"Transcoding title {track.track_number} to {shlex.quote(filepathname)}")

            track.filename = track.orig_filename = filename
            db.session.commit()

            cmd = 'nice {0} -i {1} -o {2} --preset "{3}" -t {4} {5}>> {6} 2>&1'.format(
                cfg["HANDBRAKE_CLI"],
                shlex.quote(srcpath),
                shlex.quote(filepathname),
                hb_preset,
                str(track.track_number),
                hb_args,
                logfile
            )

            logging.debug(f"Sending command: {cmd}")

            try:
                hb = subprocess.check_output(
                    cmd,
                    shell=True
                ).decode("utf-8")
                logging.debug(f"Handbrake exit code: {hb}")
                track.status = "success"
            except subprocess.CalledProcessError as hb_error:
                err = f"Handbrake encoding of title {track.track_number} failed with code: {hb_error.returncode}" \
                      f"({hb_error.output})"
                logging.error(err)
                track.status = "fail"
                track.error = err

            track.ripped = True
            db.session.commit()

    logging.info(PROCESS_COMPLETE)
    logging.debug("\n\r" + job.pretty_table())


def handbrake_mkv(srcpath, basepath, logfile, job):
    """process all mkv files in a directory.\n
    srcpath = Path to source for HB (dvd or files)\n
    basepath = Path where HB will save trancoded files\n
    logfile = Logfile for HB to redirect output to\n
    job = Disc object\n

    Returns nothing
    """
    # Added to limit number of transcodes
    job.status = "waiting_transcode"
    db.session.commit()
    utils.sleep_check_process("HandBrakeCLI", int(cfg["MAX_CONCURRENT_TRANSCODES"]))
    job.status = "transcoding"
    db.session.commit()
    if job.disctype == "dvd":
        hb_args = cfg["HB_ARGS_DVD"]
        hb_preset = cfg["HB_PRESET_DVD"]
    elif job.disctype == "bluray":
        hb_args = cfg["HB_ARGS_BD"]
        hb_preset = cfg["HB_PRESET_BD"]

    # This will fail if the directory raw gets deleted
    for f in os.listdir(srcpath):
        srcpathname = os.path.join(srcpath, f)
        destfile = os.path.splitext(f)[0]
        filename = os.path.join(basepath, destfile + "." + cfg["DEST_EXT"])
        filepathname = os.path.join(basepath, filename)

        logging.info(f"Transcoding file {shlex.quote(f)} to {shlex.quote(filepathname)}")

        cmd = 'nice {0} -i {1} -o {2} --preset "{3}" {4}>> {5} 2>&1'.format(
            cfg["HANDBRAKE_CLI"],
            shlex.quote(srcpathname),
            shlex.quote(filepathname),
            hb_preset,
            hb_args,
            logfile
        )

        logging.debug(f"Sending command: {cmd}")

        try:
            hb = subprocess.check_output(
                cmd,
                shell=True
            ).decode("utf-8")
            logging.debug(f"Handbrake exit code: {hb}")
        except subprocess.CalledProcessError as hb_error:
            err = f"Handbrake encoding of file {shlex.quote(f)} failed with code: {hb_error.returncode}" \
                  f"({hb_error.output})"
            logging.error(err)
            # job.errors.append(f)

    logging.info(PROCESS_COMPLETE)
    logging.debug("\n\r" + job.pretty_table())


def get_track_info(srcpath, job):
    """Use HandBrake to get track info and updatte Track class\n

    srcpath = Path to disc\n
    job = Job instance\n
    """
    charset_found = False
    logging.info("Using HandBrake to get information on all the tracks on the disc.  This will take a few minutes...")

    cmd = '{0} -i {1} -t 0 --scan'.format(
        cfg["HANDBRAKE_CLI"],
        shlex.quote(srcpath)
    )

    logging.debug(f"Sending command: {cmd}")
    try:
        hb = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True
        ).decode('utf-8', 'ignore').splitlines()
    except subprocess.CalledProcessError as hb_error:
        logging.error("Couldn't find a valid track. Try running the command manually to see more specific errors.")
        logging.error(f"Specific error is: {hb_error}")
    else:
        charset_found = True
    if not charset_found:
        try:
            hb = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                shell=True
            ).decode('cp437').splitlines()
        except subprocess.CalledProcessError as hb_error:
            logging.error("Couldn't find a valid track. Try running the command manually to see more specific errors.")
            logging.error(f"Specific error is: {hb_error}")
            # If it doesnt work now we either have bad encoding or HB has ran into issues
            return -1

    t_pattern = re.compile(r'.*\+ title *')
    pattern = re.compile(r'.*duration\:.*')
    seconds = 0
    t_no = 0
    fps = float(0)
    aspect = 0
    result = None
    mainfeature = False
    for line in hb:

        # get number of titles
        if result is None:
            if job.disctype == "bluray":
                result = re.search('scan: BD has (.*) title\(s\)', line)  # noqa: W605
            else:
                result = re.search('scan: DVD has (.*) title\(s\)', line)  # noqa: W605

            if result:
                titles = result.group(1)
                titles = titles.strip()
                logging.debug(f"Line found is: {line}")
                logging.info(f"Found {titles} titles")
                job.no_of_titles = titles
                db.session.commit()

        if (re.search(t_pattern, line)) is not None:
            if t_no == 0:
                pass
            else:
                utils.put_track(job, t_no, seconds, aspect, fps, mainfeature, "handbrake")

            mainfeature = False
            t_no = line.rsplit(' ', 1)[-1]
            t_no = t_no.replace(":", "")

        if (re.search(pattern, line)) is not None:
            t = line.split()
            h, m, s = t[2].split(':')
            seconds = int(h) * 3600 + int(m) * 60 + int(s)

        if (re.search("Main Feature", line)) is not None:
            mainfeature = True

        if (re.search(" fps", line)) is not None:
            fps = line.rsplit(' ', 2)[-2]
            aspect = line.rsplit(' ', 3)[-3]
            aspect = str(aspect).replace(",", "")

    utils.put_track(job, t_no, seconds, aspect, fps, mainfeature, "handbrake")
