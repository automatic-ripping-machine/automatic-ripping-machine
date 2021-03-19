import os
import psutil
import platform
import subprocess
import re
import sys  # noqa: F401
import bcrypt
import hashlib
import json
import yaml
import requests
import arm.ui.utils as utils

from time import sleep
from flask import Flask, render_template, make_response, abort, request, send_file, flash, \
    redirect, url_for  # noqa: F401
from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, Alembic_version, UISettings  # noqa: F401
from arm.config.config import cfg
from arm.ui.forms import TitleSearchForm, ChangeParamsForm, CustomTitleForm, SettingsForm
from pathlib import Path, PurePath
from flask.logging import default_handler  # noqa: F401
from flask_login import LoginManager, login_required, current_user, login_user, UserMixin, logout_user  # noqa: F401

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except Exception:
        app.logger.debug("error getting user")
        # return redirect('/login')


#  Redirect to login if we arent auth
@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/login')


@app.route('/error')
def was_error():
    return render_template('error.html', title='error')


@app.route("/logout")
def logout():
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
    if perm_file.exists():
        flash(str(perm_file) + " exists, setup cannot continue. To re-install please delete this file.", "danger")
        app.logger.debug("perm exist GTFO")
        return redirect('/setup-stage2')  # We push to setup-stage2 and let it decide where the user needs to go
    dir0 = Path(PurePath(cfg['DBFILE']).parent)
    dir1 = Path(cfg['ARMPATH'])
    dir2 = Path(cfg['RAWPATH'])
    dir3 = Path(cfg['MEDIA_DIR'])
    dir4 = Path(cfg['LOGPATH'])
    app.logger.debug("dir0 " + str(dir0))
    app.logger.debug("dir1 " + str(dir1))
    app.logger.debug("dir2 " + str(dir2))
    app.logger.debug("dir3 " + str(dir3))
    app.logger.debug("dir4 " + str(dir4))
    try:
        if not Path.exists(dir0):
            os.makedirs(dir0)
            flash(f"{dir0} was created successfully.")
        if not Path.exists(dir1):
            os.makedirs(dir1)
            flash(f"{dir1} was created successfully.")
        if not Path.exists(dir2):
            os.makedirs(dir2)
            flash(f"{dir2} was created successfully.")
        if not Path.exists(dir3):
            os.makedirs(dir3)
            flash(f"{dir3} was created successfully.")
        if not Path.exists(dir4):
            os.makedirs(dir4)
            flash(f"{dir4} was created successfully.")
    except FileNotFoundError as e:
        flash(f"Creation of the directory {dir0} failed {e}", "danger")
        app.logger.debug(f"Creation of the directory failed - {e}")
    else:
        flash("Successfully created all of the ARM directories", "success")
        app.logger.debug("Successfully created all of the ARM directories")

    try:
        if utils.setupdatabase():
            flash("Setup of the database was successful.", "success")
            app.logger.debug("Setup of the database was successful.")
            perm_file = Path(PurePath(cfg['INSTALLPATH'], "installed"))
            f = open(perm_file, "w")
            f.write("boop!")
            f.close()
            return redirect('/setup-stage2')
        else:
            flash("Couldn't setup database", "danger")
            app.logger.debug("Couldn't setup database")
            return redirect("/error")
    except Exception as e:
        flash(str(e))
        app.logger.debug("Setup - " + str(e))
        return redirect('/index')


