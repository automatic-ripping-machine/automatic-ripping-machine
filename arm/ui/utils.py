"""
Main catch all page for functions for the A.R.M ui
"""
import hashlib
import os
import shutil
import json
import re
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from time import strftime, localtime, time, sleep

import bcrypt
import requests
from werkzeug.routing import ValidationError
from flask.logging import default_handler  # noqa: F401

import arm.config.config as cfg
from arm.ui import app, db
from arm.models import models
from arm.ui.metadata import tmdb_search, get_tmdb_poster, tmdb_find, call_omdb_api


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
        app.logger.debug(f"Setting {key}: {value}")
    for i in range(wait_time):  # give up after the users wait period in seconds
        try:
            db.session.commit()
        except Exception as error:
            if "locked" in str(error):
                sleep(1)
                app.logger.debug(f"database is locked - trying in 1 second {i}/{wait_time} - {error}")
            else:
                app.logger.debug("Error: " + str(error))
                db.session.rollback()
                raise RuntimeError(str(error)) from error

    app.logger.debug("successfully written to the database")
    return True


def check_db_version(install_path, db_file):
    """
    Check if db exists and is up to date.
    If it doesn't exist create it.  If it's out of date update it.
    """
    from alembic.script import ScriptDirectory
    from alembic.config import Config  # noqa: F811
    import sqlite3
    import flask_migrate

    mig_dir = os.path.join(install_path, "arm/migrations")

    config = Config()
    config.set_main_option("script_location", mig_dir)
    script = ScriptDirectory.from_config(config)

    # create db file if it doesn't exist
    if not os.path.isfile(db_file):
        app.logger.info("No database found.  Initializing arm.db...")
        make_dir(os.path.dirname(db_file))
        with app.app_context():
            flask_migrate.upgrade(mig_dir)

        if not os.path.isfile(db_file):
            app.logger.debug("Can't create database file.  This could be a permissions issue.  Exiting...")

    # check to see if db is at current revision
    head_revision = script.get_current_head()
    app.logger.debug("Head is: " + head_revision)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    c.execute('SELECT version_num FROM alembic_version')
    db_version = c.fetchone()[0]
    app.logger.debug(f"Database version is: {db_version}")
    if head_revision == db_version:
        app.logger.info("Database is up to date")
    else:
        app.logger.info(
            f"Database out of date. Head is {head_revision} and database is {db_version}.  Upgrading database...")
        with app.app_context():
            unique_stamp = round(time() * 100)
            app.logger.info(f"Backing up database '{db_file}' to '{db_file}{unique_stamp}'.")
            shutil.copy(db_file, db_file + "_" + str(unique_stamp))
            flask_migrate.upgrade(mig_dir)
        app.logger.info("Upgrade complete.  Validating version level...")

        c.execute("SELECT version_num FROM alembic_version")
        db_version = c.fetchone()[0]
        app.logger.debug(f"Database version is: {db_version}")
        if head_revision == db_version:
            app.logger.info("Database is now up to date")
        else:
            app.logger.error(f"Database is still out of date. "
                             f"Head is {head_revision} and database is {db_version}.  Exiting arm.")


def make_dir(path):
    """
        Make a directory\n
    :param path: Path to directory
    :return: Boolean if successful
    """
    success = False
    if not os.path.exists(path):
        app.logger.debug("Creating directory: " + path)
        try:
            os.makedirs(path)
            success = True
        except OSError:
            err = "Couldn't create a directory at path: " + path + " Probably a permissions error.  Exiting"
            app.logger.error(err)
    return success


def get_info(directory):
    """
    Used to read stats from files
    -Used for view logs page
    :param directory:
    :return: list containing a list with each files stats
    """
    file_list = []
    for i in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, i)):
            file_stats = os.stat(os.path.join(directory, i))
            file_size = os.path.getsize(os.path.join(directory, i))
            file_size = round((file_size / 1024), 1)
            file_size = f"{file_size :,.1f}"
            create_time = strftime(cfg.arm_config['DATE_FORMAT'], localtime(file_stats.st_ctime))
            access_time = strftime(cfg.arm_config['DATE_FORMAT'], localtime(file_stats.st_atime))
            # [file,most_recent_access,created, file_size]
            file_list.append([i, access_time, create_time, file_size])
    return file_list


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


def getsize(path):
    """Simple function to get the free space left in a path"""
    path_stats = os.statvfs(path)
    free = (path_stats.f_bavail * path_stats.f_frsize)
    free_gb = free / 1073741824
    return free_gb


