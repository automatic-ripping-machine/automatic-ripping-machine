#!/usr/bin/env python3
"""Collection of utility functions"""
import datetime
import os
import sys
import logging
import logging.handlers
import subprocess
import shutil
import time
import random
import re
from pathlib import Path, PurePath

import bcrypt
import requests
import apprise
import psutil

from netifaces import interfaces, ifaddresses, AF_INET

import arm.config.config as cfg
from arm.ui import db  # needs to be imported before models
from arm.models.job import Job
from arm.models.notifications import Notifications
from arm.models.track import Track
from arm.models.user import User
from arm.models.system_drives import SystemDrives
from arm.ripper import apprise_bulk

NOTIFY_TITLE = "ARM notification"


def notify(job, title: str, body: str):
    """
    Send notifications with apprise\n
    :param job: Current Job
    :param title: title for notification
    :param body: body of the notification
    :return: None
    """

    # Prepend Site Name if configured
    if cfg.arm_config["ARM_NAME"] != "":
        title = f"[{cfg.arm_config['ARM_NAME']}] - {title}"

    # append Job ID if configured
    if cfg.arm_config["NOTIFY_JOBID"] and job is not None:
        title = f"{title} - {job.job_id}"

    # Send to local db
    logging.debug(f"apprise message, title: {title} body: {body}")
    notification = Notifications(title, body)
    database_adder(notification)

    bash_notify(cfg.arm_config, title, body)

    # Sent to remote sites
    # Create an Apprise instance
    apobj = apprise.Apprise()
    if cfg.arm_config["PB_KEY"] != "":
        apobj.add('pbul://' + str(cfg.arm_config["PB_KEY"]))
    if cfg.arm_config["IFTTT_KEY"] != "":
        apobj.add('ifttt://' + str(cfg.arm_config["IFTTT_KEY"]) + "@" + str(cfg.arm_config["IFTTT_EVENT"]))
    if cfg.arm_config["PO_USER_KEY"] != "":
        apobj.add('pover://' + str(cfg.arm_config["PO_USER_KEY"]) + "@" + str(cfg.arm_config["PO_APP_KEY"]))
    if cfg.arm_config["JSON_URL"] != "":
        apobj.add(str(cfg.arm_config["JSON_URL"]).replace("http://", "json://").replace("https://", "jsons://"))
    try:
        apobj.notify(body, title=title)
    except Exception as error:  # noqa: E722
        logging.error(f"Failed sending notifications. error:{error}. Continuing processing...")

    # Bulk send notifications, using the config set on the ripper config page
    if cfg.arm_config["APPRISE"] != "":
        try:
            apprise_bulk.apprise_notify(cfg.arm_config["APPRISE"], title, body)
            logging.debug(f"apprise-config: {cfg.arm_config['APPRISE']}")
        except Exception as error:  # noqa: E722
            logging.error(f"Failed sending apprise notifications. {error}")


def bash_notify(cfg, title, body):
    # bash notifications use subprocess instead of apprise.
    if cfg['BASH_SCRIPT'] != "":
        try:
            subprocess.run(["/usr/bin/bash", cfg['BASH_SCRIPT'], title, body])
            logging.debug("Sent bash notification successful")
        except Exception as error:  # noqa: E722
            logging.error(f"Failed sending notification via bash. Continuing  processing...{error}")


def notify_entry(job):
    """
    Notify On Entry\n
    :param job:
    :return: None
    """
    # TODO make this better or merge with notify/class
    notification = Notifications(f"New Job: {job.job_id} has started. Disctype: {job.disctype}",
                                 f"New job has started to rip - {job.label},"
                                 f"{job.disctype} at {datetime.datetime.now()}")
    database_adder(notification)
    if job.disctype in ["dvd", "bluray"]:
        if cfg.arm_config["UI_BASE_URL"] == "":
            display_address = (f"http://{check_ip()}:{job.config.WEBSERVER_PORT}")
        else:
            display_address = str(cfg.arm_config["UI_BASE_URL"])
        # Send the notifications
        notify(job, NOTIFY_TITLE,
               f"Found disc: {job.title}. Disc type is {job.disctype}. Main Feature is {job.config.MAINFEATURE}."
               f"Edit entry here: {display_address}/jobdetail?job_id={job.job_id}")
    elif job.disctype == "music":
        notify(job, NOTIFY_TITLE, f"Found music CD: {job.label}. Ripping all tracks.")
    elif job.disctype == "data":
        notify(job, NOTIFY_TITLE, "Found data disc.  Copying data.")
    else:
        notify(job, NOTIFY_TITLE, "Could not identify disc.  Exiting.")
        args = {'status': 'fail', 'errors': "Could not identify disc."}
        database_updater(args, job)
        sys.exit()