@app.route('/setup-stage2', methods=['GET', 'POST'])
def setup_stage2():
    """
    This is the second stage of setup this will allow the user to create an admin account
    this will also be the page for resetting the admin account password
    """
    over = request.values.get('override') if request.method == 'POST' else request.args.get('override')
    try:
        # Return the user to login screen if we dont error when calling for any users
        users = User.query.all()
        if users and over is None:
            flash("over = " + over)
            flash('You cannot create more than 1 admin account')
            return redirect(url_for('login'))
    except Exception:
        # return redirect('/index')
        app.logger.debug("No admin account found")

    save = False
    try:
        save = request.form['save']
    except KeyError:
        app.logger.debug("no post")

    # After a login for is submitted
    if save:
        username = str(request.form['username']).strip()
        pass1 = str(request.form['password']).strip().encode('utf-8')
        hash = bcrypt.gensalt(12)

        if username and pass1:
            user = User.query.filter_by(email=username).first()
            hashedpassword = bcrypt.hashpw(pass1, hash)
            if user is None:
                user = User(email=username, password=hashedpassword, hashed=hash)
                db.session.add(user)
            else:
                user.password = hashedpassword
                user.hash = hash
                app.logger.debug("hashedpass = " + str(hashedpassword))
            app.logger.debug("user: " + username + " Pass:" + pass1.decode('utf-8'))
            app.logger.debug("user db " + str(user))

            try:
                db.session.commit()
            except Exception as e:
                flash(str(e), "danger")
                return redirect('/setup-stage2')
            else:
                return redirect(url_for('login'))
        else:
            app.logger.debug("user: " + str(username) + " Pass:" + pass1)
            flash("error something was blank")
            return redirect('/setup-stage2')
    return render_template('setup.html', title='setup', override=over)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # if there is no user in the database
    try:
        x = User.query.all()
        # If we dont raise an exception but the usr table is empty
        if not x:
            return redirect('/setup-stage2')
    except Exception:
        flash("No admin account found")
        app.logger.debug("No admin account found")
        return redirect('/setup-stage2')

    # if user is logged in
    if current_user.is_authenticated:
        return redirect('/index')
    save = False
    try:
        save = request.form['save']
    except KeyError:
        app.logger.debug("no post")

    # After a login for is submitted
    if save:
        email = request.form['username']
        # TODO: we know there is only ever 1 admin account,
        #  so we can pull it and check against it locally
        user = User.query.filter_by(email=str(email).strip()).first()
        if user is None:
            return render_template('login.html', success="false", raw='Invalid username')
        app.logger.debug("user= " + str(user))
        # our previous pass
        password = user.password
        hashed = user.hash
        # our new one
        loginhashed = bcrypt.hashpw(str(request.form['password']).strip().encode('utf-8'), hashed)
        # app.logger.debug(loginhashed)
        # app.logger.debug(password)

        if loginhashed == password:
            login_user(user)
            app.logger.debug("user was logged in - redirecting")
            return redirect('/index')
        elif user is None:
            return render_template('login.html', success="false", raw='Invalid username')
        else:
            return render_template('login.html', success="false", raw='Invalid Password')

        # return redirect(url_for('home'))
    return render_template('login.html', title='Sign In')


@app.route('/database')
@login_required
def database():
    """
    The main database page

    Currently outputs every job from the databse - this can cause serious slow downs with + 3/4000 entries
    Pagination is needed!
    """
    # Success gives the user feedback to let them know if the delete worked
    success = False
    saved = False
    # Check for database file
    if os.path.isfile(cfg['DBFILE']):
        # jobs = Job.query.filter_by(status="active")
        jobs = Job.query.filter_by().order_by(db.desc(Job.job_id))
    else:
        app.logger.error('ERROR: /database no database, file doesnt exist')
        jobs = {}
    # Try to see if we have the arg set, if not ignore the error
    try:
        mode = request.args['mode']
        jobid = request.args['jobid']
        saved = True
    except Exception:
        app.logger.debug("/database - no vars set")

    if saved:
        try:
            # Find the job the user wants to delete
            if mode == 'delete' and jobid is not None:
                # User wants to wipe the whole database
                # Make a backup and everything
                # The user can only access this by typing it manually
                if jobid == 'all':
                    if os.path.isfile(cfg['DBFILE']):
                        # Make a backup of the database file
                        cmd = f'cp {cfg["DBFILE"]} {cfg["DBFILE"]}.bak'
                        app.logger.info(f"cmd  -  {cmd}")
                        os.system(cmd)
                    Track.query.delete()
                    Job.query.delete()
                    Config.query.delete()
                    db.session.commit()
                    success = True
                    """elif jobid == "logfile":
                    #  The user can only access this by typing it manually
                    #  This shouldnt be left on when on a full server
                    logfile = request.args['file']
                    Job.query.filter_by(title=logfile).delete()
                    db.session.commit()
                    """
                    # Not sure this is the greatest way of handling this
                else:
                    Track.query.filter_by(job_id=jobid).delete()
                    Job.query.filter_by(job_id=jobid).delete()
                    Config.query.filter_by(job_id=jobid).delete()
                    db.session.commit()
                    success = True
        # If we run into problems with the datebase changes
        # error out to the log and roll back
        except Exception as err:
            db.session.rollback()
            app.logger.error(f"Error:db-1 {err}")
            success = False

    return render_template('database.html', jobs=jobs, success=success, date_format=cfg['DATE_FORMAT'])


