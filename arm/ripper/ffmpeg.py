#!/usr/bin/env python3
"""FFMPEG processing of dvd/blu-ray"""

import os
import logging
import subprocess
import shlex
import arm.config.config as cfg

from arm.ripper import utils
from arm.ui import app, db  # noqa E402
from arm.models.job import JobState

PROCESS_COMPLETE = "FFMPEG processing complete"


def ffmpeg_sleep_check(job):
    """Wait until there is a spot to transcode (FFmpeg variant).

    Mirrors handbrake_sleep_check but uses the FFMPEG_CLI token and
    updates the job state via the database_updater helper.
    """
    logging.debug("FFMPEG starting.")
    utils.database_updater({"status": JobState.TRANSCODE_WAITING.value}, job)
    # TODO: send a notification that jobs are waiting ?
    utils.sleep_check_process(cfg.arm_config["FFMPEG_CLI"], int(cfg.arm_config["MAX_CONCURRENT_TRANSCODES"]))
    logging.debug(f"Setting job status to '{JobState.TRANSCODE_ACTIVE.value}'")
    utils.database_updater({"status": JobState.TRANSCODE_ACTIVE.value}, job)


def correct_ffmpeg_settings(job):
    """
    Get the correct custom arguments/options for FFmpeg for this disc.

    Tries to read per-job config attributes (if present), otherwise falls
    back to global cfg.arm_config values.
    :param job: The job
    :return: tuple (ff_args, ff_options)
    """
    ff_args = ""
    ff_options = ""
    try:
        if hasattr(job, "config") and job.config:
            if job.disctype == "dvd":
                ff_args = getattr(job.config, "FFMPEG_ARGS_DVD", "")
                ff_options = getattr(job.config, "FFMPEG_OPTIONS_DVD", "")
            elif job.disctype == "bluray":
                ff_args = getattr(job.config, "FFMPEG_ARGS_BD", "")
                ff_options = getattr(job.config, "FFMPEG_OPTIONS_BD", "")
    except Exception:
        # If anything goes wrong with job.config introspection, just fallback
        ff_args = ff_args or cfg.arm_config.get('FFMPEG_ARGS', '')
        ff_options = ff_options or cfg.arm_config.get('FFMPEG_OPTIONS', '')

    if not ff_args:
        ff_args = cfg.arm_config.get('FFMPEG_ARGS', '')
    if not ff_options:
        ff_options = cfg.arm_config.get('FFMPEG_OPTIONS', '')
    return ff_args, ff_options


def ffmpeg_main_feature(srcpath, basepath, logfile, job):
    """
    Process dvd with main_feature enabled.\n\n
    :param srcpath: Path to source for ffmpeg (dvd or files)\n
    :param basepath: Path where ffmpeg will save trancoded files\n
    :param logfile: Logfile for ffmpeg to redirect output to\n
    :param job: Disc object\n
    :return: None
    """
    logging.info("Starting DVD Movie main_feature processing")
    logging.debug("FFMPEG starting: ")
    logging.debug(f"\n\r{job.pretty_table()}")

    utils.database_updater({'status': "waiting_transcode"}, job)
    ffmpeg_sleep_check(job)
    logging.debug("Setting job status to 'transcoding'")
    utils.database_updater({'status': "transcoding"}, job)
    filename = os.path.join(job.title + "." + cfg.arm_config["DEST_EXT"])
    filepathname = os.path.join(basepath, filename)
    logging.info(f"Ripping title main_feature to {shlex.quote(filepathname)}")

    get_track_info(srcpath, job)

    track = job.tracks.filter_by(main_feature=True).first()
    if track is None:
        msg = "No main feature found by FFMPEG. Turn main_feature to false in arm.yml and try again."
        logging.error(msg)
        raise RuntimeError(msg)

    track.filename = track.orig_filename = filename
    db.session.commit()

    options = shlex.split(cfg.arm_config.get('FFMPEG_OPTIONS', ''))
    tmp = ' '.join(map(str, options))
    cmd = f"nice ffmpeg " \
          f"-i {shlex.quote(srcpath)} " \
          f" {tmp}" \
          f" {shlex.quote(filepathname)} " \
          f" >> {logfile} 2>&1"

    logging.debug(f"Sending command: {cmd}")

    try:
        cmd2 = f"nice mkdir -p {basepath} && chmod -R 777 {basepath}"
        subprocess.check_output(cmd2, shell=True).decode("utf-8")
        subprocess.check_output(cmd, shell=True).decode("utf-8")
        logging.info("FFMPEG call successful")
        track.status = "success"
    except subprocess.CalledProcessError as hb_error:
        err = f"Call to FFMPEG failed with code: {hb_error.returncode}({hb_error.output})"
        logging.error(err)
        track.status = "fail"
        track.error = job.errors = err
        job.status = "fail"
        db.session.commit()
        raise subprocess.CalledProcessError(hb_error.returncode, cmd)

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")
    track.ripped = True
    db.session.commit()


