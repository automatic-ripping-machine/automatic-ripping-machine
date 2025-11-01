#!/usr/bin/env python3
"""FFMPEG processing of dvd/blu-ray"""

import os
import logging
import subprocess
import shlex
import json
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
    Get the correct custom arguments for FFmpeg for this disc.

    Tries to read per-job config attributes (if present), otherwise falls
    back to global cfg.arm_config values.
    :param job: The job
    :return: tuple (ff_pre_args, ff_post_args)
    """
    ff_pre_args = ""
    ff_post_args = ""
    try:
        if hasattr(job, "config") and job.config:
            ff_pre_args = getattr(job.config, "FFMPEG_PRE_FILE_ARGS", "")
            ff_post_args = getattr(job.config, "FFMPEG_POST_FILE_ARGS", "")

    except Exception:
        # If anything goes wrong with job.config introspection, just fallback
        ff_pre_args = ff_pre_args or cfg.arm_config.get('FFMPEG_PRE_FILE_ARGS', '')
        ff_post_args = ff_post_args or cfg.arm_config.get('FFMPEG_POST_FILE_ARGS', '')

    if not ff_pre_args:
        ff_pre_args = cfg.arm_config.get('FFMPEG_PRE_FILE_ARGS', '')
    if not ff_post_args:
        ff_post_args = cfg.arm_config.get('FFMPEG_POST_FILE_ARGS', '')
    return ff_pre_args, ff_post_args


def probe_source(src_path):
    """
    Run ffprobe on src_path and return JSON string or None on failure.

    This is a small wrapper around subprocess.check_output so callers can
    focus on parsing and error handling.
    """
    ffprobe_bin = os.path.join(os.path.dirname(cfg.arm_config["FFMPEG_CLI"]), "ffprobe")
    cmd = f"{ffprobe_bin} -v error -print_format json -show_format -show_streams {shlex.quote(src_path)}"
    logging.debug(f"FFProbe command: {cmd}")
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
        logging.debug(f"ffprobe output: {out}")
        return out
    except subprocess.CalledProcessError as e:
        logging.error(f"ffprobe failed: {e.returncode} {e.output}")
        return None


def parse_probe_output(json_str):
    """
    Parse ffprobe JSON string and return a list of normalized track dicts.

    Each returned dict has keys: title (1-based int), duration (int seconds),
    fps (float), aspect (float), codec (str|None), stream_index (int|None).
    """
    try:
        data = json.loads(json_str)
    except Exception as e:
        logging.error(f"Failed to parse ffprobe JSON: {e}")
        return []

    streams = data.get('streams', [])
    format_info = data.get('format', {})

    # container duration fallback
    container_duration = 0
    if 'duration' in format_info:
        try:
            container_duration = int(float(format_info['duration']))
        except Exception:
            container_duration = 0

    # pick video streams only
    video_streams = [s for s in streams if s.get('codec_type') == 'video']
    if not video_streams:
        # single fallback track using container duration
        return [{
            'title': 1,
            'duration': container_duration,
            'fps': 0.0,
            'aspect': 0,
            'codec': format_info.get('format_name'),
            'stream_index': None,
        }]

    tracks = []
    for index, stream in enumerate(video_streams, start=1):
        # per-stream duration if present, else container
        dur = None
        if stream.get('duration'):
            try:
                dur = int(float(stream.get('duration')))
            except Exception:
                dur = None
        if dur is None:
            dur = container_duration

        # fps parsing
        fps_raw = stream.get('r_frame_rate') or stream.get('avg_frame_rate')
        fps = _parse_fps(fps_raw)

        # aspect ratio from width/height
        width = stream.get('width')
        height = stream.get('height')
        aspect = _compute_aspect(width, height)

        tracks.append({
            'title': index,
            'duration': dur,
            'fps': fps,
            'aspect': aspect,
            'codec': stream.get('codec_name'),
            'stream_index': stream.get('index'),
        })

    return tracks


def _parse_fps(fps_raw):
    """Parse ffprobe frame-rate string like '30000/1001' or '25' to float."""
    if not fps_raw or fps_raw == '0/0':
        return 0.0
    try:
        if '/' in fps_raw:
            num, den = fps_raw.split('/')
            return float(num) / float(den)
        return float(fps_raw)
    except Exception:
        return 0.0


def _compute_aspect(width, height):
    """Compute aspect ratio from width and height, rounded to 2 decimals."""
    if not width or not height:
        return 0
    try:
        return round(float(width) / float(height), 2)
    except Exception:
        return 0


def evaluate_and_register_tracks(tracks, job):
    """Decide main feature and register tracks via utils.put_track.

    This function sets job.no_of_titles and commits once. It marks the
    longest-duration track as the main feature.
    """
    if not tracks:
        utils.put_track(job, 1, 0, 0, 0.0, False, "FFmpeg")
        job.no_of_titles = 1
        db.session.commit()
        return

    # select main feature as the track with max duration
    max_dur = -1
    main_title = None
    for t in tracks:
        if t.get('duration', 0) > max_dur:
            max_dur = t.get('duration', 0)
            main_title = t.get('title')

    job.no_of_titles = len(tracks)
    db.session.commit()

    for t in tracks:
        is_main = (t.get('title') == main_title)
        utils.put_track(job,
                        int(t.get('title')),
                        int(t.get('duration', 0)),
                        t.get('aspect', 0),
                        float(t.get('fps', 0.0)),
                        bool(is_main),
                        "FFmpeg")


def ffmpeg_main_feature(src_path, out_path, log_file, job):
    """
    Process dvd with main_feature enabled.\n\n
    :param src_path: Path to source for ffmpeg (dvd or files)\n
    :param out_path: Path where ffmpeg will save trancoded files\n
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
    out_file_path = os.path.join(out_path, filename)
    logging.info(f"Ripping title main_feature to {shlex.quote(out_file_path)}")

    get_track_info(src_path, job)

    track = job.tracks.filter_by(main_feature=True).first()
    if track is None:
        msg = "No main feature found by FFMPEG. Turn main_feature to false in arm.yml and try again."
        logging.error(msg)
        raise RuntimeError(msg)

    track.filename = track.orig_filename = filename
    db.session.commit()

    try:
        subprocess.check_output((f"mkdir -p {shlex.quote(out_path)} "
                                 f"&& chmod -R 777 {shlex.quote(out_path)}"), shell=True)
        run_transcode_cmd(src_path, out_file_path, log_file, job)
        logging.info("FFMPEG call successful")
        track.status = "success"
    except subprocess.CalledProcessError as ffmpeg_error:
        err = f"Call to FFMPEG failed with code: {ffmpeg_error.returncode}"
        logging.error(err)
        track.status = "fail"
        track.error = job.errors = err
        job.status = "fail"
        db.session.commit()
        raise

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")
    track.ripped = True
    db.session.commit()