@app.route('/json', methods=['GET', 'POST'])
@login_required
def feed_json():
    """
    json mini API
    This is used for all api/ajax calls this makes thing easier to read/code for
    Adding a new function to the api is as simple as adding a new elif where GET[mode]
    is your call
    You can then add a function inside utils to deal with the request
    """
    j = {}
    x = request.args.get('mode')
    j_id = request.args.get('job')
    # We should never let the user pick the log file
    # logfile = request.args.get('logfile')
    searchq = request.args.get('q')
    logpath = cfg['LOGPATH']
    if x is None:
        j = utils.generate_comments()
    elif x == "delete":
        j = utils.delete_job(j_id, x)
        # app.logger.debug("delete")
    elif x == "abandon":
        j = utils.abandon_job(j_id)
        # app.logger.debug("abandon")
    elif x == "full":
        app.logger.debug("getlog")
        j = utils.generate_log(logpath, j_id)
    elif x == "search":
        app.logger.debug("search")
        j = utils.search(searchq)
    elif x == "getfailed":
        app.logger.debug("getfailed")
        j = utils.get_x_jobs("fail")
    elif x == "getsuccessful":
        app.logger.debug("getsucessful")
        j = utils.get_x_jobs("success")
    elif x == "joblist":
        app.logger.debug("joblist")
        j = utils.get_x_jobs("joblist")
    elif x == "fixperms":
        app.logger.debug("fixperms")
        j = utils.fix_permissions(j_id)
    return app.response_class(response=json.dumps(j, indent=4, sort_keys=True),
                              status=200,
                              mimetype='application/json')


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """
    The settings page - allows the user to update the arm.yaml without needing to open a text editor
    Also triggers a restart of flask for debugging.
    This wont work well if flask isnt run in debug mode

    This needs rewritten to be static
    """
    x = ""
    arm_cfg_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..", "arm.yaml")
    comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.json")
    try:
        with open(comments_file, "r") as f:
            try:
                comments = json.load(f)
            except Exception as e:
                app.logger.debug(f"Error with comments file. {e}")
                return render_template("error.html", error=str(e))
    except FileNotFoundError:
        return render_template("error.html", error="Couldn't find the comment.json file")
    # Import the cfg again as we want the latest values, not stale.
    try:
        with open(arm_cfg_file, "r") as f:
            try:
                cfg = yaml.load(f, Loader=yaml.FullLoader)
            except Exception:
                cfg = yaml.safe_load(f)  # For older versions use this
    except FileNotFoundError:
        return render_template("error.html", error="Couldn't find the arm.yaml file")
    form = SettingsForm()
    if form.validate_on_submit():
        # For testing
        x = request.form.to_dict()
        arm_cfg = comments['ARM_CFG_GROUPS']['BEGIN'] + "\n\n"
        # TODO: This is not the safest way to do things. It assumes the user isn't trying to mess with us.
        # This really should be hard coded.
        for k, v in x.items():
            if k != "csrf_token":
                if k == "ARMPATH":
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['DIR_SETUP']
                elif k == "WEBSERVER_IP":
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['WEB_SERVER']
                elif k == "SET_MEDIA_PERMISSIONS":
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['FILE_PERMS']
                elif k == "RIPMETHOD":
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['MAKE_MKV']
                elif k == "HB_PRESET_DVD":
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['HANDBRAKE']
                elif k == "EMBY_REFRESH":
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['EMBY']
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['EMBY_ADDITIONAL']
                elif k == "NOTIFY_RIP":
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['NOTIFY_PERMS']
                elif k == "APPRISE":
                    arm_cfg += "\n" + comments['ARM_CFG_GROUPS']['APPRISE']

                arm_cfg += "\n" + comments[str(k)] + "\n" if comments[str(k)] != "" else ""

                try:
                    post_value = int(v)
                    arm_cfg += f"{k}: {post_value}\n"
                except ValueError:
                    v_low = v.lower()
                    if v_low == 'false' or v_low == "true":
                        arm_cfg += f"{k}: {v_low}\n"
                    else:
                        if k == "WEBSERVER_IP":
                            arm_cfg += f"{k}: {v_low}\n"
                        else:
                            arm_cfg += f"{k}: \"{v}\"\n"
                # app.logger.debug(f"\n{k} = {v} ")

        # app.logger.debug(f"arm_cfg= {arm_cfg}")
        with open(arm_cfg_file, "w") as f:
            f.write(arm_cfg)
            f.close()
        # Now we update the file modified time to get flask to restart
        import datetime

        def set_file_last_modified(file_path, dt):
            dt_epoch = dt.timestamp()
            os.utime(file_path, (dt_epoch, dt_epoch))

        now = datetime.datetime.now()
        arm_main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes.py")
        set_file_last_modified(arm_main, now)

        flash("Setting saved successfully!", "success")
        return redirect(url_for('settings'))
    # If we get to here there was no post data
    return render_template('settings.html', settings=cfg, form=form, raw=x, jsoncomments=comments)


