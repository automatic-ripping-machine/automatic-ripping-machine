"""
ARM route blueprint for settings pages
Covers
- settings [GET]
- save_settings [POST]
- save_ui_settings [POST]
- save_abcde_settings [POST]
- save_apprise_cfg [POST]
- systeminfo [POST]
- systemdrivescan [GET]
- update_arm [POST]
- drive_eject [GET]
- testapprise [GET]
"""

import os
import platform
import importlib
import re
import subprocess

from flask_login import LoginManager, login_required, \
    current_user, login_user, UserMixin, logout_user  # noqa: F401
from flask import render_template, request, flash, \
    redirect, Blueprint

import arm.ui.utils as ui_utils
from arm.ui import app, db
from arm.models.job import Job
from arm.models.system_drives import SystemDrives
from arm.models.system_info import SystemInfo
from arm.models.ui_settings import UISettings
import arm.config.config as cfg
from arm.ui.settings import DriveUtils
from arm.ui.forms import SettingsForm, UiSettingsForm, AbcdeForm, SystemInfoDrives
from arm.ui.settings.ServerUtil import ServerUtil
import arm.ripper.utils as ripper_utils

route_settings = Blueprint('route_settings', __name__,
                           template_folder='templates',
                           static_folder='../static')

# Page definitions
page_settings = "settings/settings.html"
redirect_settings = "/settings"


@route_settings.route('/settings')
@login_required
def settings():
    """
    Page - settings
    Method - GET
    Overview - allows the user to update the all configs of A.R.M without
    needing to open a text editor
    """
    global page_settings

    # stats for info page
    with open(os.path.join(cfg.arm_config["INSTALLPATH"], 'VERSION')) as version_file:
        version = version_file.read().strip()
    failed_rips = Job.query.filter_by(status="fail").count()
    total_rips = Job.query.filter_by().count()
    movies = Job.query.filter_by(video_type="movie").count()
    series = Job.query.filter_by(video_type="series").count()
    cds = Job.query.filter_by(disctype="music").count()

    stats = {'python_version': platform.python_version(),
             'arm_version': version,
             'git_commit': ui_utils.get_git_revision_hash(),
             'movies_ripped': movies,
             'series_ripped': series,
             'cds_ripped': cds,
             'no_failed_jobs': failed_rips,
             'total_rips': total_rips,
             'updated': ui_utils.git_check_updates(ui_utils.get_git_revision_hash()),
             'hw_support': check_hw_transcode_support()
             }

    # ARM UI config
    armui_cfg = ui_utils.arm_db_cfg()

    # System details in class server
    server = SystemInfo.query.filter_by(id="1").first()
    serverutil = ServerUtil()

    # System details in class server
    arm_path = cfg.arm_config['TRANSCODE_PATH']
    media_path = cfg.arm_config['COMPLETED_PATH']

    # form_drive = SystemInfoDrives(request.form)
    # System Drives (CD/DVD/Blueray drives)
    drives = DriveUtils.drives_check_status()

    # Load up the comments.json, so we can comment the arm.yaml
    comments = ui_utils.generate_comments()
    form = SettingsForm()

    return render_template(page_settings, settings=cfg.arm_config, ui_settings=armui_cfg,
                           stats=stats, apprise_cfg=cfg.apprise_config,
                           form=form, jsoncomments=comments, abcde_cfg=cfg.abcde_config,
                           server=server, serverutil=serverutil, arm_path=arm_path, media_path=media_path,
                           drives=drives, form_drive=False)


def check_hw_transcode_support():
    cmd = f"nice {cfg.arm_config['HANDBRAKE_CLI']}"

    app.logger.debug(f"Sending command: {cmd}")
    hw_support_status = {
        "nvidia": False,
        "intel": False,
        "amd": False
    }
    try:
        hand_brake_output = subprocess.run(f"{cmd}", capture_output=True, shell=True, check=True)

        # NVENC
        if re.search(r'nvenc: version ([0-9\\.]+) is available', str(hand_brake_output.stderr)):
            app.logger.info("NVENC supported!")
            hw_support_status["nvidia"] = True
        # Intel QuickSync
        if re.search(r'qsv:\sis(.*?)available\son', str(hand_brake_output.stderr)):
            app.logger.info("Intel QuickSync supported!")
            hw_support_status["intel"] = True
        # AMD VCN
        if re.search(r'vcn:\sis(.*?)available\son', str(hand_brake_output.stderr)):
            app.logger.info("AMD VCN supported!")
            hw_support_status["amd"] = True
        app.logger.info("Handbrake call successful")
        # Dump the whole CompletedProcess object
        app.logger.debug(hand_brake_output)
    except subprocess.CalledProcessError as hb_error:
        err = f"Call to handbrake failed with code: {hb_error.returncode}({hb_error.output})"
        app.logger.error(err)
    return hw_support_status


@route_settings.route('/save_settings', methods=['POST'])
@login_required
def save_settings():
    """
    Page - save_settings
    Method - POST
    Overview - Save arm ripper settings from post. Not a user page
    """
    # Load up the comments.json, so we can comment the arm.yaml
    comments = ui_utils.generate_comments()
    success = False
    arm_cfg = {}
    form = SettingsForm()
    if form.validate_on_submit():
        # Build the new arm.yaml with updated values from the user
        arm_cfg = ui_utils.build_arm_cfg(request.form.to_dict(), comments)
        # Save updated arm.yaml
        with open(cfg.arm_config_path, "w") as settings_file:
            settings_file.write(arm_cfg)
            settings_file.close()
        success = True
        importlib.reload(cfg)
    # If we get to here there was no post data
    return {'success': success, 'settings': cfg.arm_config, 'form': 'arm ripper settings'}


