# Collection of utility functions

import os
import sys
import logging
import fcntl
import subprocess
import shutil
import requests
import time

# from arm.config.config import cfg
from arm.ui import app, db # noqa E402
from arm.models.models import Track  # noqa: E402


def notify(job, title, body):
    # Send notificaions
    # title = title for notification
    # body = body of the notification

    if job.config.PB_KEY != "":
        try:
            from pushbullet import Pushbullet
            pb = Pushbullet(job.config.PB_KEY)
            pb.push_note(title, body)
        except:  # noqa: E722
            logging.error("Failed sending PushBullet notification.  Continueing processing...")

    if job.config.IFTTT_KEY != "":
        try:
            import pyfttt as pyfttt
            event = job.config.IFTTT_EVENT
            pyfttt.send_event(job.config.IFTTT_KEY, event, title, body)
        except:  # noqa: E722
            logging.error("Failed sending IFTTT notification.  Continueing processing...")

    if job.config.PO_USER_KEY != "":
        try:
            from pushover import init, Client
            init(job.config.PO_APP_KEY)
            Client(job.config.PO_USER_KEY).send_message(body, title=title)
        except:  # noqa: E722
            logging.error("Failed sending PushOver notification.  Continueing processing...")


def scan_emby(job):
    """Trigger a media scan on Emby"""

    if job.config.EMBY_REFRESH:
        logging.info("Sending Emby library scan request")
        url = "http://" + job.config.EMBY_SERVER + ":" + job.config.EMBY_PORT + "/Library/Refresh?api_key=" + job.config.EMBY_API_KEY
        try:
            req = requests.post(url)
            if req.status_code > 299:
                req.raise_for_status()
            logging.info("Emby Library Scan request successful")
        except requests.exceptions.HTTPError:
            logging.error("Emby Library Scan request failed with status code: " + str(req.status_code))
    else:
        logging.info("EMBY_REFRESH config parameter is false.  Skipping emby scan.")


def move_files(basepath, filename, job, ismainfeature=False):
    """Move files into final media directory\n
    basepath = path to source directory\n
    filename = name of file to be moved\n
    job = instance of Job class\n
    ismainfeature = True/False"""

    logging.debug("Moving files: " + str(job))

    if job.title_manual:
        # logging.info("Found new title: " + job.new_title + " (" + str(job.new_year) + ")")
        # videotitle = job.new_title + " (" + str(job.new_year) + ")"
        hasnicetitle = True
    else:
        hasnicetitle = job.hasnicetitle

    videotitle = job.title + " (" + str(job.year) + ")"

    logging.debug("Arguments: " + basepath + " : " + filename + " : " + str(hasnicetitle) + " : " + videotitle + " : " + str(ismainfeature))

    if hasnicetitle:
        m_path = os.path.join(job.config.MEDIA_DIR + videotitle)

        if not os.path.exists(m_path):
            logging.info("Creating base title directory: " + m_path)
            os.makedirs(m_path)

        if ismainfeature is True:
            logging.info("Track is the Main Title.  Moving '" + filename + "' to " + m_path)

            m_file = os.path.join(m_path, videotitle + "." + job.config.DEST_EXT)
            if not os.path.isfile(m_file):
                try:
                    shutil.move(os.path.join(basepath, filename), m_file)
                except shutil.Error:
                    logging.error("Unable to move '" + filename + "' to " + m_path)
            else:
                logging.info("File: " + m_file + " already exists.  Not moving.")
        else:
            e_path = os.path.join(m_path, job.config.EXTRAS_SUB)

            if not os.path.exists(e_path):
                logging.info("Creating extras directory " + e_path)
                os.makedirs(e_path)

            logging.info("Moving '" + filename + "' to " + e_path)

            e_file = os.path.join(e_path, videotitle + "." + job.config.DEST_EXT)
            if not os.path.isfile(e_file):
                try:
                    shutil.move(os.path.join(basepath, filename), os.path.join(e_path, filename))
                except shutil.Error:
                    logging.error("Unable to move '" + filename + "' to " + e_path)
            else:
                logging.info("File: " + e_file + " already exists.  Not moving.")

    else:
        logging.info("hasnicetitle is false.  Not moving files.")