@app.route('/ui_settings', methods=['GET', 'POST'])
@login_required
def ui_settings():
    """
    The settings page - allows the user to update the arm.yaml without needing to open a text editor
    Also triggers a restart of flask for debugging.
    This wont work well if flask isnt run in debug mode

    This needs rewritten to be static
    """
    armui_cfg = UISettings.query.filter_by().first()
    return render_template('ui_settings.html', form=SettingsForm(), settings=armui_cfg)


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
    basepath = cfg['LOGPATH']
    fullpath = os.path.join(basepath, path)

    # Deal with bad data
    if not os.path.exists(fullpath):
        return render_template('error.html')

    # Get all files in directory
    files = utils.get_info(fullpath)
    return render_template('logfiles.html', files=files, date_format=cfg['DATE_FORMAT'])


@app.route('/logreader')
@login_required
def logreader():
    """
    The default logreader output function

    This will display or allow downloading the requested logfile
    This is where the XHR requests are sent when viewing /logs?=logfile
    """
    # use logger
    # app.logger.info('Processing default request')
    # app.logger.debug('DEBUGGING')
    # app.logger.error('ERROR Inside /logreader')

    # Setup our vars
    logpath = cfg['LOGPATH']
    mode = request.args.get('mode')
    # We should use the job id and not get the raw logfile from the user
    logfile = request.args.get('logfile')
    if logfile is None or "../" in logfile or mode is None:
        return render_template('error.html')
    # Assemble full path
    fullpath = os.path.join(logpath, logfile)
    # Check if the logfile exists
    my_file = Path(fullpath)
    if not my_file.is_file():
        # logfile doesnt exist throw out error template
        return render_template('simple_error.html')

    # Only ARM logs
    if mode == "armcat":
        def generate():
            f = open(fullpath)
            while True:
                new = f.readline()
                if new:
                    if "ARM:" in new:
                        yield new
                else:
                    sleep(1)
    # Give everything / Tail
    elif mode == "full":
        def generate():
            try:
                with open(fullpath) as f:
                    while True:
                        yield f.read()
                        sleep(1)
            except Exception:
                try:
                    with open(fullpath, encoding="utf8", errors='ignore') as f:
                        while True:
                            yield f.read()
                            sleep(1)
                except Exception:
                    return render_template('simple_error.html')
    elif mode == "download":
        app.logger.debug('fullpath: ' + fullpath)
        return send_file(fullpath, as_attachment=True)
    else:
        # do nothing/ or error out
        return render_template('error.html')

    return app.response_class(generate(), mimetype='text/plain')


@app.route('/activerips')
@login_required
def rips():
    """
    This no longer works properly because of the 'transcoding' status
    """
    return render_template('activerips.html', jobs=Job.query.filter_by(status="active"))


@app.route('/history')
@login_required
def history():
    """
    Smaller much simpler output of previously run jobs

    """
    if os.path.isfile(cfg['DBFILE']):
        # jobs = Job.query.filter_by(status="active")
        jobs = Job.query.filter_by()
    else:
        app.logger.error('ERROR: /history database file doesnt exist')
        jobs = {}
    app.logger.debug(cfg['DATE_FORMAT'])

    return render_template('history.html', jobs=jobs, date_format=cfg['DATE_FORMAT'])


@app.route('/jobdetail', methods=['GET', 'POST'])
@login_required
def jobdetail():
    """
    Page for showing in-depth details about a job

    Shows Job/Config/Track class details
    displays them in a clear and easy to ready format
    """
    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    tracks = job.tracks.all()
    s = utils.metadata_selector("get_details", job.title, job.year, job.imdb_id)
    if s and 'Error' not in s:
        job.plot = s['Plot'] if 'Plot' in s else "There was a problem getting the plot"
        job.background = s['background_url'] if 'background_url' in s else None
    return render_template('jobdetail.html', jobs=job, tracks=tracks, s=s)


