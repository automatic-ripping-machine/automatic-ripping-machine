"""
File and database utility services — extracted from arm/ui/utils.py.

All app.logger calls replaced with standard logging.
"""
import os
import re
import json
import logging
from pathlib import Path
from time import sleep

import requests

import arm.config.config as cfg
from arm.models.job import Job
from arm.database import db

log = logging.getLogger(__name__)


def database_updater(args, job, wait_time=90):
    """
    Try to update our db for x seconds and handle it nicely if we cant\n

    :param args: This needs to be a Dict with the key being the
    job.method you want to change and the value being the new value.
    :param job: This is the job object
    :param wait_time: The time to wait in seconds
    :returns : Boolean
    """
    # Loop through our args and try to set any of our job variables
    for (key, value) in args.items():
        setattr(job, key, value)
        log.debug(f"Setting {key}: {value}")
    for i in range(wait_time):  # give up after the users wait period in seconds
        try:
            db.session.commit()
            break
        except Exception as error:
            if "locked" in str(error):
                sleep(1)
                log.debug(f"database is locked - trying in 1 second {i}/{wait_time} - {error}")
            else:
                log.debug("Error: " + str(error))
                db.session.rollback()
                raise RuntimeError(str(error)) from error

    log.debug("successfully written to the database")
    return True


def make_dir(path):
    """
    Make a directory
    :param path: Path to directory
    :return: Boolean if successful
    """
    success = False
    if not os.path.exists(path):
        log.debug("Creating directory: " + path)
        try:
            os.makedirs(path)
            success = True
        except OSError:
            err = "Couldn't create a directory at path: " + path + " Probably a permissions error.  Exiting"
            log.error(err)
    return success


