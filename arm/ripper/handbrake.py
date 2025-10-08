#!/usr/bin/env python3
"""Handbrake processing of dvd/blu-ray"""

import os
import logging
import subprocess
import re
import shlex
import arm.config.config as cfg

from arm.ripper import utils
from arm.ui import app, db  # noqa E402
from arm.models.job import JobState

PROCESS_COMPLETE = "Handbrake processing complete"


def run_handbrake_command(cmd, track=None, track_number=None):
    """
    Execute a HandBrake command and handle errors consistently.

    :param cmd: The HandBrake command to execute
    :param track: Optional track object to update status
    :param track_number: Optional track number for error messages
    :return: Output from HandBrake command
    :raises subprocess.CalledProcessError: If HandBrake fails
    """
    logging.debug(f"Sending command: {cmd}")

    try:
        hand_brake_output = subprocess.check_output(
            cmd,
            shell=True
        ).decode("utf-8")
        logging.debug(f"Handbrake exit code: {hand_brake_output}")
        if track:
            track.status = "success"
        return hand_brake_output
    except subprocess.CalledProcessError as hb_error:
        if track_number:
            err = f"Handbrake encoding of title {track_number} failed with code: {hb_error.returncode}" \
                  f"({hb_error.output})"
        else:
            err = f"Call to handbrake failed with code: {hb_error.returncode}({hb_error.output})"
        logging.error(err)
        if track:
            track.status = "fail"
            track.error = err
        raise subprocess.CalledProcessError(hb_error.returncode, cmd)


def build_handbrake_command(srcpath, filepathname, hb_preset, hb_args, logfile,
                            track_number=None, main_feature=False):
    """
    Build a HandBrake command string with consistent formatting.

    :param srcpath: Path to source for HB (dvd or files)
    :param filepathname: Full output path including filename
    :param hb_preset: HandBrake preset to use
    :param hb_args: Additional HandBrake arguments
    :param logfile: Logfile for HB to redirect output to
    :param track_number: Optional track number to encode
    :param main_feature: Whether to use --main-feature flag
    :return: Formatted command string
    """
    cmd = f"nice {cfg.arm_config['HANDBRAKE_CLI']} " \
          f"-i {shlex.quote(srcpath)} " \
          f"-o {shlex.quote(filepathname)} "

    if main_feature:
        cmd += "--main-feature "

    cmd += f"--preset \"{hb_preset}\" "

    if track_number is not None:
        cmd += f"-t {track_number} "

    cmd += f"{hb_args} " \
           f">> {logfile} 2>&1"

    return cmd


def handbrake_sleep_check(job):
    """Wait until there is a spot to transcode.

    If handbrake is used as a ripping utility (the source path is a device),
    this means that the drive is blocked. If we transcode after makemkv, the
    drive associated to the job is ejected at this point.
    """
    logging.debug("Handbrake starting.")
    utils.database_updater({"status": JobState.TRANSCODE_WAITING.value}, job)
    # TODO: send a notification that jobs are waiting ?
    utils.sleep_check_process("HandBrakeCLI", int(cfg.arm_config["MAX_CONCURRENT_TRANSCODES"]))
    logging.debug(f"Setting job status to '{JobState.TRANSCODE_ACTIVE.value}'")
    utils.database_updater({"status": JobState.TRANSCODE_ACTIVE.value}, job)


def handbrake_main_feature(srcpath, basepath, logfile, job):
    """
    Process dvd with main_feature enabled.\n\n
    :param srcpath: Path to source for HB (dvd or files)\n
    :param basepath: Path where HB will save trancoded files\n
    :param logfile: Logfile for HB to redirect output to\n
    :param job: Disc object\n
    :return: None
    """
    handbrake_sleep_check(job)
    logging.info("Starting DVD Movie main_feature processing")

    filename = job.title + "." + cfg.arm_config["DEST_EXT"]
    filepathname = os.path.join(basepath, filename)
    logging.info(f"Ripping title main_feature to {shlex.quote(filepathname)}")

    get_track_info(srcpath, job)

    track = job.tracks.filter_by(main_feature=True).first()
    if track is None:
        msg = "No main feature found by Handbrake. Turn main_feature to false in arm.yml and try again."
        logging.error(msg)
        raise RuntimeError(msg)

    track.filename = track.orig_filename = filename
    db.session.commit()

    hb_args, hb_preset = correct_hb_settings(job)
    cmd = build_handbrake_command(srcpath, filepathname, hb_preset, hb_args, logfile, main_feature=True)

    try:
        run_handbrake_command(cmd, track)
        logging.info("Handbrake call successful")
    except subprocess.CalledProcessError:
        job.errors = track.error
        job.status = JobState.FAILURE.value
        db.session.commit()
        raise

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")
    track.ripped = True
    db.session.commit()