@app.route('/titlesearch', methods=['GET', 'POST'])
@login_required
def submitrip():
    """
    ...
    """
    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    form = TitleSearchForm(obj=job)
    if form.validate_on_submit():
        form.populate_obj(job)
        flash(f'Search for {form.title.data}, year={form.year.data}', 'success')
        return redirect(url_for('list_titles', title=form.title.data, year=form.year.data, job_id=job_id))
    return render_template('titlesearch.html', title='Update Title', form=form, job=job)


@app.route('/changeparams', methods=['GET', 'POST'])
@login_required
def changeparams():
    """
    For updating Config params or changing/correcting disctype manually
    """
    config_id = request.args.get('config_id')
    # app.logger.debug(config.pretty_table())
    job = Job.query.get(config_id)
    config = job.config
    for key, value in cfg.items():
        setattr(config, key, value)
    form = ChangeParamsForm(obj=config)
    if form.validate_on_submit():
        cfg["MINLENGTH"] = config.MINLENGTH = format(form.MINLENGTH.data)
        cfg["MAXLENGTH"] = config.MAXLENGTH = format(form.MAXLENGTH.data)
        cfg["RIPMETHOD"] = config.RIPMETHOD = format(form.RIPMETHOD.data)
        cfg["MAINFEATURE"] = config.MAINFEATURE = bool(format(form.MAINFEATURE.data))  # must be 1 for True 0 for False
        app.logger.debug(f"main={config.MAINFEATURE}")
        job.disctype = format(form.DISCTYPE.data)
        db.session.commit()
        db.session.refresh(job)
        db.session.refresh(config)
        flash(f'Parameters changed. Rip Method={config.RIPMETHOD}, Main Feature={config.MAINFEATURE},'
              f'Minimum Length={config.MINLENGTH}, '
              f'Maximum Length={config.MAXLENGTH}, Disctype={job.disctype}', "success")
        return redirect(url_for('home'))
    return render_template('changeparams.html', title='Change Parameters', form=form)


@app.route('/customTitle', methods=['GET', 'POST'])
@login_required
def customtitle():
    """
    For setting custom title for series with multiple discs
    """
    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    form = CustomTitleForm(obj=job)
    if form.validate_on_submit():
        form.populate_obj(job)
        job.title = format(form.title.data)
        job.year = format(form.year.data)
        db.session.commit()
        flash(f'custom title changed. Title={form.title.data}, Year={form.year.data}.', "success")
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
        flash("No job supplied", "danger")
        return redirect('/error')

    search_results = utils.metadata_selector("search", title, year)
    return render_template('list_titles.html', results=search_results, job_id=job_id)


@app.route('/gettitle', methods=['GET', 'POST'])
@app.route('/select_title', methods=['GET', 'POST'])
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
        return redirect('/error')
    if job_id == "" or job_id is None:
        app.logger.debug("gettitle - no job supplied")
        flash("No job supplied", "danger")
        return redirect('/error')
    dvd_info = utils.metadata_selector("get_details", None, None, imdb_id)
    return render_template('showtitle.html', results=dvd_info, job_id=job_id)


@app.route('/updatetitle', methods=['GET', 'POST'])
@login_required
def updatetitle():
    """
    ...
    """
    # updatetitle?title=Home&amp;year=2015&amp;imdbID=tt2224026&amp;type=movie&amp;
    #  poster=http://image.tmdb.org/t/p/original/usFenYnk6mr8C62dB1MoAfSWMGR.jpg&amp;job_id=109
    new_title = request.args.get('title')
    new_year = request.args.get('year')
    video_type = request.args.get('type')
    imdb_id = request.args.get('imdbID')
    poster_url = request.args.get('poster')
    job_id = request.args.get('job_id')
    app.logger.debug("New imdbID=" + str(imdb_id))
    job = Job.query.get(job_id)
    job.title = utils.clean_for_filename(new_title)
    job.title_manual = utils.clean_for_filename(new_title)
    job.year = new_year
    job.year_manual = new_year
    job.video_type_manual = video_type
    job.video_type = video_type
    job.imdb_id_manual = imdb_id
    job.imdb_id = imdb_id
    job.poster_url_manual = poster_url
    job.poster_url = poster_url
    job.hasnicetitle = True
    db.session.commit()
    # TODO: show the previous values that were set, not just assume it was _auto
    flash(f'Title: {job.title_auto} ({job.year_auto}) was updated to {new_title} ({new_year})', "success")
    return redirect(request.referrer)


