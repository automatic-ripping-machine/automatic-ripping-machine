"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    History

Covers
    - history [GET]
"""
from flask_login import login_required
from flask import render_template, request, session, flash
from sqlalchemy import desc, exc
from flask import current_app as app

from arm.ui.history import route_history
import arm.config.config as cfg
from arm.models.ui_settings import UISettings
from arm.models.job import Job


@route_history.route('/history')
@login_required
def history():
    """
    Flask view:
        /history

    Smaller much simpler output of previously run jobs
    """
    page = request.args.get('page', 1, type=int)
    armui_cfg = UISettings.query.first()

    try:
        # after roughly 175 entries firefox readermode will break
        # jobs = Job.query.filter_by().limit(175).all()
        jobs = Job.query.order_by(desc(Job.job_id)).paginate(page=page,
                                                             max_per_page=int(
                                                                 armui_cfg.database_limit),
                                                             error_out=False)
    except exc.SQLAlchemyError:
        flash("Unable to retrieve jobs.", category='error')
        app.logger.error("ERROR: Jobs database doesn't exist")
        jobs = {}
    app.logger.debug(f"Date format - {cfg.arm_config['DATE_FORMAT']}")

    session["page_title"] = "History"

    return render_template('history.html',
                           jobs=jobs.items,
                           pages=jobs,
                           date_format=cfg.arm_config['DATE_FORMAT'])
