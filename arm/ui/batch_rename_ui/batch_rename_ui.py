"""
ARM route blueprint for batch rename pages
Covers
- batch_rename_view [GET]
"""

from flask_login import login_required
from flask import render_template, Blueprint, session

import arm.ui.utils as ui_utils
from arm.ui import app, db
from arm.models.job import Job
import arm.config.config as cfg

route_batch_rename_ui = Blueprint('route_batch_rename_ui', __name__,
                                  template_folder='templates',
                                  static_folder='../static')

# This attaches the armui_cfg globally to let users use any bootswatch skin
armui_cfg = ui_utils.arm_db_cfg()


@route_batch_rename_ui.route('/batch_rename_view')
@login_required
def batch_rename_view():
    """
    Batch rename view - shows only completed discs in grid layout
    Allows selection and batch renaming of TV series discs
    """
    # Regenerate the armui_cfg - we don't want old settings
    armui_cfg = ui_utils.arm_db_cfg()

    # Get only completed jobs (success status)
    completed_jobs = Job.query.filter(
        Job.status == 'success'
    ).order_by(db.desc(Job.job_id)).all()

    app.logger.debug(
        f"Batch Rename View: Found {len(completed_jobs)} completed jobs"
    )
    app.logger.debug(f"Date format - {cfg.arm_config['DATE_FORMAT']}")

    session["page_title"] = "Batch Rename"

    return render_template('batch_rename_view.html',
                           jobs=completed_jobs,
                           date_format=cfg.arm_config['DATE_FORMAT'],
                           armui_cfg=armui_cfg)