def sleep_check_process(process_str, max_processes, sleep=(20, 120, 10)):
    """
    New function to check for max_transcode from job.config and force obey limits\n
    :param str process_str: The process string from arm.yaml
    :param int max_processes: The user defined limit for maximum transcodes
    :param tuple sleep: (min sleep time, max sleep time, step)
    :return bool: when we have space in the transcode queue
    """
    if max_processes <= 0:
        return False  # sleep limit disabled
    loop_count = max_processes + 1
    logging.debug(f"loop_count {loop_count}")
    logging.info(f"Starting A sleep check of {process_str}")
    while loop_count >= max_processes:
        # Maybe send a notification that jobs are waiting ?
        loop_count = sum(1 for proc in psutil.process_iter() if proc.name() == process_str)
        logging.debug(f"Number of Processes running is: {loop_count}")
        if max_processes > loop_count:
            break
        # Try to make each check at different times
        random_time = random.randrange(*sleep)
        logging.debug(f"sleeping for {random_time} seconds")
        time.sleep(random_time)
    return True


def convert_job_type(video_type):
    """
    Converts the job_type to the correct sub-folder
    :param video_type: job.video_type
    :return: string of the correct folder
    """
    if video_type == "movie":
        type_sub_folder = "movies"
    elif video_type == "series":
        type_sub_folder = "tv"
    else:
        type_sub_folder = "unidentified"
    return type_sub_folder


def fix_job_title(job):
    """
    Validate the job title remove/add job year as needed\n
    :param job:
    :return: corrected job.title
    """
    if job.year and job.year != "0000" and job.year != "":
        if job.title_manual:
            job_title = f"{job.title_manual} ({job.year})"
        else:
            job_title = f"{job.title} ({job.year})"
    else:
        if job.title_manual:
            job_title = f"{job.title_manual}"
        else:
            job_title = f"{job.title}"
    return job_title


#  ############## Start of post processing functions
def move_files(base_path, filename, job, is_main_feature=False):
    """
    Run extra checks then move files from RAW_PATH or TRANSCODE_PATH to final media directory\n
    :param str base_path: Path to source directory\n
    :param str filename: name of file to be moved\n
    :param job: instance of Job class\n
    :param bool is_main_feature: if current is main feature move to main dir
    :return str: Full movie path
    """
    video_title = fix_job_title(job)
    logging.debug(f"Arguments: {base_path} : {filename} : "
                  f"{job.hasnicetitle} : {video_title} : {is_main_feature}")
    # If filename is blank skip and return
    if filename == "":
        logging.info(f"{filename} is empty... Skipping")
        return None

    movie_path = job.path
    logging.info(f"Moving {job.video_type} {filename} to {movie_path}")
    # For series there are no extras so always use the base path
    extras_path = os.path.join(movie_path, job.config.EXTRAS_SUB) if job.video_type != "series" else movie_path
    make_dir(movie_path)

    if is_main_feature:
        movie_file = os.path.join(movie_path, video_title + "." + job.config.DEST_EXT)
        logging.info(f"Track is the Main Title.  Moving '{os.path.join(base_path, filename)}' to {movie_file}")
        move_files_main(os.path.join(base_path, filename), movie_file, movie_path)
    else:
        # Don't make the extra's path unless we need it
        make_dir(extras_path)
        logging.info(f"Moving '{os.path.join(base_path, filename)}' to {extras_path}")
        # This also handles series - But it doesn't use the extras folder
        move_files_main(os.path.join(base_path, filename), os.path.join(extras_path, filename), extras_path)
    return movie_path


def move_files_main(old_file, new_file, base_path):
    """
    The base function for moving files with logging\n
    :param str old_file: The file to be moved - must include full path
    :param str new_file: Final destination of file - must include full path
    :param str base_path: The base path of the new file - used for logging
    :return: None
    """
    if not os.path.isfile(new_file):
        try:
            shutil.move(old_file, new_file)
        except Exception as error:
            logging.error(f"Unable to move '{old_file}' to '{base_path}' - Error: {error}")
    else:
        logging.info(f"File: {new_file} already exists.  Not moving.")