def handbrake_all(srcpath, basepath, logfile, job):
    """
    Process all titles on the dvd\n
    :param srcpath: Path to source for HB (dvd or files)\n
    :param basepath: Path where HB will save trancoded files\n
    :param logfile: Logfile for HB to redirect output to\n
    :param job: Disc object\n
    :return: None
    """
    handbrake_sleep_check(job)
    logging.info("Starting BluRay/DVD transcoding - All titles")

    hb_args, hb_preset = correct_hb_settings(job)
    get_track_info(srcpath, job)

    logging.debug(f"Total number of tracks is {job.no_of_titles}")

    for track in job.tracks:
        # Don't raise error if we past max titles, skip and continue till HandBrake finishes
        if int(track.track_number) > job.no_of_titles:
            continue
        if track.length < int(cfg.arm_config["MINLENGTH"]):
            # too short
            logging.info(f"Track #{track.track_number} of {job.no_of_titles}. "
                         f"Length ({track.length}) is less than minimum length ({cfg.arm_config['MINLENGTH']}). "
                         f"Skipping...")
        elif track.length > int(cfg.arm_config["MAXLENGTH"]):
            # too long
            logging.info(f"Track #{track.track_number} of {job.no_of_titles}. "
                         f"Length ({track.length}) is greater than maximum length ({cfg.arm_config['MAXLENGTH']}). "
                         f"Skipping...")
        else:
            # just right
            logging.info(f"Processing track #{track.track_number} of {job.no_of_titles}. "
                         f"Length is {track.length} seconds.")

            track.filename = track.orig_filename = f"title_{track.track_number}.{cfg.arm_config['DEST_EXT']}"
            filepathname = os.path.join(basepath, track.filename)

            logging.info(f"Transcoding title {track.track_number} to {shlex.quote(filepathname)}")

            db.session.commit()

            cmd = build_handbrake_command(srcpath, filepathname, hb_preset, hb_args, logfile,
                                          track_number=track.track_number)

            try:
                run_handbrake_command(cmd, track, track.track_number)
            except subprocess.CalledProcessError:
                db.session.commit()
                raise

            track.ripped = True
            db.session.commit()

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")


def correct_hb_settings(job):
    """
    Get the correct custom arguments/presets for this disc
    :param job: The job
    :return: Correct preset and string arguments from A.R.M config
    """
    hb_args = ""
    hb_preset = ""
    if job.disctype == "dvd":
        hb_args = job.config.HB_ARGS_DVD
        hb_preset = job.config.HB_PRESET_DVD
    elif job.disctype == "bluray":
        hb_args = job.config.HB_ARGS_BD
        hb_preset = job.config.HB_PRESET_BD
    return hb_args, hb_preset


def handbrake_mkv(srcpath, basepath, logfile, job):
    """
    Process all mkv files in a directory.\n\n
    :param srcpath: Path to source for HB (dvd or files)\n
    :param basepath: Path where HB will save trancoded files\n
    :param logfile: Logfile for HB to redirect output to\n
    :param job: Disc object\n
    :return: None
    """
    # Added to limit number of transcodes
    handbrake_sleep_check(job)
    logging.info("Starting Handbrake for MKV files.")
    hb_args, hb_preset = correct_hb_settings(job)

    # This will fail if the directory raw gets deleted
    for files in os.listdir(srcpath):
        srcpathname = os.path.join(srcpath, files)
        destfile = os.path.splitext(files)[0]
        # MakeMKV always saves in mkv we need to update the db with the new filename
        logging.debug(destfile + ".mkv")
        job_current_track = job.tracks.filter_by(filename=destfile + ".mkv")
        for track in job_current_track:
            logging.debug("filename: " + track.filename)
            track.orig_filename = track.filename
            track.filename = destfile + "." + cfg.arm_config["DEST_EXT"]
            logging.debug("UPDATED filename: " + track.filename)
            db.session.commit()
        filename = destfile + "." + cfg.arm_config["DEST_EXT"]
        filepathname = os.path.join(basepath, filename)

        logging.info(f"Transcoding file {shlex.quote(files)} to {shlex.quote(filepathname)}")

        cmd = build_handbrake_command(srcpathname, filepathname, hb_preset, hb_args, logfile)
        run_handbrake_command(cmd)

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")


