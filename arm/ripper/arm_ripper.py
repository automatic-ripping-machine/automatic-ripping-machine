""" Main file for running DVDs/Blu-rays/CDs/data ?
It would help clear up main and make things easier to find
"""
import sys
import os
import logging

sys.path.append("/opt/arm")

from arm.ripper import utils, makemkv, handbrake  # noqa E402
from arm.ui import app, db, constants  # noqa E402


def rip_visual_media(have_dupes, job, logfile, protection):
    """
    Main ripping function for dvd and Blu-rays, movies or series
    \n
    :param have_dupes: Does this disc already exist in the database
    :param job: Current job
    :param logfile: Current logfile
    :param protection: Does the disc have 99 track protection
    :return: None
    """
    # Fix the sub-folder type - (movie|tv|unknown)
    type_sub_folder = utils.convert_job_type(job.video_type)
    # Fix the job title - Title (Year) | Title
    job_title = utils.fix_job_title(job)

    # We need to check/construct the final path, and the transcode path
    hb_out_path = os.path.join(job.config.TRANSCODE_PATH, type_sub_folder, job_title)
    final_directory = os.path.join(job.config.COMPLETED_PATH, type_sub_folder, job_title)

    # Check folders for already ripped jobs -> creates folder
    hb_out_path = utils.check_for_dupe_folder(have_dupes, hb_out_path, job)
    # If dupes rips is disabled this might kill the run
    final_directory = utils.check_for_dupe_folder(have_dupes, final_directory, job)

    # Update the job.path with the final directory
    utils.database_updater({'path': final_directory}, job)
    # Save poster image from disc if enabled
    utils.save_disc_poster(final_directory, job)

    logging.info(f"Processing files to: {hb_out_path}")
    makemkv_out_path = None
    hb_in_path = str(job.devpath)
    # Do we need to use MakeMKV - Blu-rays, protected dvd's, and dvd with mainfeature off
    use_make_mkv = rip_with_mkv(job, protection)
    logging.debug(f"Using MakeMKV: [{use_make_mkv}]")
    if use_make_mkv:
        logging.info("************* Ripping disc with MakeMKV *************")
        # Run MakeMKV and get path to output
        job.status = "ripping"
        # Set wait time in makemkvcon info to match up with manual overrides.
        # This may lead doubeling the overall wait time.
        makemkv.MAKEMKV_INFO_WAIT_TIME = job.config.MANUAL_WAIT_TIME
        db.session.commit()
        try:
            makemkv_out_path = makemkv.makemkv(job)
        except Exception as mkv_error:  # noqa: E722
            logging.error(f"MakeMKV did not complete successfully.  Exiting ARM! "
                          f"Error: {mkv_error}")
            raise ValueError from mkv_error

        if makemkv_out_path is None:
            logging.error("MakeMKV did not complete successfully.  Exiting ARM!")
            job.status = "fail"
            db.session.commit()
            sys.exit()
        if job.config.NOTIFY_RIP:
            utils.notify(job, constants.NOTIFY_TITLE, f"{job.title} rip complete. Starting transcode. ")
        logging.info("************* Ripping with MakeMKV completed *************")
        # point HB to the path MakeMKV ripped to
        hb_in_path = makemkv_out_path
    # Begin transcoding section - only transcode if skip_transcode is false
    start_transcode(job, logfile, hb_in_path, hb_out_path, protection)

    # --------------- POST PROCESSING ---------------
    # If ripped with MakeMKV remove the 'out' folder and set the raw as the output
    logging.debug(f"Transcode status: [{job.config.SKIP_TRANSCODE}] and MakeMKV Status: [{use_make_mkv}]")
    if job.config.SKIP_TRANSCODE and use_make_mkv:
        utils.delete_raw_files([hb_out_path])
        hb_out_path = hb_in_path

    # Update final path if user has set a custom/manual title
    logging.debug(f"Job title status: [{job.title_manual}]")
    if job.title_manual:
        # Remove the old final dir
        utils.delete_raw_files([final_directory])
        job_title = utils.fix_job_title(job)
        final_directory = os.path.join(job.config.COMPLETED_PATH, type_sub_folder, job_title)
        # Update the job.path with the final directory
        utils.database_updater({'path': final_directory}, job)

    # Move to final folder
    move_files_post(hb_out_path, job)
    # Movie the movie poster if we have one - no longer needed, now handled by save_movie_poster
    utils.move_movie_poster(final_directory, hb_out_path)
    # Scan Emby if arm.yaml requires it
    utils.scan_emby()
    # Set permissions if arm.yaml requires it
    utils.set_permissions(final_directory)
    # If set in the arm.yaml remove the raw files
    utils.delete_raw_files([hb_in_path, hb_out_path, makemkv_out_path])
    # report errors if any
    notify_exit(job)
    logging.info("************* ARM processing complete *************")


