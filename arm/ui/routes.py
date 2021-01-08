import os
import psutil
import platform
import subprocess
import re
import sys  # noqa: F401
import bcrypt
import hashlib  # noqa: F401
import json
import arm.ui.utils as utils
from time import sleep
from flask import Flask, render_template, make_response, abort, request, send_file, flash, redirect, url_for, \
    Markup  # noqa: F401
from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, Alembic_version  # noqa: F401
from arm.config.config import cfg
# from arm.ui.utils import get_info, call_omdb_api, clean_for_filename, generate_comments
from arm.ui.forms import TitleSearchForm, ChangeParamsForm, CustomTitleForm
from pathlib import Path, PurePath
from flask.logging import default_handler  # noqa: F401

from flask_login import LoginManager, login_required, current_user, login_user, UserMixin  # noqa: F401

#  the login manager
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


@app.route('/setup')
def setup():
    perm_file = Path(PurePath(cfg['INSTALLPATH'], "installed"))
    app.logger.debug("perm " + str(perm_file))
    if perm_file.exists():
        flash(str(perm_file) + " exists, setup cannot continue. To re-install please delete this file.")
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
            flash("{} was created successfully.".format(str(dir0)))
        if not Path.exists(dir1):
            os.makedirs(dir1)
            flash("{} was created successfully.".format(str(dir1)))
        if not Path.exists(dir2):
            os.makedirs(dir2)
            flash("{} was created successfully.".format(str(dir2)))
        if not Path.exists(dir3):
            os.makedirs(dir3)
            flash("{} was created successfully.".format(str(dir3)))
        if not Path.exists(dir4):
            os.makedirs(dir4)
            flash("{} was created successfully.".format(str(dir4)))
    except FileNotFoundError as e:
        flash("Creation of the directory {} failed {}".format(str(dir0), e))
        app.logger.debug("Creation of the directory failed - {}".format(str(e)))
    else:
        flash("Successfully created all of the ARM directories")
        app.logger.debug("Successfully created all of the ARM directories")

    try:
        if utils.setupdatabase():
            flash("Setup of the database was successful.")
            app.logger.debug("Setup of the database was successful.")
            perm_file = Path(PurePath(cfg['INSTALLPATH'], "installed"))
            f = open(perm_file, "w")
            f.write("boop!")
            f.close()
            return redirect('/setup-stage2')
        else:
            flash("Couldn't setup database")
            app.logger.debug("Couldn't setup database")
            return redirect("/error")
    except Exception as e:
        flash(str(e))
        app.logger.debug("Setup - " + str(e))
        return redirect('/index')


@app.route('/error')
def was_error():
    return render_template('error.html', title='error')


@app.route('/setup-stage2', methods=['GET', 'POST'])
def setup_stage2():
    # if there is no user in the database
    try:
        # Return the user to login screen if we dont error when calling for any users
        users = User.query.all()
        if users:
            # TODO remove all flash() and use the nicer ui
            flash('You cannot create more than 1 admin account')
            return redirect(url_for('login'))
        # return redirect('/login')
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

        if request.form['username'] != "" and request.form['password'] != "":
            hashedpassword = bcrypt.hashpw(pass1, hash)
            user = User(email=username, password=hashedpassword, hashed=hash)
            # app.logger.debug("user: " + str(username) + " Pass:" + str(pass1))
            # app.logger.debug("user db " + str(user))
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                flash(str(e))
                return redirect('/setup-stage2')
            else:
                return redirect(url_for('login'))
        else:
            # app.logger.debug("user: "+ str(username) + " Pass:" + pass1 )
            flash("error something was blank")
            return redirect('/setup-stage2')
    return render_template('setup.html', title='setup')


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
    # Success gives the user feedback to let them know if the delete worked
    success = False
    saved = False
    # Check for database file
    if os.path.isfile(cfg['DBFILE']):
        # jobs = Job.query.filter_by(status="active")
        jobs = Job.query.filter_by()
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
                        cmd = 'cp ' + str(cfg['DBFILE']) + ' ' + str(cfg['DBFILE']) + '.bak'
                        app.logger.info("cmd  -  {0}".format(cmd))
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
            app.logger.error("Error:db-1 {0}".format(err))
            success = False

    return render_template('database.html', jobs=jobs, success=success, date_format=cfg['DATE_FORMAT'])


@app.route('/json', methods=['GET', 'POST'])
@login_required
def feed_json():
    x = request.args.get('mode')
    j_id = request.args.get('job')
    logfile = request.args.get('logfile')
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
        j = utils.generate_log(logfile, logpath, j_id)
    elif x == "search":
        app.logger.debug("search")
        j = utils.search(searchq)

    return app.response_class(response=json.dumps(j, indent=4, sort_keys=True),
                              status=200,
                              mimetype='application/json')


