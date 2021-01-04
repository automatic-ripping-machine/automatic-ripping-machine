import os
from time import strftime, localtime
import urllib
import json
import re
import bcrypt  # noqa: F401

# import logging
# import omdb
from pathlib import Path
from arm.config.config import cfg
from flask.logging import default_handler  # noqa: F401
from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, Alembic_version  # noqa: F401
from flask import Flask, render_template  # noqa: F401


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


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub(r'\[.*?\]', '', string)  # noqa: W605

    string = re.sub('\s+', ' ', string)  # noqa: W605
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = string.strip()
    # return re.sub('[^\w\-_\.\(\) ]', '', string)
    return string


def getsize(path):
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    freegb = free / 1073741824
    return freegb


def call_omdb_api(title=None, year=None, imdbID=None, plot="short"):
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """
    omdb_api_key = cfg['OMDB_API_KEY']

    if imdbID:
        strurl = "http://www.omdbapi.com/?i={1}&plot={2}&r=json&apikey={0}".format(omdb_api_key, imdbID, plot)
    elif title:
        # try:
        title = urllib.parse.quote(title)
        year = urllib.parse.quote(year)
        strurl = "http://www.omdbapi.com/?s={1}&y={2}&plot={3}&r=json&apikey={0}".format(omdb_api_key,
                                                                                         title, year, plot)
    else:
        print("no params")
        return None

    # strurl = urllib.parse.quote(strurl)
    # logging.info("OMDB string query"+str(strurl))
    print(strurl)
    title_info_json = urllib.request.urlopen(strurl).read()
    title_info = json.loads(title_info_json.decode())
    print(title_info)
    # logging.info("Response from Title Info command"+str(title_info))
    # d = {'year': '1977'}
    # dvd_info = omdb.get(title=title, year=year)
    print("call was successful")
    return title_info
    # except Exception:
    #     print("call failed")
    #     return(None)


def generate_comments():
    comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.json")
    try:
        with open(comments_file, "r") as f:
            try:
                comments = json.load(f)
                return comments
            except Exception as e:
                comments = None
                app.logger.debug("Error with comments file. {}".format(str(e)))
                return "{'error':'" + str(e) + "'}"
    except FileNotFoundError:
        return "{'error':'File not found'}"


def generate_log(log_file, logpath, job_id):
    app.logger.debug("in logging")
    if "../" in log_file:
        return {'success': False, 'job': job_id, 'log': 'Not Allowed'}
    # Assemble full path
    fullpath = os.path.join(logpath, log_file)
    # Check if the logfile exists
    my_file = Path(fullpath)
    if not my_file.is_file():
        # logfile doesnt exist throw out error template
        return render_template('simple_error.html')
    try:
        with open(fullpath) as f:
            r = f.read()
    except Exception:
        try:
            with open(fullpath, encoding="utf8", errors='ignore') as f:
                r = f.read()
        except Exception:
            return render_template('simple_error.html')

    return {'success': True, 'job': job_id, 'mode': 'logfile', 'log': r}


def abandon_job(job_id):
    # job_id = request.args.get('job_id')
    # TODO add a confirm and then
    #  delete the raw folder (this will cause ARM to bail)
    try:
        job = Job.query.get(job_id)
        job.status = "fail"
        db.session.commit()
        t = {'success': True, 'job': job_id, 'mode': 'abandon'}
    except Exception:
        # flash("Failed to update job" + str(e))
        db.session.rollback()
        t = {'success': False, 'job': job_id, 'mode': 'abandon'}
    return t


def delete_job(job_id, mode):
    try:
        t = {}
        app.logger.debug("job_id= {}".format(job_id))
        # Find the job the user wants to delete
        if mode == 'delete' and job_id is not None:
            # User wants to wipe the whole database
            # Make a backup and everything
            # The user can only access this by typing it manually
            if job_id == 'all':
                # if os.path.isfile(cfg['DBFILE']):
                #    # Make a backup of the database file
                #    cmd = 'cp ' + str(cfg['DBFILE']) + ' ' + str(cfg['DBFILE']) + '.bak'
                #    app.logger.info("cmd  -  {0}".format(cmd))
                #    os.system(cmd)
                # Track.query.delete()
                # Job.query.delete()
                # Config.query.delete()
                # db.session.commit()
                t = {'success': True, 'job': job_id, 'mode': mode}
            elif job_id == "title":
                #  The user can only access this by typing it manually
                #  This shouldn't be left on when on a full server
                # logfile = request.args['file']
                # Job.query.filter_by(title=logfile).delete()
                # db.session.commit()
                t = {'success': True, 'job': job_id, 'mode': mode}
                # Not sure this is the greatest way of handling this
            else:
                try:
                    post_value = int(job_id)
                except ValueError:
                    return {'success': False, 'job': 'invalid', 'mode': mode, 'error': 'Not a valid job'}
                else:
                    app.logger.debug("No errors: job_id=" + str(post_value))
                    # TODO maybe/ re.sub('[^0-9]{1,10}', '', job_id)
                    Track.query.filter_by(job_id=job_id).delete()
                    Job.query.filter_by(job_id=job_id).delete()
                    Config.query.filter_by(job_id=job_id).delete()
                    db.session.commit()
                    t = {'success': True, 'job': job_id, 'mode': mode}
    # If we run into problems with the datebase changes
    # error out to the log and roll back
    except Exception as err:
        # db.session.rollback()
        app.logger.error("Error:db-1 {0}".format(err))
        t = {'success': False}

    return t