@app.route('/')
@app.route('/index.html')
@app.route('/index')
def home():
    """
    The main homepage showing current rips and server stats
    """
    # app.logger.info('Processing default request')
    # app.logger.debug('DEBUGGING')
    # app.logger.error('ERROR Inside /logreader')

    # Hard drive space
    try:
        freegb = psutil.disk_usage(cfg['ARMPATH']).free
        freegb = round(freegb / 1073741824, 1)
        arm_percent = psutil.disk_usage(cfg['ARMPATH']).percent
        mfreegb = psutil.disk_usage(cfg['MEDIA_DIR']).free
        mfreegb = round(mfreegb / 1073741824, 1)
        media_percent = psutil.disk_usage(cfg['MEDIA_DIR']).percent
    except FileNotFoundError:
        freegb = 0
        arm_percent = 0
        mfreegb = 0
        media_percent = 0
        app.logger.debug("ARM folders not found")
        flash("There was a problem accessing the ARM folders. Please make sure you have setup the ARMui", "danger")
        # We could check for the install file here  and then error out if we want
    #  RAM
    memory = psutil.virtual_memory()
    mem_total = round(memory.total / 1073741824, 1)
    mem_free = round(memory.available / 1073741824, 1)
    mem_used = round(memory.used / 1073741824, 1)
    ram_percent = memory.percent
    #  get out cpu info
    try:
        our_cpu = get_processor_name()
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
        # jobs = Job.query.filter_by(status="active")
        try:
            jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()
        except Exception:
            # db isnt setup
            return redirect(url_for('setup'))
        for job in jobs:
            job_log = cfg['LOGPATH'] + job.logfile
            # Try to catch if the logfile gets delete before the job is finished
            try:
                line = subprocess.check_output(['tail', '-n', '1', job_log])
            except subprocess.CalledProcessError:
                app.logger.debug("Error while reading logfile for ETA")
                line = ""
            # job_status = re.search("([0-9]{1,2}\.[0-9]{2}) %.*ETA ([0-9]{2})h([0-9]{2})m([0-9]{2})s", str(line))
            # ([0-9]{1,3}\.[0-9]{2}) %.*(?!ETA) ([0-9hms]*?)\)  # This is more dumb but it returns with the h m s
            # job_status = re.search(r"([0-9]{1,2}\.[0-9]{2}) %.*ETA\s([0-9hms]*?)\)", str(line))
            # This correctly get the very last ETA and %
            job_status = re.search(r"Encoding: task ([0-9] of [0-9]), ([0-9]{1,3}\.[0-9]{2}) %.{0,40}"
                                   r"ETA ([0-9hms]*?)\)(?!\\rEncod)", str(line))
            if job_status:
                app.logger.debug(str(job_status.group(1)))
                job.stage = job_status.group(1)
                job.progress = job_status.group(2)
                # job.eta = job_status.group(2)+":"+job_status.group(3)+":"+job_status.group(4)
                job.eta = job_status.group(3)
                app.logger.debug("job.progress = " + str(job.progress))
                x = job.progress
                job.progress_round = int(float(x))
                app.logger.debug("Job.round = " + str(job.progress_round))
    else:
        jobs = {}

    return render_template('index.html', freegb=freegb, mfreegb=mfreegb,
                           arm_percent=arm_percent, media_percent=media_percent,
                           jobs=jobs, cpu=our_cpu, cputemp=temp, cpu_usage=cpu_usage,
                           ram=mem_total, ramused=mem_used, ramfree=mem_free, ram_percent=ram_percent,
                           ramdump=str(temps))


