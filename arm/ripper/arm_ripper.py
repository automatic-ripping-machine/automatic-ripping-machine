""" Main file for running DVDs/Blu-rays/CDs/data ?
It would help clear up main and make things easier to find
"""
import sys
import os
import logging
from importlib.util import find_spec
from pathlib import Path
from typing import Tuple
# If the arm module can't be found, add the folder this file is in to PYTHONPATH
# This is a bad workaround for non-existent packaging
if find_spec("arm") is None:
    sys.path.append(str(Path(__file__).parents[2]))

from arm.ripper import utils, makemkv, handbrake, ffmpeg  # noqa E402
from arm.ui import app, db, constants  # noqa E402
from arm.models.job import Job, JobState  # noqa E402


def rip_visual_media(job: Job, logfile, protection) -> Tuple[str, bool]:
    """
    Main ripping function for dvd and Blu-rays, movies or series
    \n
    :param job: Current job
    :param logfile: Current logfile
    :param protection: Does the disc have 99 track protection
    :return: the output path of the rip, and whether the files are raw from disc or transcoded
    """
    is_transcoded = False
    output_path = utils.create_unique_dir(os.path.join(str(job.config.RAW_PATH), str(job.title)), job)
    # Do we need to use MakeMKV - Blu-rays, protected dvd's, and dvd with mainfeature off
    if should_rip_with_MakeMKV(job, protection):
        logging.debug("Using MakeMKV")
        logging.info("************* Ripping disc with MakeMKV *************")
        # Run MakeMKV and get path to output
        job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()
        try:
            makemkv.makemkv(job, output_path)
        except Exception as mkv_error:  # noqa: E722
            raise utils.RipperException("Error while running MakeMKV") from mkv_error
        if job.config.NOTIFY_RIP:
            utils.notify(job, constants.NOTIFY_TITLE, f"{job.title} rip complete. Starting transcode. ")
        logging.info("************* Ripping with MakeMKV completed *************")
    else:
        logging.debug("Skipping MakeMKV: Using FFMPEG or Handbrake to ")
        utils.database_updater({'status': JobState.VIDEO_RIPPING.value}, job)
        if job.config.USE_FFMPEG:
            _transcode_rip_ffmpeg(job, drive_path=job.devpath, raw_output_path=output_path)
        else:
            _transcode_rip_handbrake(job, logfile, drive_path=job.devpath, raw_output_path=output_path)
        # These ripping methods transcode the files during rip
        is_transcoded = True
    # Save poster image from disc if enabled
    utils.save_disc_poster(output_path, job)
    return output_path, is_transcoded


def transcode_visual_media(job: Job, logfile, raw_output_path: str, skip_transcode: bool) -> str | None:
    logging.debug(f"Transcode status: [{job.config.SKIP_TRANSCODE}]")
    if job.config.SKIP_TRANSCODE or skip_transcode:
        logging.info("Skipping transcode")
        return None
    # Fix the job title - Title (Year) | Title
    job_title = utils.fix_job_title(job)
    # Fix the sub-folder type - (movie|tv|unknown)
    type_sub_folder = utils.convert_job_type(job.video_type)
    # We need to construct the transcode path
    transcode_output_path = os.path.join(job.config.TRANSCODE_PATH, type_sub_folder, job_title)
    transcode_output_path = utils.create_unique_dir(transcode_output_path, job)
    logging.info(f"Processing files to: {transcode_output_path}")
    # Begin transcoding section - only transcode if skip_transcode is false
    start_transcode(job, logfile, raw_in_path=raw_output_path, transcode_out_path=transcode_output_path)
    return transcode_output_path


def post_process_ripping_job_cleanup(job: Job, transcode_path: str | None, raw_path: str):
    """
    After transcoding and ripping, do cleanup by moving files and posters
    and delete raw files based on arm.yaml config
    """
    final_input_path = transcode_path if transcode_path else raw_path
    # --------------- POST PROCESSING ---------------
    final_output_path = create_final_output_path(job)
    # Move to final folder.
    move_video_files_post(final_input_path, job)
    # Move the movie poster if we have one
    utils.move_movie_poster(raw_path, final_output_path)
    # Scan Emby if arm.yaml requires it
    utils.scan_emby()
    # Set permissions if arm.yaml requires it
    utils.set_permissions(final_output_path)
    # If set in the arm.yaml remove the raw files
    # Removes files in both the raw path and the transcode path.
    utils.delete_raw_files([raw_path, transcode_path])
    # report errors if any
    notify_exit(job)
    logging.info("************* ARM processing complete *************")
