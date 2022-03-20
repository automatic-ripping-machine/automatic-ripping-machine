import os
import shutil
import json
import re
import bcrypt  # noqa: F401
import yaml

from time import strftime, localtime, time
from arm.config.config import cfg
from flask.logging import default_handler  # noqa: F401
from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, AlembicVersion, UISettings  # noqa: F401
from flask import Flask, render_template, flash, request  # noqa: F401

from arm.ui.metadata import tmdb_search, get_tmdb_poster, tmdb_find, call_omdb_api


def database_updater(args, job, wait_time=90):
    """
    Try to update our db for x seconds and handle it nicely if we cant

    :param args: This needs to be a Dict with the key being the job.method you want to change and the value being
    the new value.

    :param job: This is the job object
    :param wait_time: The time to wait in seconds
    :return: Nothing
    """
    # Loop through our args and try to set any of our job variables
    for (key, value) in args.items():
        setattr(job, key, value)
        app.logger.debug(str(key) + "= " + str(value))
    for i in range(wait_time):  # give up after the users wait period in seconds
        try:
            db.session.commit()
        except Exception as e:
            if "locked" in str(e):
                time.sleep(1)
                app.logger.debug(f"database is locked - trying in 1 second {i}/{wait_time} - {e}")
            else:
                app.logger.debug("Error: " + str(e))
                raise RuntimeError(str(e))
        else:
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

    c.execute("SELECT {cn} FROM {tn}".format(cn="version_num", tn="alembic_version"))
    db_version = c.fetchone()[0]
    app.logger.debug("Database version is: " + db_version)
    if head_revision == db_version:
        app.logger.info("Database is up to date")
    else:
        app.logger.info(
            "Database out of date. Head is " + head_revision + " and database is " + db_version
            + ".  Upgrading database...")
        with app.app_context():
            ts = round(time() * 100)
            app.logger.info("Backuping up database '" + db_file + "' to '" + db_file + str(ts) + "'.")
            shutil.copy(db_file, db_file + "_" + str(ts))
            flask_migrate.upgrade(mig_dir)
        app.logger.info("Upgrade complete.  Validating version level...")

        c.execute("SELECT {cn} FROM {tn}".format(tn="alembic_version", cn="version_num"))
        db_version = c.fetchone()[0]
        app.logger.debug("Database version is: " + db_version)
        if head_revision == db_version:
            app.logger.info("Database is now up to date")
        else:
            app.logger.error(
                "Database is still out of date. Head is " + head_revision + " and database is " + db_version
                + ".  Exiting arm.")
            # sys.exit()


def make_dir(path):
    """
    Make a directory\n
    path = Path to directory\n

    returns success True if successful
        false if the directory already exists
    """
    if not os.path.exists(path):
        app.logger.debug("Creating directory: " + path)
        try:
            os.makedirs(path)
            return True
        except OSError:
            err = "Couldn't create a directory at path: " + path + " Probably a permissions error.  Exiting"
            app.logger.error(err)
    else:
        return False


def get_info(directory):
    file_list = []
    for i in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, i)):
            a = os.stat(os.path.join(directory, i))
            fsize = os.path.getsize(os.path.join(directory, i))
            fsize = round((fsize / 1024), 1)
            fsize = "{0:,.1f}".format(fsize)
            create_time = strftime(cfg['DATE_FORMAT'], localtime(a.st_ctime))
            access_time = strftime(cfg['DATE_FORMAT'], localtime(a.st_atime))
            file_list.append([i, access_time, create_time, fsize])  # [file,most_recent_access,created]
    return file_list


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub(r"\[.*?]", "", string)  # noqa: W605
    string = re.sub('\s+', ' ', string)  # noqa: W605
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
    comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.json")
    try:
        with open(comments_file, "r") as f:
            try:
                comments = json.load(f)
                return comments
            except Exception as e:
                comments = None
                app.logger.debug("Error with comments file. {}".format(str(e)))
                return "{'error':'" + str(e) + "'}"
    except FileNotFoundError:
        return "{'error':'File not found'}"


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
        # flash(str(err))
        try:
            db.drop_all()
        except Exception:
            app.logger.debug("couldn't drop all")
        try:
            #  Recreate everything
            db.metadata.create_all(db.engine)
            db.create_all()
            db.session.commit()
            #  push the database version arm is looking for
            user = AlembicVersion('c54d68996895')
            ui_config = UISettings(1, 1, "spacelab", "en", 10, 200)
            db.session.add(ui_config)
            db.session.add(user)
            db.session.commit()
            return True
        except Exception:
            app.logger.debug("couldn't create all")
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
    r = {}
    i = 0
    for j in jobs:
        app.logger.debug("job obj= " + str(j.get_d()))
        x = j.get_d().items()
        r[i] = {}
        for key, value in iter(x):
            r[i][str(key)] = str(value)
            # logging.debug(str(key) + "= " + str(value))
        i += 1

    app.logger.debug(r)
    app.logger.debug("r len=" + str(len(r)))
    if jobs is not None and len(r) > 0:
        app.logger.debug("jobs is none or len(r) - we have jobs")
        return True, r
    else:
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
            return tmdb_search(str(query), str(year))
        elif func == "get_details":
            if query:
                return get_tmdb_poster(str(query), str(year))
            elif imdb_id:
                return tmdb_find(imdb_id)

    elif cfg['METADATA_PROVIDER'].lower() == "omdb":
        app.logger.debug("provider omdb")
        if func == "search":
            return call_omdb_api(str(query), str(year))
        elif func == "get_details":
            s = call_omdb_api(title=str(query), year=str(year), imdb_id=str(imdb_id), plot="full")
            return s
    app.logger.debug(cfg['METADATA_PROVIDER'])
    app.logger.debug("unknown provider - doing nothing, saying nothing. Getting Kryten")


