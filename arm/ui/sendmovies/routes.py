"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Send Movies

Covers
- send_movies [GET]
"""

from flask_login import login_required
from flask import render_template, request, session
from flask import current_app as app

from arm.ui.sendmovies import route_sendmovies
from arm.models.job import Job


@route_sendmovies.route('/send_movies')
@login_required
def send_movies():
    """
    function for sending all dvd crc64 ids to off-site api
    This isn't very optimised and can be slow and causes a huge number of requests
    """
    if request.args.get('s') is None:
        app.logger.debug('No arguments passed to send_movies')
        session["page_title"] = "Send Movies/Series"
        return render_template('send_movies_form.html')

    app.logger.debug('Collecting job list')
    job_list = Job.query.filter_by(hasnicetitle=True, disctype="dvd").all()
    return_job_list = [job.job_id for job in job_list]

    app.logger.debug('Sending Job List')
    session["page_title"] = "Send Movies/Series"

    return render_template('send_movies.html',
                           job_list=return_job_list)