def ffmpeg_all(srcpath, basepath, logfile, job):
    """
    Process all titles on the dvd\n
    :param srcpath: Path to source for HB (dvd or files)\n
    :param basepath: Path where HB will save trancoded files\n
    :param logfile: Logfile for HB to redirect output to\n
    :param job: Disc object\n
    :return: None
    """
    # Wait until there is a spot to transcode
    job.status = "waiting_transcode"
    db.session.commit()
    utils.sleep_check_process(cfg.arm_config["FFMPEG_CLI"], int(cfg.arm_config["MAX_CONCURRENT_TRANSCODES"]))
    job.status = "transcoding"
    db.session.commit()
    logging.info("Starting BluRay/DVD transcoding - All titles")

    get_track_info(srcpath, job)

    logging.debug(f"Total number of tracks is {job.no_of_titles}")

    for track in job.tracks:
        # Don't raise error if we past max titles, skip and continue till FFMPEG finishes
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

            filename = f"title_{track.track_number}.{cfg.arm_config['DEST_EXT']}"
            filepathname = os.path.join(basepath, filename)

            logging.info(f"Transcoding title {track.track_number} to {shlex.quote(filepathname)}")

            track.filename = track.orig_filename = filename
            db.session.commit()

            options = shlex.split(cfg.arm_config.get('FFMPEG_OPTIONS', ''))
            tmp = ' '.join(map(str, options))
            cmd = f"nice ffmpeg " \
                  f"-i {shlex.quote(srcpath)} " \
                  f" {tmp}" \
                  f" {shlex.quote(filepathname)} " \
                  f" >> {logfile} 2>&1"

            logging.debug(f"Sending command: {cmd}")

            try:
                ffmpeg_output = subprocess.check_output(
                    cmd,
                    shell=True
                ).decode("utf-8")
                logging.debug(f"FFMPEG exit code: {ffmpeg_output}")
                track.status = "success"
            except subprocess.CalledProcessError as ff_error:
                err = f"FFMPEG encoding of title {track.track_number} failed with code: {ff_error.returncode}" \
                      f"({ff_error.output})"
                logging.error(err)
                track.status = "fail"
                track.error = err
                db.session.commit()
                raise subprocess.CalledProcessError(ff_error.returncode, cmd)

            track.ripped = True
            db.session.commit()

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")




