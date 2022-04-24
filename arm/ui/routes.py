#!/usr/bin/env python3
"""Main routes for the A.R.M ui"""
import os
import re
import sys  # noqa: F401
import json
from pathlib import Path, PurePath

import bcrypt
import psutil
from werkzeug.exceptions import HTTPException
from werkzeug.routing import ValidationError
from flask import Flask, render_template, request, send_file, flash, \
    redirect, url_for  # noqa: F401
from flask.logging import default_handler  # noqa: F401
from flask_login import LoginManager, login_required, \
    current_user, login_user, UserMixin, logout_user  # noqa: F401
import arm.ui.utils as ui_utils
from arm.ui import app, db, constants, json_api
from arm.models import models as models
from arm.config.config import cfg
from arm.ui.forms import TitleSearchForm, ChangeParamsForm, SettingsForm, UiSettingsForm, SetupForm
from arm.ui.metadata import get_omdb_poster

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    """
    Logged in check
    :param user_id:
    :return:
    """
    try:
        return models.User.query.get(int(user_id))
    except Exception:
        app.logger.debug("Error getting user")
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """
    User isn't authorised to view the page
    :return: Page redirect
    """
    return redirect('/login')


@app.route('/error')
def was_error(error):
    """
    Catch all error page
    :return: Error page
    """
    return render_template(constants.ERROR_PAGE, title='error', error=error)


@app.route("/logout")
def logout():
    """
    Log user out
    :return:
    """
    logout_user()
    flash("logged out", "success")
    return redirect('/')


@app.route('/setup')
def setup():
    """
    This is the initial setup page for fresh installs
    This is no longer recommended for upgrades

    This function will do various checks to make sure everything can be setup for ARM
    Directory ups, create the db, etc
    """
    perm_file = Path(PurePath(cfg['INSTALLPATH'], "installed"))
    app.logger.debug("perm " + str(perm_file))
    # Check for install file and that db is correctly setup
    if perm_file.exists() and ui_utils.setup_database():
        flash(str(perm_file) + " exists, setup cannot continue."
                               " To re-install please delete this file.", "danger")
        return redirect("/")
    dir0 = Path(PurePath(cfg['DBFILE']).parent)
    dir1 = Path(cfg['RAW_PATH'])
    dir2 = Path(cfg['TRANSCODE_PATH'])
    dir3 = Path(cfg['COMPLETED_PATH'])
    dir4 = Path(cfg['LOGPATH'])
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
        if ui_utils.setup_database():
            flash("Setup of the database was successful.", "success")
            app.logger.debug("Setup of the database was successful.")
            perm_file = Path(PurePath(cfg['INSTALLPATH'], "installed"))
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


