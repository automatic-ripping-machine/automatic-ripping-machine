#!/usr/bin/env python3
"""
Main routes for the A.R.M ui
Covers
- index [GET]
- error [GET]
- errorhandler [GET]
- setup [GET] -- penned for removal
Other routes handled in flask blueprints
- auth, database, history, jobs, logs, sendmovies, settings
"""

import os
import json
from pathlib import Path, PurePath
from werkzeug.exceptions import HTTPException
from flask import Flask, render_template, request, flash, \
    redirect, url_for, session   # noqa: F401
from flask.logging import default_handler  # noqa: F401
from flask_login import LoginManager, login_required, \
    current_user, login_user, logout_user  # noqa: F401

import arm.ui.utils as ui_utils
from arm.ui import app, db, constants
from arm.models.job import Job
from arm.models.system_info import SystemInfo
from arm.models.user import User
import arm.config.config as cfg
from arm.ui.forms import DBUpdate
from arm.ui.settings.ServerUtil import ServerUtil
from arm.ui.settings.settings import check_hw_transcode_support

# This attaches the armui_cfg globally to let the users use any bootswatch skin from cdn
armui_cfg = ui_utils.arm_db_cfg()

# Page definitions
page_support_databaseupdate = "support/databaseupdate.html"
redirect_settings = "/settings"

# Define the Flask login manager
login_manager = LoginManager()
login_manager.init_app(app)


@app.route('/')
@app.route('/index.html')
@app.route('/index')
def home():
    """
    The main homepage showing current rips and server stats
    """
    global page_support_databaseupdate

    # Check the database is current
    db_update = ui_utils.arm_db_check()
    # Push out HW transcode status for homepage
    stats = {'hw_support': check_hw_transcode_support()}
    if not db_update["db_current"] or not db_update["db_exists"]:
        dbform = DBUpdate(request.form)
        app.logger.debug(f"Error with ARM DB: [{db_update['db_current']}]-[{db_update['db_exists']}]")
        return render_template(page_support_databaseupdate, db_update=db_update, dbform=dbform)

    # System details in class server
    server = SystemInfo.query.filter_by(id="1").first()
    serverutil = ServerUtil()

    # System details in class server
    arm_path = cfg.arm_config['TRANSCODE_PATH']
    media_path = cfg.arm_config['COMPLETED_PATH']

    # Page titles
    session["arm_name"] = cfg.arm_config['ARM_NAME']
    session["page_title"] = "Home"

    if os.path.isfile(cfg.arm_config['DBFILE']):
        try:
            jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()
        except Exception:
            # db isn't setup
            return redirect(url_for('setup'))
    else:
        jobs = {}

    # Set authentication state for index
    authenticated = ui_utils.authenticated_state()

    app.logger.debug(f'Authentication state: {authenticated}')

    return render_template("index.html",
                           authenticated=authenticated,
                           jobs=jobs,
                           children=cfg.arm_config['ARM_CHILDREN'],
                           server=server, serverutil=serverutil,
                           arm_path=arm_path, media_path=media_path, stats=stats)


@app.route('/error')
def was_error(error):
    """
    Catch all error page
    :return: Error page
    """
    return render_template(constants.ERROR_PAGE, title='error', error=error)


@app.errorhandler(Exception)
def handle_exception(sent_error):
    """
    Exception handler - This breaks all the normal debug functions \n
    :param sent_error: error
    :return: error page
    """
    # pass through HTTP errors
    if isinstance(sent_error, HTTPException):
        return sent_error

    app.logger.debug(f"Error: {sent_error}", exc_info=sent_error)
    if request.path.startswith('/json') or request.args.get('json'):
        app.logger.debug(f"{request.path} - {sent_error}")
        return_json = {
            'path': request.path,
            'Error': str(sent_error)
        }
        return app.response_class(response=json.dumps(return_json, indent=4, sort_keys=True),
                                  status=200,
                                  mimetype=constants.JSON_TYPE)

    return render_template(constants.ERROR_PAGE, error=sent_error), 500


@app.route('/setup')
def setup():
    """
    This is the initial setup page for fresh installs
    This is no longer recommended for upgrades

    This function will do various checks to make sure everything can be setup for ARM
    Directory ups, create the db, etc
    """
    # perm_file = Path(PurePath(cfg.arm_config['INSTALLPATH'], "installed"))
    # app.logger.debug("perm " + str(perm_file))
    # # Check for install file and that db is correctly setup
    # if perm_file.exists() and ui_utils.setup_database():
    #     flash(f"{perm_file} exists, setup cannot continue. To re-install please delete this file.", "danger")
    #     return redirect("/")
    # dir0 = Path(PurePath(cfg.arm_config['DBFILE']).parent)
    # dir1 = Path(cfg.arm_config['RAW_PATH'])
    # dir2 = Path(cfg.arm_config['TRANSCODE_PATH'])
    # dir3 = Path(cfg.arm_config['COMPLETED_PATH'])
    # dir4 = Path(cfg.arm_config['LOGPATH'])
    # arm_directories = [dir0, dir1, dir2, dir3, dir4]

    # try:
    #     for arm_dir in arm_directories:
    #         if not Path.exists(arm_dir):
    #             os.makedirs(arm_dir)
    #             flash(f"{arm_dir} was created successfully.", "success")
    # except FileNotFoundError as error:
    #     flash(f"Creation of the directory {dir0} failed {error}", "danger")
    #     app.logger.debug(f"Creation of the directory failed - {error}")
    # else:
    #     flash("Successfully created all of the ARM directories", "success")
    #     app.logger.debug("Successfully created all of the ARM directories")

    try:
        if ui_utils.setup_database():
            flash("Setup of the database was successful.", "success")
            app.logger.debug("Setup of the database was successful.")
            perm_file = Path(PurePath(cfg.arm_config['INSTALLPATH'], "installed"))
            write_permission_file = open(perm_file, "w")
            write_permission_file.write("boop!")
            write_permission_file.close()
            return redirect(constants.HOME_PAGE)
        flash("Couldn't setup database", "danger")
        app.logger.debug("Couldn't setup database")
        return redirect("/error")
    except Exception as error:
        flash(str(error))
        app.logger.debug("Setup - " + str(error))
        return redirect(constants.HOME_PAGE)


@login_manager.user_loader
def load_user(user_id):
    """
    Logged in check
    :param user_id:
    :return:
    """
    try:
        return User.query.get(int(user_id))
    except Exception:
        app.logger.debug("Error getting user")
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """
    User isn't authorised to view the page
    :return: Page redirect
    """
    return redirect('/login')
