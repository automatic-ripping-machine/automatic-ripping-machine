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
- drive_remove [GET]
- testapprise [GET]
- updatesysinfo [GET]
"""
import platform
import importlib
import re
import subprocess
from datetime import datetime
import os

import sqlalchemy

from flask_login import login_required, \
    current_user, login_user, UserMixin, logout_user  # noqa: F401
from flask import render_template, request, flash, \
    redirect, Blueprint, session, url_for, jsonify, Response
from wtforms import Form
from typing import Optional

import arm.ui.utils as ui_utils
from arm.ui import app, db
from arm.models.job import Job
from arm.models.system_drives import SystemDrives
from arm.models.system_info import SystemInfo
from arm.models.ui_settings import UISettings
import arm.config.config as cfg
from arm.ui.settings import DriveUtils as drive_utils
from arm.ui.forms import SettingsFormFunction, UiSettingsForm, AbcdeForm, SystemInfoDrives
from arm.ui.settings.ServerUtil import ServerUtil
import arm.ripper.utils as ripper_utils

route_settings = Blueprint('route_settings', __name__,
                           template_folder='templates',
                           static_folder='../static')
REDIRECT_SETTINGS = "route_settings.settings"


def mask_last(value: str, n: int = 4):
    """
    Replaces the last `n` characters of a string with asterisks.
    """
    if not isinstance(value, str):
        return value
    return value[:-n] + '*' * n if len(value) > n else '*' * len(value)


def populate_form_fields(form: Form, data: Optional[dict[str, str]], titles: Optional[dict[str, str]] = None):
    """
    Populates a WTForms form with data from a dictionary.
    """
    starter = "Field "
    ender = "has value with value: "
    # Set the nicer attributes for the form.
    if titles is not None:
        if isinstance(data, dict):
            app.logger.debug(f"Titles were provided. Populating form with {len(form._fields)} fields,\
                              data is type{type(data)}, titles are {type(titles)} ")
            for field_name, field in form._fields.items():
                if field_name == 'submit':
                    continue
                else:
                    if field_name in data:
                        field.data = data[field_name]
                    else:
                        app.logger.debug(f"Field {field_name} not found in data dict")
                    if field_name in titles:
                        field.render_kw = {'title': titles[field_name]}
                        app.logger.debug(f"{starter}{field_name} {ender}{field.data} ")
                    else:
                        app.logger.debug(f"Title for field {field_name} not found in titles dict")
            return form

        app.logger.debug(f"Titles were provided. Populating form with {len(form._fields)} fields, \
                            data is type{type(data)}, titles are {type(titles)} ")
        for field_name, field in form._fields.items():
            if field_name == 'submit':
                continue
            else:
                if not hasattr(data, field_name):
                    app.logger.debug(f"Field {field_name} not found in data object")
                    continue
                field.data = getattr(data, field_name)
                field.render_kw = {'title': titles[field_name]}
                app.logger.debug(f"{starter}{field_name} {ender}{field.data} ")
        return form

    app.logger.debug(f"No TITLES provided Populating form with {len(form._fields)} fields")
    for field_name, field in form._fields.items():
        if field_name == 'submit':
            continue
        else:
            if not hasattr(data, field_name):
                app.logger.debug(f"Field {field_name} not found in data object")
                continue
            field.data = getattr(data, field_name)
            app.logger.debug(f" {starter}{field_name} {ender}{field.data} ")
    return form


route_settings.add_app_template_filter(mask_last, name='mask_last')


@route_settings.route('/settings')
@login_required
def settings():
    """
    Page - settings
    Method - GET
    Overview - allows the user to update the all configs of A.R.M without
    needing to open a text editor
    """

    # stats for info page
    failed_rips = Job.query.filter_by(status="fail").count()
    total_rips = Job.query.filter_by().count()
    movies = Job.query.filter_by(video_type="movie").count()
    series = Job.query.filter_by(video_type="series").count()
    cds = Job.query.filter_by(disctype="music").count()

    # Get the current server time and timezone
    server_timezone = os.environ.get("TZ", "Etc/UTC")
    current_time = datetime.now()
    server_datetime = current_time.strftime(cfg.arm_config['DATE_FORMAT'])
    [arm_version_local, arm_version_remote] = ui_utils.git_check_version()
    local_git_hash = ui_utils.get_git_revision_hash()

    stats = {'server_datetime': server_datetime,
             'server_timezone': server_timezone,
             'python_version': platform.python_version(),
             'arm_version_local': arm_version_local,
             'arm_version_remote': arm_version_remote,
             'git_commit': local_git_hash,
             'movies_ripped': movies,
             'series_ripped': series,
             'cds_ripped': cds,
             'no_failed_jobs': failed_rips,
             'total_rips': total_rips,
             'updated': ui_utils.git_check_updates(local_git_hash),
             'hw_support': check_hw_transcode_support()
             }
    # Load up the comments.json, so we can comment the arm.yaml
    # jsoncomments is used by all config fields
    comments = ui_utils.generate_comments()
    # ARM UI config
    armui_cfg = ui_utils.arm_db_cfg()
    ui_form = UiSettingsForm()
    # Set the nicer attributes for the UI settings form.
    ui_form = UiSettingsForm()
    for field_name, field in ui_form._fields.items():
        if field_name == 'submit':
            break
        else:
            field.data = getattr(armui_cfg, field_name)
            field.render_kw = {'title': comments[field_name]}
            app.logger.debug(f"Field {field_name} has value with value: {field.data}")
    # Get system details from Server Info and Config
    server = SystemInfo.query.filter_by(id="1").first()
    serverutil = ServerUtil()
    arm_path = cfg.arm_config['TRANSCODE_PATH']
    media_path = cfg.arm_config['COMPLETED_PATH']
    # System Drives (CD/DVD/Blueray drives)
    drive_utils.update_job_status()
    drives = drive_utils.get_drives()
    drive_utils.update_tray_status(drives)
    form_drive = SystemInfoDrives(request.form)
    # Build the dynamic form for the ripper settings
    form = SettingsFormFunction(comments=comments)
    # now go through all teh arm config keys and set the form fields.data
    for key, value in cfg.arm_config.items():
        field = getattr(form, key, None)
        if field:
            app.logger.debug(f"Config key: {key} resolved to field: {field.name}")
            field.data = value
    session["page_title"] = "Settings"
    app.logger.debug(f"stats: {stats}")
    return render_template(
        "settings/settings.html",
        settings=cfg.arm_config,
        ui_settings=ui_form,
        stats=stats,
        apprise_cfg=cfg.apprise_config,
        form=form,
        jsoncomments=comments,
        abcde_cfg=cfg.abcde_config,
        server=server,
        serverutil=serverutil,
        arm_path=arm_path,
        media_path=media_path,
        drives=drives,
        form_drive=form_drive
        )  # type: ignore


@route_settings.route('/help')
@login_required
def help_page():
    """
    Page - help_page
    Method - GET
    Overview - page with links to help locations
    """
    session["page_title"] = "help page"
    return render_template(
        "settings/help.html"
        )  # type: ignore


@route_settings.route('/general_settings')
@login_required
def settings_general():
    """
    Page - General Settings
    Method - GET
    Overview - Mostly drives and statistical information.
    TODO: Really shoudl include a web based system to update ARM in this section
    """

    # stats for info page
    failed_rips = Job.query.filter_by(status="fail").count()
    total_rips = Job.query.filter_by().count()
    movies = Job.query.filter_by(video_type="movie").count()
    series = Job.query.filter_by(video_type="series").count()
    cds = Job.query.filter_by(disctype="music").count()

    # Get the current server time and timezone
    server_timezone = os.environ.get("TZ", "Etc/UTC")
    current_time = datetime.now()
    server_datetime = current_time.strftime(cfg.arm_config['DATE_FORMAT'])
    [arm_version_local, arm_version_remote] = ui_utils.git_check_version()
    local_git_hash = ui_utils.get_git_revision_hash()

    stats = {'server_datetime': server_datetime,
             'server_timezone': server_timezone,
             'python_version': platform.python_version(),
             'arm_version_local': arm_version_local,
             'arm_version_remote': arm_version_remote,
             'git_commit': local_git_hash,
             'movies_ripped': movies,
             'series_ripped': series,
             'cds_ripped': cds,
             'no_failed_jobs': failed_rips,
             'total_rips': total_rips,
             'updated': ui_utils.git_check_updates(local_git_hash),
             'hw_support': check_hw_transcode_support()
             }
    # System Drives (CD/DVD/Blueray drives)
    drive_utils.update_job_status()
    drives = drive_utils.get_drives()
    drive_utils.update_tray_status(drives)
    session["page_title"] = "General Settings and Drives"
    return render_template(
        "settings/general.html",
        stats=stats,
        drives=drives
        )  # type: ignore


@route_settings.route('/abcde_settings')
@login_required
def settings_abcde():
    """
    Page - settings
    Method - GET
    Overview - allows the user to update the all configs of A.R.M without
    needing to open a text editor
    """
    # app.logger.debug(app.config)
    # form.abcdeConfig.data = cfg.abcde_config
    abcde_record = cfg.abcde_config
    # load the abcde config into the form
    form = AbcdeForm(abcdeConfig=abcde_record)
    session["page_title"] = "Music Ripping - ABCDE Settings"
    return render_template(
        "settings/dynamic_form.html",
        form=form,
        )  # type: ignore


@route_settings.route('/ui_settings')
@login_required
def settings_ui():
    """
    Page - Settings - UI
    Method - GET
    Overview - Allow user to change UI Specfic settings
    """

    # Load up the comments.json, so we can comment the arm.yaml
    # jsoncomments is used by all config fields
    comments = ui_utils.generate_comments()
    # ARM UI config
    armui_cfg = ui_utils.arm_db_cfg()
    ui_form = UiSettingsForm()
    # Set the nicer attributes for the UI settings form.
    ui_form = populate_form_fields(ui_form, armui_cfg, comments)
    session["page_title"] = "UI Settings"
    return render_template(
        "settings/dynamic_form.html",
        form=ui_form
        )  # type: ignore


@route_settings.route('/ripper_settings')
@login_required
def settings_ripper():
    """
    Page - ripper_settings
    Method - GET
    Overview - allows the user to update arm.yaml
    needing to open a text editor
    """

    # Build the dynamic form for the ripper settings
    comments:dict[str, str] = ui_utils.generate_comments()
    form = SettingsFormFunction(comments)
    app.logger.debug(f"Ripper settings form created with {len(form._fields)} fields")
    form = populate_form_fields(form, cfg.arm_config, comments)
    app.logger.debug(f"Ripper settings form populated with {len(form.__dict__)} fields")
    session["page_title"] = "Ripper Settings"
    
    return render_template(
        "settings/dynamic_form.html",
        form=form
        )  # type: ignore


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

###############################################################################
##  POST routes below here
###############################################################################

@route_settings.route('/save_arm_settings', methods=['POST'])
@login_required
def save_settings():
    """
    Page - save_settings
    Method - POST
    Overview - Save arm ripper settings from post. Not a user page
    This function writes to arm.yaml
    """
    # Load up the comments.json, so we can comment the arm.yaml
    app.logger.info("Saving ARM Ripper settings")
    comments = ui_utils.generate_comments()
    task_success = False
    arm_cfg = {}
    form_name = "arm ripper settings"
    app.logger.debug("Generating a temporary instance of SettingsForm")
    form = SettingsFormFunction(comments=comments)
    if form.validate_on_submit():
        app.logger.debug("Saving Ripper settings")
        # Build the new arm.yaml with updated values from the user
        arm_cfg = ui_utils.build_arm_cfg(form_data=request.form.to_dict(), comments=comments)
        app.logger.debug(f"Cleansed Form Data: \r\n{arm_cfg}")
        try:
            # Save updated arm.yaml
            app.logger.debug(f"routes.save_settings: Saving new arm.yaml: {cfg.arm_config_path}")
            with open(cfg.arm_config_path, "w", encoding="utf-8") as settings_file:
                settings_file.write(arm_cfg)
            task_success = True
        except Exception as e:
            exception_msg = f"Error saving arm.yaml: {e}"
            app.logger.exception(exception_msg)
            flash(exception_msg, "error")
            return {'error': True, 'errors': str(exception_msg), 'form': form_name}
        importlib.reload(cfg)
        # Set the ARM Log level to the config
        app.logger.info(f"Setting log level to: {cfg.arm_config['LOGLEVEL']}")
        app.logger.setLevel(cfg.arm_config['LOGLEVEL'])
        return jsonify({'success': task_success, 'settings': cfg.arm_config, 'form': form_name})
    else:
        # form is not valid
        fields_errors = {field: errs for field, errs in form.errors.items()}
        app.logger.error(f"Error validating form: {form.errors}, I found these errors: {fields_errors}")
        flash(f"Error validating form: {form.errors}", "error")
        return jsonify({'error': True, 'message':"Validation Failed", 'errors': fields_errors})


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
    ui_form = UiSettingsForm()
    form_name = 'arm ui settings'
    success = False
    arm_ui_cfg = UISettings.query.get(1)
    if ui_form.validate_on_submit():
        # use_icons = (str(ui_form.use_icons.data).strip().lower() == "true")
        # save_remote_images = (str(ui_form.save_remote_images.data).strip().lower() == "true")
        arm_ui_cfg.index_refresh = format(ui_form.index_refresh.data)
        arm_ui_cfg.use_icons = bool(str(ui_form.use_icons.data).strip().lower())
        arm_ui_cfg.save_remote_images = bool(str(ui_form.save_remote_images.data).strip().lower())
        arm_ui_cfg.bootstrap_skin = format(ui_form.bootstrap_skin.data)
        arm_ui_cfg.language = format(ui_form.language.data)
        arm_ui_cfg.database_limit = format(ui_form.database_limit.data)
        arm_ui_cfg.notify_refresh = format(ui_form.notify_refresh.data)
        try:
            db.session.commit()
            success = True
            # Masking the jinja update, otherwise an error is thrown
            # sqlalchemy.orm.exc.DetachedInstanceError: Instance <UISettings at 0x7f294c109fd0>
            app.jinja_env.globals.update(armui_cfg=arm_ui_cfg)
            return {'success': success, 'settings': str(arm_ui_cfg), 'form': form_name}
        except Exception as e:
            err_msg = f"Error validating form: {ui_form.errors} because {e}"
            app.logger.error(err_msg)
            return {'error': True, 'errors': str(err_msg), 'form': form_name}
    else:
        fields_errors = {field: errs for field, errs in ui_form.errors.items()}
        app.logger.error(f"Error validating form: {ui_form.errors}, I found these errors: {fields_errors}")
        return jsonify({'error': True, 'message':"Validation Failed", 'errors': fields_errors})


@route_settings.route('/save_abcde_settings', methods=['POST'])
@login_required
def save_abcde():
    """
    Page - save_abcde_settings
    Method - POST
    Overview - Save 'abcde Config' page settings to the database. Not a user page
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
        success = True
        # Update the abcde config
        cfg.abcde_config = clean_abcde_str

    # If we get to here, there was no post-data
    return {'success': success,
            'settings': clean_abcde_str,
            'form': 'abcde config'}


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
    # System Drives (CD/DVD/Blueray drives)
    form_drive = SystemInfoDrives(request.form)
    if request.method == 'POST' and form_drive.validate():
        # Return for POST
        app.logger.debug(
            f"Drive id: {str(form_drive.id.data)} " +
            f"Updated name: {str(form_drive.name.data)} " +
            f"Updated description: [{str(form_drive.description.data)}] " +
            f"Updated mode: [{str(form_drive.drive_mode.data)}]")
        drive = SystemDrives.query.filter_by(drive_id=form_drive.id.data).first()
        drive.description = str(form_drive.description.data).strip()
        drive.name = str(form_drive.name.data).strip()
        drive.drive_mode = str(form_drive.drive_mode.data).strip()
        db.session.commit()
        flash(f"Updated Drive {drive.name} details", "success")
        # Return to the systeminfo page (refresh page)
        return redirect(url_for(REDIRECT_SETTINGS))
    else:
        flash("Error: Unable to update drive details", "error")
        # Return for GET
        return redirect(url_for(REDIRECT_SETTINGS))