@app.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    """
    updating password for the admin account
    """
    # After a login for is submitted
    form = SetupForm()
    if form.validate_on_submit():
        username = str(request.form['username']).strip()
        new_password = str(request.form['newpassword']).strip().encode('utf-8')
        user = models.User.query.filter_by(email=username).first()
        password = user.password
        hashed = user.hash
        # our new one
        login_hashed = bcrypt.hashpw(str(request.form['password']).strip().encode('utf-8'), hashed)
        if login_hashed == password:
            hashed_password = bcrypt.hashpw(new_password, hashed)
            user.password = hashed_password
            user.hash = hashed
            try:
                db.session.commit()
                flash("Password successfully updated", "success")
                return redirect("logout")
            except Exception as error:
                flash(str(error), "danger")
        else:
            flash("Password couldn't be updated. Problem with old password", "danger")
    return render_template('update_password.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page if login is enabled
    :return: redirect
    """
    return_redirect = None
    # if there is no user in the database
    try:
        user_list = models.User.query.all()
        # If we don't raise an exception but the usr table is empty
        if not user_list:
            app.logger.debug("No admin found")
            return_redirect = redirect(constants.SETUP_STAGE_2)
    except Exception:
        flash(constants.NO_ADMIN_ACCOUNT, "danger")
        app.logger.debug(constants.NO_ADMIN_ACCOUNT)
        return_redirect = redirect(constants.SETUP_STAGE_2)

    # if user is logged in
    if current_user.is_authenticated:
        return_redirect = redirect(constants.HOME_PAGE)

    form = SetupForm()
    if form.validate_on_submit():
        login_username = request.form['username']
        # we know there is only ever 1 admin account, so we can pull it and check against it locally
        admin = models.User.query.filter_by().first()
        app.logger.debug("user= " + str(admin))
        # our pass
        password = admin.password
        # hashed pass the user provided
        login_hashed = bcrypt.hashpw(str(request.form['password']).strip().encode('utf-8'), admin.hash)

        if login_hashed == password and login_username == admin.email:
            login_user(admin)
            app.logger.debug("user was logged in - redirecting")
            return_redirect = redirect(constants.HOME_PAGE)
        else:
            flash("Something isn't right", "danger")
    # If nothing has gone wrong give them the login page
    if return_redirect is None:
        return_redirect = render_template('login.html', form=form)
    return return_redirect


@app.route('/database')
@login_required
def database():
    """
    The main database page

    Outputs every job from the database
     this can cause serious slow-downs with + 3/4000 entries
    """

    page = request.args.get('page', 1, type=int)
    # Check for database file
    if os.path.isfile(cfg['DBFILE']):
        jobs = models.Job.query.order_by(db.desc(models.Job.job_id)).paginate(page, 100, False)
    else:
        app.logger.error('ERROR: /database no database, file doesnt exist')
        jobs = {}
    return render_template('database.html', jobs=jobs.items,
                           date_format=cfg['DATE_FORMAT'], pages=jobs)


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
    return_json = {}
    mode = str(request.args.get('mode'))

    valid_data = {
        'j_id': request.args.get('job'),
        'searchq': request.args.get('q'),
        'logpath': cfg['LOGPATH'],
        'fail': 'fail',
        'success': 'success',
        'joblist': 'joblist',
        'mode': mode
    }
    valid_modes = {
        'delete': {'funct': json_api.delete_job, 'args': ('j_id', 'mode')},
        'abandon': {'funct': json_api.abandon_job, 'args': ('j_id',)},
        'full': {'funct': json_api.generate_log, 'args': ('logpath', 'j_id')},
        'search': {'funct': json_api.search, 'args': ('searchq',)},
        'getfailed': {'funct': json_api.get_x_jobs, 'args': ('fail',)},
        'getsuccessful': {'funct': json_api.get_x_jobs, 'args': ('success',)},
        'fixperms': {'funct': ui_utils.fix_permissions, 'args': ('j_id',)},
        'joblist': {'funct': json_api.get_x_jobs, 'args': ('joblist',)},
        'send_item': {'funct': ui_utils.send_to_remote_db, 'args': ('j_id',)}
    }
    if mode in valid_modes:
        args = [valid_data[x] for x in valid_modes[mode]['args']]
        app.logger.debug(args)
        return_json = valid_modes[mode]['funct'](*args)
    app.logger.debug(f"Json - {return_json}")
    return app.response_class(response=json.dumps(return_json, indent=4, sort_keys=True),
                              status=200,
                              mimetype=constants.JSON_TYPE)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """
    The settings page - allows the user to update the arm.yaml without needing to open a text editor
    This needs to be rewritten to be static
    """
    # Path to arm.yaml
    arm_cfg_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "arm.yaml")
    # Load up the comments.json, so we can comment the arm.yaml
    comments = ui_utils.generate_comments()
    # Get the current config, so we can show the current values with no post data
    current_cfg = ui_utils.get_settings(arm_cfg_file)
    form = SettingsForm()
    if form.validate_on_submit():
        # Build the new arm.yaml with updated values from the user
        arm_cfg = ui_utils.build_arm_cfg(request.form.to_dict(), comments)
        # Save updated arm.yaml
        with open(arm_cfg_file, "w") as settings_file:
            settings_file.write(arm_cfg)
            settings_file.close()
        flash("Setting saved successfully!", "success")
        # Redirect so we show the new config values
        return redirect(url_for('settings'))
    # If we get to here there was no post data
    return render_template('settings.html', settings=current_cfg,
                           form=form, raw=request.form.to_dict(), jsoncomments=comments)


@app.route('/ui_settings', methods=['GET', 'POST'])
@login_required
def ui_settings():
    """
    The ARMui settings page - allows the user to update the armui_settings
    This function needs to trigger a restart of flask for debugging to update the values

    """
    armui_cfg = models.UISettings.query.filter_by().first()
    form = UiSettingsForm()
    if form.validate_on_submit():
        # json.loads("false".lower())
        use_icons = (str(form.use_icons.data).strip().lower() == "true")
        save_remote_images = (str(form.save_remote_images.data).strip().lower() == "true")
        database_arguments = {
            'index_refresh': format(form.index_refresh.data),
            'use_icons': use_icons,
            'save_remote_images': save_remote_images,
            'bootstrap_skin': format(form.bootstrap_skin.data),
            'language': format(form.language.data),
            'database_limit': format(form.database_limit.data),
        }
        ui_utils.database_updater(database_arguments, armui_cfg)
        db.session.refresh(armui_cfg)
        flash("Settings saved successfully!", "success")

    return render_template('ui_settings.html', form=form, settings=armui_cfg)


@app.route('/logs')
@login_required
def logs():
    """
    This is the main page for viewing a logfile

    this holds the XHR request that sends to other routes for the data
    """
    mode = request.args['mode']
    logfile = request.args['logfile']

    return render_template('logview.html', file=logfile, mode=mode)


@app.route('/listlogs', defaults={'path': ''})
@login_required
def listlogs(path):
    """
    The 'View logs' page - show a list of logfiles in the log folder with creation time and size
    Gives the user links to tail/arm/Full/download
    """
    base_path = cfg['LOGPATH']
    full_path = os.path.join(base_path, path)

    # Deal with bad data
    if not os.path.exists(full_path):
        raise ValidationError

    # Get all files in directory
    files = ui_utils.get_info(full_path)
    return render_template('logfiles.html', files=files, date_format=cfg['DATE_FORMAT'])


@app.route('/logreader')
@login_required
def logreader():
    """
    The default logreader output function

    This will display or allow downloading the requested logfile
    This is where the XHR requests are sent when viewing /logs?=logfile
    """
    log_path = cfg['LOGPATH']
    mode = request.args.get('mode')
    # We should use the job id and not get the raw logfile from the user
    # Maybe search database and see if we can match the logname with a previous rip ?
    full_path = os.path.join(log_path, request.args.get('logfile'))
    ui_utils.validate_logfile(request.args.get('logfile'), mode, Path(full_path))

    # Only ARM logs
    if mode == "armcat":
        generate = ui_utils.generate_arm_cat(full_path)
    # Give everything / Tail
    elif mode == "full":
        generate = ui_utils.generate_full_log(full_path)
    elif mode == "download":
        return send_file(full_path, as_attachment=True)
    else:
        # No mode - error out
        raise ValidationError

    return app.response_class(generate, mimetype='text/plain')


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
    if os.path.isfile(cfg['DBFILE']):
        # after roughly 175 entries firefox readermode will break
        # jobs = Job.query.filter_by().limit(175).all()
        jobs = models.Job.query.order_by(db.desc(models.Job.job_id)).paginate(page, 100, False)
    else:
        app.logger.error('ERROR: /history database file doesnt exist')
        jobs = {}
    app.logger.debug(f"Date format - {cfg['DATE_FORMAT']}")

    return render_template('history.html', jobs=jobs.items,
                           date_format=cfg['DATE_FORMAT'], pages=jobs)


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


@app.route('/titlesearch', methods=['GET'])
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


@app.route('/changeparams', methods=['GET', 'POST'])
@login_required
def changeparams():
    """
    For updating Config params or changing/correcting job.disctype manually
    """
    config_id = request.args.get('config_id')
    # app.logger.debug(config.pretty_table())
    job = models.Job.query.get(config_id)
    config = job.config
    form = ChangeParamsForm(obj=config)
    if form.validate_on_submit():
        job.disctype = format(form.DISCTYPE.data)
        cfg["MINLENGTH"] = config.MINLENGTH = format(form.MINLENGTH.data)
        cfg["MAXLENGTH"] = config.MAXLENGTH = format(form.MAXLENGTH.data)
        cfg["RIPMETHOD"] = config.RIPMETHOD = format(form.RIPMETHOD.data)
        # must be 1 for True 0 for False
        cfg["MAINFEATURE"] = config.MAINFEATURE = 1 if format(form.MAINFEATURE.data).lower() == "true" else 0
        args = {'disctype': job.disctype}
        # We don't need to set the config as they are set with job commit
        ui_utils.database_updater(args, job)

        flash(f'Parameters changed. Rip Method={config.RIPMETHOD}, Main Feature={config.MAINFEATURE},'
              f'Minimum Length={config.MINLENGTH}, '
              f'Maximum Length={config.MAXLENGTH}, Disctype={job.disctype}', "success")
    return render_template('changeparams.html', title='Change Parameters', form=form)


@app.route('/customTitle', methods=['GET'])
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
            'year': request.args.get("year")
        }
        ui_utils.database_updater(args, job)
        flash(f'Custom title changed. Title={job.title}, Year={job.year}.', "success")
        return redirect(url_for('home'))
    return render_template('customTitle.html', title='Change Title', form=form, job=job)


@app.route('/list_titles', methods=['GET'])
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


@app.route('/gettitle', methods=['GET'])
@app.route('/select_title', methods=['GET'])
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


@app.route('/updatetitle', methods=['GET'])
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
    # Force a db update
    ui_utils.check_db_version(cfg['INSTALLPATH'], cfg['DBFILE'])

    # Hard drive space
    try:
        freegb = psutil.disk_usage(cfg['TRANSCODE_PATH']).free
        freegb = round(freegb / 1073741824, 1)
        arm_percent = psutil.disk_usage(cfg['TRANSCODE_PATH']).percent
        mfreegb = psutil.disk_usage(cfg['COMPLETED_PATH']).free
        mfreegb = round(mfreegb / 1073741824, 1)
        media_percent = psutil.disk_usage(cfg['COMPLETED_PATH']).percent
    except FileNotFoundError:
        freegb = 0
        arm_percent = 0
        mfreegb = 0
        media_percent = 0
        app.logger.debug("ARM folders not found")
        flash("There was a problem accessing the ARM folders. Please make sure you have setup ARM<br/>"
              "Setup can be started by visiting <a href=\"/setup\">setup page</a> ARM will not work correctly until"
              "until you have added an admin account", "danger")
    #  RAM
    memory = psutil.virtual_memory()
    mem_total = round(memory.total / 1073741824, 1)
    mem_free = round(memory.available / 1073741824, 1)
    mem_used = round(memory.used / 1073741824, 1)
    ram_percent = memory.percent

    armname = ""
    if cfg['ARM_NAME'] != "":
        armname = f"[{cfg['ARM_NAME']}] - "

    #  get out cpu info
    try:
        our_cpu = ui_utils.get_processor_name()
        cpu_usage = psutil.cpu_percent()
    except EnvironmentError:
        our_cpu = "Not found"
        cpu_usage = "0"

    try:
        temps = psutil.sensors_temperatures()
        temp = temps['coretemp'][0][1]
    except KeyError:
        temp = temps = None

    if os.path.isfile(cfg['DBFILE']):
        try:
            jobs = db.session.query(models.Job).filter(models.Job.status.notin_(['fail', 'success'])).all()
        except Exception:
            # db isn't setup
            return redirect(url_for('setup'))
    else:
        jobs = {}

    return render_template('index.html', freegb=freegb, mfreegb=mfreegb,
                           arm_percent=arm_percent, media_percent=media_percent,
                           jobs=jobs, cpu=our_cpu, cputemp=temp, cpu_usage=cpu_usage,
                           ram=mem_total, ramused=mem_used, ramfree=mem_free, ram_percent=ram_percent,
                           ramdump=str(temps), armname=armname, children=cfg['ARM_CHILDREN'])


@app.route('/import_movies')
@login_required
def import_movies():
    """
    Function for finding all movies not currently tracked by ARM in the COMPLETED_PATH
    This should not be run frequently
    This causes a HUGE number of requests to OMdb\n
    :return: Outputs json - contains a dict/json of movies added and a notfound list
             that doesn't match ARM identified folder format.
    .. note:: This should eventually be moved to /json page load times are too long
    """
    my_path = cfg['COMPLETED_PATH']
    app.logger.debug(my_path)
    movies = {0: {'notfound': {}}}
    i = 1
    movie_dirs = ui_utils.generate_file_list(my_path)
    app.logger.debug(movie_dirs)
    if len(movie_dirs) < 1:
        app.logger.debug("movie_dirs found none")

    for movie in movie_dirs:
        # will match 'Movie (0000)'
        regex = r"([\w\ \'\.\-\&\,]*?) \(([0-9]{2,4})\)"
        # get our match
        matched = re.match(regex, movie)
        # if we can match the standard arm output format "Movie (year)"
        if matched:
            poster_image, imdb_id = get_omdb_poster(matched.group(1), matched.group(2))
            app.logger.debug(os.path.join(my_path, str(movie)))
            app.logger.debug(str(os.listdir(os.path.join(my_path, str(movie)))))
            movies[i] = ui_utils.import_movie_add(poster_image,
                                                  imdb_id, matched,
                                                  os.path.join(my_path, str(movie)))
        else:
            # If we didn't get a match assume that the directory is a main directory for other folders
            # This means we can check for "series" type movie folders e.g
            # - Lord of the rings
            #     - The Lord of the Rings The Fellowship of the Ring (2001)
            #     - The Lord of the Rings The Two Towers (2002)
            #     - The Lord of the Rings The Return of the King (2003)
            #
            sub_path = os.path.join(my_path, str(movie))
            # Go through each folder and treat it as a sub-folder of movie folder
            subfiles = ui_utils.generate_file_list(sub_path)
            for sub_movie in subfiles:
                sub_matched = re.match(regex, sub_movie)
                if sub_matched:
                    # Fix poster image and imdb_id
                    poster_image, imdb_id = get_omdb_poster(sub_matched.group(1), sub_matched.group(2))
                    app.logger.debug(os.listdir(os.path.join(sub_path, str(sub_movie))))
                    # Add the movies to the main movie dict
                    movies[i] = ui_utils.import_movie_add(poster_image,
                                                          imdb_id, sub_matched,
                                                          os.path.join(sub_path, str(sub_movie)))
                else:
                    movies[0]['notfound'][str(i)] = str(sub_movie)
            app.logger.debug(subfiles)
        i += 1
    app.logger.debug(movies)
    db.session.commit()
    movies = {k: v for k, v in movies.items() if v}
    return app.response_class(response=json.dumps(movies, indent=4, sort_keys=True),
                              status=200,
                              mimetype=constants.JSON_TYPE)


@app.route('/send_movies', methods=['GET'])
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