def start_transcode(job, logfile, hb_in_path, hb_out_path, protection):
    """
    This checks if transcoding is enabled for the job and then passes it off to the correct
    handbrake function\n
    :param hb_in_path: HandBrake in path (makeMKV_out_path|/dev/sr0)
    :param hb_out_path: Path HandBrake should put the files (transcode_path)
    :param job: Current job
    :param logfile: Current logfile
    :param protection: If disc has 99 track protection
    :return: None
    """
    # Update db with transcoding status
    utils.database_updater({'status': "transcoding"}, job)
    logging.info("************* Starting Transcode With HandBrake *************")
    if rip_with_mkv(job, protection) and job.config.RIPMETHOD == "mkv":
        # skip if transcode is disable
        if job.config.SKIP_TRANSCODE:
            logging.info("Transcoding is disabled, skipping transcode")
            return None
        logging.debug(f"handbrake_mkv: {hb_in_path}, {hb_out_path}, {logfile}")
        handbrake.handbrake_mkv(hb_in_path, hb_out_path, logfile, job)
    elif job.video_type == "movie" and job.config.MAINFEATURE and job.hasnicetitle:
        logging.debug(f"handbrake_main_feature: {hb_in_path}, {hb_out_path}, {logfile}")
        handbrake.handbrake_main_feature(hb_in_path, hb_out_path, logfile, job)
        job.eject()
    else:
        logging.debug(f"handbrake_all: {hb_in_path}, {hb_out_path}, {logfile}")
        handbrake.handbrake_all(hb_in_path, hb_out_path, logfile, job)
        job.eject()
    logging.info("************* Finished Transcode With HandBrake *************")
    utils.database_updater({'status': "active"}, job)
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


def move_files_post(hb_out_path, job):
    """
    Logic for moving files post transcoding\n
    if series move all to 1 folder\n
    if movie check what source we got them from, for MakeMKV use skip_transcode_movie, so we can check filesize\n
    :param hb_out_path: This should either be the RAW_PATH from MakeMKV or the disc from /dev/srX or TRANSCODE_PATH
    :param job: current job
    :return: None
    """
    tracks = job.tracks.filter_by(ripped=True)  # .order_by(job.tracks.length.desc())
    if job.video_type == "series":
        for track in tracks:
            utils.move_files(hb_out_path, track.filename, job, False)
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


def skip_transcode_movie(files, job, raw_path):
    """
    Only ran if job is a movie - find the largest file use it as mainfeature\n
    Movie everything else to extras folder\n
    If mainfeature is enabled skip moving everything but the main file\n
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
        logging.info(f"{raw_path} is empty or very small size. - Folder size: {os.stat(temp_path).st_size}")
    for file in files:
        # move main into main folder
        # move others into extras folder
        if file == largest_file_name:
            # largest movie
            utils.move_files(raw_path, file, job, True)
        else:
            # If mainfeature is enabled - skip to the next file
            if job.config.MAINFEATURE:
                logging.info(f"MAINFEATURE IS {job.config.MAINFEATURE} - Skipping move of {file}")
                continue
            # Other/extras
            if str(job.config.EXTRAS_SUB).lower() != "none":
                utils.move_files(raw_path, file, job, False)
            else:
                logging.info(f"Not moving extra: \"{file}\" - Sub folder is not set or named incorrectly")
