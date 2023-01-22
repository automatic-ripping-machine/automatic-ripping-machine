#!/usr/bin/env python3
"""Main routes for the A.R.M ui"""
import os
import json
from pathlib import Path, PurePath
from werkzeug.exceptions import HTTPException
from werkzeug.routing import ValidationError
from flask import Flask, render_template, request, send_file, flash, \
    redirect, url_for  # noqa: F401
from flask.logging import default_handler  # noqa: F401
from flask_login import login_required, UserMixin  # noqa: F401
import arm.ui.utils as ui_utils
from arm.ui import app, db, constants, json_api
from arm.models import models as models
import arm.config.config as cfg
from arm.ui.forms import TitleSearchForm, ChangeParamsForm, DBUpdate
from arm.ui.settings.ServerUtil import ServerUtil

# This attaches the armui_cfg globally to let the users use any bootswatch skin from cdn
armui_cfg = ui_utils.arm_db_cfg()

# Page definitions
page_support_databaseupdate = "support/databaseupdate.html"
redirect_settings = "/settings"


@app.route('/error')
def was_error(error):
    """
    Catch all error page
    :return: Error page
    """
    return render_template(constants.ERROR_PAGE, title='error', error=error)


@app.route('/setup')
def setup():
    """
    This is the initial setup page for fresh installs
    This is no longer recommended for upgrades

    This function will do various checks to make sure everything can be setup for ARM
    Directory ups, create the db, etc
    """
    perm_file = Path(PurePath(cfg.arm_config['INSTALLPATH'], "installed"))
    app.logger.debug("perm " + str(perm_file))
    # Check for install file and that db is correctly setup
    if perm_file.exists() and ui_utils.setup_database(cfg.arm_config['INSTALLPATH']):
        flash(f"{perm_file} exists, setup cannot continue. To re-install please delete this file.", "danger")
        return redirect("/")
    dir0 = Path(PurePath(cfg.arm_config['DBFILE']).parent)
    dir1 = Path(cfg.arm_config['RAW_PATH'])
    dir2 = Path(cfg.arm_config['TRANSCODE_PATH'])
    dir3 = Path(cfg.arm_config['COMPLETED_PATH'])
    dir4 = Path(cfg.arm_config['LOGPATH'])
    arm_directories = [dir0, dir1, dir2, dir3, dir4]

    try:
        for arm_dir in arm_directories:
            if not Path.exists(arm_dir):
                os.makedirs(arm_dir)
                flash(f"{arm_dir} was created successfully.", "success")
    except FileNotFoundError as error:
        flash(f"Creation of the directory {dir0} failed {error}", "danger")
        app.logger.debug(f"Creation of the directory failed - {error}")
    else:
        flash("Successfully created all of the ARM directories", "success")
        app.logger.debug("Successfully created all of the ARM directories")

    try:
        if ui_utils.setup_database(cfg['INSTALLPATH']):
            flash("Setup of the database was successful.", "success")
            app.logger.debug("Setup of the database was successful.")
            perm_file = Path(PurePath(cfg.arm_config['INSTALLPATH'], "installed"))
            write_permission_file = open(perm_file, "w")
            write_permission_file.write("boop!")
            write_permission_file.close()
            return redirect(constants.HOME_PAGE)
        flash("Couldn't setup database", "danger")
        app.logger.debug("Couldn't setup database")
        return redirect("/error")
    except Exception as error:
        flash(str(error))
        app.logger.debug("Setup - " + str(error))
        return redirect(constants.HOME_PAGE)


@app.route('/json', methods=['GET'])
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
        'notify_id': request.args.get('notify_id')
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
        'read_notification': {'funct': json_api.read_notification, 'args': ('notify_id',)}
    }
    if mode in valid_modes:
        args = [valid_data[x] for x in valid_modes[mode]['args']]
        return_json = valid_modes[mode]['funct'](*args)
    return_json['notes'] = json_api.get_notifications()
    return app.response_class(response=json.dumps(return_json, indent=4, sort_keys=True),
                              status=200,
                              mimetype=constants.JSON_TYPE)


@app.route('/activerips')
@login_required
def rips():
    """
    This no longer works properly because of the 'transcoding' status
    """
    return render_template('activerips.html', jobs=models.Job.query.filter_by(status="active"))


@app.route('/history')
@login_required
def history():
    """
    Smaller much simpler output of previously run jobs

    """
    page = request.args.get('page', 1, type=int)
    if os.path.isfile(cfg.arm_config['DBFILE']):
        # after roughly 175 entries firefox readermode will break
        # jobs = Job.query.filter_by().limit(175).all()
        jobs = models.Job.query.order_by(db.desc(models.Job.job_id)).paginate(page, 100, False)
    else:
        app.logger.error('ERROR: /history database file doesnt exist')
        jobs = {}
    app.logger.debug(f"Date format - {cfg.arm_config['DATE_FORMAT']}")

    return render_template('history.html', jobs=jobs.items,
                           date_format=cfg.arm_config['DATE_FORMAT'], pages=jobs)