# New page for editing/Viewing the ARM config
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    x = ""
    save = False
    try:
        save = request.form['save']
    except KeyError:
        app.logger.debug("no post")

    comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.json")
    try:
        with open(comments_file, "r") as f:
            try:
                comments = json.load(f)
            except Exception as e:
                comments = None
                app.logger.debug("Error with comments file. {}".format(str(e)))
                return render_template("error.html", error=str(e))
    except FileNotFoundError:
        return render_template("error.html", error="Couldn't find the comment.json file")

    if save:
        success = "false"
        # For testing
        x = request.form.to_dict()
        arm_cfg = comments['ARM_CFG_GROUPS']['BEGIN'] + "\n\n"
        for k, v in x.items():
            if k != "save":
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
                # arm_cfg += "{}: \"{}\"\n".format(k, v)
                try:
                    post_value = int(v)
                    arm_cfg += "{}: {}\n".format(k, post_value)
                except ValueError:
                    v_low = v.lower()
                    if v_low == 'false' or v_low == "true":
                        arm_cfg += "{}: {}\n".format(k, v_low)
                    else:
                        if k == "WEBSERVER_IP":
                            arm_cfg += "{}: {}\n".format(k, v_low)
                        else:
                            arm_cfg += "{}: \"{}\"\n".format(k, v)
                app.logger.debug("\n{} = {} ".format(k, v))

        # app.logger.debug("arm_cfg= {}".format(arm_cfg))
        arm_cfg_file = "/opt/arm/arm.yaml"
        app.logger.debug(str(arm_cfg_file))
        with open(arm_cfg_file, "w") as f:
            f.write(arm_cfg)
            f.close()
        success = "true"
        return render_template('settings.html', success=success, settings=cfg,
                               raw=x, jsoncomments=comments)

    # If we get to here there was no post data
    return render_template('settings.html', success="null", settings=cfg, raw=x, jsoncomments=comments)


@app.route('/logreader')
@login_required
def logreader():
    # use logger
    # app.logger.info('Processing default request')
    # app.logger.debug('DEBUGGING')
    # app.logger.error('ERROR Inside /logreader')

    # Setup our vars
    logpath = cfg['LOGPATH']
    mode = request.args.get('mode')
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
        # exit()

    return app.response_class(generate(), mimetype='text/plain')


@app.route('/activerips')
@login_required
def rips():
    return render_template('activerips.html', jobs=Job.query.filter_by(status="active"))


@app.route('/history')
@login_required
def history():
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
    job_id = request.args.get('job_id')
    jobs = Job.query.get(job_id)
    tracks = jobs.tracks.all()
    return render_template('jobdetail.html', jobs=jobs, tracks=tracks, success="null")


@app.route('/abandon', methods=['GET', 'POST'])
@login_required
def abandon_job():
    job_id = request.args.get('job_id')
    # TODO add a confirm and then
    #  delete the raw folder (this will cause ARM to bail)
    try:
        # This should be none if we aren't set
        job = Job.query.get(job_id)
        job.status = "fail"
        db.session.commit()
        return render_template('jobdetail.html', success="true", jobmessage="Job was abandoned!", jobs=job)
    except Exception as e:
        flash("Failed to update job" + str(e))
        return render_template('error.html')


@app.route('/titlesearch', methods=['GET', 'POST'])
@login_required
def submitrip():
    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    form = TitleSearchForm(obj=job)
    if form.validate_on_submit():
        form.populate_obj(job)
        flash('Search for {}, year={}'.format(form.title.data, form.year.data), category='success')
        return redirect(url_for('list_titles', title=form.title.data, year=form.year.data, job_id=job_id))
    return render_template('titlesearch.html', title='Update Title', form=form)


@app.route('/changeparams', methods=['GET', 'POST'])
@login_required
def changeparams():
    config_id = request.args.get('config_id')
    config = Config.query.get(config_id)
    job = Job.query.get(config_id)
    form = ChangeParamsForm(obj=config)
    if form.validate_on_submit():
        config.MINLENGTH = format(form.MINLENGTH.data)
        config.MAXLENGTH = format(form.MAXLENGTH.data)
        config.RIPMETHOD = format(form.RIPMETHOD.data)
        config.MAINFEATURE = int(format(form.MAINFEATURE.data) == 'true')
        # config.MAINFEATURE = int(format(form.MAINFEATURE.data)) #  must be 1 for True 0 for False
        job.disctype = format(form.DISCTYPE.data)
        db.session.commit()
        flash(
            'Parameters changed. Rip Method={}, Main Feature={}, Minimum Length={}, '
            'Maximum Length={}, Disctype={}'.format(
                form.RIPMETHOD.data, form.MAINFEATURE.data, form.MINLENGTH.data, form.MAXLENGTH.data,
                form.DISCTYPE.data))
        return redirect(url_for('home'))
    return render_template('changeparams.html', title='Change Parameters', form=form)


