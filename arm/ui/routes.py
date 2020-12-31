import os
import psutil
import platform
import subprocess
import re
import sys  # noqa: F401
import bcrypt
import hashlib  # noqa: F401
from time import sleep
from flask import Flask, render_template, make_response, abort, request, send_file, flash, redirect, url_for, \
    Markup  # noqa: F401
from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, Alembic_version  # noqa: F401
from arm.config.config import cfg
from arm.ui.utils import get_info, call_omdb_api, clean_for_filename
from arm.ui.forms import TitleSearchForm, ChangeParamsForm, CustomTitleForm, LoginForm
from pathlib import Path
from flask.logging import default_handler  # noqa: F401

from flask_login import LoginManager, login_required, current_user, login_user, UserMixin  # noqa: F401

#  the login manager
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


#  Redirect to login if we arent auth
@login_manager.unauthorized_handler
def unauthorized():
    # do stuff
    return redirect('/login')


@app.route('/setup')
def setup():
    # TODO Verify this with a secret key in the config for set up
    # So not just anyone can wipe the database
    try:
        if setupdatabase():
            return redirect('/setup-stage2')
        else:
            return redirect("/error")
    except Exception as e:
        flash(str(e))
        return redirect('/index')


@app.route('/setup-stage2', methods=['GET', 'POST'])
def setup_stage2():
    # if there is no user in the database
    try:
        # Return the user to login screen if we dont error when calling for any users
        User.query.all()
        # return redirect('/login')
    except Exception:
        # return redirect('/index')
        app.logger.debug("No admin account found")
    form = LoginForm()

    # After a login for is submited
    if form.validate_on_submit():
        username = str(form.username.data).strip()
        pass1 = str(form.password.data).strip().encode('utf-8')
        hash = bcrypt.gensalt(12)

        if form.username.data != "" and form.password.data != "":
            hashedpassword = bcrypt.hashpw(pass1, hash)
            user = User(email=username, password=hashedpassword, hashed=hash)
            app.logger.debug("user: " + str(username) + " Pass:" + str(pass1))
            app.logger.debug("user db " + str(user))
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                flash(str(e))
                return redirect('/setup-stage2')
        else:
            # app.logger.debug("user: "+ str(username) + " Pass:" + pass1 )
            flash("error something was blank")
            return redirect('/setup-stage2')
    return render_template('setup.html', title='setup', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # if there is no user in the database
    try:
        User.query.all()
    except Exception:
        flash("No admin account found")
        return redirect('/setup-stage2')

    # if user is logged in
    if current_user.is_authenticated:
        return redirect('/index')

    form = LoginForm()

    # After a login for is submited
    if form.validate_on_submit():
        user = User.query.filter_by(email=str(form.username.data).strip()).first()
        if user is None:
            flash('Invalid username')
            return redirect(url_for('login'))
        app.logger.debug("user= " + str(user))
        # our previous pass
        password = user.password
        hashed = user.hash
        # our new one
        loginhashed = bcrypt.hashpw(str(form.password.data).strip().encode('utf-8'), hashed)
        app.logger.debug(loginhashed)
        app.logger.debug(password)

        if loginhashed == password:
            login_user(user)
            flash('Logged in')
        elif user is None:
            flash('Invalid username')
            return redirect(url_for('login'))
        else:
            flash('Invalid pass')
            return redirect(url_for('login'))
        return redirect('/index')
    return render_template('login.html', title='Sign In', form=form)


@app.route('/database')
@login_required
def database():
    # Success gives the user feedback to let them know if the delete worked
    success = False

    # Check for database file
    if os.path.isfile(cfg['DBFILE']):
        # jobs = Job.query.filter_by(status="active")
        jobs = Job.query.filter_by()
    else:
        app.logger.error('ERROR: /database no database, file doesnt exist')
        jobs = {}
    # Try to see if we have the arg set, if not ignore the error
    try:
        # Mode to make sure the users has confirmed
        # jobid if they one to only delete 1 job
        mode = request.args['mode']
        jobid = request.args['jobid']

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
        app.logger.error("Error:  {0}".format(err))

    return render_template('database.html', jobs=jobs, success=success)


# New page for editing/Viewing the ARM config
@app.route('/settings')
@login_required
def settings():
    # This loop syntax accesses the whole dict by looping
    # over the .items() tuple list, accessing one (key, value)
    raw_html = '<form id="form1" name="form1" method="get" action="">'
    # pair on each iteration.
    for k, v in cfg.items():
        raw_html += '<tr> <td><label for="' + str(k) + '"> ' + str(
            k) + ': </label></td> <td><input type="text" name="' + str(k) + '" id="' + str(k) + '" value="' + str(
            v) + '"/></td></tr>'  # noqa: E501
        app.logger.info(str(k) + str(' > ') + str(v) + "\n")
        # app.logger.info(str(raw_html))
    raw_html += " </form>"

    # TODO: Check if the users is posting data
    # For now it only shows the config
    # path1 = os.path.dirname(os.path.abspath(__file__))
    # with open(str(path1) + '/test.json', 'w') as f:
    #    f.write(raw_html + "\n")

    # app.logger.error("Error:  {0}".format(str(cfg)))
    return render_template('settings.html', html=Markup(raw_html), success="")


@app.route('/logreader')
@login_required
def logreader():
    # use logger
    # app.logger.info('Processing default request')
    # app.logger.debug('DEBUGGING')
    # app.logger.error('ERROR Inside /logreader')

    # Setup our vars
    logpath = cfg['LOGPATH']
    mode = request.args['mode']
    logfile = request.args['logfile']

    # Assemble full path
    fullpath = os.path.join(logpath, logfile)
    # Check if the logfile exists
    my_file = Path(fullpath)
    if not my_file.is_file():
        # logfile doesnt exist throw out error template
        return render_template('error.html')

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
            with open(fullpath) as f:
                while True:
                    yield f.read()
                    sleep(1)
    elif mode == "download":
        app.logger.debug('fullpath: ' + fullpath)
        # TODO: strip all keys/secrets
        return send_file(fullpath, as_attachment=True)
    # Give a version thats safe to post online
    elif mode == "onlinepost":
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
        app.logger.error('ERROR: /history not database file doesnt exist')
        jobs = {}

    return render_template('history.html', jobs=jobs)


@app.route('/jobdetail', methods=['GET', 'POST'])
@login_required
def jobdetail():
    job_id = request.args.get('job_id')
    jobs = Job.query.get(job_id)
    tracks = jobs.tracks.all()
    """try:
        if not jobs.poster_url_auto or jobs.poster_url_auto == "None":
            jobs.poster_url_auto = jobs.poster_url = "static/img/none.png"
            db.session.commit()
    except Exception as e:
        jobs.poster_url_auto = jobs.poster_url = "static/img/none.png"
        app.logger.error('ERROR:' + str(e))
        db.session.commit()"""

    return render_template('jobdetail.html', jobs=jobs, tracks=tracks)


@app.route('/abandon', methods=['GET', 'POST'])
@login_required
def abandon_job():
    job_id = request.args.get('job_id')
    # TODO add a confirm and then
    #  delete the raw folder (this will cause ARM to bail)
    try:
        job = Job.query.get(job_id)
        job.status = "fail"
        db.session.commit()
        flash("Job was abandoned!")
        return render_template('jobdetail.html', jobs=job)
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
        # dvd_info = call_omdb_api(form.title.data, form.year.data)
        return redirect(url_for('list_titles', title=form.title.data, year=form.year.data, job_id=job_id))
        # return render_template('list_titles.html', results=dvd_info, job_id=job_id)
        # return redirect('/gettitle', title=form.title.data, year=form.year.data)
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
            'Parameters changed. Rip Method={}, Main Feature={}, Minimum Length={}, Maximum Length={}, Disctype={}'.format(
                form.RIPMETHOD.data, form.MAINFEATURE.data, form.MINLENGTH.data, form.MAXLENGTH.data,
                form.DISCTYPE.data))  # noqa: E501
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
        flash('custom title changed. Title={}, Year={}, '.format(form.title, form.year))
        return redirect(url_for('home'))
    return render_template('customTitle.html', title='Change Title', form=form)