def ffmpeg_default(srcpath, basepath, logfile, job):
    """
    Process all mkv files in a directory.\n\n
    :param srcpath: Path to source for ffmpeg (dvd or files)\n
    :param basepath: Path where ffmpeg will save trancoded files\n
    :param logfile: Logfile for ffmpeg to redirect output to\n
    :param job: Disc object\n
    :return: None
    """
    # Added to limit number of transcodes
    job.status = "waiting_transcode"
    db.session.commit()
    ffmpeg_sleep_check(job)
    job.status = "transcoding"
    db.session.commit()

    # This will fail if the directory raw gets deleted
    for files in os.listdir(srcpath):
        srcpathname = os.path.join(srcpath, files)
        destfile = os.path.splitext(files)[0]
        # MakeMKV always saves in mkv we need to update the db with the new filename
        logging.debug(destfile + ".mkv")
        job_current_track = job.tracks.filter_by(filename=destfile + ".mkv")
        track = None
        for track in job_current_track:
            logging.debug("filename: " + track.filename)
            track.orig_filename = track.filename
            track.filename = destfile + "." + cfg.arm_config["DEST_EXT"]
            logging.debug("UPDATED filename: " + track.filename)
            db.session.commit()
        filename = os.path.join(basepath, destfile + "." + cfg.arm_config["DEST_EXT"])
        filepathname = os.path.join(basepath, filename)

        logging.info(f"Transcoding file {shlex.quote(files)} to {shlex.quote(filepathname)}")

        options = shlex.split(cfg.arm_config.get('FFMPEG_ARGS', ''))
        tmp = ' '.join(map(str, options))
        cmd = f"nice ffmpeg " \
              f"-i {shlex.quote(srcpathname)} " \
              f" {tmp}" \
              f" {shlex.quote(filepathname)} " \
              f" >> {logfile} 2>&1"

        logging.debug(f"Sending command: {cmd}")

        try:
            ffmpeg_output = subprocess.check_output(
                cmd,
                shell=True
            ).decode("utf-8")
            logging.debug(f"FFMPEG exit code: {ffmpeg_output}")
        except subprocess.CalledProcessError as ff_error:
            err = f"FFMPEG encoding of file {shlex.quote(files)} failed with code: {ff_error.returncode}" \
                  f"({ff_error.output})"
            logging.error(err)
            raise subprocess.CalledProcessError(ff_error.returncode, cmd)
            # job.errors.append(f)

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")


def get_track_info(srcpath, job):
    """
    Use FFMPEG to get track info and update Track class\n\n
    :param srcpath: Path to disc\n
    :param job: Job instance\n
    :return: None
    """
    logging.info("Using ffprobe to get information on tracks. This will take a few moments...")

    # Use ffprobe (part of ffmpeg) to get stream and format information in JSON
    # We'll query the format duration and the video streams for width/height and r_frame_rate
    cmd = (
        f"{cfg.arm_config.get('FFPROBE_CLI', 'ffprobe')} -v error -print_format json -show_format -show_streams "
        f"{shlex.quote(srcpath)}"
    )
    logging.debug(f"Sending command: {cmd}")
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
    except subprocess.CalledProcessError as e:
        logging.error(f"ffprobe failed: {e.returncode} {e.output}")
        # fall back to original behavior: no track info
        utils.put_track(job, 0, 0, 0, 0.0, False, "FFmpeg")
        return

    # parse JSON
    try:
        import json

        data = json.loads(output)
    except Exception as e:
        logging.error(f"Failed to parse ffprobe output as JSON: {e}")
        utils.put_track(job, 0, 0, 0, 0.0, False, "FFmpeg")
        return

    # Determine number of titles/tracks from streams (count video streams or program entry if available)
    # Here we interpret each video stream as a track candidate
    streams = data.get('streams', [])
    format_info = data.get('format', {})

    # ffprobe provides duration as a string in format section
    duration = 0
    if 'duration' in format_info:
        try:
            duration = int(float(format_info['duration']))
        except Exception:
            duration = 0

    # If multiple video streams exist, treat each as a title/track; otherwise treat the input as a single track
    video_streams = [s for s in streams if s.get('codec_type') == 'video']
    no_of_titles = len(video_streams) if video_streams else 1
    job.no_of_titles = no_of_titles
    db.session.commit()

    # Iterate and create/update Track entries. We will use stream index+1 as title number.
    t_no = 0
    for idx, vs in enumerate(video_streams, start=1):
        t_no = idx
        # duration for the specific stream may not be present; fall back to container duration
        track_duration = 0
        if vs.get('duration'):
            try:
                track_duration = int(float(vs.get('duration')))
            except Exception:
                track_duration = 0
        else:
            track_duration = duration

        # fps: ffprobe uses r_frame_rate or avg_frame_rate as strings like '30000/1001'
        fps = 0.0
        fps_raw = vs.get('r_frame_rate') or vs.get('avg_frame_rate')
        if fps_raw and fps_raw != '0/0':
            try:
                if '/' in fps_raw:
                    num, den = fps_raw.split('/')
                    fps = float(num) / float(den)
                else:
                    fps = float(fps_raw)
            except Exception:
                fps = 0.0

        # aspect: compute from width/height if available
        aspect = 0
        width = vs.get('width')
        height = vs.get('height')
        if width and height:
            try:
                aspect = round(float(width) / float(height), 2)
            except Exception:
                aspect = 0

        # Determine main_feature heuristics: choose the longest video stream as main
        main_feature = False
        # We'll mark main_feature True if this stream has the longest duration seen so far
        # To do that, we need to compare durations. Keep a simple check: if this is the first, mark it and later update via utils.put_track calls
        if idx == 1:
            main_feature = True

        # call utils.put_track for each discovered track
        utils.put_track(job, t_no, track_duration, aspect, fps, main_feature, "FFmpeg")

    # If there were no video streams, still register a single track using container duration
    if not video_streams:
        utils.put_track(job, 1, duration, 0, 0.0, False, "FFmpeg")



