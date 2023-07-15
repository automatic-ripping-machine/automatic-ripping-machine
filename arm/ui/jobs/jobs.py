"""
ARM route blueprint for jobs pages
Covers
- jobdetail [GET]
- titlesearch [GET]
- custometitle [GET]
- gettitle / customtitle [GET]
- updatetitle [GET]
- activerips [GET]
- changeparams [GET]
- list_titles [GET]
- json [JSON GET]
"""

import json
from flask_login import LoginManager, login_required  # noqa: F401
from flask import render_template, request, Blueprint, flash, redirect, url_for
from werkzeug.routing import ValidationError

import arm.ui.utils as ui_utils
from arm.ui import app, db, constants, json_api
from arm.models import models as models
import arm.config.config as cfg
from arm.ui.forms import TitleSearchForm, ChangeParamsForm

route_jobs = Blueprint('route_jobs', __name__,
                       template_folder='templates',
                       static_folder='../static')


@route_jobs.route('/jobdetail')
@login_required
def jobdetail():
    """
    Page for showing in-depth details about a job

    Shows Job/Config/Track class details
    displays them in a clear and easy to ready format
    """
    job_id = request.args.get('job_id')
    job = models.Job.query.get(job_id)
    tracks = job.tracks.all()
    search_results = ui_utils.metadata_selector("get_details", job.title, job.year, job.imdb_id)
    if search_results and 'Error' not in search_results:
        job.plot = search_results['Plot'] if 'Plot' in search_results else "There was a problem getting the plot"
        job.background = search_results['background_url'] if 'background_url' in search_results else None
    return render_template('jobdetail.html', jobs=job, tracks=tracks, s=search_results)


@route_jobs.route('/titlesearch')
@login_required
def title_search():
    """
    The initial search page
    """
    job_id = request.args.get('job_id')
    job = models.Job.query.get(job_id)
    form = TitleSearchForm(request.args)
    if form.validate():
        flash(f'Search for {request.args.get("title")}, year={request.args.get("year")}', 'success')
        return redirect(url_for('route_jobs.list_titles', title=request.args.get("title"),
                                year=request.args.get("year"), job_id=job_id))
    return render_template('titlesearch.html', title='Update Title', form=form, job=job)


@route_jobs.route('/customTitle')
@login_required
def customtitle():
    """
    For setting custom title for series with multiple discs
    """
    job_id = request.args.get('job_id')
    ui_utils.job_id_validator(job_id)
    job = models.Job.query.get(job_id)
    form = TitleSearchForm(obj=job)
    if request.args.get("title"):
        args = {
            'title': request.args.get("title"),
            'title_manual': request.args.get("title"),
            'year': request.args.get("year")
        }
        notification = models.Notifications(f"Job: {job.job_id} was updated",
                                            f'Title: {job.title} ({job.year}) was updated to '
                                            f'{request.args.get("title")} ({request.args.get("year")})')
        db.session.add(notification)
        ui_utils.database_updater(args, job)
        flash(f'Custom title changed. Title={job.title}, Year={job.year}.', "success")
        return redirect(url_for('home'))
    return render_template('customTitle.html', title='Change Title', form=form, job=job)


@route_jobs.route('/gettitle')
@route_jobs.route('/select_title')
@login_required
def gettitle():
    """
    Used to display plot info from the search result page when the user clicks the title
    and to forward the user to save the selected details

    This was also used previously for the getdetails page but it no longer needed there
    """
    imdb_id = request.args.get('imdbID').strip() if request.args.get('imdbID') else None
    job_id = request.args.get('job_id').strip() if request.args.get('job_id') else None
    if imdb_id == "" or imdb_id is None:
        app.logger.debug("gettitle - no imdb supplied")
        flash("No imdb supplied", "danger")
        raise ValidationError("No imdb supplied")
    if job_id == "" or job_id is None:
        app.logger.debug("gettitle - no job supplied")
        flash(constants.NO_JOB, "danger")
        raise ValidationError(constants.NO_JOB)
    dvd_info = ui_utils.metadata_selector("get_details", None, None, imdb_id)
    return render_template('showtitle.html', results=dvd_info, job_id=job_id)


@route_jobs.route('/updatetitle')
@login_required
def updatetitle():
    """
    used to save the details from the search
    """
    # updatetitle?title=Home&amp;year=2015&amp;imdbID=tt2224026&amp;type=movie&amp;
    #  poster=http://image.tmdb.org/t/p/original/usFenYnk6mr8C62dB1MoAfSWMGR.jpg&amp;job_id=109
    job_id = request.args.get('job_id')
    job = models.Job.query.get(job_id)
    old_title = job.title
    old_year = job.year
    job.title = job.title_manual = ui_utils.clean_for_filename(request.args.get('title'))
    job.year = job.year_manual = request.args.get('year')
    job.video_type = job.video_type_manual = request.args.get('type')
    job.imdb_id = job.imdb_id_manual = request.args.get('imdbID')
    job.poster_url = job.poster_url_manual = request.args.get('poster')
    job.hasnicetitle = True
    notification = models.Notifications(f"Job: {job.job_id} was updated",
                                        f'Title: {old_title} ({old_year}) was updated to '
                                        f'{request.args.get("title")} ({request.args.get("year")})')
    db.session.add(notification)
    db.session.commit()
    flash(f'Title: {old_title} ({old_year}) was updated to '
          f'{request.args.get("title")} ({request.args.get("year")})', "success")
    return redirect("/")