def ffmpeg_all(src_path, base_path, log_file, job):
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

    get_track_info(src_path, job)

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
            out_file_path = os.path.join(base_path, filename)

            logging.info(f"Transcoding title {track.track_number} to {shlex.quote(out_file_path)}")

            track.filename = track.orig_filename = filename
            db.session.commit()

            try:
                run_transcode_cmd(src_path, out_file_path, log_file, job)
                track.status = "success"
            except subprocess.CalledProcessError as ff_error:
                err = f"FFMPEG encoding of title {track.track_number} failed with code: {ff_error.returncode}"
                logging.error(err)
                track.status = "fail"
                track.error = err
                db.session.commit()
                raise
            track.ripped = True
            db.session.commit()

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")


def ffmpeg_default(src_path, basepath, logfile, job):
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
    for files in os.listdir(src_path):
        src_path_name = os.path.join(src_path, files)
        dest_file = os.path.splitext(files)[0]
        # MakeMKV always saves in mkv we need to update the db with the new filename
        logging.debug(dest_file + ".mkv")
        job_current_track = job.tracks.filter_by(filename=dest_file + ".mkv")
        track = None
        for track in job_current_track:
            logging.debug("filename: " + track.filename)
            track.orig_filename = track.filename
            track.filename = dest_file + "." + cfg.arm_config["DEST_EXT"]
            logging.debug("UPDATED filename: " + track.filename)
            db.session.commit()
        file_name = os.path.join(basepath, dest_file + "." + cfg.arm_config["DEST_EXT"])
        out_file_path = os.path.join(basepath, file_name)

        logging.info(f"Transcoding file {shlex.quote(files)} to {shlex.quote(out_file_path)}")

        try:
            run_transcode_cmd(src_path_name, out_file_path, logfile, job)
            logging.info("Transcode succeeded")
        except subprocess.CalledProcessError as e:
            logging.error(f"Transcode failed: {e}")

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")