def generate_comments():
    """
    load comments.json and use it for settings page
    allows us to easily add more settings later
    :return: json
    """
    comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.json")
    try:
        with open(comments_file, "r") as comments_read_file:
            try:
                comments = json.load(comments_read_file)
            except Exception as error:
                app.logger.debug(f"Error with comments file. {error}")
                comments = "{'error':'" + str(error) + "'}"
    except FileNotFoundError:
        comments = "{'error':'File not found'}"
    return comments


def generate_full_log(full_path):
    """
    Gets/tails all lines from log file
    :param full_path: full path to job logfile
    :return: None
    """
    try:
        with open(full_path) as read_log_file:
            while True:
                yield read_log_file.read()
                sleep(1)
    except Exception:
        try:
            with open(full_path, encoding="utf8", errors='ignore') as read_log_file:
                while True:
                    yield read_log_file.read()
                    sleep(1)
        except FileNotFoundError as error:
            raise FileNotFoundError("Not found with utf8 encoding") from error


def generate_arm_cat(full_path):
    """
    Read from log file and only output ARM: logs
    :param full_path: full path to job logfile
    :return: None
    """
    read_log_file = open(full_path)
    while True:
        new = read_log_file.readline()
        if new:
            if "ARM:" in new:
                yield new
            else:
                sleep(1)


def setup_database():
    """
    Try to get the db.User if not we nuke everything
    """
    # This checks for a user table
    try:
        admins = models.User.query.all()
        app.logger.debug(f"Number of admins: {len(admins)}")
        if len(admins) > 0:
            return True
    except Exception:
        app.logger.debug("Couldn't find a user table")
    else:
        app.logger.debug("Found User table but didnt find any admins... triggering db wipe")
    #  Wipe everything
    try:
        db.drop_all()
    except Exception:
        app.logger.debug("Couldn't drop all")
    try:
        #  Recreate everything
        db.metadata.create_all(db.engine)
        db.create_all()
        db.session.commit()
        #  push the database version arm is looking for
        version = models.AlembicVersion('f1054468c1c7')
        ui_config = models.UISettings(1, 1, "spacelab", "en", 2000, 200)
        # Create default user to save problems with ui and ripper having diff setups
        hashed = bcrypt.gensalt(12)
        default_user = models.User(email="admin", password=bcrypt.hashpw("password".encode('utf-8'), hashed),
                                   hashed=hashed)
        db.session.add(ui_config)
        db.session.add(version)
        db.session.add(default_user)
        db.session.commit()
        return True
    except Exception:
        app.logger.debug("Couldn't create all")
    return False


def job_dupe_check(crc_id):
    """
    function for checking the database to look for jobs that have completed
    successfully with the same crc

    :param crc_id: The job obj so we can use the crc/title etc
    :return: True if we have found dupes with the same crc
              - Will also return a dict of all the jobs found.
             False if we didnt find any with the same crc
              - Will also return None as a secondary param
    """
    if crc_id is None:
        return False, None
    jobs = models.Job.query.filter_by(crc_id=crc_id, status="success", hasnicetitle=True)
    # app.logger.debug("search - posts=" + str(jobs))
    return_results = {}
    i = 0
    for j in jobs:
        app.logger.debug("job obj= " + str(j.get_d()))
        return_results[i] = {}
        for key, value in iter(j.get_d().items()):
            return_results[i][str(key)] = str(value)
            # logging.debug(str(key) + "= " + str(value))
        i += 1

    app.logger.debug(return_results)
    app.logger.debug("r len=" + str(len(return_results)))
    if jobs is not None and len(return_results) > 0:
        app.logger.debug("jobs is none or len(r) - we have jobs")
        return True, return_results
    app.logger.debug("jobs is none or len(r) is 0 - we have no jobs")
    return False, None


