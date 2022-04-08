"""
Main catch all page for functions for the A.R.M ui
"""
import os
import shutil
import json
import re
import platform
import subprocess

from time import strftime, localtime, time, sleep

import bcrypt
from werkzeug.routing import ValidationError
import yaml
from flask.logging import default_handler  # noqa: F401
from arm.config.config import cfg
from arm.ui import app, db
from arm.models.models import Job, User, AlembicVersion, UISettings
from arm.ui.metadata import tmdb_search, get_tmdb_poster, tmdb_find, call_omdb_api


def database_updater(args, job, wait_time=90):
    """
    Try to update our db for x seconds and handle it nicely if we cant

    :param args: This needs to be a Dict with the key being the
    job.method you want to change and the value being the new value.

    :param job: This is the job object
    :param wait_time: The time to wait in seconds
    :returns : Boolean
    """
    # Loop through our args and try to set any of our job variables
    for (key, value) in args.items():
        setattr(job, key, value)
        app.logger.debug(str(key) + "= " + str(value))
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
            "Database out of date. Head is " + head_revision + " and database is " + db_version
            + ".  Upgrading database...")
        with app.app_context():
            unique_stamp = round(time() * 100)
            app.logger.info("Backuping up database '" + db_file + "' to '" + db_file + str(unique_stamp) + "'.")
            shutil.copy(db_file, db_file + "_" + str(unique_stamp))
            flask_migrate.upgrade(mig_dir)
        app.logger.info("Upgrade complete.  Validating version level...")

        c.execute("SELECT version_num FROM alembic_version")
        db_version = c.fetchone()[0]
        app.logger.debug("Database version is: " + db_version)
        if head_revision == db_version:
            app.logger.info("Database is now up to date")
        else:
            app.logger.error("Database is still out of date. "
                             "Head is " + head_revision + " and database is " + db_version
                             + ".  Exiting arm.")


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
            create_time = strftime(cfg['DATE_FORMAT'], localtime(file_stats.st_ctime))
            access_time = strftime(cfg['DATE_FORMAT'], localtime(file_stats.st_atime))
            # [file,most_recent_access,created, file_size]
            file_list.append([i, access_time, create_time, file_size])
    return file_list


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub(r"\[[^]]*]", "", string)
    string = re.sub('\\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = string.strip()
    return string


def getsize(path):
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    freegb = free / 1073741824
    return freegb


def generate_comments():
    """
    load comments.json and use it for settings page
    allows us to easily add more settings later
    :return: json
    """
    comments = "{'error':'Unknown error'}"
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
    try:
        User.query.all()
        return True
    except Exception:
        #  We only need this on first run
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
            version = AlembicVersion('c54d68996895')
            ui_config = UISettings(1, 1, "spacelab", "en", 10, 200)
            # Create default user to save problems with ui and ripper having diff setups
            hashed = bcrypt.gensalt(12)
            default_user = User(email="admin", password=bcrypt.hashpw("password".encode('utf-8'), hashed),
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
    if cfg['METADATA_PROVIDER'].lower() == "tmdb":
        app.logger.debug("provider tmdb")
        if func == "search":
            return_function = tmdb_search(str(query), str(year))
        elif func == "get_details":
            if query:
                return_function = get_tmdb_poster(str(query), str(year))
            elif imdb_id:
                return_function = tmdb_find(imdb_id)

    elif cfg['METADATA_PROVIDER'].lower() == "omdb":
        app.logger.debug("provider omdb")
        if func == "search":
            return_function = call_omdb_api(str(query), str(year))
        elif func == "get_details":
            return_function = call_omdb_api(title=str(query), year=str(year), imdb_id=str(imdb_id), plot="full")

    return return_function


def fix_permissions(j_id):
    """
    Json api version

    ARM can sometimes have issues with changing the file owner, we can use the fact ARMui is run
    as a service to fix permissions.
    """
    # TODO add new json exception - break these checks out into a function
    try:
        job_id = int(j_id.strip())
    except ValueError:
        raise ValueError("No Valid Job Id Supplied")
    job = Job.query.get(job_id)
    if not job:
        raise TypeError("Job Has Been Deleted From The Database")
    job_log = os.path.join(cfg['LOGPATH'], job.logfile)
    if not os.path.isfile(job_log):
        raise FileNotFoundError("Logfile Has Been Deleted Or Moved")

    # This is kind of hacky way to get around the fact we don't save the ts variable
    with open(job_log, 'r') as reader:
        for line in reader.readlines():
            failed_perms_found = re.search("Operation not permitted: '([0-9a-zA-Z()/ -]*?)'", str(line))
            if failed_perms_found:
                break
    if failed_perms_found:
        app.logger.debug(str(failed_perms_found.group(1)))
        directory_to_traverse = failed_perms_found.group(1)
    else:
        app.logger.debug("not found")
        directory_to_traverse = os.path.join(job.config.COMPLETED_PATH, str(job.title) + " (" + str(job.year) + ")")
    try:
        corrected_chmod_value = int(str(job.config.CHMOD_VALUE), 8)
        app.logger.info(f"Setting permissions to: {job.config.CHMOD_VALUE} on: {directory_to_traverse}")
        os.chmod(directory_to_traverse, corrected_chmod_value)
        if job.config.SET_MEDIA_OWNER and job.config.CHOWN_USER and job.config.CHOWN_GROUP:
            import pwd
            import grp
            uid = pwd.getpwnam(job.config.CHOWN_USER).pw_uid
            gid = grp.getgrnam(job.config.CHOWN_GROUP).gr_gid
            os.chown(directory_to_traverse, uid, gid)

        for dirpath, l_directories, l_files in os.walk(directory_to_traverse):
            for cur_dir in l_directories:
                app.logger.debug("Setting path: " + cur_dir + " to permissions value: " + str(job.config.CHMOD_VALUE))
                os.chmod(os.path.join(dirpath, cur_dir), corrected_chmod_value)
                if job.config.SET_MEDIA_OWNER:
                    os.chown(os.path.join(dirpath, cur_dir), uid, gid)
            for cur_file in l_files:
                app.logger.debug("Setting file: " + cur_file + " to permissions value: " + str(job.config.CHMOD_VALUE))
                os.chmod(os.path.join(dirpath, cur_file), corrected_chmod_value)
                if job.config.SET_MEDIA_OWNER:
                    os.chown(os.path.join(dirpath, cur_file), uid, gid)
        return_json = {"success": True, "mode": "fixperms", "folder": str(directory_to_traverse)}
    except Exception as error:
        err = f"Permissions setting failed as: {error}"
        app.logger.error(err)
        return_json = {"success": False, "mode": "fixperms", "Error": str(err), "ts": str(failed_perms_found)}
    return return_json


def job_id_validator(job_id):
    """
    Validate job id is an int
    :return:
    """
    try:
        int(job_id.strip())
        valid = True
    except AttributeError:
        valid = False
    return valid


def trigger_restart():
    """
    We update the file modified time to get flask to restart
    This only works if ARMui is running as a service & in debug mode
    """
    import datetime

    def set_file_last_modified(file_path, date_time):
        dt_epoch = date_time.timestamp()
        os.utime(file_path, (dt_epoch, dt_epoch))

    now = datetime.datetime.now()
    arm_main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes.py")
    set_file_last_modified(arm_main, now)


def get_settings(arm_cfg_file):
    """
    yaml file loader - is used for loading fresh arm.yaml config

    :param arm_cfg_file: full path to arm.yaml
    :return: the loaded yaml file
    """
    try:
        with open(arm_cfg_file, "r") as yaml_file:
            try:
                yaml_cfg = yaml.load(yaml_file, Loader=yaml.FullLoader)
            except Exception as error:
                app.logger.debug(error)
                yaml_cfg = yaml.safe_load(yaml_file)  # For older versions use this
    except FileNotFoundError as error:
        app.logger.debug(error)
        yaml_cfg = {}
    return yaml_cfg


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
    :param mode:
    :param my_file: full base path using Path()
    :return: None
    :raise ValidationError:
    """
    if logfile is None or "../" in logfile or mode is None or logfile.find("/") != -1:
        raise ValidationError
    if not my_file.is_file():
        # logfile doesnt exist throw out error template
        raise FileNotFoundError("File not found")