@route_settings.route('/systemdrivescan')
def system_drive_scan():
    """
    Page - systemdrivescan
    Method - GET
    Overview - Scan for the system drives and update the database.
    """
    # Update to scan for changes to the ripper system
    new_count = drive_utils.drives_update()
    flash(f"ARM found {new_count} new drives", "success")
    return redirect(url_for(REDIRECT_SETTINGS))


@route_settings.route('/drive/eject/<eject_id>')
@login_required
def drive_eject(eject_id):
    """
    Server System - change state of CD/DVD/BluRay drive - toggle eject status
    """
    try:
        drive = SystemDrives.query.filter_by(drive_id=eject_id).one()
    except sqlalchemy.exc.NoResultFound as e:
        app.logger.error(f"Drive eject encountered an error: {e}")
        flash(f"Cannot find drive {eject_id} in database.", "error")
        return redirect(url_for(REDIRECT_SETTINGS))
    # block for running jobs
    if drive.job_id_current:
        drive.tray_status()  # update tray status
        if not drive.open:  # allow closing
            flash(f"Job [{drive.job_id_current}] in progress. Cannot eject {eject_id}.", "error")
            return redirect(url_for(REDIRECT_SETTINGS))
    # toggle open/close (with non-critical error)
    if (error := drive.eject(method="toggle", logger=app.logger)) is not None:
        flash(error, "error")
    return redirect(url_for(REDIRECT_SETTINGS))