@app.route('/import_movies')
@login_required
def import_movies():
    """
    Function for finding all movies not currently tracked by ARM in the MEDIA_DIR
    This should not be run frequently
    This causes a HUGE number of requests to OMdb
    :return: Outputs json - contains a dict/json of movies added and a notfound list
             that doesnt match ARM identified folder format.
    """
    import time
    from os import listdir
    from os.path import isfile, join, isdir
    t0 = time.time()

    my_path = cfg['MEDIA_DIR']
    movies = {0: {'notfound': {}}}
    dest_ext = cfg['DEST_EXT']
    i = 1
    movie_dirs = [f for f in listdir(my_path) if isfile(join(my_path, f)) and not f.startswith(".")
                  or isdir(join(my_path, f)) and not f.startswith(".")]

    app.logger.debug(movie_dirs)
    if len(movie_dirs) < 1:
        app.logger.debug("movie_dirs found none")

    for movie in movie_dirs:
        mystring = f"{movie}"
        regex = r"([\w\ \'\.\-\&\,]*?) \(([0-9]{2,4})\)"
        matched = re.match(regex, movie)
        if matched:
            # This is only for pycharm
            movie_name = re.sub(" ", "%20", matched.group(1).strip())  # movie

            p1, imdb_id = utils.get_omdb_poster(movie_name, matched.group(2))
            # ['poster.jpg', 'title_t00.mkv', 'title_t00.xml', 'fanart.jpg',
            #  'title_t00.nfo-orig', 'title_t00.nfo', 'title_t00.xml-orig', 'folder.jpg']
            app.logger.debug(str(listdir(join(my_path, str(movie)))))
            movie_files = [f for f in listdir(join(my_path, str(movie)))
                           if isfile(join(my_path, str(movie), f)) and f.endswith("." + dest_ext)
                           or isfile(join(my_path, str(movie), f)) and f.endswith(".mp4")
                           or isfile(join(my_path, str(movie), f)) and f.endswith(".avi")]
            app.logger.debug("movie files = " + str(movie_files))

            hash_object = hashlib.md5(mystring.encode())
            dupe_found, x = utils.job_dupe_check(hash_object.hexdigest())
            if dupe_found:
                app.logger.debug("We found dupes breaking loop")
                continue

            movies[i] = {
                'title': matched.group(1),
                'year': matched.group(2),
                'crc_id': hash_object.hexdigest(),
                'imdb_id': imdb_id,
                'poster': p1,
                'status': 'success' if len(movie_files) > 0 else 'fail',
                'video_type': 'movie',
                'disctype': 'unknown',
                'hasnicetitle': True,
                'no_of_titles': len(movie_files)
            }

            new_movie = Job("/dev/sr0")
            new_movie.title = movies[i]['title']
            new_movie.year = movies[i]['year']
            new_movie.crc_id = hash_object.hexdigest()
            new_movie.imdb_id = imdb_id
            new_movie.poster_url = movies[i]['poster']
            new_movie.status = movies[i]['status']
            new_movie.video_type = movies[i]['video_type']
            new_movie.disctype = movies[i]['disctype']
            new_movie.hasnicetitle = movies[i]['hasnicetitle']
            new_movie.no_of_titles = movies[i]['no_of_titles']
            db.session.add(new_movie)
            i += 1
        else:
            sub_path = join(my_path, str(movie))
            # go through each folder and treat it as a subfolder of movie folder
            subfiles = [f for f in listdir(sub_path) if isfile(join(sub_path, f)) and not f.startswith(".")
                        or isdir(join(sub_path, f)) and not f.startswith(".")]
            for sub_movie in subfiles:
                mystring = f"{sub_movie}"
                sub_matched = re.match(regex, sub_movie)
                if sub_matched:
                    # This is only for pycharm
                    sub_movie_name = re.sub(" ", "%20", sub_matched.group(1).strip())  # movie
                    sub_movie_name = re.sub("&", "%26", sub_movie_name)
                    p2, imdb_id = utils.get_omdb_poster(sub_movie_name, sub_matched.group(2))
                    app.logger.debug(listdir(join(sub_path, str(sub_movie))))
                    # If the user selects another ext thats not mkv we are f
                    sub_movie_files = [f for f in listdir(join(sub_path, str(sub_movie)))
                                       if isfile(join(sub_path, str(sub_movie), f)) and f.endswith("." + dest_ext)
                                       or isfile(join(sub_path, str(sub_movie), f)) and f.endswith(".mp4")
                                       or isfile(join(my_path, str(movie), f)) and f.endswith(".avi")]
                    app.logger.debug("movie files = " + str(sub_movie_files))
                    hash_object = hashlib.md5(mystring.encode())
                    dupe_found, x = utils.job_dupe_check(hash_object.hexdigest())
                    if dupe_found:
                        app.logger.debug("We found dupes breaking loop")
                        continue
                    movies[i] = {
                        'title': sub_matched.group(1),
                        'year': sub_matched.group(2),
                        'crc_id': hash_object.hexdigest(),
                        'imdb_id': imdb_id,
                        'poster': p2,
                        'status': 'success' if len(sub_movie_files) > 0 else 'fail',
                        'video_type': 'movie',
                        'disctype': 'unknown',
                        'hasnicetitle': True,
                        'no_of_titles': len(sub_movie_files)
                    }
                    new_movie = Job("/dev/sr0")
                    new_movie.title = movies[i]['title']
                    new_movie.year = movies[i]['year']
                    new_movie.crc_id = hash_object.hexdigest()
                    new_movie.imdb_id = imdb_id
                    new_movie.poster_url = p2
                    new_movie.status = movies[i]['status']
                    new_movie.video_type = movies[i]['video_type']
                    new_movie.disctype = movies[i]['disctype']
                    new_movie.hasnicetitle = movies[i]['hasnicetitle']
                    new_movie.no_of_titles = movies[i]['no_of_titles']
                    db.session.add(new_movie)
                    i += 1
                else:
                    movies[0]['notfound'][str(i)] = str(sub_movie)
            print(subfiles)
    # app.logger.debug(movies)

    t1 = time.time()
    total = round(t1 - t0, 3)
    app.logger.debug(str(total) + " sec")
    db.session.commit()
    return app.response_class(response=json.dumps(movies, indent=4, sort_keys=True),
                              status=200,
                              mimetype='application/json')