def create_final_output_path(job) -> Path:
    """
    Create the final destination folder and (in the case of series) disc_number sub directory.
    Update the path property on the job to represent this final path.
    """
    job_title = utils.fix_job_title(job)
    # Fix the sub-folder type - (movie|tv|unknown)
    type_sub_folder = utils.convert_job_type(job.video_type)
    final_output_path = Path(job.config.COMPLETED_PATH, type_sub_folder, job_title)
    if job.video_type == "series":
        # Series are a special case: we want to put the episodes in a Disc folder
        # Example: competed/tv/{series_name}/Disc_2
        if job.label != "" and job.label is not None:
            final_output_path = Path(job.config.COMPLETED_PATH,
                                     type_sub_folder,
                                     job_title,
                                     utils.clean_for_filename(job.label))
    utils.make_dir(final_output_path, True)
    utils.database_updater({'path': final_output_path}, job)
    db.session.commit()
    return final_output_path


def start_transcode(job: Job, logfile, raw_in_path: str, transcode_out_path: str):
    """
    Passes the job to the right transcoding function, first if handbrake or ffmpeg
    should be used, then how it should be ripped\n
    :param raw_in_path: HandBrake in path (mkv_out_path|/dev/sr0)
    :param transcode_out_path: Path HandBrake should put the files (transcode_path)
    :param job: Current job
    :param logfile: Current logfile
    :param protection: If disc has 99 track protection
    :return: None
    """
    # Update db with transcoding status
    utils.database_updater({'status': JobState.TRANSCODE_ACTIVE.value}, job)
    # Use FFMPEG or HandBrake depending on arm.yaml setting
    if job.config.USE_FFMPEG:
        logging.info("************* Starting Transcode With FFMPEG *************")
        logging.debug(f"ffmpeg_mkv: {raw_in_path}, {transcode_out_path}")
        ffmpeg.ffmpeg_mkv(raw_in_path, transcode_out_path, job)
        logging.info("************* Finished Transcode With FFMPEG *************")
        db.session.commit()
    else:
        logging.info("************* Starting Transcode With HandBrake *************")
        # If it was ripped with MakeMKV or we are doing a mkv rip then run the handbrake_mkv function
        logging.debug(f"handbrake_mkv: {raw_in_path}, {transcode_out_path}")
        handbrake.handbrake_mkv(raw_in_path, transcode_out_path, logfile, job)
        logging.info("************* Finished Transcode With HandBrake *************")


def _transcode_rip_ffmpeg(job: Job, drive_path: str, raw_output_path: str):
    """
    Passes the job to the right ffmpeg ripping function
    :param job: Current job
    :param drive_path: /dev/sr0 and similar
    :param raw_output_path : Path FFMPEG should put the files.
    """
    logging.info("************* Starting Rip With FFMPEG *************")
    # if it is a movie and mainfeature is enabled then run ffmpeg_main_feature
    if utils.check_if_main_feature_applicable(job):
        logging.debug(f"ffmpeg_main_feature: {drive_path}, {raw_output_path}")
        ffmpeg.ffmpeg_main_feature(drive_path, raw_output_path, job)
        db.session.commit()
    # if it is a series or mainfeature is disabled run ffmpeg_all to transcode all tracks
    else:
        logging.debug(f"ffmpeg_all: {drive_path}, {raw_output_path}")
        ffmpeg.ffmpeg_all(drive_path, raw_output_path, job)
        db.session.commit()
    # If it was ripped with MakeMKV or we are doing a mkv rip then run the ffmpeg_mkv function
    logging.info("************* Finished Rip With FFMPEG *************")
    # After transcoding update db status back to idle
    utils.database_updater({'status': JobState.IDLE.value}, job)