def fix_permissions(j_id):
    """
    Json api version

    ARM can sometimes have issues with changing the file owner, we can use the fact ARMui is run
    as a service to fix permissions.
    """
    try:
        job_id = int(j_id.strip())
    except AttributeError:
        return {"success": False, "mode": "fixperms", "Error": "AttributeError",
                "PrettyError": "No Valid Job Id Supplied"}
    job = Job.query.get(job_id)
    if not job:
        return {"success": False, "mode": "fixperms", "Error": "JobDeleted",
                "PrettyError": "Job Has Been Deleted From The Database"}
    job_log = os.path.join(cfg['LOGPATH'], job.logfile)
    if not os.path.isfile(job_log):
        return {"success": False, "mode": "fixperms", "Error": "FileNotFoundError",
                "PrettyError": "Logfile Has Been Deleted Or Moved"}

    # This is kind of hacky way to get around the fact we dont save the ts variable
    with open(job_log, 'r') as reader:
        for line in reader.readlines():
            ts = re.search("Operation not permitted: '([0-9a-zA-Z()/ -]*?)'", str(line))
            if ts:
                break
            # app.logger.debug(ts)
            # Operation not permitted: '([0-9a-zA-Z\(\)/ -]*?)'
    if ts:
        app.logger.debug(str(ts.group(1)))
        directory_to_traverse = ts.group(1)
    else:
        app.logger.debug("not found")
        directory_to_traverse = os.path.join(job.config.COMPLETED_PATH, str(job.title) + " (" + str(job.year) + ")")
    try:
        corrected_chmod_value = int(str(job.config.CHMOD_VALUE), 8)
        app.logger.info("Setting permissions to: " + str(job.config.CHMOD_VALUE) + " on: " + directory_to_traverse)
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
        d = {"success": True, "mode": "fixperms", "folder": str(directory_to_traverse)}
    except Exception as e:
        err = "Permissions setting failed as: " + str(e)
        app.logger.error(err)
        d = {"success": False, "mode": "fixperms", "Error": str(err), "ts": str(ts)}
    return d


def trigger_restart():
    """
    We update the file modified time to get flask to restart
    This only works if ARMui is running as a service & in debug mode
    """
    import datetime

    def set_file_last_modified(file_path, dt):
        dt_epoch = dt.timestamp()
        os.utime(file_path, (dt_epoch, dt_epoch))

    now = datetime.datetime.now()
    arm_main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes.py")
    set_file_last_modified(arm_main, now)


def get_settings(arm_cfg_file):
    """
    yaml file loader - is used for loading fresh arm.yaml config
    Args:
        arm_cfg_file: full path to arm.yaml

    Returns:
        cfg: the loaded yaml file
    """
    try:
        with open(arm_cfg_file, "r") as f:
            try:
                cfg = yaml.load(f, Loader=yaml.FullLoader)
            except Exception as e:
                app.logger.debug(e)
                cfg = yaml.safe_load(f)  # For older versions use this
    except FileNotFoundError as e:
        app.logger.debug(e)
        cfg = {}
    return cfg
