"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Main

Covers
    - index [GET]
    - dbupdate [POST]
"""
import flask
from flask import current_app as app
from flask import render_template, session
from flask_login import login_required

import config.config as cfg
import ui.settings.ServerUtil
from models.system_info import SystemInfo
from models.ui_settings import UISettings
from ui.settings.routes import check_hw_transcode_support


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

    # Push out HW transcode status for homepage
    stats = {'hw_support': check_hw_transcode_support()}

    # System details in class server
    server = SystemInfo.query.filter_by(id="1").first()
    serverutil = ui.settings.ServerUtil.ServerUtil()

    # System details in class server
    arm_path = cfg.arm_config['TRANSCODE_PATH']
    media_path = cfg.arm_config['COMPLETED_PATH']

    # Page titles
    session["arm_name"] = cfg.arm_config['ARM_NAME']
    session["page_title"] = "Home"

    # if os.path.isfile(cfg.arm_config['DBFILE']):
    #     jobs = {}
    #     # try:
    #     #     jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()
    #     # except Exception:
    #     #     # db isn't setup
    #     #     return redirect(url_for('setup'))
    # else:
    jobs = {}

    response = flask.make_response(render_template("index.html",
                                                   jobs=jobs,
                                                   children=cfg.arm_config['ARM_CHILDREN'],
                                                   server=server,
                                                   serverutil=serverutil,
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
