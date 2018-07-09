import os
from time import sleep, strftime, localtime
from flask import Flask, render_template, abort, request, send_file
import psutil
from config import cfg

# time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(1347517370))
app = Flask(__name__)


def get_info(directory):
    file_list = []
    for i in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, i)):
            a = os.stat(os.path.join(directory, i))
            fsize = os.path.getsize(os.path.join(directory, i))
            fsize = round((fsize / 1024), 1)
            fsize = "{0:,.1f}".format(fsize)
            create_time = strftime('%Y-%m-%d %H:%M:%S', localtime(a.st_ctime))
            access_time = strftime('%Y-%m-%d %H:%M:%S', localtime(a.st_atime))
            file_list.append([i, access_time, create_time, fsize])  # [file,most_recent_access,created]
    return file_list


def getsize(path):
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    freegb = free/1073741824
    return freegb


def convert_log(logfile):
    logpath = cfg['LOGPATH']
    fullpath = os.path.join(logpath, logfile)

    output_log = os.path.join('static/tmp/', logfile)

    with open(fullpath) as infile, open(output_log, 'w') as outfile:
        txt = infile.read()
        txt = txt.replace('\n', '\r\n')
        outfile.write(txt)

    return(output_log)


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


if __name__ == '__main__':
    # app.run(host='10.10.10.174', port='8080', debug=True)
    app.run(debug=True)
