""" Main file for running DVDs/Blu-rays/CDs/data ?
It would help clear up main and make things easier to find
"""
import sys
import os
import logging
from importlib.util import find_spec
from pathlib import Path

# If the arm module can't be found, add the folder this file is in to PYTHONPATH
# This is a bad workaround for non-existent packaging
if find_spec("arm") is None:
    sys.path.append(str(Path(__file__).parents[2]))

from arm.ripper import utils, makemkv, handbrake, ffmpeg  # noqa E402
from arm.ui import app, db, constants  # noqa E402
from arm.models.job import Job, JobState  # noqa E402


def rip_visual_media(job: Job, logfile, protection):
    """
    Main ripping function for dvd and Blu-rays, movies or series
    \n
    :param job: Current job
    :param logfile: Current logfile
    :param protection: Does the disc have 99 track protection
    :return: None
    """

    raw_output_path = None
    # Do we need to use MakeMKV - Blu-rays, protected dvd's, and dvd with mainfeature off
    use_make_mkv = rip_with_mkv(job, protection)
    logging.debug(f"Using MakeMKV: [{use_make_mkv}]")
    if use_make_mkv:
        logging.info("************* Ripping disc with MakeMKV *************")
        # Run MakeMKV and get path to output
        job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()
        try:
            raw_output_path = makemkv.makemkv(job)
        except Exception as mkv_error:  # noqa: E722
            raise utils.RipperException("Error while running MakeMKV") from mkv_error

        if job.config.NOTIFY_RIP:
            utils.notify(job, constants.NOTIFY_TITLE, f"{job.title} rip complete. Starting transcode. ")
        logging.info("************* Ripping with MakeMKV completed *************")
    if raw_output_path is None:
        raise utils.RipperException("No output path for rip")

    # Save poster image from disc if enabled
    utils.save_disc_poster(raw_output_path, job)
    # Fix the sub-folder type - (movie|tv|unknown)
    type_sub_folder = utils.convert_job_type(job.video_type)
    # Fix the job title - Title (Year) | Title
    job_title = utils.fix_job_title(job)
    # --------------- POST PROCESSING ---------------
    # Start moving and (optionally) deleting the raw files
    final_input_path = None
    logging.debug(f"Transcode status: [{job.config.SKIP_TRANSCODE}] and MakeMKV Status: [{use_make_mkv}]")
    if job.config.SKIP_TRANSCODE:
        # If we skip transcoding, then we want to copy the files from the raw folder into the end destination
        final_input_path = raw_output_path
        logging.info("Skipping transcode")
    else:
        # The input for this step is the output of the last step
        transcode_input_path = raw_output_path

        # We need to construct the transcode path
        transcode_output_path = os.path.join(job.config.TRANSCODE_PATH, type_sub_folder, job_title)
        transcode_output_path = utils.create_unique_dir(transcode_output_path, job)
        logging.info(f"Processing files to: {transcode_output_path}")
        # Begin transcoding section - only transcode if skip_transcode is false
        start_transcode(job, logfile, transcode_input_path, transcode_output_path, protection)
        final_input_path = transcode_output_path

    # Check folders for already ripped jobs -> creates folder
    final_output_path = os.path.join(job.config.COMPLETED_PATH, type_sub_folder, job_title)
    final_output_path = utils.ensure_dir_exists(final_output_path)
    # Update the job.path with the final directory
    utils.database_updater({'path': final_output_path}, job)
    # Movie the movie poster if we have one
    utils.move_movie_poster(raw_output_path, final_output_path)
    # Move to final folder. The final_output_path is stored in job.path
    move_files_post(final_input_path, job)
    # Scan Emby if arm.yaml requires it
    utils.scan_emby()
    # Set permissions if arm.yaml requires it
    utils.set_permissions(final_output_path)
    # If set in the arm.yaml remove the raw files
    # Removes files in both the raw path and the transcode path.
    utils.delete_raw_files([raw_output_path, final_input_path])
    # report errors if any
    notify_exit(job)
    logging.info("************* ARM processing complete *************")


