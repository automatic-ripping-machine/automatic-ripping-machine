import os
import platform
import subprocess
import re
import psutil

from time import sleep
from flask import render_template, abort, request, send_file, flash, redirect, url_for
from arm.ui import app, db
from arm.models.models import Job, Config
from arm.config.config import cfg
from arm.ui.utils import convert_log, get_info, call_omdb_api, clean_for_filename
from arm.ui.forms import TitleSearchForm, ChangeParamsForm, CustomTitleForm
from pathlib import Path


@app.route('/logreader')
def logreader():
    #  TODO: check if logfile exist, if not error out
    logpath = cfg['LOGPATH']
    mode = request.args['mode']
    logfile = request.args['logfile']

    # Assemble full path
    fullpath = os.path.join(logpath, logfile)
    #  Check if the logfile exists
    my_file = Path(fullpath)
    if not my_file.is_file():
        # file exists
        # clogfile = convert_log(logfile)
        return render_template('error.html')
        # return send_file("templates/error.html")
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
    elif mode == "full":
        def generate():
            with open(fullpath) as f:
                while True:
                    yield f.read()
                    sleep(1)
    elif mode == "download":
        clogfile = convert_log(logfile)
        return send_file(clogfile, as_attachment=True)
    else:
        # do nothing
        exit()

    return app.response_class(generate(), mimetype='text/plain')


@app.route('/activerips')
def rips():
    return render_template('activerips.html', jobs=Job.query.filter_by(status="active"))


@app.route('/history')
def history():
    if os.path.isfile(cfg['DBFILE']):
        # jobs = Job.query.filter_by(status="active")
        jobs = Job.query.filter_by()
    else:
        jobs = {}

    return render_template('history.html', jobs=jobs)


@app.route('/jobdetail', methods=['GET', 'POST'])
def jobdetail():
    job_id = request.args.get('job_id')
    jobs = Job.query.get(job_id)
    tracks = jobs.tracks.all()

    return render_template('jobdetail.html', jobs=jobs, tracks=tracks)


@app.route('/titlesearch', methods=['GET', 'POST'])
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
def changeparams():
    config_id = request.args.get('config_id')
    config = Config.query.get(config_id)
    app.logger.debug(config.pretty_table())
    job = Job.query.get(config_id)
    form = ChangeParamsForm(obj=config)
    if form.validate_on_submit():
        config.MINLENGTH = format(form.MINLENGTH.data)
        config.MAXLENGTH = format(form.MAXLENGTH.data)
        config.RIPMETHOD = format(form.RIPMETHOD.data)
        # config.MAINFEATURE = int(format(form.MAINFEATURE.data) == 'true')
        config.MAINFEATURE = bool(format(form.MAINFEATURE.data))  # must be 1 for True 0 for False
        app.logger.debug(f"main={config.MAINFEATURE}")
        job.disctype = format(form.DISCTYPE.data)
        db.session.commit()
        db.session.refresh(job)
        db.session.refresh(config)
        flash('Parameters changed. Rip Method={}, Main Feature={}, Minimum Length={}, '
              'Maximum Length={}, Disctype={}'.format(
                config.RIPMETHOD, config.MAINFEATURE, config.MINLENGTH, config.MAXLENGTH,
                job.disctype))
        return redirect(url_for('home'))
    return render_template('changeparams.html', title='Change Parameters', form=form)


@app.route('/customTitle', methods=['GET', 'POST'])
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
def list_titles():
    title = request.args.get('title').strip()
    year = request.args.get('year').strip()
    job_id = request.args.get('job_id')
    dvd_info = call_omdb_api(title, year)
    return render_template('list_titles.html', results=dvd_info, job_id=job_id)


@app.route('/gettitle', methods=['GET', 'POST'])
def gettitle():
    imdbID = request.args.get('imdbID')
    job_id = request.args.get('job_id')
    dvd_info = call_omdb_api(None, None, imdbID, "full")
    return render_template('showtitle.html', results=dvd_info, job_id=job_id)


@app.route('/updatetitle', methods=['GET', 'POST'])
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
def logs():
    mode = request.args['mode']
    logfile = request.args['logfile']

    return render_template('logview.html', file=logfile, mode=mode)


@app.route('/listlogs', defaults={'path': ''})
def listlogs(path):
    basepath = cfg['LOGPATH']
    fullpath = os.path.join(basepath, path)

    # Deal with bad data
    if not os.path.exists(fullpath):
        return abort(404)

    # Get all files in directory
    files = get_info(fullpath)
    return render_template('logfiles.html', files=files)


@app.route('/')
@app.route('/index.html')
def home():
    # Hard drive space
    freegb = psutil.disk_usage(cfg['ARMPATH']).free
    freegb = round(freegb / 1073741824, 1)
    mfreegb = psutil.disk_usage(cfg['MEDIA_DIR']).free
    mfreegb = round(mfreegb / 1073741824, 1)

    # RAM memory
    meminfo = dict((i.split()[0].rstrip(':'), int(i.split()[1])) for i in open('/proc/meminfo').readlines())
    mem_kib = meminfo['MemTotal']  # e.g. 3921852
    mem_gib = mem_kib / (1024.0 * 1024.0)
    # lets make sure we only give back small numbers
    mem_gib = round(mem_gib, 2)

    memused_kib = meminfo['MemFree']  # e.g. 3921852
    memused_gib = memused_kib / (1024.0 * 1024.0)
    # lets make sure we only give back small numbers
    memused_gib = round(memused_gib, 2)
    memused_gibs = round(mem_gib - memused_gib, 2)

    # get out cpu info
    ourcpu = get_processor_name()

    if os.path.isfile(cfg['DBFILE']):
        # jobs = Job.query.filter_by(status="active")
        jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()
    else:
        jobs = {}

    return render_template('index.html', freegb=freegb, mfreegb=mfreegb, jobs=jobs, cpu=ourcpu, ram=mem_gib,
                           ramused=memused_gibs, ramfree=memused_gib, ramdump=meminfo)


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