@route_settings.route('/drive/remove/<remove_id>')
@login_required
def drive_remove(remove_id):
    """
    Server System - remove a drive from the ARM UI
    """
    try:
        app.logger.debug(f"Removing drive {remove_id}")
        drive = SystemDrives.query.filter_by(drive_id=remove_id).first()
        dev_path = drive.mount
        SystemDrives.query.filter_by(drive_id=remove_id).delete()
        db.session.commit()
        flash(f"Removed drive [{dev_path}] from ARM", "success")
    except Exception as e:
        app.logger.error(f"Drive removal encountered an error: {e}")
        flash("Drive unable to be removed, check logs for error", "error")
    return redirect(url_for(REDIRECT_SETTINGS))


@route_settings.route('/drive/manual/<manual_id>')
@login_required
def drive_manual(manual_id):
    """
    Manually start a job on ARM
    """

    drive = SystemDrives.query.filter_by(drive_id=manual_id).first()
    dev_path = drive.mount.lstrip('/dev/')

    cmd = f"/opt/arm/scripts/docker/docker_arm_wrapper.sh {dev_path}"
    app.logger.debug(f"Running command[{cmd}]")

    # Manually start ARM if the udev rules are not working for some reason
    try:
        manual_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = manual_process.communicate()

        if manual_process.returncode != 0:
            raise subprocess.CalledProcessError(manual_process.returncode, cmd, output=stdout, stderr=stderr)

        message = f"Manually starting a job on Drive: '{drive.name}'"
        status = "success"
        app.logger.debug(stdout)

    except subprocess.CalledProcessError as e:
        message = f"Failed to start a job on Drive: '{drive.name}' See logs for info"
        status = "danger"
        app.logger.error(message)
        app.logger.error(f"error: {e}")
        app.logger.error(f"stdout: {e.output}")
        app.logger.error(f"stderr: {e.stderr}")

    flash(message, status)
    return redirect('/settings')