def move_movie_poster(final_directory, hb_out_path):
    """move movie poster\n
    ---------\n
    DEPRECIATED - Arm already builds the final path so moving is no longer needed"""
    src_poster = os.path.join(hb_out_path, "poster.png")
    dst_poster = os.path.join(final_directory, "poster.png")
    if os.path.isfile(src_poster):
        if not os.path.isfile(dst_poster):
            try:
                shutil.move(src_poster, dst_poster)
            except Exception as poster_error:
                logging.error(f"Unable to move poster.png to '{final_directory}' - Error: {poster_error}")
        else:
            logging.info("File: poster.png already exists.  Not moving.")


def scan_emby():
    """Trigger a media scan on Emby"""

    if cfg.arm_config["EMBY_REFRESH"]:
        logging.info("Sending Emby library scan request")
        url = f"http://{cfg.arm_config['EMBY_SERVER']}:{cfg.arm_config['EMBY_PORT']}/Library/Refresh?api_key={cfg.arm_config['EMBY_API_KEY']}"  # noqa: E501
        try:
            req = requests.post(url)
            if req.status_code > 299:
                req.raise_for_status()
            logging.info("Emby Library Scan request successful")
        except requests.exceptions.HTTPError:
            logging.error(f"Emby Library Scan request failed with status code: {req.status_code}")
    else:
        logging.info("EMBY_REFRESH config parameter is false.  Skipping emby scan.")


def delete_raw_files(dir_list):
    """
    Delete the raw folders from arm after job has finished
    :param list dir_list: Python list containing strings of the folders to be deleted

    """
    if cfg.arm_config["DELRAWFILES"]:
        for raw_folder in dir_list:
            try:
                logging.info(f"Removing raw path - {raw_folder}")
                shutil.rmtree(raw_folder)
            except UnboundLocalError as error:
                logging.debug(f"No raw files found to delete in {raw_folder}- {error}")
            except OSError as error:
                logging.debug(f"No raw files found to delete in {raw_folder} - {error}")
            except TypeError as error:
                logging.debug(f"No raw files found to delete in {raw_folder} - {error}")


#  ############## End of post processing functions


def make_dir(path):
    """
    Make a directory\n
    :param path: Path to directory
    :return: True if successful, false if the directory already exists
    """
    if not os.path.exists(path):
        logging.debug(f"Creating directory: {path}")
        try:
            os.makedirs(path)
            return True
        except OSError as error:
            err = f"Couldn't create a directory at path: {path} Probably a permissions error.  Exiting"
            logging.error(err)
            raise OSError from error
    else:
        return False


def find_file(filename, search_path):
    """
    Check to see if file exists by searching a directory recursively\n
    :param filename: filename to look for
    :param search_path: path to search recursively
    :return bool:
    """
    for dirpath, dirnames, filenames in os.walk(search_path):
        if filename in filenames:
            return True
    return False


def find_largest_file(files, mkv_out_path):
    """
    Step through given dir and return the largest file name\n
    :param files: dir in os.listdir() format
    :param mkv_out_path: RAW_PATH
    :return: largest file name
    """
    largest_file_name = ""
    for file in files:
        # initialize largest_file_name
        if largest_file_name == "":
            largest_file_name = file
        temp_path_f = os.path.join(mkv_out_path, file)
        temp_path_largest = os.path.join(mkv_out_path, largest_file_name)
        if os.stat(temp_path_f).st_size > os.stat(temp_path_largest).st_size:
            largest_file_name = file
    return largest_file_name


def rip_music(job, logfile):
    """
    Rip music CD using abcde config\n
    :param job: job object
    :param logfile: location of logfile\n
    :return: Bool on success or fail
    """

    abcfile = cfg.arm_config["ABCDE_CONFIG_FILE"]
    if job.disctype == "music":
        logging.info("Disc identified as music")
        # If user has set a cfg.arm_config file with ARM use it
        if os.path.isfile(abcfile):
            cmd = f'abcde -d "{job.devpath}" -c {abcfile} >> "{os.path.join(job.config.LOGPATH, logfile)}" 2>&1'
        else:
            cmd = f'abcde -d "{job.devpath}" >> "{os.path.join(job.config.LOGPATH, logfile)}" 2>&1'

        logging.debug(f"Sending command: {cmd}")

        try:
            # TODO check output and confirm all tracks ripped; find "Finished\.$"
            subprocess.check_output(cmd, shell=True).decode("utf-8")
            logging.info("abcde call successful")
            return True
        except subprocess.CalledProcessError as ab_error:
            err = f"Call to abcde failed with code: {ab_error.returncode} ({ab_error.output})"
            args = {'status': 'fail', 'errors': err}
            database_updater(args, job)
            logging.error(err)
    return False