@app.route('/jobdetail')
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


@app.route('/titlesearch')
@login_required
def title_search():
    """
    The initial search page
    """
    job_id = request.args.get('job_id')
    job = models.Job.query.get(job_id)
    form = TitleSearchForm(request.args, meta={'csrf': False})
    if form.validate():
        flash(f'Search for {request.args.get("title")}, year={request.args.get("year")}', 'success')
        return redirect(url_for('list_titles', title=request.args.get("title"),
                                year=request.args.get("year"), job_id=job_id))
    return render_template('titlesearch.html', title='Update Title', form=form, job=job)


@app.route('/changeparams')
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


@app.route('/customTitle')
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


@app.route('/list_titles')
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


@app.route('/gettitle')
@app.route('/select_title')
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


@app.route('/updatetitle')
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


@app.route('/')
@app.route('/index.html')
@app.route('/index')
@login_required
def home():
    """
    The main homepage showing current rips and server stats
    """
    global page_support_databaseupdate

    # Check the database is current
    db_update = ui_utils.arm_db_check()
    if not db_update["db_current"] or not db_update["db_exists"]:
        dbform = DBUpdate(request.form)
        return render_template(page_support_databaseupdate, db_update=db_update, dbform=dbform)

    # System details in class server
    server = models.SystemInfo.query.filter_by(id="1").first()
    serverutil = ServerUtil()
    serverutil.get_update()
    # System details in class server
    arm_path = cfg.arm_config['TRANSCODE_PATH']
    media_path = cfg.arm_config['COMPLETED_PATH']
    armname = ""
    if cfg.arm_config['ARM_NAME'] != "":
        armname = f"[{cfg.arm_config['ARM_NAME']}] - "

    if os.path.isfile(cfg.arm_config['DBFILE']):
        try:
            jobs = db.session.query(models.Job).filter(models.Job.status.notin_(['fail', 'success'])).all()
        except Exception:
            # db isn't setup
            return redirect(url_for('setup'))
    else:
        jobs = {}

    return render_template("index.html", jobs=jobs, armname=armname,
                           children=cfg.arm_config['ARM_CHILDREN'],
                           server=server, serverutil=serverutil,
                           arm_path=arm_path, media_path=media_path)


@app.route('/send_movies')
@login_required
def send_movies():
    """
    function for sending all dvd crc64 ids to off-site api
    This isn't very optimised and can be slow and causes a huge number of requests
    """
    if request.args.get('s') is None:
        return render_template('send_movies_form.html')

    job_list = db.session.query(models.Job).filter_by(hasnicetitle=True, disctype="dvd").all()
    return_job_list = [job.job_id for job in job_list]
    return render_template('send_movies.html', job_list=return_job_list)


@app.errorhandler(Exception)
def handle_exception(sent_error):
    """
    Exception handler - This breaks all of the normal debug functions \n
    :param sent_error: error
    :return: error page
    """
    # pass through HTTP errors
    if isinstance(sent_error, HTTPException):
        return sent_error

    app.logger.debug(f"Error: {sent_error}")
    if request.path.startswith('/json') or request.args.get('json'):
        app.logger.debug(f"{request.path} - {sent_error}")
        return_json = {
            'path': request.path,
            'Error': str(sent_error)
        }
        return app.response_class(response=json.dumps(return_json, indent=4, sort_keys=True),
                                  status=200,
                                  mimetype=constants.JSON_TYPE)

    return render_template(constants.ERROR_PAGE, error=sent_error), 500


@app.route('/update_arm', methods=['POST'])
@login_required
def update_git():
    """Update arm via git command line"""
    return ui_utils.git_get_updates()


@app.route('/driveeject/<id>')
@login_required
def drive_eject(id):
    """
    Server System  - change state of CD/DVD/BluRay drive - toggle eject
    """
    global redirect_settings
    drive = models.SystemDrives.query.filter_by(drive_id=id).first()
    drive.open_close()
    db.session.commit()
    return redirect(redirect_settings)


@app.route('/dbupdate', methods=['POST'])
def update_database():
    """
    Update the ARM database when changes are made or the arm db file is missing
    """
    form = DBUpdate(request.form)
    if request.method == 'POST' and form.validate():
        if form.dbfix.data == "migrate":
            app.logger.debug("User requested - Database migration")
            ui_utils.arm_db_migrate()
            flash("ARM database migration successful!", "success")
        elif form.dbfix.data == "new":
            app.logger.debug("User requested - New database")
            flash("ARM database setup successful!", "success")
        else:
            # No method defined
            app.logger.debug(f"No update method defined from DB Update - {form.dbfix.data}")
            flash("Error no update method specified, report this as a bug.", "error")

        return redirect('/index')
    else:
        # Catch for GET requests of the page, redirect to index
        return redirect('/index')
