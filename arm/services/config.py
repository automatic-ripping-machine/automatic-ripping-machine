"""
Configuration and database management services — extracted from arm/ui/utils.py.

All app.logger calls replaced with standard logging.
"""
import os
import shutil
import json
import re
import logging
from datetime import datetime
from time import time

import bcrypt
from sqlalchemy.exc import SQLAlchemyError

import arm.config.config as cfg
from arm.config.config_utils import arm_yaml_test_bool
from arm.config import config_utils
from arm.models.alembic_version import AlembicVersion
from arm.models.system_info import SystemInfo
from arm.models.ui_settings import UISettings
from arm.models.user import User
from arm.database import db
from arm.services.files import make_dir

log = logging.getLogger(__name__)

# Path definitions
path_migrations = "arm/migrations"


def _alembic_upgrade(mig_dir, db_uri):
    """Run ``alembic upgrade head`` without Flask."""
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", mig_dir)
    alembic_cfg.set_main_option("sqlalchemy.url", db_uri)
    command.upgrade(alembic_cfg, "head")


def check_db_version(install_path, db_file):
    """
    Check if db exists and is up-to-date.
    If it doesn't exist create it.  If it's out of date update it.
    """
    from alembic.script import ScriptDirectory
    from alembic.config import Config
    import sqlite3

    db_uri = 'sqlite:///' + db_file
    mig_dir = os.path.join(install_path, path_migrations)

    config = Config()
    config.set_main_option("script_location", mig_dir)
    script = ScriptDirectory.from_config(config)

    # Create db file if it doesn't exist
    if not os.path.isfile(db_file):
        log.info("No database found.  Initializing arm.db...")
        make_dir(os.path.dirname(db_file))
        _alembic_upgrade(mig_dir, db_uri)
        if not os.path.isfile(db_file):
            log.error("Can't create database file.  This could be a permissions issue.")
            return

    # Check to see if db is at current revision
    head_revision = script.get_current_head()
    log.debug("Alembic Head is: " + head_revision)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    try:
        c.execute('SELECT version_num FROM alembic_version')
        db_version = c.fetchone()[0]
    except sqlite3.OperationalError:
        log.warning("alembic_version table missing — database may need migration.")
        conn.close()
        return

    log.debug(f"Database version is: {db_version}")
    if head_revision == db_version:
        log.info("Database is up to date")
    else:
        log.info(
            f"Database out of date. Head is {head_revision} and database is {db_version}.  Upgrading database...")
        dt = datetime.now()
        timestamp = dt.strftime("%Y-%m-%d_%H%M%S")
        backup_path = f"{db_file}_migration_{timestamp}"
        log.info(f"Backing up database '{db_file}' to '{backup_path}'.")
        shutil.copy(db_file, backup_path)
        _alembic_upgrade(mig_dir, db_uri)
        log.info("Upgrade complete.  Validating version level...")

        try:
            c.execute("SELECT version_num FROM alembic_version")
            db_version = c.fetchone()[0]
        except sqlite3.OperationalError:
            log.error("alembic_version table still missing after upgrade.")
            conn.close()
            return

        log.debug(f"Database version is: {db_version}")
        if head_revision == db_version:
            log.info("Database is now up to date")
        else:
            log.error(f"Database is still out of date. "
                      f"Head is {head_revision} and database is {db_version}.  Exiting arm.")

    conn.close()


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
    log.debug(f"Alembic Head is: {head_revision}")
    return head_revision


def arm_db_get():
    """
    Get the Alembic Head revision
    """
    try:
        alembic_db = AlembicVersion()
        db_revision = alembic_db.query.first()
        if db_revision is None:
            log.warning("alembic_version table is empty.")
            return None
        log.debug(f"Database Head is: {db_revision.version_num}")
        return db_revision
    except Exception:
        log.warning("Could not read alembic_version table — database may need migration.")
        return None


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
        if db_revision is None:
            db_current = False
            log.warning("Database file exists but alembic_version unreadable.")
        elif db_revision.version_num == head_revision:
            db_current = True
            log.debug(
                f"Database is current. Head: {head_revision}" +
                f"DB: {db_revision.version_num}")
        else:
            db_current = False
            log.info(
                "Database is not current, update required." +
                f" Head: {head_revision} DB: {db_revision.version_num}")
    else:
        db_exists = False
        db_current = False
        head_revision = None
        db_revision = None
        log.debug(f"Database file is not present: {db_file}")

    db_result = {
        "db_exists": db_exists,
        "db_current": db_current,
        "head_revision": head_revision,
        "db_revision": db_revision,
        "db_file": db_file
    }
    return db_result


def arm_db_migrate():
    """
    Migrate the existing database to the newest version, keeping user data
    """
    install_path = cfg.arm_config['INSTALLPATH']
    db_file = cfg.arm_config['DBFILE']
    db_uri = 'sqlite:///' + db_file
    mig_dir = os.path.join(install_path, path_migrations)

    head_revision = arm_alembic_get()
    db_revision = arm_db_get()

    log.info(
        "Database out of date." +
        f" Head is {head_revision} and database is {db_revision.version_num}." +
        " Upgrading database...")
    dt = datetime.now()
    timestamp = dt.strftime("%Y-%m-%d_%H%M")
    log.info(
        f"Backing up database '{db_file}' " +
        f"to '{db_file}_migration_{timestamp}'.")
    shutil.copy(db_file, db_file + "_migration_" + timestamp)
    _alembic_upgrade(mig_dir, db_uri)
    log.info("Upgrade complete.  Validating version level...")

    # Check the update worked
    db_revision = arm_db_get()
    log.info(f"ARM head: {head_revision} database: {db_revision.version_num}")
    if head_revision == db_revision.version_num:
        log.info("Database is now up to date")
        arm_db_initialise()
    else:
        log.error(
            "Database is still out of date. " +
            f"Head is {head_revision} and database " +
            f"is {db_revision.version_num}.  Exiting arm.")


