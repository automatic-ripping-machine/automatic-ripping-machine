"""
Main catch all page for functions for the A.R.M ui
"""
import hashlib
import os
import shutil
import json
import platform
import subprocess
import re
from datetime import datetime
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from time import strftime, localtime, time, sleep

import bcrypt
import requests
from werkzeug.routing import ValidationError
from flask.logging import default_handler  # noqa: F401
from flask_login import current_user

import arm.config.config as cfg
from arm.config.config_utils import arm_yaml_test_bool
from arm.config import config_utils
from arm.models.alembic_version import AlembicVersion
from arm.models.job import Job
from arm.models.system_info import SystemInfo
from arm.models.ui_settings import UISettings
from arm.models.user import User
from arm.ui import app, db
from arm.ui.metadata import tmdb_search, get_tmdb_poster, tmdb_find, call_omdb_api
from arm.ui.settings import DriveUtils

# Path definitions
path_migrations = "arm/migrations"


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
    Check if db exists and is up-to-date.
    If it doesn't exist create it.  If it's out of date update it.
    """
    from alembic.script import ScriptDirectory
    from alembic.config import Config  # noqa: F811
    import sqlite3
    import flask_migrate

    mig_dir = os.path.join(install_path, path_migrations)

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
        else:
            # Only run the below if the db exists
            # Check to see if db is at current revision
            head_revision = script.get_current_head()
            app.logger.debug("Alembic Head is: " + head_revision)

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


def arm_alembic_get():
    """
    Get the Alembic Head revision
    """
    from alembic.script import ScriptDirectory
    from alembic.config import Config

    install_path = cfg.arm_config['INSTALLPATH']

    # Get the arm alembic current head revision
    mig_dir = os.path.join(install_path, path_migrations)
    config = Config()
    config.set_main_option("script_location", mig_dir)
    script = ScriptDirectory.from_config(config)
    head_revision = script.get_current_head()
    app.logger.debug(f"Alembic Head is: {head_revision}")
    return head_revision


def arm_db_get():
    """
    Get the Alembic Head revision
    """
    alembic_db = AlembicVersion()
    db_revision = alembic_db.query.first()
    app.logger.debug(f"Database Head is: {db_revision.version_num}")
    return db_revision


def arm_db_check():
    """
    Check if db exists and is up-to-date.
    """
    db_file = cfg.arm_config['DBFILE']
    db_exists = False
    db_current = False
    head_revision = None
    db_revision = None

    head_revision = arm_alembic_get()

    # Check if the db file exists
    if os.path.isfile(db_file):
        db_exists = True
        # Get the database alembic version
        db_revision = arm_db_get()
        if db_revision.version_num == head_revision:
            db_current = True
            app.logger.debug(
                f"Database is current. Head: {head_revision}" +
                f"DB: {db_revision.version_num}")
        else:
            db_current = False
            app.logger.info(
                "Database is not current, update required." +
                f" Head: {head_revision} DB: {db_revision.version_num}")
    else:
        db_exists = False
        db_current = False
        head_revision = None
        db_revision = None
        app.logger.debug(f"Database file is not present: {db_file}")

    db = {
        "db_exists": db_exists,
        "db_current": db_current,
        "head_revision": head_revision,
        "db_revision": db_revision,
        "db_file": db_file
    }
    return db


def arm_db_cfg():
    """
    Check if the database exists prior to creating global ui settings
    """
    db_update = arm_db_check()
    if not db_update["db_exists"]:
        app.logger.debug("No armui cfg setup")
        check_db_version(cfg.arm_config['INSTALLPATH'], cfg.arm_config['DBFILE'])
        setup_database()

    # if the database has been updated
    # UISettings could be incorrect, return None
    try:
        armui_cfg = UISettings.query.get(1)
        app.jinja_env.globals.update(armui_cfg=armui_cfg)
    except Exception as e:
        app.logger.debug(f"arm_cfg request error {e}")
        armui_cfg = None

    app.logger.debug(armui_cfg)

    return armui_cfg


def arm_db_migrate():
    """
    Migrate the existing database to the newest version, keeping user data
    """
    import flask_migrate

    install_path = cfg.arm_config['INSTALLPATH']
    db_file = cfg.arm_config['DBFILE']
    mig_dir = os.path.join(install_path, path_migrations)

    head_revision = arm_alembic_get()
    db_revision = arm_db_get()

    app.logger.info(
        "Database out of date." +
        f" Head is {head_revision} and database is {db_revision.version_num}." +
        " Upgrading database...")
    with app.app_context():
        time = datetime.now()
        timestamp = time.strftime("%Y-%m-%d_%H%M")
        app.logger.info(
            f"Backing up database '{db_file}' " +
            f"to '{db_file}_migration_{timestamp}'.")
        shutil.copy(db_file, db_file + "_migration_" + timestamp)
        flask_migrate.upgrade(mig_dir)
    app.logger.info("Upgrade complete.  Validating version level...")

    # Check the update worked
    db_revision = arm_db_get()
    app.logger.info(f"ARM head: {head_revision} database: {db_revision.version_num}")
    if head_revision == db_revision.version_num:
        app.logger.info("Database is now up to date")
        arm_db_initialise()
    else:
        app.logger.error(
            "Database is still out of date. " +
            f"Head is {head_revision} and database " +
            f"is {db_revision.version_num}.  Exiting arm.")


def arm_db_initialise():
    """
    Initialise the ARM DB, ensure system values and disk drives are loaded
    """
    # Check system/server information is loaded
    if not SystemInfo.query.filter_by(id="1").first():
        # Define system info and load to db
        server = SystemInfo()
        app.logger.debug("****** System Information ******")
        app.logger.debug(f"Name: {server.name}")
        app.logger.debug(f"CPU: {server.cpu}")
        app.logger.debug(f"Description: {server.description}")
        app.logger.debug(f"Memory Total: {server.mem_total}")
        app.logger.debug("****** End System Information ******")
        db.session.add(server)
        db.session.commit()
    # Scan and load drives to database
    DriveUtils.drives_update()


def make_dir(path):
    """
    Make a directory
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
    :return: list containing a list with each file's stats
    """
    file_list = []
    for i in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, i)):
            file_stats = os.stat(os.path.join(directory, i))
            file_size = os.path.getsize(os.path.join(directory, i))
            file_size = round((file_size / 1024), 1)
            file_size = f"{file_size:,.1f}"
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
    except IOError:
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
        admins = User.query.all()
        app.logger.debug(f"Number of admins: {len(admins)}")
        if len(admins) > 0:
            return True
    except SQLAlchemyError as e:
        app.logger.debug(f"SQLAlchemy error: {e}")
        app.logger.debug("Couldn't find a user table")
    else:
        app.logger.debug("Found User table but didnt find any admins...")

    try:
        #  Recreate everything
        db.metadata.create_all(db.engine)
        db.create_all()
        db.session.commit()
        # UI Config
        # UI config is already set within the alembic migration file - 9cae4aa05dd7_create_settingsui_table.py
        # Create default user to save problems with ui and ripper having diff setups
        hashed = bcrypt.gensalt(12)
        default_user = User(email="admin", password=bcrypt.hashpw("password".encode('utf-8'), hashed), hashed=hashed)
        app.logger.debug("DB Init - Admin user loaded")
        db.session.add(default_user)
        # Server config
        server = SystemInfo()
        db.session.add(server)
        app.logger.debug("DB Init - Server info loaded")
        db.session.commit()
        # Scan and load drives to database
        DriveUtils.drives_update()
        app.logger.debug("DB Init - Drive info loaded")
        return True
    except SQLAlchemyError as e:
        app.logger.debug(f"SQLAlchemy error: {e}")
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
    jobs = Job.query.filter_by(crc_id=crc_id, status="success", hasnicetitle=True)
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
    job = Job.query.get(job_id)
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
    # This is not the safest way to do things.
    # It assumes the user isn't trying to mess with us.
    # This really should be hard coded.
    app.logger.debug("save_settings: START")
    for key, value in form_data.items():
        # Skip the Cross Site Request Forgery (CSRF) token
        if key == "csrf_token":
            continue
        # Check if value contains "KEY" or "API" (any case)
        elif re.search(r"_KEY|_API|_PASSWORD", key):
            key_value = "####--redacted--####"
        else:
            key_value = value
        # Print output
        app.logger.debug(f"save_settings: [{key}] = {key_value} ")

        # Add any grouping comments
        arm_cfg += config_utils.arm_yaml_check_groups(comments, key)
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
            arm_cfg += config_utils.arm_yaml_test_bool(key, value)

    app.logger.debug("save_settings: FINISH")
    return arm_cfg


def build_apprise_cfg(form_data):
    """
    Main function for saving new updated apprise.yaml\n
    :param form_data: post data
    :return: full new arm.yaml as a String
    """
    # This really should be hard coded.
    app.logger.debug("save_apprise: START")
    apprise_cfg = "\n\n"
    for key, value in form_data.items():
        # Skip the Cross Site Request Forgery (CSRF) token
        if key == "csrf_token":
            continue
        # Check if value contains "KEY" or "API" (any case)
        elif re.search(r"KEY|API|PASS|TOKEN|SECRET", key):
            key_value = "####--redacted--####"
        else:
            key_value = value
        # Print output
        app.logger.debug(f"save_settings: [{key}] = {key_value} ")

        # test if key value is an int
        try:
            post_value = int(value)
            apprise_cfg += f"{key}: {post_value}\n"
        except ValueError:
            # Test if value is Boolean
            apprise_cfg += arm_yaml_test_bool(key, value)
    app.logger.debug("save_apprise: FINISH")
    return apprise_cfg


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
    dupe_found, _ = job_dupe_check(hash_object.hexdigest())
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
    new_movie = Job("/dev/sr0")
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
    git_hash: str = 'unknown'
    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                                           cwd=cfg.arm_config['INSTALLPATH']).decode('ascii').strip()
        # Trunkate to seven characters (aligns with the github commit values reported)
        git_hash = git_hash[:7]
        app.logger.debug(f"GIT revision: {git_hash}")
    except subprocess.CalledProcessError as e:
        app.logger.debug(f"GIT revision error: {e}")

    return git_hash


def get_git_revision_short_hash() -> str:
    """Get short hash of current git commit"""
    git_hash: str = 'unknown'
    try:
        subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                cwd=cfg.arm_config['INSTALLPATH']).decode('ascii').strip()
    except subprocess.CalledProcessError as e:
        app.logger.debug(f"GIT revision error: {e}")

    return git_hash


def git_check_updates(current_hash) -> bool:
    """
    Check the ARM commit hash against the remote (GitHub) commit hash
    :param
        current_hash: str - string of current ARM commit hash
    :return:
        arm_current: Bool - True for no update (or exceptions), False for update possible
    """
    # GitHub API url - branch main
    url = "https://api.github.com/repos/automatic-ripping-machine/automatic-ripping-machine/commits/main"
    arm_current = True      # set True, any exceptions will return a true value

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for HTTP failures (4xx, 5xx)

        latest_commit = response.json().get("sha", "").strip()
        if not latest_commit:
            app.logger.error("Failed to retrieve latest commit hash from GitHub API.")

        # Compare local and remote hashes
        arm_current = latest_commit.startswith(current_hash)

        app.logger.debug(f"Remote hash: {latest_commit}")
        app.logger.debug(f"Local hash: {current_hash}")
        app.logger.debug(f"ARM current: {arm_current}")

    except requests.RequestException as e:
        app.logger.error(f"GitHub API request failed: {e}")

    return arm_current


def git_check_version():
    """
    Check the current ARM version locally against the remote (GitHub) version.

    This function compares the installed ARM version with the latest version available
    in the remote GitHub repository.

    :return:
        tuple: (local_version, remote_version)
            - local_version (str): The version currently installed locally (from the VERSION file).
            - remote_version (str): The latest version available in the remote repository.
    """

    install_path = cfg.arm_config['INSTALLPATH']

    # Read the local version from the VERSION file
    version_file_path = os.path.join(install_path, 'VERSION')
    try:
        with open(version_file_path) as version_file:
            local_version = version_file.read().strip()
    except FileNotFoundError as e:
        app.logger.debug(f"Error - ARM Local Version file not found: {e}")
    except IOError as e:
        app.logger.debug(f"Error - ARM Local Version file error: {e}")

    # Read the remote version from Git (without modifying local files)
    try:
        remote_version = subprocess.check_output(
            'git show origin/HEAD:VERSION', shell=True, cwd=install_path
        ).decode('ascii').strip()
    except subprocess.CalledProcessError as e:
        app.logger.debug(f"Error - ARM Remote Version error: {e}")
        remote_version = "Unknown"

    app.logger.debug(f"Local version: {local_version}")
    app.logger.debug(f"Remote version: {remote_version}")

    return local_version, remote_version


def authenticated_state() -> bool:
    """
    Determines whether the current user is considered authenticated.

    This function checks the application's configuration to see if login
    authentication is disabled. If login is disabled, it automatically
    returns `True`, indicating that the user is authenticated. Otherwise,
    it checks the `current_user.is_authenticated` attribute provided by
    Flask-Login to determine if the user is logged in.

    Returns:
        bool: `True` if the user is authenticated, either by bypassing
        the login requirement or by being a logged-in user; `False` otherwise.
    """
    authenticated = False
    if cfg.arm_config['DISABLE_LOGIN']:
        authenticated = True
    else:
        if current_user.is_authenticated:
            authenticated = True

    return authenticated