@app.route('/send_movies', methods=['GET', 'POST'])
@login_required
def send_movies():
    """
    function for sending all dvd crc64 ids to off-site api
    This isn't very optimised and can be slow and causes a huge number of requests
    """
    if request.args.get('s') is None:
        return render_template('send_movies_form.html')

    posts = db.session.query(Job).filter_by(hasnicetitle=True, disctype="dvd").all()
    app.logger.debug("search - posts=" + str(posts))
    r = {'failed': {}, 'sent': {}}
    i = 0
    api_key = cfg['ARM_API_KEY']

    for p in posts:
        # if i>5:break
        base_url = "https://1337server.pythonanywhere.com"  # This allows easy updates to the API url
        url = f"{base_url}/api/v1/?mode=p&api_key={api_key}&crc64={p.crc_id}&t={p.title}&y={p.year}&imdb={p.imdb_id}" \
              f"&hnt={p.hasnicetitle}&l={p.label}"
        app.logger.debug(url)
        response = requests.get(url)
        req = json.loads(response.text)
        app.logger.debug("req= " + str(req))
        if bool(req['success']):
            x = p.get_d().items()
            r['sent'][i] = {}
            for key, value in iter(x):
                r['sent'][i][str(key)] = str(value)
                # app.logger.debug(str(key) + "= " + str(value))
            i += 1
        else:
            x = p.get_d().items()
            r['failed'][i] = {}
            r['failed'][i]['Error'] = req['Error']
            for key, value in iter(x):
                r['failed'][i][str(key)] = str(value)
                # app.logger.debug(str(key) + "= " + str(value))
            i += 1
    # return {'success': True, 'mode': 'search', 'results': r}
    return render_template('send_movies.html', sent=r['sent'], failed=r['failed'], full=r)


def get_processor_name():
    """
    function to collect and return some cpu info
    ideally want to return {name} @ {speed} Ghz
    """
    if platform.system() == "Windows":
        return platform.processor()
    elif platform.system() == "Darwin":
        return subprocess.check_output(['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]).strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        # return \
        fulldump = str(subprocess.check_output(command, shell=True).strip())
        # Take any float trailing "MHz", some whitespace, and a colon.
        speeds = re.search(r"\\nmodel name\\t:.*?GHz\\n", fulldump)
        if speeds:
            # We have intel CPU
            speeds = str(speeds.group())
            speeds = speeds.replace('\\n', ' ')
            speeds = speeds.replace('\\t', ' ')
            speeds = speeds.replace('model name :', '')
            return speeds

        # AMD CPU
        # model name.*?:(.*?)\n
        # matches = re.search(regex, test_str)
        amd_name_full = re.search(r"model name\\t: (.*?)\\n", fulldump)
        if amd_name_full:
            amd_name = amd_name_full.group(1)
            amd_mhz = re.search(r"cpu MHz(?:\\t)*: ([.0-9]*)\\n", fulldump)  # noqa: W605
            if amd_mhz:
                # amd_ghz = re.sub('[^.0-9]', '', amd_mhz.group())
                amd_ghz = round(float(amd_mhz.group(1)) / 1000, 2)  # this is a good idea
                return str(amd_name) + " @ " + str(amd_ghz) + " GHz"
    return None  # We didnt find our cpu
