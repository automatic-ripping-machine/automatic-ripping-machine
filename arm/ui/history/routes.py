"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    History

Covers
    - history [GET]
"""
from flask_login import login_required
from flask import render_template, request, session, flash
from flask import current_app as app
from sqlalchemy import desc, exc

from ui.history import route_history
import arm.config.config as cfg
from arm.models.ui_settings import UISettings
from arm.models.job import Job


# This attaches the armui_cfg globally to let the users use any bootswatch skin from cdn
# armui_cfg = ui_utils.arm_db_cfg()


@route_history.route('/history')
@login_required
def history():
    """
    Smaller much simpler output of previously run jobs

    """
    # regenerate the armui_cfg we don't want old settings
    armui_cfg = UISettings.query.filter_by().first()

    page = request.args.get('page', 1, type=int)
    try:
        # after roughly 175 entries firefox readermode will break
        # jobs = Job.query.filter_by().limit(175).all()
        jobs = Job.query.order_by(desc(Job.job_id)).paginate(page=page,
                                                             max_per_page=int(
                                                                 armui_cfg.database_limit),
                                                             error_out=False)
    except exc.SQLAlchemyError:
        flash("Unable to retrieve jobs.", category='error')
        app.logger.error('ERROR: /history database file doesnt exist')
        jobs = {}
    app.logger.debug(f"Date format - {cfg.arm_config['DATE_FORMAT']}")

    session["page_title"] = "History"

    return render_template('history.html', jobs=jobs.items,
                           date_format=cfg.arm_config['DATE_FORMAT'], pages=jobs)