def metadata_selector(func, query="", year="", imdb_id=""):
    """
    Used to switch between OMDB or TMDB as the metadata provider
    - TMDB returned queries are converted into the OMDB format

    :param func: the function that is being called - allows for more dynamic results
    :param query: this can either be a search string or movie/show title
    :param year: the year of movie/show release
    :param imdb_id: the imdb id to lookup

    :return: json/dict object
    """
    return_function = None
    if cfg.arm_config['METADATA_PROVIDER'].lower() == "tmdb":
        app.logger.debug(f"provider tmdb - function: {func}")
        if func == "search":
            return_function = tmdb_search(str(query), str(year))
        elif func == "get_details":
            if query:
                app.logger.debug("provider tmdb - using: get_tmdb_poster")
                return_function = get_tmdb_poster(str(query), str(year))
            elif imdb_id:
                app.logger.debug("provider tmdb - using: tmdb_find")
                return_function = tmdb_find(imdb_id)
            app.logger.debug("No title or imdb provided")

    elif cfg.arm_config['METADATA_PROVIDER'].lower() == "omdb":
        app.logger.debug(f"provider omdb - function: {func}")
        if func == "search":
            return_function = call_omdb_api(str(query), str(year))
        elif func == "get_details":
            return_function = call_omdb_api(title=str(query), year=str(year), imdb_id=str(imdb_id), plot="full")
    else:
        app.logger.debug("Unknown metadata selected")
    return return_function


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
    job = models.Job.query.get(j_id)
    if not job:
        raise TypeError("Job Has Been Deleted From The Database")
    # If there is no path saved in the job
    if not job.path:
        # Check logfile still exists
        validate_logfile(job.logfile, "true", Path(os.path.join(cfg.arm_config['LOGPATH'], job.logfile)))
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
        app.logger.info(f"Setting permissions to: {job.config.CHMOD_VALUE} on: {directory_to_traverse}")
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
                app.logger.debug(f"Setting path: {cur_dir} to permissions value: {job.config.CHMOD_VALUE}")
                os.chmod(os.path.join(dirpath, cur_dir), corrected_chmod_value)
                set_media_owner(dirpath, cur_dir, uid, gid)
            # Set permissions on each file
            for cur_file in l_files:
                app.logger.debug(f"Setting file: {cur_file} to permissions value: {job.config.CHMOD_VALUE}")
                os.chmod(os.path.join(dirpath, cur_file), corrected_chmod_value)
                set_media_owner(dirpath, cur_file, uid, gid)
        return_json["success"] = True
    except Exception as error:
        app.logger.error(f"Permissions setting failed as: {error}")
        return_json["Error"] = str(f"Permissions setting failed as: {error}")
    return return_json


def send_to_remote_db(job_id):
    """
    Send a local db job to the arm remote crc64 database
    :param job_id: Job id
    :return: dict/json to return to user
    """
    job = models.Job.query.get(job_id)
    return_dict = {}
    api_key = cfg.arm_config['ARM_API_KEY']

    # This allows easy updates to the API url
    base_url = "https://1337server.pythonanywhere.com"
    url = f"{base_url}/api/v1/?mode=p&api_key={api_key}&crc64={job.crc_id}&t={job.title}" \
          f"&y={job.year}&imdb={job.imdb_id}" \
          f"&hnt={job.hasnicetitle}&l={job.label}&vt={job.video_type}"
    app.logger.debug(url.replace(api_key, "<api_key>"))
    response = requests.get(url)
    req = json.loads(response.text)
    app.logger.debug("req= " + str(req))
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


def trigger_restart():
    """
    We update the file modified time to get flask to restart
    This only works if ARMui is running as a service & in debug mode

    notes: This has been removed, breaks and causes errors when run as 'arm' user
    """

    def set_file_last_modified(file_path, date_time):
        dt_epoch = date_time.timestamp()
        os.utime(file_path, (dt_epoch, dt_epoch))

    now = datetime.now()
    arm_main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes.py")
    set_file_last_modified(arm_main, now)


def build_arm_cfg(form_data, comments):
    """
    Main function for saving new updated arm.yaml\n
    :param form_data: post data
    :param comments: comments file loaded as dict
    :return: full new arm.yaml as a String
    """
    arm_cfg = comments['ARM_CFG_GROUPS']['BEGIN'] + "\n\n"
    # TODO: This is not the safest way to do things.
    #  It assumes the user isn't trying to mess with us.
    # This really should be hard coded.
    app.logger.debug("save_settings: START")
    for key, value in form_data.items():
        app.logger.debug(f"save_settings: current key {key} = {value} ")
        if key == "csrf_token":
            continue
        # Add any grouping comments
        arm_cfg += arm_yaml_check_groups(comments, key)
        # Check for comments for this key in comments.json, add them if they exist
        try:
            arm_cfg += "\n" + comments[str(key)] + "\n" if comments[str(key)] != "" else ""
        except KeyError:
            arm_cfg += "\n"
        # test if key value is an int
        try:
            post_value = int(value)
            arm_cfg += f"{key}: {post_value}\n"
        except ValueError:
            # Test if value is Boolean
            arm_cfg += arm_yaml_test_bool(key, value)
    app.logger.debug("save_settings: FINISH")
    return arm_cfg


