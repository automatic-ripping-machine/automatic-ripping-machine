"""ARM route blueprint for history pages."""
from flask_login import LoginManager, login_required  # noqa: F401
from flask import render_template, request, Blueprint, session
from sqlalchemy.exc import SQLAlchemyError

import arm.ui.utils as ui_utils
from arm.ui import app, db
from arm.models.job import Job
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
    try:
        jobs = Job.query.order_by(db.desc(Job.job_id)).paginate(
            page=page,
            max_per_page=int(armui_cfg.database_limit),
            error_out=False
        )
        job_items = jobs.items
    except SQLAlchemyError as error:
        app.logger.error('ERROR: /history unable to query database: %s', error)
        jobs = type('Pagination', (), {
            'page': 1,
            'pages': 1,
            'prev_num': 1,
            'next_num': 1,
            'iter_pages': staticmethod(lambda *_, **__: [])
        })()
        job_items = []
    app.logger.debug(f"Date format - {cfg.arm_config['DATE_FORMAT']}")

    session["page_title"] = "History"

    return render_template('history.html', jobs=job_items,
                           date_format=cfg.arm_config['DATE_FORMAT'], pages=jobs)