@route_settings.route('/testapprise')
def testapprise():
    """
    Page - testapprise
    Method - GET
    Overview - Send a test notification to Apprise.
    """
    # Send a sample notification
    message = "This is a notification by the ARM-Notification Test!"
    if cfg.arm_config["UI_BASE_URL"] and cfg.arm_config["WEBSERVER_PORT"]:
        message = message + f" Server URL: http://{cfg.arm_config['UI_BASE_URL']}:{cfg.arm_config['WEBSERVER_PORT']}"
    ripper_utils.notify(None, "ARM notification", message)
    flash("Test notification sent ", "success")
    return redirect(url_for(REDIRECT_SETTINGS))


@route_settings.route('/updatesysinfo')
def update_sysinfo():
    """
    Update system information
    """
    # Get current system information from database
    current_system = SystemInfo.query.first()
    # Query system for new information
    new_system = SystemInfo()

    app.logger.debug("****** System Information ******")
    if current_system is not None:
        app.logger.debug(f"Name old [{current_system.name}] new [{new_system.name}]")
        app.logger.debug(f"Name old [{current_system.cpu}] new [{new_system.cpu}]")
        app.logger.debug(f"Name old [{current_system.mem_total}] new [{new_system.mem_total}]")
        current_system.name = new_system.name
        current_system.cpu = new_system.cpu
        current_system.mem_total = new_system.mem_total
        db.session.add(current_system)
    else:
        app.logger.debug(f"Name old [No Info] new [{new_system.name}]")
        app.logger.debug(f"Name old [No Info] new [{new_system.cpu}]")
        app.logger.debug(f"Name old [No Info] new [{new_system.mem_total}]")
        db.session.add(new_system)

    app.logger.debug("****** End System Information ******")
    app.logger.info(f"Updated CPU Details with new info - {new_system.name} - {new_system.cpu} - "
                    f"{new_system.mem_total}")

    db.session.commit()

    return redirect(url_for(REDIRECT_SETTINGS))