@app.route('/list_titles')
@login_required
def list_titles():
    title = request.args.get('title').strip()
    year = request.args.get('year').strip()
    job_id = request.args.get('job_id')
    dvd_info = call_omdb_api(title, year)
    return render_template('list_titles.html', results=dvd_info, job_id=job_id)


@app.route('/gettitle', methods=['GET', 'POST'])
@login_required
def gettitle():
    imdbID = request.args.get('imdbID')
    job_id = request.args.get('job_id')
    dvd_info = call_omdb_api(None, None, imdbID, "full")
    return render_template('showtitle.html', results=dvd_info, job_id=job_id)


@app.route('/updatetitle', methods=['GET', 'POST'])
@login_required
def updatetitle():
    new_title = request.args.get('title')
    new_year = request.args.get('year')
    video_type = request.args.get('type')
    imdbID = request.args.get('imdbID')
    poster_url = request.args.get('poster')
    job_id = request.args.get('job_id')
    print("New imdbID=" + imdbID)
    job = Job.query.get(job_id)
    job.title = clean_for_filename(new_title)
    job.title_manual = clean_for_filename(new_title)
    job.year = new_year
    job.year_manual = new_year
    job.video_type_manual = video_type
    job.video_type = video_type
    job.imdb_id_manual = imdbID
    job.imdb_id = imdbID
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
    files = get_info(fullpath)
    return render_template('logfiles.html', files=files)