def arm_yaml_test_bool(key, value):
    """
    we need to test if the key is a bool, as we need to lower() it for yaml\n\n
    or check if key is the webserver ip. \nIf not we need to wrap the value with quotes\n
    :param key: the current key
    :param value: the current value
    :return: the new updated arm.yaml config with new key: values
    """
    if value.lower() == 'false' or value.lower() == "true":
        arm_cfg = f"{key}: {value.lower()}\n"
    else:
        # If we got here, the only key that doesn't need quotes is the webserver key
        # everything else needs "" around the value
        if key == "WEBSERVER_IP":
            arm_cfg = f"{key}: {value.lower()}\n"
        else:
            arm_cfg = f"{key}: \"{value}\"\n"
    return arm_cfg


def arm_yaml_check_groups(comments, key):
    """
    Check the current key to be added to arm.yaml and insert the group
    separator comment, if the key matches\n
    :param comments: comments dict, containing all comments from the arm.yaml
    :param key: the current post key from form.args
    :return: arm.yaml config with any new comments added
    """
    comment_groups = {'COMPLETED_PATH': "\n" + comments['ARM_CFG_GROUPS']['DIR_SETUP'],
                      'WEBSERVER_IP': "\n" + comments['ARM_CFG_GROUPS']['WEB_SERVER'],
                      'SET_MEDIA_PERMISSIONS': "\n" + comments['ARM_CFG_GROUPS']['FILE_PERMS'],
                      'RIPMETHOD': "\n" + comments['ARM_CFG_GROUPS']['MAKE_MKV'],
                      'HB_PRESET_DVD': "\n" + comments['ARM_CFG_GROUPS']['HANDBRAKE'],
                      'EMBY_REFRESH': "\n" + comments['ARM_CFG_GROUPS']['EMBY']
                                      + "\n" + comments['ARM_CFG_GROUPS']['EMBY_ADDITIONAL'],
                      'NOTIFY_RIP': "\n" + comments['ARM_CFG_GROUPS']['NOTIFY_PERMS'],
                      'APPRISE': "\n" + comments['ARM_CFG_GROUPS']['APPRISE']}
    if key in comment_groups:
        arm_cfg = comment_groups[key]
    else:
        arm_cfg = ""
    return arm_cfg


