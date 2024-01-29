"""
ARM route blueprint for send_movies page
Covers
- send_movies [GET]
"""

from flask_login import LoginManager, login_required  # noqa: F401
from flask import render_template, request, Blueprint, session

from arm.ui import db
from arm.models.job import Job

route_sendmovies = Blueprint('route_sendmovies', __name__,
                             template_folder='templates',
                             static_folder='../static')


@route_sendmovies.route('/send_movies')
@login_required
def send_movies():
    """
    function for sending all dvd crc64 ids to off-site api
    This isn't very optimised and can be slow and causes a huge number of requests
    """
    if request.args.get('s') is None:
        session["page_title"] = "Send Movies/Series"
        return render_template('send_movies_form.html')

    job_list = db.session.query(Job).filter_by(hasnicetitle=True, disctype="dvd").all()
    return_job_list = [job.job_id for job in job_list]

    session["page_title"] = "Send Movies/Series"

    return render_template('send_movies.html', job_list=return_job_list)