def rip_data(job):
    """
    Rip data disc using dd on the command line\n
    :param job: Current job
    :return: True/False for success/fail
    """
    success = False
    if job.label == "" or job.label is None:
        job.label = "data-disc"
    # get filesystem in order
    raw_path = os.path.join(job.config.RAW_PATH, str(job.label))
    final_path = os.path.join(job.config.COMPLETED_PATH, convert_job_type(job.video_type))
    final_file_name = str(job.label)

    if (make_dir(raw_path)) is False:
        random_time = str(round(time.time() * 100))
        raw_path = os.path.join(job.config.RAW_PATH, str(job.label) + "_" + random_time)
        final_file_name = f"{job.label}_{random_time}"
        if (make_dir(raw_path)) is False:
            logging.info(f"Could not create data directory: {raw_path}  Exiting ARM. ")
            args = {'status': 'fail', 'errors': "Couldn't create data directory"}
            database_updater(args, job)
            sys.exit()

    final_path = os.path.join(final_path, final_file_name)
    incomplete_filename = os.path.join(raw_path, str(job.label) + ".part")
    make_dir(final_path)
    logging.info(f"Ripping data disc to: {incomplete_filename}")
    # Added from pull 366
    cmd = f'dd if="{job.devpath}" of="{incomplete_filename}" {cfg.arm_config["DATA_RIP_PARAMETERS"]} 2>> ' \
          f'{os.path.join(job.config.LOGPATH, job.logfile)}'
    logging.debug(f"Sending command: {cmd}")
    try:
        subprocess.check_output(cmd, shell=True).decode("utf-8")
        full_final_file = os.path.join(final_path, f"{str(job.label)}.iso")
        logging.info(f"Moving data-disc from '{incomplete_filename}' to '{full_final_file}'")
        move_files_main(incomplete_filename, full_final_file, final_path)
        logging.info("Data rip call successful")
        success = True
    except subprocess.CalledProcessError as dd_error:
        err = f"Data rip failed with code: {dd_error.returncode}({dd_error.output})"
        logging.error(err)
        os.unlink(incomplete_filename)
        args = {'status': 'fail', 'errors': err}
        database_updater(args, job)
    try:
        logging.info(f"Trying to remove raw_path: '{raw_path}'")
        shutil.rmtree(raw_path)
    except OSError as error:
        logging.error(f"Error: {error.filename} - {error.strerror}.")
    return success


def set_permissions(directory_to_traverse):
    """

    :param directory_to_traverse: directory to fix permissions
    :return: False if fails
    """
    if not cfg.arm_config['SET_MEDIA_PERMISSIONS']:
        return False
    try:
        corrected_chmod_value = int(str(cfg.arm_config["CHMOD_VALUE"]), 8)
        logging.info(f"Setting permissions to: {cfg.arm_config['CHMOD_VALUE']} on: {directory_to_traverse}")
        os.chmod(directory_to_traverse, corrected_chmod_value)

        for dirpath, l_directories, l_files in os.walk(directory_to_traverse):
            for cur_dir in l_directories:
                logging.debug(f"Setting path: {cur_dir} to permissions value: {cfg.arm_config['CHMOD_VALUE']}")
                os.chmod(os.path.join(dirpath, cur_dir), corrected_chmod_value)

            for cur_file in l_files:
                logging.debug(f"Setting file: {cur_file} to permissions value: {cfg.arm_config['CHMOD_VALUE']}")
                os.chmod(os.path.join(dirpath, cur_file), corrected_chmod_value)

        logging.info("Permissions set successfully: True")
    except Exception as error:
        logging.error(f"Permissions setting failed as: {error}")
    return True


def try_add_default_user():
    """
    Added to fix missmatch from the armui and armripper\n
    This will try to add a default user for the armui
    with the details\n
    Username: admin\n
    Password: password\n
    :return: None
    """
    try:
        username = "admin"
        pass1 = "password".encode('utf-8')
        hashed = bcrypt.gensalt(12)
        database_adder(User(email=username, password=bcrypt.hashpw(pass1, hashed), hashed=hashed))
        perm_file = Path(PurePath(cfg.arm_config['INSTALLPATH'], "installed"))
        write_permission_file = open(perm_file, "w")
        write_permission_file.write("boop!")
        write_permission_file.close()
    except Exception as error:
        #  notify("", str(error), str(error))
        logging.error(error)