@app.route('/customTitle', methods=['GET', 'POST'])
@login_required
def customtitle():
    job_id = request.args.get('job_id')
    job = Job.query.get(job_id)
    form = CustomTitleForm(obj=job)
    if form.validate_on_submit():
        form.populate_obj(job)
        job.title = format(form.title.data)
        job.year = format(form.year.data)
        db.session.commit()
        flash('custom title changed. Title={}, Year={}.'.format(form.title.data, form.year.data))
        return redirect(url_for('home'))
    return render_template('customTitle.html', title='Change Title', form=form)


@app.route('/list_titles')
@login_required
def list_titles():
    title = request.args.get('title').strip() if request.args.get('title') else ''
    year = request.args.get('year').strip() if request.args.get('year') else ''
    job_id = request.args.get('job_id').strip() if request.args.get('job_id') else ''
    if job_id == "":
        app.logger.debug("list_titles - no job supplied")
        flash("No job supplied")
        return redirect('/error')
    dvd_info = utils.call_omdb_api(title, year)
    return render_template('list_titles.html', results=dvd_info, job_id=job_id)


@app.route('/gettitle', methods=['GET', 'POST'])
@login_required
def gettitle():
    imdb_id = request.args.get('imdbID').strip() if request.args.get('imdbID') else ''
    job_id = request.args.get('job_id').strip() if request.args.get('job_id') else ''
    if job_id == "":
        app.logger.debug("gettitle - no job supplied")
        flash("No job supplied")
        return redirect('/error')
    dvd_info = utils.call_omdb_api(None, None, imdb_id, "full")
    return render_template('showtitle.html', results=dvd_info, job_id=job_id)


@app.route('/updatetitle', methods=['GET', 'POST'])
@login_required
def updatetitle():
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
    flash('Title: {} ({}) was updated to {} ({})'.format(job.title_auto, job.year_auto, new_title, new_year),
          category='success')
    return redirect(url_for('home'))


@app.route('/logs')
@login_required
def logs():
    mode = request.args['mode']
    logfile = request.args['logfile']

    return render_template('logview.html', file=logfile, mode=mode)


@app.route('/listlogs', defaults={'path': ''})
@login_required
def listlogs(path):
    basepath = cfg['LOGPATH']
    fullpath = os.path.join(basepath, path)

    # Deal with bad data
    if not os.path.exists(fullpath):
        return render_template('error.html')

    # Get all files in directory
    files = utils.get_info(fullpath)
    return render_template('logfiles.html', files=files, date_format=cfg['DATE_FORMAT'])


@app.route('/')
@app.route('/index.html')
@app.route('/index')
def home():
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
        flash("There was a problem accessing the ARM folders. Please make sure you have setup the ARMui")
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
        temp = None

    if os.path.isfile(cfg['DBFILE']):
        # jobs = Job.query.filter_by(status="active")
        try:
            jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()
        except Exception:
            # db isnt setup
            return redirect(url_for('setup'))
        for job in jobs:
            if job.logfile is not None:
                job_log = cfg['LOGPATH'] + str(job.logfile)
                line = subprocess.check_output(['tail', '-n', '1', str(job_log)])
                # job_status = re.search("([0-9]{1,2}\.[0-9]{2}) %.*ETA ([0-9]{2})h([0-9]{2})m([0-9]{2})s", str(line))
                # ([0-9]{1,3}\.[0-9]{2}) %.*(?!ETA) ([0-9hms]*?)\)  # This is more dumb but it returns with the h m s
                # job_status = re.search(r"([0-9]{1,2}\.[0-9]{2}) %.*ETA\s([0-9hms]*?)\)", str(line))
                # This correctly get the very last ETA and %
                job_status = re.search(r"([0-9]{1,3}\.[0-9]{2}) %.{0,40}ETA ([0-9hms]*?)\)(?!\\rEncod)", str(line))
                if job_status:
                    job.progress = job_status.group(1)
                    # job.eta = job_status.group(2)+":"+job_status.group(3)+":"+job_status.group(4)
                    job.eta = job_status.group(2)
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


#  Lets show some cpu info
#  only tested on OMV
def get_processor_name():
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
        amd_name_full = re.search(r"vendor_id\\t:(.*?)\\n", fulldump)
        if amd_name_full:
            amd_name = amd_name_full.group(1)
            amd_hz = re.search(r"cpu\sMHz\\t.*?([.0-9]*?)\\n", fulldump)  # noqa: W605
            if amd_hz:
                amd_ghz = re.sub('[^.0-9]', '', amd_hz.group())
                amd_ghz = int(float(amd_ghz))  # Not sure this is a good idea
                return str(amd_name) + " @" + str(amd_ghz) + " GHz"
    return None  # We didnt find our cpu