def rename_files(oldpath, job):
    """
    Rename a directory and its contents based on job class details\n
    oldpath = Path to existing directory\n
    job = An instance of the Job class\n

    returns new path if successful
    """

    newpath = os.path.join(job.config.ARMPATH, job.title + " (" + str(job.year) + ")")
    logging.debug("oldpath: " + oldpath + " newpath: " + newpath)
    logging.info("Changing directory name from " + oldpath + " to " + newpath)

    try:
        shutil.move(oldpath, newpath)
        logging.debug("Directory name change successful")
    except shutil.Error:
        logging.info("Error change directory from " + oldpath + " to " + newpath + ".  Likely the path already exists.")
        raise OSError(2, 'No such file or directory', newpath)

    # try:
    #     shutil.rmtree(oldpath)
    #     logging.debug("oldpath deleted successfully.")
    # except shutil.Error:
    #     logging.info("Error change directory from " + oldpath + " to " + newpath + ".  Likely the path already exists.")
    #     raise OSError(2, 'No such file or directory', newpath)

    # tracks = Track.query.get(job.job_id)
    # tracks = job.tracks.all()
    # for track in tracks:
    #     if track.main_feature:
    #         newfilename = job.title + " (" + str(job.year) + ")" + "." + cfg["DEST_EXT"]
    #     else:
    #         newfilename = job.title + " (" + str(job.year) + ")" + track.track_number + "." + cfg["DEST_EXT"]

    #     track.new_filename = newfilename

    #     # newfullpath = os.path.join(newpath, job.new_title + " (" + str(job.new_year) + ")" + track.track_number + "." + cfg["DEST_EXT"])
    #     logging.info("Changing filename '" + os.path.join(newpath, track.filename) + "' to '" + os.path.join(newpath, newfilename) + "'")
    #     try:
    #         shutil.move(os.path.join(newpath, track.filename), os.path.join(newpath, newfilename))
    #         logging.debug("Filename change successful")
    #     except shutil.Error:
    #         logging.error("Unable to change '" + track.filename + "' to '" + newfilename + "'")
    #         raise OSError(3, 'Unable to change file', newfilename)

    #     track.filename = newfilename
        # db.session.commit()

    return newpath


def make_dir(path):
    """
Make a directory\n
    path = Path to directory\n

    returns success True if successful
        false if the directory already exists
    """
    if not os.path.exists(path):
        logging.debug("Creating directory: " + path)
        try:
            os.makedirs(path)
            return True
        except OSError:
            err = "Couldn't create a directory at path: " + path + " Probably a permissions error.  Exiting"
            logging.error(err)
            sys.exit(err)
            # return False
    else:
        return False


def get_cdrom_status(devpath):
    """get the status of the cdrom drive\n
    devpath = path to cdrom\n

    returns int
    CDS_NO_INFO		0\n
    CDS_NO_DISC		1\n
    CDS_TRAY_OPEN		2\n
    CDS_DRIVE_NOT_READY	3\n
    CDS_DISC_OK		4\n

    see linux/cdrom.h for specifics\n
    """

    try:
        fd = os.open(devpath, os.O_RDONLY | os.O_NONBLOCK)
    except Exception:
        logging.info("Failed to open device " + devpath + " to check status.")
        exit(2)
    result = fcntl.ioctl(fd, 0x5326, 0)

    return result


def find_file(filename, search_path):
    """
    Check to see if file exists by searching a directory recursively\n
    filename = filename to look for\n
    search_path = path to search recursively\n

    returns True or False
    """

    for dirpath, dirnames, filenames in os.walk(search_path):
        if filename in filenames:
            return True
    return False


def rip_music(job, logfile):
    """
    Rip music CD using abcde using abcde config\n
    job = job object\n
    logfile = location of logfile\n

    returns True/False for success/fail
    """

    if job.disctype == "music":
        logging.info("Disc identified as music")
        cmd = 'abcde -d "{0}" >> "{1}" 2>&1'.format(
            job.devpath,
            logfile
        )

        logging.debug("Sending command: " + cmd)

        try:
            subprocess.check_output(
                cmd,
                shell=True
            ).decode("utf-8")
            logging.info("abcde call successful")
            return True
        except subprocess.CalledProcessError as ab_error:
            err = "Call to abcde failed with code: " + str(ab_error.returncode) + "(" + str(ab_error.output) + ")"
            logging.error(err)
            # sys.exit(err)

    return False


def rip_data(job, datapath, logfile):
    """
    Rip data disc using cat on the command line\n
    job = job object\n
    datapath = path to copy data to\n
    logfile = location of logfile\n

    returns True/False for success/fail
    """

    if job.disctype == "data":
        logging.info("Disc identified as data")

        if (job.label) == "":
            job.label = "datadisc"

        filename = os.path.join(datapath, job.label + ".iso")

        logging.info("Ripping data disc to: " + filename)

        cmd = 'cat "{0}" > "{1}" 2>> {2}'.format(
            job.devpath,
            filename,
            logfile
        )

        logging.debug("Sending command: " + cmd)

        try:
            subprocess.check_output(
                cmd,
                shell=True
            ).decode("utf-8")
            logging.info("Data rip call successful")
            return True
        except subprocess.CalledProcessError as dd_error:
            err = "Data rip failed with code: " + str(dd_error.returncode) + "(" + str(dd_error.output) + ")"
            logging.error(err)
            # sys.exit(err)

    return False