def getsize(path):
    """Get the free space left in a path. Uses cached values to avoid NFS stalls."""
    from arm.services.disk_usage_cache import get_disk_usage
    usage = get_disk_usage(path)
    if usage:
        return usage["free"] / 1073741824
    # Fallback for paths not in cache (non-NFS)
    path_stats = os.statvfs(path)
    free = (path_stats.f_bavail * path_stats.f_frsize)
    return free / 1073741824


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub(r'\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    # Strip out any remaining illegal chars
    string = re.sub(r"[^\w -]", "", string)
    string = string.strip()
    return string


def fix_permissions(j_id):
    """
    Json api version

    ARM can sometimes have issues with changing the file owner, we can use the fact ARMui is run
    as a service to fix permissions.
    """

    # Use set_media_owner to keep complexity low
    def set_media_owner(dirpath, cur_dir, uid, gid):
        if job.config.SET_MEDIA_OWNER:
            os.chown(os.path.join(dirpath, cur_dir), uid, gid)

    # Validate job is valid
    job_id_validator(j_id)
    job = Job.query.get(j_id)
    if not job:
        raise TypeError("Job Has Been Deleted From The Database")
    # If there is no path saved in the job
    if not job.path:
        # Check logfile still exists
        validate_logfile(job.logfile, "true", Path(os.path.join(str(cfg.arm_config['LOGPATH']), job.logfile)))
        # Find the correct path to use for fixing perms
        directory_to_traverse = find_folder_in_log(os.path.join(cfg.arm_config['LOGPATH'], job.logfile),
                                                   os.path.join(job.config.COMPLETED_PATH,
                                                                f"{job.title} ({job.year})"))
    else:
        directory_to_traverse = job.path
    # Build return json dict
    return_json = {"success": False, "mode": "fixperms", "folder": str(directory_to_traverse), "path": str(job.path)}
    # Set defaults as fail-safe
    uid = 1000
    gid = 1000
    try:
        corrected_chmod_value = int(str(job.config.CHMOD_VALUE), 8)
        log.info(f"Setting permissions to: {job.config.CHMOD_VALUE} on: {directory_to_traverse}")
        os.chmod(directory_to_traverse, corrected_chmod_value)
        # If set media owner in arm.yaml was true set them as users
        if job.config.SET_MEDIA_OWNER and job.config.CHOWN_USER and job.config.CHOWN_GROUP:
            import pwd
            import grp
            uid = pwd.getpwnam(job.config.CHOWN_USER).pw_uid
            gid = grp.getgrnam(job.config.CHOWN_GROUP).gr_gid
            os.chown(directory_to_traverse, uid, gid)
        # walk through each folder and file in the final directory
        for dirpath, l_directories, l_files in os.walk(directory_to_traverse):
            # Set permissions on each directory
            for cur_dir in l_directories:
                log.debug(f"Setting path: {cur_dir} to permissions value: {job.config.CHMOD_VALUE}")
                os.chmod(os.path.join(dirpath, cur_dir), corrected_chmod_value)
                set_media_owner(dirpath, cur_dir, uid, gid)
            # Set permissions on each file
            for cur_file in l_files:
                log.debug(f"Setting file: {cur_file} to permissions value: {job.config.CHMOD_VALUE}")
                os.chmod(os.path.join(dirpath, cur_file), corrected_chmod_value)
                set_media_owner(dirpath, cur_file, uid, gid)
        return_json["success"] = True
    except Exception as error:
        log.error(f"Permissions setting failed as: {error}")
        return_json["Error"] = str(f"Permissions setting failed as: {error}")
    return return_json


def send_to_remote_db(job_id):
    """
    Send a local db job to the arm remote crc64 database
    :param job_id: Job id
    :return: dict/json to return to user
    """
    job = Job.query.get(job_id)
    return_dict = {}
    api_key = cfg.arm_config['ARM_API_KEY']

    # This allows easy updates to the API url
    base_url = "https://1337server.pythonanywhere.com"
    url = f"{base_url}/api/v1/?mode=p&api_key={api_key}&crc64={job.crc_id}&t={job.title}" \
          f"&y={job.year}&imdb={job.imdb_id}" \
          f"&hnt={job.hasnicetitle}&l={job.label}&vt={job.video_type}"
    redacted_url = url.replace(api_key, "<redacted>") if api_key else "<no api key>"
    log.debug("Remote DB URL: %s", str(redacted_url))
    response = requests.get(url)
    req = json.loads(response.text)
    log.debug("Remote DB response success: %s", str(req.get('success', 'unknown')))
    job_dict = job.get_d().items()
    return_dict['config'] = job.config.get_d()
    for key, value in iter(job_dict):
        return_dict[str(key)] = str(value)
    if req['success']:
        return_dict['status'] = "success"
    else:
        return_dict['error'] = req['Error']
        return_dict['status'] = "fail"
    return return_dict


def find_folder_in_log(job_log, default_directory):
    """
    This is kind of hacky way to get around the fact we don't save the ts variable
    Opens the job logfile and searches for arm.ripper failing to set permissions\n

    :param job_log: full path to job.log
    :param default_directory: full path to the final directory prebuilt
    :return: full path to the final directory prebuilt or found in log
    """
    with open(job_log, 'r') as reader:
        for line in reader.readlines():
            failed_perms_found = re.search("Operation not permitted: '([0-9a-zA-Z()/ -]*?)'", str(line))
            if failed_perms_found:
                return failed_perms_found.group(1)
    return default_directory


def validate_logfile(logfile, mode, my_file):
    """
    Check if logfile we got from the user is valid and return
    the resolved (canonicalized) path.

    :param logfile: logfile name
    :param mode: This is used by the json.api
    :param my_file: full base path using Path()
    :return: str — resolved, validated path safe for file operations
    :raise ValueError: if logfile fails sanity checks or escapes LOGPATH
    :raise FileNotFoundError: if logfile cant be found in arm log folder
    """
    log.debug(f"Logfile: {logfile}")
    if logfile is None or mode is None:
        raise ValueError("logfile doesnt pass sanity checks")
    log_dir = Path(cfg.arm_config['LOGPATH']).resolve()
    resolved = my_file.resolve()
    if not str(resolved).startswith(str(log_dir) + os.sep) and resolved != log_dir:
        raise ValueError("logfile doesnt pass sanity checks")
    if not resolved.is_file():
        raise FileNotFoundError("File not found")
    return str(resolved)


def job_id_validator(job_id):
    """
    Validate job id is an int
    :return: bool if is valid
    """
    try:
        int(job_id.strip())
        valid = True
    except AttributeError:
        valid = False
    return valid
