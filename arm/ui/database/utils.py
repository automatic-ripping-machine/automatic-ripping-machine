"""
ARM Utilities Functions for:
    Database

Functions
    - check_sqlite_file - check if sqlite file (arm.db) exists
    - get_session - Create a database session for switching between database binds
    - migrate_jobs - migrate jobs from sqlite
"""
import os
from sqlalchemy import exc
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import current_app as app

from ui import db
import config.config as cfg
from models.job import Job
from models.config import Config
from models.track import Track


def check_sqlite_file(db_file: str) -> bool:
    """
    Check if sqlite file (arm.db) exists
    """
    file_exists: bool = False

    if os.path.isfile(db_file):
        file_exists = True

    return file_exists


def get_session(bind_key=None):
    """
    Create a database session for switching between database binds

    Values:
        bind_key (str): SQLAlchemy bind value linking back to the ARM UI configuration.
            - 'mysql': Use the MYSQL database.
            - 'sqlite': Use the SQLite database file (old arm.db).

    """
    engine = db.get_engine(app, bind=bind_key)
    session_factory = sessionmaker(bind=engine)
    return scoped_session(session_factory)


def migrate_data() -> int:
    """
    Migrate Jobs from SQLite to the ARM MySQL database.

    This function uses a session to bind queries to the old database and
    then migrates the requested data.

    Returns:
        count:int - count of migrated jobs
    """
    count_job: int = 0
    sqlite_data_job = None

    try:
        # Set the database to use sqlite
        app.logger.debug(f"Migrating data from {cfg.arm_config['DBFILE']}")
        arm_sqlite_job = Job.change_binds(bind_key='sqlite')
        sqlite_session = get_session(bind_key='sqlite')
        sqlite_data_job = sqlite_session.query(arm_sqlite_job).all()
        app.logger.debug("Data gathered")

        # Loop through jobs and migrate data to the new database
        if sqlite_data_job:
            for sqlite_job in sqlite_data_job:
                job_id = migrate_jobs(sqlite_job)
                migrate_config(job_id, sqlite_job)
                tracks = sqlite_session.query(Track).filter_by(job_id=sqlite_job.job_id).all()
                migrate_tracks(job_id, tracks)

                count_job += 1

        # Close sqlite session to arm.db
        sqlite_session.remove()
    except exc.SQLAlchemyError as e:
        app.logger.error(f"ERROR: Unable to retrieve data from SQLite file. {e}")

    return count_job


def migrate_jobs(sqlite_job) -> int:
    """
    Migrate the Job table

    :param sqlite_job The Job table to migrate
    """
    mysql_job = Job(devpath=sqlite_job.devpath)

    mysql_job.arm_version = sqlite_job.arm_version
    mysql_job.crc_id = sqlite_job.crc_id
    mysql_job.logfile = sqlite_job.logfile
    mysql_job.start_time = sqlite_job.start_time
    mysql_job.stop_time = sqlite_job.stop_time
    mysql_job.job_length = sqlite_job.job_length
    mysql_job.status = sqlite_job.status
    mysql_job.stage = sqlite_job.stage
    mysql_job.no_of_titles = sqlite_job.no_of_titles
    mysql_job.title = sqlite_job.title
    mysql_job.title_auto = sqlite_job.title_auto
    mysql_job.title_manual = sqlite_job.title_manual
    mysql_job.year = sqlite_job.year
    mysql_job.year_auto = sqlite_job.year_auto
    mysql_job.year_manual = sqlite_job.year_manual
    mysql_job.video_type = sqlite_job.video_type
    mysql_job.video_type_auto = sqlite_job.video_type_auto
    mysql_job.video_type_manual = sqlite_job.video_type_manual
    mysql_job.imdb_id = sqlite_job.imdb_id
    mysql_job.imdb_id_auto = sqlite_job.imdb_id_auto
    mysql_job.imdb_id_manual = sqlite_job.imdb_id_manual
    mysql_job.poster_url = sqlite_job.poster_url
    mysql_job.poster_url_auto = sqlite_job.poster_url_auto
    mysql_job.poster_url_manual = sqlite_job.poster_url_manual
    mysql_job.mountpoint = sqlite_job.mountpoint
    mysql_job.hasnicetitle = sqlite_job.hasnicetitle
    mysql_job.errors = sqlite_job.errors
    mysql_job.disctype = sqlite_job.disctype
    mysql_job.label = sqlite_job.label
    mysql_job.path = sqlite_job.path
    mysql_job.ejected = sqlite_job.ejected
    mysql_job.updated = sqlite_job.updated
    mysql_job.pid = sqlite_job.pid
    mysql_job.pid_hash = abs(sqlite_job.pid_hash)
    mysql_job.is_iso = sqlite_job.is_iso

    db.session.add(mysql_job)
    db.session.commit()

    # return the inserted jobid
    return mysql_job.job_id