def get_processor_name():
    """
    function to collect and return some cpu info
    ideally want to return {name} @ {speed} Ghz
    """
    cpu_info = None
    if platform.system() == "Windows":
        cpu_info = platform.processor()
    elif platform.system() == "Darwin":
        cpu_info = subprocess.check_output(['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]).strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        fulldump = str(subprocess.check_output(command, shell=True).strip())
        # Take any float trailing "MHz", some whitespace, and a colon.
        speeds = re.search(r"\\nmodel name\\t:.*?GHz\\n", fulldump)
        if speeds:
            # We have intel CPU
            speeds = str(speeds.group())
            speeds = speeds.replace('\\n', ' ')
            speeds = speeds.replace('\\t', ' ')
            speeds = speeds.replace('model name :', '')
            cpu_info = speeds

        # AMD CPU
        amd_name_full = re.search(r"model name\\t: (.*?)\\n", fulldump)
        if amd_name_full:
            amd_name = amd_name_full.group(1)
            amd_mhz = re.search(r"cpu MHz(?:\\t)*: ([.0-9]*)\\n", fulldump)  # noqa: W605
            if amd_mhz:
                amd_ghz = round(float(amd_mhz.group(1)) / 1000, 2)  # this is a good idea
                cpu_info = str(amd_name) + " @ " + str(amd_ghz) + " GHz"
    return cpu_info


def validate_logfile(logfile, mode, my_file):
    """
    check if logfile we got from the user is valid
    :param logfile: logfile name
    :param mode: This is used by the json.api
    :param my_file: full base path using Path()
    :return: None
    :raise ValidationError: if logfile has "/" or "../" in it or "mode" is None
    :raise FileNotFoundError: if logfile cant be found in arm log folder
    """
    app.logger.debug(f"Logfile: {logfile}")
    if logfile is None or "../" in logfile or mode is None or logfile.find("/") != -1:
        raise ValidationError("logfile doesnt pass sanity checks")
    if not my_file.is_file():
        # logfile doesnt exist throw out error template
        raise FileNotFoundError("File not found")


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


def generate_file_list(my_path):
    """
    Generate a list of files from given path\n
    :param my_path: path to folder
    :return: list of files
    """
    movie_dirs = [f for f in os.listdir(my_path) if os.path.isdir(os.path.join(my_path, f)) and not f.startswith(".")
                  and os.path.isdir(os.path.join(my_path, f))]
    app.logger.debug(movie_dirs)
    return movie_dirs


def import_movie_add(poster_image, imdb_id, movie_group, my_path):
    """
    Search the movie directory, make sure we have movie files and then import it into the db\n
    :param poster_image:
    :param imdb_id:
    :param movie_group:
    :param my_path:
    :return:
    """
    app.logger.debug(f"Poster image: {poster_image}, IMDB: {imdb_id}, "
                     f"Movie_group: {movie_group.group(0)}, Path: {my_path}")
    # only used to add a non-unique crc64
    movie = movie_group.group(0)
    # Fake crc64 number
    hash_object = hashlib.md5(f"{movie}".strip().encode())
    # Check if we already have this in the db exit if we do
    dupe_found, not_used_variable = job_dupe_check(hash_object.hexdigest())
    if dupe_found:
        app.logger.debug("We found dupes breaking loop")
        return None
    app.logger.debug(f"List dir = {os.listdir(my_path)}")

    # Build file list with common video extension types
    movie_files = [f for f in os.listdir(my_path)
                   if os.path.isfile(os.path.join(my_path, f))
                   and f.endswith((".mkv", ".avi", ".mp4", ".avi"))]
    app.logger.debug(f"movie files = {movie_files}")

    # This dict will be returned to the big list, so we can display to the user
    movie_dict = {
        'title': movie_group.group(1),
        'year': movie_group.group(2),
        'crc_id': hash_object.hexdigest(),
        'imdb_id': imdb_id,
        'poster': poster_image,
        'status': 'success' if len(movie_files) >= 1 else 'fail',
        'video_type': 'movie',
        'disctype': 'unknown',
        'hasnicetitle': True,
        'no_of_titles': len(movie_files)
    }
    app.logger.debug(movie_dict)
    # Create the new job and use the found values
    new_movie = models.Job("/dev/sr0")
    new_movie.title = movie_dict['title']
    new_movie.year = movie_dict['year']
    new_movie.crc_id = hash_object.hexdigest()
    new_movie.imdb_id = imdb_id
    new_movie.status = movie_dict['status']
    new_movie.video_type = movie_dict['video_type']
    new_movie.disctype = movie_dict['disctype']
    new_movie.hasnicetitle = movie_dict['hasnicetitle']
    new_movie.no_of_titles = movie_dict['no_of_titles']
    new_movie.poster_url = movie_dict['poster']
    new_movie.start_time = datetime.now()
    new_movie.logfile = "imported.log"
    new_movie.ejected = True
    new_movie.path = my_path
    app.logger.debug(new_movie)
    db.session.add(new_movie)
    return movie_dict


def get_git_revision_hash() -> str:
    """Get full hash of current git commit"""
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                   cwd=cfg.arm_config['INSTALLPATH']).decode('ascii').strip()


def get_git_revision_short_hash() -> str:
    """Get short hash of current git commit"""
    return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                   cwd=cfg.arm_config['INSTALLPATH']).decode('ascii').strip()


def git_check_updates(current_hash) -> bool:
    """Check if we are on latest commit"""
    git_update = subprocess.run(['git', 'fetch',
                                 'https://github.com/automatic-ripping-machine/automatic-ripping-machine'],
                                cwd=cfg.arm_config['INSTALLPATH'], check=False)
    # git for-each-ref refs/remotes/origin --sort="-committerdate" | head -1
    git_log = subprocess.check_output('git for-each-ref refs/remotes/origin --sort="-committerdate" | head -1',
                                      shell=True, cwd="/opt/arm").decode('ascii').strip()
    app.logger.debug(git_update.returncode)
    app.logger.debug(git_log)
    app.logger.debug(current_hash)
    app.logger.debug(bool(re.search(rf"\A{current_hash}", git_log)))
    return bool(re.search(rf"\A{current_hash}", git_log))


def git_get_updates() -> dict:
    """update arm"""
    git_log = subprocess.run(['git', 'pull'], cwd=cfg.arm_config['INSTALLPATH'], check=False)
    return {'stdout': git_log.stdout, 'stderr': git_log.stderr,
            'return_code': git_log.returncode, 'form': 'ARM Update', "success": (git_log.returncode == 0)}
