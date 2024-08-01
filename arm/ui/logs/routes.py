"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Logs

Covers
    - logs [GET]
    - listlogs [GET]
    - logreader [GET]
"""
import os
from pathlib import Path
from flask_login import login_required
from flask import render_template, request, send_file, session
from werkzeug.routing import ValidationError
from flask import current_app as app

from arm.ui.logs import route_logs
import arm.config.config as cfg
from arm.ui.logs import utils


@route_logs.route('/logs')
@login_required
def logs():
    """
    Flask view:
        /logs

    Returns a log view in one of the following formats
    tail: Output to browser in real time. Similar to 'tail -f'
    arm: Static output of just the ARM log entries
    full: Static output of all of the log including MakeMKV and HandBrake
    download: Download the full log file

    Input (GET):
        mode - tail, arm, full
        logfile - name of the file
    """

    mode = request.args['mode']
    logfile = request.args['logfile']
    session["page_title"] = "Logs"

    return render_template('logview.html',
                           file=logfile,
                           mode=mode)


@route_logs.route('/listlogs', defaults={'path': ''})
@login_required
def list_logs(path):
    """
    Flask view:
        /listlogs

    The 'View logs' page - shows a list of logfiles in the log folder with creation time and size
    Gives the user links to tail/arm/Full/download

    Input:
        None
    """
    base_path = cfg.arm_config['LOGPATH']
    full_path = str(os.path.join(base_path, path))
    session["page_title"] = "Logs"

    # Deal with bad data
    if not os.path.exists(full_path):
        raise ValidationError

    # Get all files in directory
    files = utils.get_info(full_path)

    return render_template('logfiles.html',
                           files=files,
                           date_format=cfg.arm_config['DATE_FORMAT'])


@route_logs.route('/logreader')
@login_required
def logreader():
    """
    Flask view:
        /logreader

    The default logreader output function
    This will display or allow downloading the requested logfile
    This is where the XHR requests are sent when viewing /logs?=logfile

    Returns a log view in one of the following formats
    tail: Output to browser in real time. Similar to 'tail -f'
    arm: Static output of just the ARM log entries
    full: Static output of all of the log including MakeMKV and HandBrake
    download: Download the full log file

    Input (Get):
        mode - download
        logfile - name of the file
    """
    log_path = cfg.arm_config['LOGPATH']
    mode = request.args.get('mode')
    session["page_title"] = "Logs"

    # We should use the job id and not get the raw logfile from the user
    # Maybe search database and see if we can match the logname with a previous rip ?
    full_path = os.path.join(log_path, request.args.get('logfile'))
    app.logger.debug(f"Generating full log from: {full_path}")
    utils.validate_logfile(request.args.get('logfile'), mode, Path(full_path))

    # Only ARM logs
    if mode == "armcat":
        generate = utils.generate_arm_cat(full_path)
    # Give everything / Tail
    elif mode == "full":
        generate = utils.generate_full_log(full_path)
    elif mode == "download":
        return send_file(full_path, as_attachment=True)
    else:
        # No mode - error out
        raise ValidationError

    return app.response_class(generate,
                              mimetype='text/plain')
