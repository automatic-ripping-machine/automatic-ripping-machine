"""
ARM route blueprint for history pages
Covers
- history [GET]
"""

import os
from flask_login import LoginManager, login_required  # noqa: F401
from flask import render_template, request, Blueprint, session

import arm.ui.utils as ui_utils
from arm.ui import app, db
from arm.models.job import Job
from arm.ui.history.view_options import get_view_options, STATUS_FILTERS, ORDERS
import arm.config.config as cfg

route_history = Blueprint('route_history', __name__,
                          template_folder='templates',
                          static_folder='../static')

# This attaches the armui_cfg globally to let the users use any bootswatch skin from cdn
armui_cfg = ui_utils.arm_db_cfg()


@route_history.route('/history')
@login_required
def history():
    """
    Smaller much simpler output of previously run jobs

    """
    # regenerate the armui_cfg we don't want old settings
    armui_cfg = ui_utils.arm_db_cfg()
    page = request.args.get('page', 1, type=int)
    view = get_view_options(request.args, armui_cfg.database_limit)
    if os.path.isfile(cfg.arm_config['DBFILE']):
        query = Job.query
        if view['status'] != 'all':
            query = query.filter(Job.status == view['status'])
        if view['order'] == 'oldest':
            query = query.order_by(Job.job_id)
        else:
            query = query.order_by(db.desc(Job.job_id))
        jobs = query.paginate(page=page, per_page=view['per_page'], error_out=False)
    else:
        app.logger.error('ERROR: /history database file doesnt exist')
        jobs = {}
    app.logger.debug(f"Date format - {cfg.arm_config['DATE_FORMAT']}")

    session["page_title"] = "History"

    # Carried through the pagination links so changing page keeps the view
    page_args = {key: view[key] for key in ('per_page', 'status', 'order')}

    return render_template('history.html', jobs=jobs.items,
                           date_format=cfg.arm_config['DATE_FORMAT'], pages=jobs,
                           view=view, page_args=page_args,
                           status_filters=STATUS_FILTERS, orders=ORDERS)