def arm_db_initialise():
    """
    Initialise the ARM DB, ensure system values and disk drives are loaded
    """
    from arm.services.drives import drives_update

    # Check system/server information is loaded
    if not SystemInfo.query.filter_by(id="1").first():
        # Define system info and load to db
        server = SystemInfo()
        log.debug("****** System Information ******")
        log.debug(f"Name: {server.name}")
        log.debug(f"CPU: {server.cpu}")
        log.debug(f"Description: {server.description}")
        log.debug(f"Memory Total: {server.mem_total}")
        log.debug("****** End System Information ******")
        db.session.add(server)
        db.session.commit()
    # Scan and load drives to database
    drives_update()


def setup_database():
    """
    Try to get the db.User if not we nuke everything
    """
    from arm.services.drives import drives_update

    # This checks for a user table
    try:
        admins = User.query.all()
        log.debug(f"Number of admins: {len(admins)}")
        if len(admins) > 0:
            return True
    except SQLAlchemyError as e:
        log.debug(f"SQLAlchemy error: {e}")
        log.debug("Couldn't find a user table")
    else:
        log.debug("Found User table but didnt find any admins...")

    try:
        #  Recreate everything
        db.metadata.create_all(db.engine)
        db.create_all()
        db.session.commit()
        # Create default user to save problems with ui and ripper having diff setups
        hashed = bcrypt.gensalt(12)
        default_user = User(email="admin", password=bcrypt.hashpw("password".encode('utf-8'), hashed), hashed=hashed)
        log.debug("DB Init - Admin user loaded")
        db.session.add(default_user)
        # Server config
        server = SystemInfo()
        db.session.add(server)
        log.debug("DB Init - Server info loaded")
        db.session.commit()
        # Scan and load drives to database
        drives_update()
        log.debug("DB Init - Drive info loaded")
        return True
    except SQLAlchemyError as e:
        log.debug(f"SQLAlchemy error: {e}")
        log.debug("Couldn't create all")
    return False


def generate_comments():
    """
    load comments.json and use it for settings page
    allows us to easily add more settings later
    :return: json
    """
    comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "..", "data", "comments.json")
    try:
        with open(comments_file, "r") as comments_read_file:
            try:
                comments = json.load(comments_read_file)
            except Exception as error:
                log.debug(f"Error with comments file. {error}")
                comments = "{'error':'" + str(error) + "'}"
    except FileNotFoundError:
        comments = "{'error':'File not found'}"
    return comments


def _format_yaml_value(key, value):
    """Format a single key-value pair as a YAML line."""
    try:
        return f"{key}: {int(value)}\n"
    except ValueError:
        return config_utils.arm_yaml_test_bool(key, value)


def build_arm_cfg(form_data, comments):
    """
    Main function for saving new updated arm.yaml\n
    :param form_data: post data
    :param comments: comments file loaded as dict
    :return: full new arm.yaml as a String
    """
    arm_cfg = comments['ARM_CFG_GROUPS']['BEGIN'] + "\n\n"
    log.debug("save_settings: START")
    for key, value in form_data.items():
        if key == "csrf_token":
            continue
        value = value.strip() if isinstance(value, str) else value
        key_value = "####--redacted--####" if re.search(r"_KEY|_API|_PASSWORD", key) else value
        log.debug(f"save_settings: [{key}] = {key_value} ")

        arm_cfg += config_utils.arm_yaml_check_groups(comments, key)
        try:
            arm_cfg += "\n" + comments[str(key)] + "\n" if comments[str(key)] != "" else ""
        except KeyError:
            arm_cfg += "\n"
        arm_cfg += _format_yaml_value(key, value)

    log.debug("save_settings: FINISH")
    return arm_cfg


def build_apprise_cfg(form_data):
    """
    Main function for saving new updated apprise.yaml\n
    :param form_data: post data
    :return: full new arm.yaml as a String
    """
    log.debug("save_apprise: START")
    apprise_cfg = "\n\n"
    for key, value in form_data.items():
        # Skip the Cross Site Request Forgery (CSRF) token
        if key == "csrf_token":
            continue
        if isinstance(value, str):
            value = value.strip()
        if re.search(r"KEY|API|PASS|TOKEN|SECRET", key):
            key_value = "####--redacted--####"
        else:
            key_value = value
        log.debug(f"save_settings: [{key}] = {key_value} ")

        # test if key value is an int
        try:
            post_value = int(value)
            apprise_cfg += f"{key}: {post_value}\n"
        except ValueError:
            apprise_cfg += arm_yaml_test_bool(key, value)
    log.debug("save_apprise: FINISH")
    return apprise_cfg