@route_jobs.route('/activerips')
@login_required
def rips():
    """
    This no longer works properly because of the 'transcoding' status
    """
    return render_template('activerips.html', jobs=models.Job.query.filter_by(status="active"))


@route_jobs.route('/changeparams')
@login_required
def changeparams():
    """
    For updating Config params or changing/correcting job.disctype manually
    """
    config_id = request.args.get('config_id')
    job = models.Job.query.get(config_id)
    config = job.config
    form = ChangeParamsForm(obj=config)
    return render_template('changeparams.html', title='Change Parameters', form=form, config=config)


@route_jobs.route('/list_titles')
@login_required
def list_titles():
    """
    The search results page

    This will display the returned search results from OMDB or TMDB from the users input search
    """
    title = request.args.get('title').strip() if request.args.get('title') else ''
    year = request.args.get('year').strip() if request.args.get('year') else ''
    job_id = request.args.get('job_id').strip() if request.args.get('job_id') else ''
    if job_id == "":
        app.logger.debug("list_titles - no job supplied")
        flash(constants.NO_JOB, "danger")
        raise ValidationError
    job = models.Job.query.get(job_id)
    form = TitleSearchForm(obj=job)
    search_results = ui_utils.metadata_selector("search", title, year)
    if search_results is None or 'Error' in search_results or (
            'Search' in search_results and len(search_results['Search']) < 1):
        app.logger.debug("No results found. Trying without year")
        flash(f"No search results found for {title} ({year})<br/> Trying without year", 'danger')
        search_results = ui_utils.metadata_selector("search", title, "")

    if search_results is None or 'Error' in search_results or (
            'Search' in search_results and len(search_results['Search']) < 1):
        flash(f"No search results found for {title}", 'danger')
    return render_template('list_titles.html', results=search_results, job_id=job_id,
                           form=form, title=title, year=year)


@route_jobs.route('/json', methods=['GET'])
@login_required
def feed_json():
    """
    json mini API
    This is used for all api/ajax calls this makes thing easier to read/code for
    Adding a new function to the api is as simple as adding a new elif where GET[mode]
    is your call
    You can then add a function inside utils to deal with the request
    """
    mode = str(request.args.get('mode'))
    return_json = {'mode': mode, 'success': False}
    # Hold valid data (post/get data) we might receive from pages - not in here ? it's going to throw a key error
    valid_data = {
        'j_id': request.args.get('job'),
        'searchq': request.args.get('q'),
        'logpath': cfg.arm_config['LOGPATH'],
        'fail': 'fail',
        'success': 'success',
        'joblist': 'joblist',
        'mode': mode,
        'config_id': request.args.get('config_id'),
        'notify_id': request.args.get('notify_id'),
        'notify_timeout': {'funct': json_api.get_notify_timeout, 'args': ('notify_timeout',)},
        'restart': {'funct': json_api.restart_ui, 'args': ()},
    }
    # Valid modes that should trigger functions
    valid_modes = {
        'delete': {'funct': json_api.delete_job, 'args': ('j_id', 'mode')},
        'abandon': {'funct': json_api.abandon_job, 'args': ('j_id',)},
        'full': {'funct': json_api.generate_log, 'args': ('logpath', 'j_id')},
        'search': {'funct': json_api.search, 'args': ('searchq',)},
        'getfailed': {'funct': json_api.get_x_jobs, 'args': ('fail',)},
        'getsuccessful': {'funct': json_api.get_x_jobs, 'args': ('success',)},
        'fixperms': {'funct': ui_utils.fix_permissions, 'args': ('j_id',)},
        'joblist': {'funct': json_api.get_x_jobs, 'args': ('joblist',)},
        'send_item': {'funct': ui_utils.send_to_remote_db, 'args': ('j_id',)},
        'change_job_params': {'funct': json_api.change_job_params, 'args': ('config_id',)},
        'read_notification': {'funct': json_api.read_notification, 'args': ('notify_id',)},
        'notify_timeout': {'funct': json_api.get_notify_timeout, 'args': ('notify_timeout',)}
    }
    if mode in valid_modes:
        args = [valid_data[x] for x in valid_modes[mode]['args']]
        return_json = valid_modes[mode]['funct'](*args)
    return_json['notes'] = json_api.get_notifications()
    return app.response_class(response=json.dumps(return_json, indent=4, sort_keys=True),
                              status=200,
                              mimetype=constants.JSON_TYPE)