@route_settings.route('/save_ui_settings', methods=['POST'])
@login_required
def save_ui_settings():
    """
    Page - save_ui_settings
    Method - POST
    Overview - Save 'UI Settings' page settings to database. Not a user page
    Notes - This function needs to trigger a restart of flask for
        debugging to update the values
    """
    form = UiSettingsForm()
    success = False
    arm_ui_cfg = UISettings.query.get(1)
    if form.validate_on_submit():
        use_icons = (str(form.use_icons.data).strip().lower() == "true")
        save_remote_images = (str(form.save_remote_images.data).strip().lower() == "true")
        arm_ui_cfg.index_refresh = format(form.index_refresh.data)
        arm_ui_cfg.use_icons = use_icons
        arm_ui_cfg.save_remote_images = save_remote_images
        arm_ui_cfg.bootstrap_skin = format(form.bootstrap_skin.data)
        arm_ui_cfg.language = format(form.language.data)
        arm_ui_cfg.database_limit = format(form.database_limit.data)
        arm_ui_cfg.notify_refresh = format(form.notify_refresh.data)
        db.session.commit()
        success = True
    # Masking the jinja update, otherwise an error is thrown
    # sqlalchemy.orm.exc.DetachedInstanceError: Instance <UISettings at 0x7f294c109fd0>
    # app.jinja_env.globals.update(armui_cfg=arm_ui_cfg)
    return {'success': success, 'settings': str(arm_ui_cfg), 'form': 'arm ui settings'}


@route_settings.route('/save_abcde_settings', methods=['POST'])
@login_required
def save_abcde():
    """
    Page - save_abcde_settings
    Method - POST
    Overview - Save 'abcde Config' page settings to database. Not a user page
    """
    success = False
    abcde_cfg_str = ""
    form = AbcdeForm()
    if form.validate():
        app.logger.debug(f"routes.save_abcde: Saving new abcde.conf: {cfg.abcde_config_path}")
        abcde_cfg_str = str(form.abcdeConfig.data).strip()
        # Windows machines can put \r\n instead of \n newlines, which corrupts the config file
        clean_abcde_str = '\n'.join(abcde_cfg_str.splitlines())
        # Save updated abcde.conf
        with open(cfg.abcde_config_path, "w") as abcde_file:
            abcde_file.write(clean_abcde_str)
            abcde_file.close()
        success = True
        # Update the abcde config
        cfg.abcde_config = clean_abcde_str
    # If we get to here there was no post data
    return {'success': success, 'settings': clean_abcde_str, 'form': 'abcde config'}


@route_settings.route('/save_apprise_cfg', methods=['POST'])
@login_required
def save_apprise_cfg():
    """
    Page - save_apprise_cfg
    Method - POST
    Overview - Save 'Apprise Config' page settings to database. Not a user page
    """
    success = False
    # Since we can't be sure of any values, we can't validate it
    if request.method == 'POST':
        # Save updated apprise.yaml
        # Build the new arm.yaml with updated values from the user
        apprise_cfg = ui_utils.build_apprise_cfg(request.form.to_dict())
        with open(cfg.apprise_config_path, "w") as settings_file:
            settings_file.write(apprise_cfg)
            settings_file.close()
        success = True
        importlib.reload(cfg)
    # If we get to here there was no post data
    return {'success': success, 'settings': cfg.apprise_config, 'form': 'Apprise config'}


@route_settings.route('/systeminfo', methods=['POST'])
@login_required
def server_info():
    """
    Page - systeminfo
    Method - POST
    Overview - Save 'System Info' page settings to database. Not a user page
    """
    global redirect_settings

    # System Drives (CD/DVD/Blueray drives)
    form_drive = SystemInfoDrives(request.form)
    if request.method == 'POST' and form_drive.validate():
        # Return for POST
        app.logger.debug(
            "Drive id: " + str(form_drive.id.data) +
            " Updated db description: " + form_drive.description.data)
        drive = SystemDrives.query.filter_by(drive_id=form_drive.id.data).first()
        drive.description = str(form_drive.description.data).strip()
        db.session.commit()
        # Return to systeminfo page (refresh page)
        return redirect(redirect_settings)
    else:
        # Return for GET
        return redirect(redirect_settings)


@route_settings.route('/systemdrivescan')
def system_drive_scan():
    """
    Page - systemdrivescan
    Method - GET
    Overview - Scan for the system drives and update the database.
    """
    global redirect_settings
    # Update to scan for changes from system
    new_count = DriveUtils.drives_update()
    flash(f"ARM found {new_count} new drives", "success")
    return redirect(redirect_settings)


@route_settings.route('/update_arm', methods=['POST'])
@login_required
def update_git():
    """Update arm via git command line"""
    return ui_utils.git_get_updates()


@route_settings.route('/driveeject/<id>')
@login_required
def drive_eject(id):
    """
    Server System  - change state of CD/DVD/BluRay drive - toggle eject
    """
    global redirect_settings
    drive = SystemDrives.query.filter_by(drive_id=id).first()
    drive.open_close()
    db.session.commit()
    return redirect(redirect_settings)


@route_settings.route('/testapprise')
def testapprise():
    """
    Page - testapprise
    Method - GET
    Overview - Send a test notification to Apprise.
    """
    global redirect_settings
    # Send a sample notification
    ripper_utils.notify("/dev/null", "ARM notification", "This is a notification by the ARM-Notification Test!")
    flash("Test notification sent ", "success")
    return redirect(redirect_settings)
