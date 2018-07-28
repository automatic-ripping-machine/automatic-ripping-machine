import os
from time import sleep
from flask import render_template, abort, request, send_file, flash, redirect
import psutil
from armui import app
from armui.models import Job
from armui.config import cfg
from armui.utils import convert_log, get_info, call_omdb_api
from armui.forms import TitleUpdateForm


@app.route('/logreader')
def logreader():

    logpath = cfg['LOGPATH']
    mode = request.args['mode']
    logfile = request.args['logfile']

    # Assemble full path
    fullpath = os.path.join(logpath, logfile)

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
    return render_template('activerips.html', jobs=Job.query.all())


@app.route('/titleupdate', methods=['GET', 'POST'])
def submitrip():
    job = Job.query.get(1)
    form = TitleUpdateForm(obj=job)
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(
            form.title.data, form.year.data))
        dvd_info = call_omdb_api(form.title.data, form.year.data)
        return render_template('list_titles.html', results=dvd_info)
        # return redirect('/gettitle', title=form.title.data, year=form.year.data)
    return render_template('titleupdate.html', title='Update Title', form=form)


@app.route('/gettitle')
def gettitle(title, year):
    dvd_info = call_omdb_api(title, year)
    return render_template('renametitle.html', results=dvd_info)


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
    # freegb = getsize(cfg['RAWPATH'])
    freegb = psutil.disk_usage(cfg['LOGPATH']).free
    freegb = round(freegb/1073741824, 1)
    return render_template('index.html', freegb=freegb)