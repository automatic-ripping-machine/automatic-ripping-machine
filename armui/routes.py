import os
from time import sleep
from flask import Flask, render_template, abort, request, send_file
import psutil
from armui import app
from armui.config import cfg
from armui.utils import convert_log, get_info


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


@app.route('/rips')
def rips():
    return render_template('rips.html')


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


# if __name__ == '__main__':
#     app.run(host='10.10.10.174', port='8080', debug=True)
#     # app.run(debug=True)