def put_track(job, t_no, seconds, aspect, fps, mainfeature, source, filename=""):
    """
    Put data into a track instance.\n
    Having this here saves importing the models file everywhere\n

    :param job: instance of job class
    :param str t_no: track number
    :param int seconds: length of track in seconds
    :param str aspect: aspect ratio (ie '16:9')
    :param str fps: frames per second:str (-not a float-)
    :param bool mainfeature: If the file is identified as the mainfeature
    :param str source: Source of information (HandBrake, MakeMKV, abcde)
    :param str filename: filename of track
    """

    logging.debug(
        f"Track #{int(t_no):02} Length: {seconds: >4} fps: {float(fps):2.3f} "
        f"aspect: {aspect: >4} Mainfeature: {mainfeature} Source: {source}")

    job_track = Track(
        job_id=job.job_id,
        track_number=t_no,
        length=seconds,
        aspect_ratio=aspect,
        fps=fps,
        main_feature=mainfeature,
        source=source,
        basename=job.title,
        filename=filename
    )
    job_track.ripped = (seconds > int(job.config.MINLENGTH))
    database_adder(job_track)


def arm_setup(arm_log):
    """
    Setup arm - Create all the directories we need for arm to run
    check that folders are writeable, and the db file is writeable
    logging doesn't work here, need to write to empty.log or error.log ?\n
    :arguments: None
    :return: None
    """
    arm_directories = [cfg.arm_config['RAW_PATH'], cfg.arm_config['TRANSCODE_PATH'],
                       cfg.arm_config['COMPLETED_PATH'], cfg.arm_config['LOGPATH']]
    try:
        # Check db file is writeable
        if not os.access(cfg.arm_config['DBFILE'], os.W_OK):
            arm_log.error(f"Cant write to database file! Permission ERROR: {cfg.arm_config['DBFILE']} - ARM Will Fail!")
            raise IOError
        # Check directories for read/write permission -> create if they don't exist
        for folder in arm_directories:
            if not os.access(folder, os.R_OK):
                # don't raise as we may be able to create
                arm_log.error(f"Cant read from folder, Permission ERROR: {folder} - ARM Will Fail!")
            if not os.access(folder, os.W_OK):
                arm_log.error(f"Cant write to folder, Permission ERROR: {folder} - ARM Will Fail!")
                raise IOError
            if make_dir(folder):
                arm_log.error(f"Cant create folder: {folder} - ARM Will Fail!")
                raise IOError
    except IOError as error:
        arm_log.error(f"A fatal error has occurred. "
                      f"Cant find/create the folders set in arm.yaml - Error:{error} - ARM Will Fail!")


def database_updater(args, job, wait_time=90):
    """
    Try to update our db for x seconds and handle it nicely if we can't
    If args isn't a dict assume we are wanting a rollback\n

    :param args: This needs to be a Dict with the key being the job.method
    you want to change and the value being
    the new value.
    :param job: This is the job object
    :param int wait_time: Number of times to try(1 sec sleep between try)
    :return: Success
    """
    if not isinstance(args, dict):
        db.session.rollback()
        return False
    # Loop through our args and try to set any of our job variables
    for (key, value) in args.items():
        setattr(job, key, value)
        logging.debug(f"ID:{job.job_id} {key}={value}:{type(value)}")

    for i in range(wait_time):  # give up after the users wait period in seconds
        try:
            db.session.commit()
        except Exception as error:
            if "locked" in str(error):
                time.sleep(1)
                logging.debug(f"database is locked - try {i}/{wait_time}")
            else:
                logging.debug(f"Error: {error}")
                raise RuntimeError(str(error)) from error
    logging.debug("successfully written to the database")
    return True


def database_adder(obj_class):
    """
    Adds model item to db\n
    Used to stop database locked error\n
    :param obj_class: Job/Config/Track/ etc
    :return: True if success
    """
    for i in range(90):  # give up after the users wait period in seconds
        try:
            logging.debug(f"Trying to add {type(obj_class).__name__}")
            db.session.add(obj_class)
            db.session.commit()
            break
        except Exception as error:
            if "locked" in str(error):
                time.sleep(1)
                logging.debug(f"database is locked - try {i}/90")
            else:
                logging.error(f"Error: {error}")
                raise RuntimeError(str(error)) from error
    logging.debug(f"successfully written {type(obj_class).__name__} to the database")
    return True