def start_transcode(job, logfile, raw_in_path, transcode_out_path, protection):
    """
    This checks if transcoding is enabled for the job and then passes it off to the correct
    transcoding function, first if handbrake or ffmpegshould be used, then how it should be ripped\n
    :param raw_in_path: HandBrake in path (makeMKV_out_path|/dev/sr0)
    :param transcode_out_path: Path HandBrake should put the files (transcode_path)
    :param job: Current job
    :param logfile: Current logfile
    :param protection: If disc has 99 track protection
    :return: None
    """
    if job.config.SKIP_TRANSCODE:
        logging.info("Transcoding is disabled, skipping transcode")
        return None

    # Update db with transcoding status
    utils.database_updater({'status': JobState.TRANSCODE_ACTIVE.value}, job)
    # Use FFMPEG or HandBrake depending on arm.yaml setting
    if job.config.USE_FFMPEG:
        logging.info("************* Starting Transcode With FFMPEG *************")
        # If it was ripped with MakeMKV or we are doing a mkv rip then run the ffmpeg_mkv function
        if rip_with_mkv(job, protection) and job.config.RIPMETHOD == "mkv":
            logging.debug(f"ffmpeg_mkv: {raw_in_path}, {transcode_out_path}")
            ffmpeg.ffmpeg_mkv(raw_in_path, transcode_out_path, job)
        # Otherwise if it is a movie and mainfeature is enabled then run ffmpeg_main_feature
        elif job.video_type == "movie" and job.config.MAINFEATURE and job.hasnicetitle:
            logging.debug(f"ffmpeg_main_feature: {raw_in_path}, {transcode_out_path}")
            ffmpeg.ffmpeg_main_feature(raw_in_path, transcode_out_path, job)
            db.session.commit()
        # Finally if it is a series or mainfeature is disabled run ffmpeg_all to transcode all tracks
        else:
            logging.debug(f"ffmpeg_all: {raw_in_path}, {transcode_out_path}")
            ffmpeg.ffmpeg_all(raw_in_path, transcode_out_path, job)
            db.session.commit()
        logging.info("************* Finished Transcode With FFMPEG *************")
        # After transcoding update db status back to idle
        utils.database_updater({'status': JobState.IDLE.value}, job)
        return True

    elif not job.config.USE_FFMPEG:
        logging.info("************* Starting Transcode With HandBrake *************")
        # If it was ripped with MakeMKV or we are doing a mkv rip then run the handbrake_mkv function
        if rip_with_mkv(job, protection) and job.config.RIPMETHOD == "mkv":
            logging.debug(f"handbrake_mkv: {raw_in_path}, {transcode_out_path}, {logfile}")
            handbrake.handbrake_mkv(raw_in_path, transcode_out_path, logfile, job)
        # Otherwise if it is a movie and mainfeature is enabled then run handbrake_main_feature
        elif job.video_type == "movie" and job.config.MAINFEATURE and job.hasnicetitle:
            logging.debug(f"handbrake_main_feature: {raw_in_path}, {transcode_out_path}, {logfile}")
            handbrake.handbrake_main_feature(raw_in_path, transcode_out_path, logfile, job)
            db.session.commit()
        # Finally if it is a series or mainfeature is disabled run handbrake_all to transcode all tracks
        else:
            logging.debug(f"handbrake_all: {raw_in_path}, {transcode_out_path}, {logfile}")
            handbrake.handbrake_all(raw_in_path, transcode_out_path, logfile, job)
            db.session.commit()
        logging.info("************* Finished Transcode With HandBrake *************")
        # After transcoding update db status back to idle
        utils.database_updater({'status': JobState.IDLE.value}, job)
        return True
    else:
        logging.info("Invalid transcoding option selected. Skipping transcode."
                     "Set USE_FFMPEG with valid boolean value fix error")
        return None


def notify_exit(job):
    """
    Notify post transcoding - ARM finished\n
    Includes any errors
    :param job: current job
    :return: None
    """
    if job.config.NOTIFY_TRANSCODE:
        if job.errors:
            errlist = ', '.join(job.errors)
            utils.notify(job, constants.NOTIFY_TITLE,
                         f" {job.title} processing completed with errors. "
                         f"Title(s) {errlist} failed to complete. ")
            logging.info(f"Transcoding completed with errors.  Title(s) {errlist} failed to complete. ")
        else:
            utils.notify(job, constants.NOTIFY_TITLE, f"{job.title} {constants.PROCESS_COMPLETE}")