def ffmpeg_mkv(srcpath, basepath, logfile, job):
    """
    Process all mkv files in a directory.\n\n
    :param srcpath: Path to source for HB (dvd or files)\n
    :param basepath: Path where HB will save trancoded files\n
    :param logfile: Logfile for HB to redirect output to\n
    :param job: Disc object\n
    :return: None
    """
    # Added to limit number of transcodes
    job.status = "waiting_transcode"
    db.session.commit()
    ffmpeg_sleep_check(job)
    job.status = "transcoding"
    db.session.commit()

    # This will fail if the directory raw gets deleted
    for files in os.listdir(srcpath):
        srcpathname = os.path.join(srcpath, files)
        destfile = os.path.splitext(files)[0]
        # MakeMKV always saves in mkv we need to update the db with the new filename
        logging.debug(destfile + ".mkv")
        job_current_track = job.tracks.filter_by(filename=destfile + ".mkv")
        track = None
        for track in job_current_track:
            logging.debug("filename: " + track.filename)
            track.orig_filename = track.filename
            track.filename = destfile + "." + cfg.arm_config["DEST_EXT"]
            logging.debug("UPDATED filename: " + track.filename)
            db.session.commit()

        # Use filename relative to basepath, join once
        filename = destfile + "." + cfg.arm_config["DEST_EXT"]
        filepathname = os.path.join(basepath, filename)

        logging.info(f"Transcoding file {shlex.quote(files)} to {shlex.quote(filepathname)}")

        options = shlex.split(cfg.arm_config.get('FFMPEG_ARGS', ''))
        tmp = ' '.join(map(str, options))
        cmd = f"nice ffmpeg " \
              f"-i {shlex.quote(srcpathname)} " \
              f" {tmp}" \
              f" {shlex.quote(filepathname)} " \
              f" >> {logfile} 2>&1"

        logging.debug(f"Sending command: {cmd}")

        try:
            cmd2 = f"nice mkdir -p {basepath} && chmod -R 777 {basepath}"
            subprocess.check_output(cmd2, shell=True).decode("utf-8")
            subprocess.check_output(cmd, shell=True).decode("utf-8")
            logging.info("FFmpeg call successful")
            if track is not None:
                track.status = "success"
                db.session.commit()
            else:
                logging.debug("No matching DB track found to mark success")
        except subprocess.CalledProcessError as ff_error:
            err = f"Call to FFmpeg failed with code: {ff_error.returncode}({ff_error.output})"
            logging.error(err)
            if track is not None:
                track.status = "fail"
                track.error = err
            job.errors = err
            job.status = "fail"
            db.session.commit()
            raise subprocess.CalledProcessError(ff_error.returncode, cmd)

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")