def clean_old_jobs():
    """
    Check for running jobs - Update failed jobs that are no longer running\n
    :return: None
    """
    active_jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()
    # Clean up abandoned jobs
    for job in active_jobs:
        if psutil.pid_exists(job.pid):
            job_process = psutil.Process(job.pid)
            if job.pid_hash == hash(job_process):
                logging.info(f"Job #{job.job_id} with PID {job.pid} is currently running.")
        else:
            logging.info(f"Job #{job.job_id} with PID {job.pid} has been abandoned."
                         f"Updating job status to fail.")
            job.status = "fail"
            db.session.commit()
            database_updater({'status': "fail"}, job)


def check_ip():
    """
        Check if user has set an ip in the config file
        if not gets the most likely ip
        arguments:
        none
        return: the ip of the host or 127.0.0.1
    """
    if cfg.arm_config['WEBSERVER_IP'] != 'x.x.x.x':
        return cfg.arm_config['WEBSERVER_IP']
    # autodetect host IP address
    ip_list = []
    for interface in interfaces():
        inet_links = ifaddresses(interface).get(AF_INET, [])
        for link in inet_links:
            ip_address = link['addr']
            if ip_address != '127.0.0.1' and not ip_address.startswith('172'):
                ip_list.append(ip_address)
    if len(ip_list) > 0:
        return ip_list[0]
    return '127.0.0.1'


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub('\\[(.*?)]', '', string)
    string = re.sub('\\s+', '-', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = string.replace(" ", " - ")
    string = string.strip()
    return re.sub('[^\\w.() -]', '', string)


def duplicate_run_check(dev_path):
    """
    Kills this run if another run was triggered recently on the same device\n
    Some drives will trigger the udev twice causing 1 disc insert to add 2 jobs\n
    this stops that issue
    :return: None
    """
    running_jobs = db.session.query(Job).filter(
        Job.status.notin_(['fail', 'success']), Job.devpath == dev_path).all()
    if len(running_jobs) >= 1:
        for j in running_jobs:
            print(j.start_time - datetime.datetime.now())
            mins_last_run = int(round(abs(j.start_time - datetime.datetime.now()).total_seconds()) / 60)
            # Some (older) devices can take at least 3 minutes to receive the
            # duplicate event, treat two events within 3 minutes as duplicate.
            if mins_last_run <= 3:
                logging.error(f"Job already running on {dev_path}")
                sys.exit(1)


def save_disc_poster(final_directory, job):
    """
     Use FFMPeg to convert Large Poster if enabled in config
    :param final_directory: folder to put the poster in
    :param job: Current Job
    :return: None
    """
    if job.disctype == "dvd" and cfg.arm_config["RIP_POSTER"]:
        os.system(f"mount {job.devpath}")
        if os.path.isfile(job.mountpoint + "/JACKET_P/J00___5L.MP2"):
            logging.info("Converting NTSC Poster Image")
            os.system(f'ffmpeg -i "{job.mountpoint}/JACKET_P/J00___5L.MP2" "{final_directory}/poster.png"')
        elif os.path.isfile(job.mountpoint + "/JACKET_P/J00___6L.MP2"):
            logging.info("Converting PAL Poster Image")
            os.system(f'ffmpeg -i "{job.mountpoint}/JACKET_P/J00___6L.MP2" "{final_directory}/poster.png"')
        os.system(f"umount {job.devpath}")


def check_for_dupe_folder(have_dupes, hb_out_path, job):
    """
    Check if the folder already exists
     if it exists lets make a new one using random numbers
    :param have_dupes: is this title in the local arm database
    :param hb_out_path: path to HandBrake out
    :param job: Current job
    :return: Final media directory path
    """
    if (make_dir(hb_out_path)) is False:
        logging.info(f"Output directory \"{hb_out_path}\" already exists.")
        # Only begin ripping if we are allowed to make duplicates
        # Or the successful rip of the disc is not found in our database
        logging.debug(f"Value of ALLOW_DUPLICATES: {cfg.arm_config['ALLOW_DUPLICATES']}")
        logging.debug(f"Value of have_dupes: {have_dupes}")
        if cfg.arm_config["ALLOW_DUPLICATES"] or not have_dupes:
            hb_out_path = hb_out_path + "_" + job.stage
            if not (make_dir(hb_out_path)):
                # We failed to make a random directory, most likely a permission issue
                logging.exception(
                    "A fatal error has occurred and ARM is exiting.  "
                    "Couldn't create filesystem. Possible permission error")
                notify(job, NOTIFY_TITLE,
                       f"ARM encountered a fatal error processing {job.title}."
                       f" Couldn't create filesystem. Possible permission error. ")
                database_updater({'status': "fail", 'errors': 'Creating folder failed'}, job)
                sys.exit()
        else:
            # We aren't allowed to rip dupes, notify and exit
            logging.info("Duplicate rips are disabled.")
            notify(job, NOTIFY_TITLE, f"ARM Detected a duplicate disc. For {job.title}. "
                                      f"Duplicate rips are disabled. "
                                      f"You can re-enable them from your config file. ")
            job.eject()
            database_updater({'status': "fail", 'errors': 'Duplicate rips are disabled'}, job)
            sys.exit()
    logging.info(f"Final Output directory \"{hb_out_path}\"")
    return hb_out_path


def job_dupe_check(job):
    """
    function for checking the database to look for jobs that have completed
    successfully with the same label
    :param job: The job obj, so we can use the crc/title etc.
    :return: True/False, dict/None
    """
    logging.debug(f"Trying to find jobs with matching Label={job.label}")
    if job.label is None:
        logging.info("Disc title 'None' not searched in database")
        return False
    else:
        previous_rips = Job.query.filter_by(label=job.label, status="success")
        results = {}
        i = 0
        for j in previous_rips:
            # logging.debug(f"job obj= {j.get_d()}")
            job_dict = j.get_d().items()
            results[i] = {}
            for key, value in iter(job_dict):
                results[i][str(key)] = str(value)
            i += 1

    # logging.debug(f"previous rips = {results}")
    if results:
        logging.debug(f"we have {len(results)} jobs")
        # Check if results too large (over 1), skip if too many
        if len(results) == 1:
            # This might need some tweaks to because of title/year manual
            title = results[0]['title'] if results[0]['title'] else job.label
            year = results[0]['year'] if results[0]['year'] != "" else ""
            poster_url = results[0]['poster_url'] if results[0]['poster_url'] != "" else None
            hasnicetitle = (str(results[0]['hasnicetitle']).lower() == 'true')
            video_type = results[0]['video_type'] if results[0]['hasnicetitle'] != "" else "unknown"
            active_rip = {
                "title": title, "year": year, "poster_url": poster_url, "hasnicetitle": hasnicetitle,
                "video_type": video_type}
            database_updater(active_rip, job)
            return True
        else:
            logging.debug(f"Skipping - There are too many results [{len(results)}]")
            return False
    else:
        logging.info("We have no previous rips/jobs matching this label")
        return False


def check_for_wait(job):
    """
    Wait if we have waiting for user input updates\n\n
    :param job: Current Job
    :return: None
    """
    #  If we have waiting for user input enabled
    if job.config.MANUAL_WAIT:
        logging.info(f"Waiting {job.config.MANUAL_WAIT_TIME} seconds for manual override.")
        database_updater({'status': "waiting"}, job)
        sleep_time = 0
        while sleep_time < job.config.MANUAL_WAIT_TIME:
            time.sleep(5)
            sleep_time += 5
            db.session.refresh(job)
            if job.title_manual:
                logging.info("Manual override found.  Overriding auto identification values.")
                job.updated = True
                job.hasnicetitle = True
                database_updater({'status': "active", "hasnicetitle": True, "updated": True}, job)
                break
        database_updater({'status': "active"}, job)


def get_drive_mode(devpath: str) -> str:
    """
    Retrieve the drive mode for a specified device path.

    This function queries the database for a drive associated with the provided
    device path (`devpath`). If a drive is found, it returns the drive's mode;
    otherwise, it defaults to 'auto'.

    Parameters:
        devpath (str): The device path used to identify the drive in the database.

    Returns:
        str: The drive mode associated with the specified device path if found;
             otherwise, returns 'auto'.
    """
    drive = SystemDrives.query.filter_by(mount=devpath).first()
    if drive:
        mode = drive.drive_mode
    else:
        mode = 'auto'
    return mode