@app.route('/')
@app.route('/index.html')
@app.route('/index')
def home():
    # Hard drive space
    freegb = psutil.disk_usage(cfg['ARMPATH']).free
    freegb = round(freegb / 1073741824, 1)
    mfreegb = psutil.disk_usage(cfg['MEDIA_DIR']).free
    mfreegb = round(mfreegb / 1073741824, 1)

    #  RAM
    meminfo = dict((i.split()[0].rstrip(':'), int(i.split()[1])) for i in open('/proc/meminfo').readlines())
    mem_kib = meminfo['MemTotal']  # e.g. 3921852
    mem_gib = mem_kib / (1024.0 * 1024.0)
    #  lets make sure we only give back small numbers
    mem_gib = round(mem_gib, 2)

    memused_kib = meminfo['MemFree']  # e.g. 3921852
    memused_gib = memused_kib / (1024.0 * 1024.0)
    #  lets make sure we only give back small numbers
    memused_gib = round(memused_gib, 2)
    memused_gibs = round(mem_gib - memused_gib, 2)

    #  get out cpu info
    ourcpu = get_processor_name()

    if os.path.isfile(cfg['DBFILE']):
        # jobs = Job.query.filter_by(status="active")
        jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()
    else:
        jobs = {}

    return render_template('index.html', freegb=freegb, mfreegb=mfreegb, jobs=jobs, cpu=ourcpu, ram=mem_gib,
                           ramused=memused_gibs, ramfree=memused_gib, ramdump=meminfo)  # noqa: E501


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
        # return str(fulldump)
        speeds = str(speeds.group())
        speeds = speeds.replace('\\n', ' ')
        speeds = speeds.replace('\\t', ' ')
        speeds = speeds.replace('model name :', '')
        return speeds
    return ""


def setupdatabase():
    """
    Try to get the db. User if not we nuke everything
    """
    # TODO need to check if all the arm directories have been made
    # logs, media, db
    try:
        User.query.all()
        return True
    except Exception as err:
        #  We only need this on first run
        #  Wipe everything
        flash(str(err))
        try:
            db.drop_all()
        except Exception:
            app.logger.debug("couldnt drop all")
        try:
            #  Recreate everything
            db.metadata.create_all(db.engine)
            # See important note below
            # from arm.models.models import User, Job, Track, Config, Alembic_version
            db.create_all()
            db.session.commit()
            #  push the database version arm is looking for
            user = Alembic_version('c3a3fa694636')
            db.session.add(user)
            db.session.commit()
            return True
        except Exception:
            app.logger.debug("couldnt create all")