def migrate_config(job_id: int, sqlite_config):
    """
    Migrate the config table

    Pass in the Job table, which references the Config table via foreign keys

    :param job_id:int the job id for config to link the foreign key to
    :param sqlite_config: The Config from the SQLite database to be migrated.
    """
    sqlite_config_dict = {
        # "CONFIG_ID": sqlite_config.config.CONFIG_ID,
        "ARM_CHECK_UDF": sqlite_config.config.ARM_CHECK_UDF,
        "GET_VIDEO_TITLE": sqlite_config.config.GET_VIDEO_TITLE,
        "SKIP_TRANSCODE": sqlite_config.config.SKIP_TRANSCODE,
        "VIDEOTYPE": sqlite_config.config.VIDEOTYPE,
        "MINLENGTH": sqlite_config.config.MINLENGTH,
        "MAXLENGTH": sqlite_config.config.MAXLENGTH,
        "MANUAL_WAIT": sqlite_config.config.MANUAL_WAIT,
        "MANUAL_WAIT_TIME": sqlite_config.config.MANUAL_WAIT_TIME,
        "RAW_PATH": sqlite_config.config.RAW_PATH,
        "TRANSCODE_PATH": sqlite_config.config.TRANSCODE_PATH,
        "COMPLETED_PATH": sqlite_config.config.COMPLETED_PATH,
        "EXTRAS_SUB": sqlite_config.config.EXTRAS_SUB,
        "INSTALLPATH": sqlite_config.config.INSTALLPATH,
        "LOGPATH": sqlite_config.config.LOGPATH,
        "LOGLEVEL": sqlite_config.config.LOGLEVEL,
        "LOGLIFE": sqlite_config.config.LOGLIFE,
        "DBFILE": sqlite_config.config.DBFILE,
        "WEBSERVER_IP": sqlite_config.config.WEBSERVER_IP,
        "WEBSERVER_PORT": sqlite_config.config.WEBSERVER_PORT,
        "UI_BASE_URL": sqlite_config.config.UI_BASE_URL,
        "SET_MEDIA_PERMISSIONS": sqlite_config.config.SET_MEDIA_PERMISSIONS,
        "CHMOD_VALUE": sqlite_config.config.CHMOD_VALUE,
        "SET_MEDIA_OWNER": sqlite_config.config.SET_MEDIA_OWNER,
        "CHOWN_USER": sqlite_config.config.CHOWN_USER,
        "CHOWN_GROUP": sqlite_config.config.CHOWN_GROUP,
        "RIPMETHOD": sqlite_config.config.RIPMETHOD,
        "MKV_ARGS": sqlite_config.config.MKV_ARGS,
        "DELRAWFILES": sqlite_config.config.DELRAWFILES,
        "HASHEDKEYS": sqlite_config.config.HASHEDKEYS,
        "HB_PRESET_DVD": sqlite_config.config.HB_PRESET_DVD,
        "HB_PRESET_BD": sqlite_config.config.HB_PRESET_BD,
        "DEST_EXT": sqlite_config.config.DEST_EXT,
        "HANDBRAKE_CLI": sqlite_config.config.HANDBRAKE_CLI,
        "MAINFEATURE": sqlite_config.config.MAINFEATURE,
        "HB_ARGS_DVD": sqlite_config.config.HB_ARGS_DVD,
        "HB_ARGS_BD": sqlite_config.config.HB_ARGS_BD,
        "EMBY_REFRESH": sqlite_config.config.EMBY_REFRESH,
        "EMBY_SERVER": sqlite_config.config.EMBY_SERVER,
        "EMBY_PORT": sqlite_config.config.EMBY_PORT,
        "EMBY_CLIENT": sqlite_config.config.EMBY_CLIENT,
        "EMBY_DEVICE": sqlite_config.config.EMBY_DEVICE,
        "EMBY_DEVICEID": sqlite_config.config.EMBY_DEVICEID,
        "EMBY_USERNAME": sqlite_config.config.EMBY_USERNAME,
        "EMBY_USERID": sqlite_config.config.EMBY_USERID,
        "EMBY_PASSWORD": sqlite_config.config.EMBY_PASSWORD,
        "EMBY_API_KEY": sqlite_config.config.EMBY_API_KEY,
        "NOTIFY_RIP": sqlite_config.config.NOTIFY_RIP,
        "NOTIFY_TRANSCODE": sqlite_config.config.NOTIFY_TRANSCODE,
        "PB_KEY": sqlite_config.config.PB_KEY,
        "IFTTT_KEY": sqlite_config.config.IFTTT_KEY,
        "IFTTT_EVENT": sqlite_config.config.IFTTT_EVENT,
        "PO_USER_KEY": sqlite_config.config.PO_USER_KEY,
        "PO_APP_KEY": sqlite_config.config.PO_APP_KEY,
        "OMDB_API_KEY": sqlite_config.config.OMDB_API_KEY,
    }

    mysql_config = Config(c=sqlite_config_dict,
                          job_id=job_id)

    db.session.add(mysql_config)
    db.session.commit()


def migrate_tracks(job_id: int, sqlite_tracks):
    """
    Migrate the track table

    Pass in the Job table, which references the Track table via foreign keys

    :param job_id:int the job id for track to link the foreign key to
    :param sqlite_tracks:list a list of all tracks associated with the provided track id
    """
    for sqlite_track in sqlite_tracks:
        app.logger.info(sqlite_track)
        mysql_track = Track(
            job_id=job_id,
            track_number=sqlite_track.track_number,
            length=sqlite_track.length,
            aspect_ratio=sqlite_track.aspect_ratio,
            fps=sqlite_track.fps,
            main_feature=sqlite_track.main_feature,
            source=sqlite_track.source,
            basename=sqlite_track.basename,
            filename=sqlite_track.filename
        )

        # Set additional fields not in the __init__ method
        mysql_track.orig_filename = sqlite_track.orig_filename
        mysql_track.new_filename = sqlite_track.new_filename
        mysql_track.ripped = sqlite_track.ripped
        mysql_track.status = sqlite_track.status
        mysql_track.error = sqlite_track.error

        db.session.add(mysql_track)
        db.session.commit()