def get_track_info(src_path, job):
    """
    Use FFMPEG to get track info and update Track class\n\n
    :param srcpath: Path to disc\n
    :param job: Job instance\n
    :return: None
    """
    logging.info("Using ffprobe to get information on tracks. This will take a few moments...")

    # Orchestrate probing and registering via helpers
    probe_json = probe_source(src_path)
    if not probe_json:
        logging.info("ffprobe returned no data; registering fallback track")
        utils.put_track(job, 0, 0, 0, 0.0, False, "FFmpeg")
        return

    tracks = parse_probe_output(probe_json)
    if not tracks:
        logging.info("No tracks parsed from ffprobe; registering fallback track")
        utils.put_track(job, 0, 0, 0, 0.0, False, "FFmpeg")
        return

    evaluate_and_register_tracks(tracks, job)


def ffmpeg_mkv(src_path, base_path, log_file, job):
    """
    Process all mkv files in a directory.\n\n
    :param src_path: Path to source for HB (dvd or files)\n
    :param base_path: Path where HB will save trancoded files\n
    :param log_file: Logfile for HB to redirect output to\n
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
    for files in os.listdir(src_path):
        src_files_path = os.path.join(src_path, files)
        dest_file = os.path.splitext(files)[0]
        # MakeMKV always saves in mkv we need to update the db with the new filename
        logging.debug(dest_file + ".mkv")
        job_current_track = job.tracks.filter_by(filename=dest_file + ".mkv")
        track = None
        for track in job_current_track:
            logging.debug("filename: " + track.filename)
            track.orig_filename = track.filename
            track.filename = dest_file + "." + cfg.arm_config["DEST_EXT"]
            logging.debug("UPDATED filename: " + track.filename)
            db.session.commit()

        # Use filename relative to basepath, join once
        file_name = dest_file + "." + cfg.arm_config["DEST_EXT"]
        file_path_name = os.path.join(base_path, file_name)

        logging.info(f"Transcoding file {shlex.quote(files)} to {shlex.quote(file_path_name)}")

        try:
            subprocess.check_output((f"mkdir -p {shlex.quote(base_path)} "
                                     f"&& chmod -R 777 {shlex.quote(base_path)}"), shell=True)
            run_transcode_cmd(src_files_path, file_path_name, log_file, job)
            logging.info("FFmpeg call successful")
            if track is not None:
                track.status = "success"
                db.session.commit()
            else:
                logging.debug("No matching DB track found to mark success")
        except subprocess.CalledProcessError as ff_error:
            err = f"Call to FFmpeg failed with code: {ff_error.returncode}"
            logging.error(err)
            if track is not None:
                track.status = "fail"
                track.error = err
            job.errors = err
            job.status = "fail"
            db.session.commit()
            raise

    logging.info(PROCESS_COMPLETE)
    logging.debug(f"\n\r{job.pretty_table()}")


def run_transcode_cmd(src_file, out_file, log_file, job, ff_pre_args="", ff_post_args=""):
    """
    Run the FFmpeg command and capture progress.
    """
    if not ff_pre_args or not ff_post_args:
        ff_pre_args, ff_post_args = correct_ffmpeg_settings(job)

    cmd = (f"{cfg.arm_config['FFMPEG_CLI']} {ff_pre_args} -i {shlex.quote(src_file)}"
           f" -progress pipe:1 {ff_post_args} {shlex.quote(out_file)}")

    logging.debug(f"FFMPEG command: {cmd}")

    duration_us = 0
    ffprobe_bin = os.path.join(os.path.dirname(cfg.arm_config["FFMPEG_CLI"]), "ffprobe")
    try:
        duration_sec_str = subprocess.check_output(
            f"{ffprobe_bin} -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "
            f"{shlex.quote(src_file)}",
            shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()
        duration_us = int(float(duration_sec_str) * 1_000_000)
    except (subprocess.CalledProcessError, ValueError) as e:
        logging.error(f"Could not get duration from ffprobe: {e}")
        # We can continue without progress reporting if this fails

    process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True, bufsize=1)

    with open(log_file, "a") as f:
        for line in process.stdout:  # type: ignore
            f.write(line)
            if duration_us > 0 and "out_time_us" in line:
                parts = line.strip().split("=")
                if len(parts) == 2 and parts[0] == "out_time_us":
                    try:
                        out_time_us = int(parts[1])
                        percentage = (out_time_us / duration_us) * 100
                        # Clamp percentage between 0 and 100
                        percentage = max(0, min(100, percentage))
                        logging.info(f"ARM: Transcoding progress: {percentage:.2f}%")
                    except ValueError:
                        pass

    process.wait()

    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)
