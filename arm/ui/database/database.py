"""
ARM route blueprint for database pages
Covers
- database [GET]
"""

import os
from flask_login import LoginManager, login_required  # noqa: F401
from flask import render_template, request, Blueprint, redirect

import arm.ui.utils as ui_utils
from arm.ui import app, db
from arm.models import models as models
import arm.config.config as cfg

route_database = Blueprint('route_database', __name__,
                        template_folder='templates',
                        static_folder='../static')

# This attaches the armui_cfg globally to let the users use any bootswatch skin from cdn
armui_cfg = ui_utils.arm_db_cfg()


@route_database.route('/database')
@login_required
def view_database():
    """
    The main database page

    Outputs every job from the database
     this can cause serious slow-downs with + 3/4000 entries
    """
    page = request.args.get('page', 1, type=int)
    app.logger.debug(armui_cfg)
    ## Check for database file
    if os.path.isfile(cfg.arm_config['DBFILE']):
        jobs = models.Job.query.order_by(db.desc(models.Job.job_id)).paginate(page,
                                                                              int(armui_cfg.database_limit), False)
    else:
        app.logger.error('ERROR: /database no database, file doesnt exist')
        jobs = {}

    return render_template('databaseview.html',
                           jobs=jobs.items, pages=jobs,
                           date_format=cfg.arm_config['DATE_FORMAT'])
    #return redirect('/index')