def move_files_post(input_path, job: Job):
    """
    Logic for moving files post transcoding\n
    if series move all to 1 folder\n
    if movie check what source we got them from, for MakeMKV we can check filesize\n
    :param input_path: This should either be the input_path from MakeMKV, /dev/srX or TRANSCODE_PATH
    :param job: current job
    :return: None
    """
    if job.video_type == "series":
        tracks = job.tracks.filter_by(ripped=True)
        for track in tracks:
            utils.move_files(input_path, track.filename, job, False)
        return
    is_bonus_disc = guess_if_bonus_disc(job)
    tracks = job.tracks.filter_by(ripped=True).order_by(job.tracks.filesize.desc())
    largest_file = True
    if tracks.count() == 1:
        utils.move_files(input_path, tracks[0].filename, job, True)
        return
    for track in tracks:
        if track.source == "MakeMKV":
            logging.debug(f"Videotype: {job.video_type}")
            # if video_type is movie, then move the biggest title to media_dir
            # move the rest of the files to the extras' folder
            # find largest filesize
            temp_path = os.path.join(input_path, track.filename)

            if os.stat(temp_path).st_size <= 1:  # sanity check for filesize
                logging.info(f"{input_path} is empty or very small size. - Folder size: {os.stat(temp_path).st_size}")
                continue
            if largest_file is True:
                largest_file = False
                logging.debug(f"Largest file is: {track.filename}")
                # We only treat it as main feauture if its not a bonus disc
                utils.move_files(input_path, track.filename, job, is_main_feature=is_bonus_disc is False)
            else:
                # If mainfeature is enabled - skip to the next file
                if job.config.MAINFEATURE and is_bonus_disc is False:
                    logging.info(f"MAINFEATURE IS {job.config.MAINFEATURE} - Skipping move of {track.filename}")
                    continue
                # Other/extras
                if str(job.config.EXTRAS_SUB).lower() != "none":
                    utils.move_files(input_path, track.filename, job, is_main_feature=False)
                else:
                    logging.info(f"Not moving extra: \"{track.filename}\" - Sub folder is not set or named incorrectly")
        else:
            # If HandBrake was used we can pass track.main_feature
            utils.move_files(input_path, track.filename, job, track.main_feature and is_bonus_disc is False)


def rip_with_mkv(current_job, protection=0):
    """
    Test to check if title was or should be ripped by MakeMKV\n
    :param current_job: current job
    :param protection: If the disc have 99 track protection
    :return: Bool
    """
    mkv_ripped = False
    # Rip bluray
    if current_job.disctype == "bluray":
        mkv_ripped = True
    # Rip dvd with mode: mkv and mainfeature: false
    if current_job.disctype == "dvd" and (not current_job.config.MAINFEATURE and current_job.config.RIPMETHOD == "mkv"):
        mkv_ripped = True
    # Rip dvds with skip transcode
    if current_job.disctype == "dvd" and current_job.config.SKIP_TRANSCODE:
        mkv_ripped = True
    # If dvd has 99 protection force MakeMKV to be used
    if protection and current_job.disctype == "dvd":
        mkv_ripped = True
    # if backup_dvd, always use mkv
    if current_job.config.RIPMETHOD == "backup_dvd":
        mkv_ripped = True
    return mkv_ripped


def guess_if_bonus_disc(job: Job) -> bool:
    """
    If the disc is a bonus disc,
    we dont want to assume there is a main feature
    :param job: current job
    :return: True if bonus disc
    """
    if job.video_type != "movie":
        # We assume that only movies have bonus discs
        return False
    # All of these have been seen in real disc labels
    bonus_disc_labels = ["_DISC_2", "_Disc_2", "_BONUS_DISC", "_SPECIAL_FEATURES", "Special_Features", "_Bonus_Disc"]
    label = str(job.label)
    for substring in bonus_disc_labels:
        if substring in label:
            return True
    # Bonus disc hint is usually at the end of the label
    # Some of these strings are short, so we only want to interpret them
    # If theyre close to the second half of the label
    last_half = ["_D2"]
    label_len = len(label)
    label_last_half = label[slice(int(label_len//2), label_len)]
    for half in last_half:
        if half in label_last_half:
            return True

    suffixes = ["_BONUS"]
    for suffix in suffixes:
        if label.endswith(suffix):
            return True
    return False