def set_permissions(job, directory_to_traverse):
    try:
        corrected_chmod_value = int(str(job.config.CHMOD_VALUE), 8)
        logging.info("Setting permissions to: " + str(job.config.CHMOD_VALUE) + " on: " + directory_to_traverse)
        os.chmod(directory_to_traverse, corrected_chmod_value)

        for dirpath, l_directories, l_files in os.walk(directory_to_traverse):
            for cur_dir in l_directories:
                logging.debug("Setting path: " + cur_dir + " to permissions value: " + str(job.config.CHMOD_VALUE))
                os.chmod(os.path.join(dirpath, cur_dir), corrected_chmod_value)
            for cur_file in l_files:
                logging.debug("Setting file: " + cur_file + " to permissions value: " + str(job.config.CHMOD_VALUE))
                os.chmod(os.path.join(dirpath, cur_file), corrected_chmod_value)
        return True
    except Exception as e:
        err = "Permissions setting failed as: " + str(e)
        logging.error(err)
        return False


def check_db_version(install_path, db_file):
    """
    Check if db exists and is up to date.
    If it doesn't exist create it.  If it's out of date update it.
    """
    from alembic.script import ScriptDirectory
    from alembic.config import Config
    import sqlite3
    import flask_migrate

    # db_file = job.config.DBFILE
    mig_dir = os.path.join(install_path, "arm/migrations")

    config = Config()
    config.set_main_option("script_location", mig_dir)
    script = ScriptDirectory.from_config(config)

    # create db file if it doesn't exist
    if not os.path.isfile(db_file):
        logging.info("No database found.  Initializing arm.db...")
        make_dir(os.path.dirname(db_file))
        with app.app_context():
            flask_migrate.upgrade(mig_dir)

        if not os.path.isfile(db_file):
            logging.error("Can't create database file.  This could be a permissions issue.  Exiting...")
            sys.exit()

    # check to see if db is at current revision
    head_revision = script.get_current_head()
    logging.debug("Head is: " + head_revision)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    c.execute("SELECT {cn} FROM {tn}".format(cn="version_num", tn="alembic_version"))
    db_version = c.fetchone()[0]
    logging.debug("Database version is: " + db_version)
    if head_revision == db_version:
        logging.info("Database is up to date")
    else:
        logging.info("Database out of date. Head is " + head_revision + " and database is " + db_version + ".  Upgrading database...")
        with app.app_context():
            ts = round(time.time() * 100)
            logging.info("Backuping up database '" + db_file + "' to '" + db_file + str(ts) + "'.")
            shutil.copy(db_file, db_file + "_" + str(ts))
            flask_migrate.upgrade(mig_dir)
        logging.info("Upgrade complete.  Validating version level...")

        c.execute("SELECT {cn} FROM {tn}".format(tn="alembic_version", cn="version_num"))
        db_version = c.fetchone()[0]
        logging.debug("Database version is: " + db_version)
        if head_revision == db_version:
            logging.info("Database is now up to date")
        else:
            logging.error("Database is still out of date. Head is " + head_revision + " and database is " + db_version + ".  Exiting arm.")
            sys.exit()


def put_track(job, t_no, seconds, aspect, fps, mainfeature, source, filename=""):
    """
    Put data into a track instance\n


    job = job ID\n
    t_no = track number\n
    seconds = lenght of track in seconds\n
    aspect = aspect ratio (ie '16:9')\n
    fps = frames per second (float)\n
    mainfeature = True/False\n
    source = Source of information\n
    filename = filename of track\n
    """

    logging.debug("Track #" + str(t_no) + " Length: " + str(seconds) + " fps: " + str(fps) + " aspect: " + str(aspect) + " Mainfeature: " +
                  str(mainfeature) + " Source: " + source)

    t = Track(
        job_id=job.job_id,
        track_number=t_no,
        length=seconds,
        aspect_ratio=aspect,
        # blocks=b,
        fps=fps,
        main_feature=mainfeature,
        source=source,
        basename=job.title,
        filename=filename
        )
    db.session.add(t)
    db.session.commit()