def _transcode_rip_handbrake(job: Job, logfile, drive_path: str, raw_output_path: str):
    """
    Passes the job to the right HandBrake ripping function
    :param job: Current job
    :param logfile: The output file to write handbrake logs to
    :param drive_path: /dev/sr0 and similar
    :param raw_output_path : Path FFMPEG should put the files.
    """
    logging.info("************* Starting Rip With HandBrake *************")
    # Otherwise if it is a movie and mainfeature is enabled then run handbrake_main_feature

    if utils.check_if_main_feature_applicable(job):
        logging.debug(f"handbrake_main_feature: {drive_path}, {raw_output_path}")
        handbrake.handbrake_main_feature(drive_path, raw_output_path, logfile, job)
        db.session.commit()
    # Finally if it is a series or mainfeature is disabled run handbrake_all to transcode all tracks
    else:
        logging.debug(f"handbrake_all: {drive_path}, {raw_output_path}")
        handbrake.handbrake_all(drive_path, raw_output_path, logfile, job)
        db.session.commit()
    logging.info("************* Finished Rip With HandBrake *************")
    # After transcoding update db status back to idle
    utils.database_updater({'status': JobState.IDLE.value}, job)
    return True


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


def move_video_files_post(input_path, job: Job):
    """
    Logic for moving files post transcoding\n
    if series move all to 1 main folder containing Disc_label folders\n
    if movie check what source we got them from, for MakeMKV we can check filesize\n
    :param input_path: This should either be the input_path from MakeMKV, /dev/srX or TRANSCODE_PATH
    :param job: current job
    :return: None
    """
    tracks = job.tracks.filter_by(ripped=True)
    if job.video_type == "series":
        for track in tracks:
            utils.move_files_main(Path(input_path, track.filename), Path(job.path, track.filename), job)
        return
    if utils.is_bonus_disc(job):
        logging.info("Disc is Bonus Disc")
        bonus_disc_path = extras_path(job)
        utils.make_dir(bonus_disc_path, exist_ok=True)
        for track in tracks:
            utils.move_files_main(Path(input_path, track.filename), Path(bonus_disc_path, track.filename), job)
        return
    if job.video_type == "movie":
        move_movie_files_post(input_path, tracks, job)


def move_movie_files_post(input_path, tracks, job):
    """
    Move movie files to the final folder.
    """
    if len(tracks) == 1:
        final_filepath = Path(job.path, main_feature_filename(job))
        logging.info(f"Track is the Main Title.  Moving '{Path(input_path, tracks[0].filename)}' to {final_filepath}")
        utils.move_files_main(Path(input_path, tracks[0].filename), final_filepath, job)
        return
    tracks = sorted(tracks, key=lambda x: x.filesize, reverse=True)
    is_main_feature = True
    extras_dir = extras_path(job)
    utils.make_dir(extras_dir, exist_ok=True)
    logging.debug(f"Largest file is: {tracks[0].filename}")
    for track in tracks:
        logging.debug(f"Videotype: {job.video_type}")
        input_filepath = Path(input_path, track.filename)
        if os.stat(input_filepath).st_size <= 1:  # sanity check for filesize
            logging.error(f"{input_path} is empty or very small size. - Folder size: {os.stat(input_filepath).st_size}")
            is_main_feature = False
            continue
        final_filepath = Path(job.path, track.filename)
        if track.source == "MakeMKV":
            if is_main_feature:
                final_filepath = Path(job.path, main_feature_filename(job))
                logging.info(f"Track is the Main Title.  Moving '{input_filepath}' to {final_filepath}")
                is_main_feature = False
            utils.move_files_main(input_filepath, final_filepath, job)
        else:
            # If HandBrake was used we can pass track.main_feature
            if track.main_feature:
                final_filepath = Path(job.path, main_feature_filename(job))
                logging.info(f"Track is Handbrake Main Title.  Moving '{input_filepath}' to {final_filepath}")
            utils.move_files_main(input_filepath, final_filepath, job)


def main_feature_filename(job) -> str:
    return f"{utils.fix_job_title(job)}.{job.config.DEST_EXT}"


def extras_path(job) -> Path:
    if str(job.config.EXTRAS_SUB).lower() == "none":
        logging.info(f"EXTRAS_SUB is {job.config.EXTRAS_SUB} ... Skipping making extras folder")
        return Path(job.path)
    return Path(job.path, job.config.EXTRAS_SUB)


def should_rip_with_MakeMKV(current_job, protection=0):
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
