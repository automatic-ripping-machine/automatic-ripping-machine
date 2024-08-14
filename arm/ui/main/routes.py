"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Main

Covers
    - index [GET]
    - dbupdate [POST]
"""
import flask
from flask import current_app as app
from flask import render_template, session, redirect
from flask_login import login_required

import config.config as cfg
from ui import db
from ui.main.forms import SystemInfoLoad
from ui.settings.ServerUtil import ServerUtil
from ui.settings.routes import check_hw_transcode_support
from models.system_info import SystemInfo
from models.ui_settings import UISettings


@app.route('/')
@app.route('/index.html')
@app.route('/index')
@login_required
def home():
    """
    The main homepage showing current rips and server stats
    """
    # Set UI Config values for cookies
    # the database should be available and data loaded by this point
    try:
        armui_cfg = UISettings.query.filter_by().first()
    except Exception as error:
        return render_template('error.html', error=error)

    # Check if system info is populated, otherwise go to system setup
    server = SystemInfo.query.filter_by().first()
    server_util = ServerUtil()
    if not server:
        return redirect('/systemsetup')

    # Push out HW transcode status for homepage
    stats = {'hw_support': check_hw_transcode_support()}

    # System details in class server
    arm_path = cfg.arm_config['TRANSCODE_PATH']
    media_path = cfg.arm_config['COMPLETED_PATH']

    # Page titles
    session["arm_name"] = cfg.arm_config['ARM_NAME']
    session["page_title"] = "Home"

    jobs = {}

    response = flask.make_response(render_template("index.html",
                                                   jobs=jobs,
                                                   children=cfg.arm_config['ARM_CHILDREN'],
                                                   server=server,
                                                   serverutil=server_util,
                                                   arm_path=arm_path,
                                                   media_path=media_path,
                                                   stats=stats))
    # remove the unused cookies if not required by other functions/pages
    # response.set_cookie("use_icons", value=f"{armui_cfg.use_icons}")
    # response.set_cookie("save_remote_images", value=f"{armui_cfg.save_remote_images}")
    # response.set_cookie("bootstrap_skin", value=f"{armui_cfg.bootstrap_skin}")
    # response.set_cookie("language", value=f"{armui_cfg.language}")
    response.set_cookie("index_refresh", value=f"{armui_cfg.index_refresh}")
    # response.set_cookie("database_limit", value=f"{armui_cfg.database_limit}")
    # response.set_cookie("notify_refresh", value=f"{armui_cfg.notify_refresh}")
    return response


@app.route('/systemsetup', methods=['GET', 'POST'])
@login_required
def system_info_load():
    """
    Load system initial system info
    """
    form = SystemInfoLoad()

    if form.validate_on_submit():
        app.logger.debug("*******SystemInfo*******")
        app.logger.debug(f"name: {str(form.name.data)}")
        app.logger.debug(f"cpu: {str(form.cpu.data)}")
        app.logger.debug(f"description: {str(form.description.data)}")
        app.logger.debug(f"mem_total: {str(form.mem_total.data)}")
        app.logger.debug("************************")

        system_info = SystemInfo(name=str(form.name.data),
                                 description=str(form.description.data))
        system_info.cpu = str(form.cpu.data)
        system_info.mem_total = form.mem_total.data
        db.session.add(system_info)
        db.session.commit()

        return redirect("/index")

    server_util = ServerUtil()
    return render_template("systemsetup.html",
                           form=form,
                           server_util=server_util)