def get_track_info(srcpath, job):
    """
    Use HandBrake to get track info and update Track class\n\n
    :param srcpath: Path to disc\n
    :param job: Job instance\n
    :return: None
    """
    logging.info("Using HandBrake to get information on all the tracks on the disc.  This will take a few minutes...")

    cmd = f'{cfg.arm_config["HANDBRAKE_LOCAL"]} -i {shlex.quote(srcpath)} -t 0 --scan'
    logging.debug(f"Sending command: {cmd}")
    hand_break_output = handbrake_char_encoding(cmd)

    if hand_break_output is not None:
        t_pattern = re.compile(r'.*\+ title *')
        pattern = re.compile(r'.*duration:.*')
        seconds = 0
        t_no = 0
        fps = float(0)
        aspect = 0
        result = None
        main_feature = False
        for line in hand_break_output:

            # get number of titles
            if result is None:
                # scan: DVD has 12 title(s)
                result = re.search(r'scan: (BD|DVD) has (\d{1,3}) title\(s\)', line)

                if result:
                    titles = result.group(2).strip()
                    logging.debug(f"Line found is: {line}")
                    logging.info(f"Found {titles} titles")
                    job.no_of_titles = titles
                    db.session.commit()

            main_feature, t_no = title_finder(aspect, fps, job, line, main_feature, seconds, t_no, t_pattern)
            seconds = seconds_builder(line, pattern, seconds)
            main_feature = is_main_feature(line, main_feature)

            if (re.search(" fps", line)) is not None:
                fps = line.rsplit(' ', 2)[-2]
                aspect = line.rsplit(' ', 3)[-3]
                aspect = str(aspect).replace(",", "")
    else:
        logging.info("HandBrake unable to get track information")

    utils.put_track(job, t_no, seconds, aspect, fps, main_feature, "HandBrake")


def title_finder(aspect, fps, job, line, main_feature, seconds, t_no, t_pattern):
    """

    :param aspect:
    :param fps:
    :param job:
    :param line:
    :param main_feature:
    :param seconds:
    :param t_no:
    :param t_pattern:
    :return: None
    """
    if (re.search(t_pattern, line)) is not None:
        if t_no != 0:
            utils.put_track(job, t_no, seconds, aspect, fps, main_feature, "HandBrake")

        main_feature = False
        t_no = line.rsplit(' ', 1)[-1]
        t_no = t_no.replace(":", "")
    return main_feature, t_no


def is_main_feature(line, main_feature):
    """
    Check if we can find 'Main Feature' in hb output line\n
    :param str line: Line from HandBrake output
    :param bool main_feature:
    :return bool main_feature: Return true if we fine main feature
    """
    if (re.search("Main Feature", line)) is not None:
        main_feature = True
    return main_feature


def seconds_builder(line, pattern, seconds):
    """
    Find the track time and convert to seconds\n
    :param line: Line from HandBrake output
    :param pattern: regex patter
    :param seconds:
    :return:
    """
    if (re.search(pattern, line)) is not None:
        time = line.split()
        hour, mins, secs = time[2].split(':')
        seconds = int(hour) * 3600 + int(mins) * 60 + int(secs)
    return seconds


def handbrake_char_encoding(cmd):
    """
    Allows us to try multiple char encoding types\n\n
    :param cmd: CMD to push
    :return: the output from HandBrake or -1 if it fails
    """
    charset_found = False
    hand_brake_output = -1
    try:
        hand_brake_output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            shell=True
        ).decode('utf-8', 'ignore').splitlines()
    except subprocess.CalledProcessError as hb_error:
        logging.error("Couldn't find a valid track with utf-8 encoding. Trying with cp437")
        logging.error(f"Specific error is: {hb_error}")
    else:
        charset_found = True
    if not charset_found:
        try:
            hand_brake_output = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                shell=True
            ).decode('cp437').splitlines()
        except subprocess.CalledProcessError as hb_error:
            logging.error("Couldn't find a valid track. "
                          "Try running the command manually to see more specific errors.")
            logging.error(f"Specific error is: {hb_error}")
            # If it doesn't work now we either have bad encoding or HB has ran into issues
    return hand_brake_output
