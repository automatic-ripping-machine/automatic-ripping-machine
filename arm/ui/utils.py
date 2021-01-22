import os
from time import strftime, localtime
import urllib
import json
import re
import bcrypt  # noqa: F401
import html
from pathlib import Path
from arm.config.config import cfg
from flask.logging import default_handler  # noqa: F401
from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, Alembic_version  # noqa: F401
from flask import Flask, render_template, flash  # noqa: F401


def get_info(directory):
    file_list = []
    for i in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, i)):
            a = os.stat(os.path.join(directory, i))
            fsize = os.path.getsize(os.path.join(directory, i))
            fsize = round((fsize / 1024), 1)
            fsize = "{0:,.1f}".format(fsize)
            create_time = strftime(cfg['DATE_FORMAT'], localtime(a.st_ctime))
            access_time = strftime(cfg['DATE_FORMAT'], localtime(a.st_atime))
            file_list.append([i, access_time, create_time, fsize])  # [file,most_recent_access,created]
    return file_list


def clean_for_filename(string):
    """ Cleans up string for use in filename """
    string = re.sub(r"\[.*?]", "", string)  # noqa: W605
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
        app.logger.debug("no params")
        return None

    # strurl = urllib.parse.quote(strurl)
    # app.logger.info("OMDB string query"+str(strurl))
    app.logger.debug("omdb - " + str(strurl))
    title_info_json = urllib.request.urlopen(strurl).read()
    title_info = json.loads(title_info_json.decode())
    app.logger.debug("omdb - " + str(title_info))
    # logging.info("Response from Title Info command"+str(title_info))
    # d = {'year': '1977'}
    # dvd_info = omdb.get(title=title, year=year)
    app.logger.debug("omdb - call was successful")
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


def generate_log(logpath, job_id):

    try:
        job = Job.query.get(job_id)
    except Exception:
        app.logger.debug(f"Cant find job {job_id} ")
        job = None

    app.logger.debug("in logging")
    if job is None:
        app.logger.debug(f"Cant find the job {job_id}")
        return {'success': False, 'job': job_id, 'log': 'Not found'}
    # Assemble full path
    fullpath = os.path.join(logpath, job.logfile)
    # Check if the logfile exists
    my_file = Path(fullpath)
    if not my_file.is_file():
        # logfile doesnt exist throw out error template
        app.logger.debug("Couldn't find the logfile requested, Possibly deleted/moved")
        return {'success': False, 'job': job_id, 'log': 'File not found'}
    try:
        with open(fullpath) as f:
            r = f.read()
    except Exception:
        try:
            with open(fullpath, encoding="utf8", errors='ignore') as f:
                r = f.read()
        except Exception:
            app.logger.debug("Cant read logfile. Possibly encoding issue")
            return {'success': False, 'job': job_id, 'log': 'Cant read logfile'}
    r = html.escape(r)
    title_year = str(job.title) + " (" + str(job.year) + ") - file: " + str(job.logfile)
    return {'success': True, 'job': job_id, 'mode': 'logfile', 'log': r,
            'escaped': True, 'job_title': title_year}


def abandon_job(job_id):
    # job_id = request.args.get('job_id')
    # TODO add a confirm and then
    #  delete the raw folder (this will cause ARM to bail)
    try:
        job = Job.query.get(job_id)
        job.status = "fail"
        db.session.commit()
        app.logger.debug("Job {} was abandoned successfully".format(job_id))
        t = {'success': True, 'job': job_id, 'mode': 'abandon'}
    except Exception:
        # flash("Failed to update job" + str(e))
        db.session.rollback()
        app.logger.debug("Job {} couldn't be abandoned ".format(job_id))
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
                app.logger.debug("Admin is requesting to delete all jobs from database!!! No deletes went to db")
                t = {'success': True, 'job': job_id, 'mode': mode}
            elif job_id == "title":
                #  The user can only access this by typing it manually
                #  This shouldn't be left on when on a full server
                # logfile = request.args['file']
                # Job.query.filter_by(title=logfile).delete()
                # db.session.commit()
                app.logger.debug("Admin is requesting to delete all jobs with (x) title. No deletes went to db")
                t = {'success': True, 'job': job_id, 'mode': mode}
                # Not sure this is the greatest way of handling this
            else:
                try:
                    post_value = int(job_id)
                    app.logger.debug("Admin requesting delete job {} from database!".format(job_id))
                except ValueError:
                    app.logger.debug("Admin is requesting to delete a job but didnt provide a valid job ID")
                    return {'success': False, 'job': 'invalid', 'mode': mode, 'error': 'Not a valid job'}
                else:
                    app.logger.debug("No errors: job_id=" + str(post_value))
                    # TODO maybe/ re.sub('[^0-9]{1,10}', '', job_id)
                    Track.query.filter_by(job_id=job_id).delete()
                    Job.query.filter_by(job_id=job_id).delete()
                    Config.query.filter_by(job_id=job_id).delete()
                    db.session.commit()
                    app.logger.debug("Admin deleting  job {} was successful")
                    t = {'success': True, 'job': job_id, 'mode': mode}
    # If we run into problems with the datebase changes
    # error out to the log and roll back
    except Exception as err:
        # db.session.rollback()
        app.logger.error("Error:db-1 {0}".format(err))
        t = {'success': False}

    return t


def setupdatabase():
    """
    Try to get the db.User if not we nuke everything
    """
    try:
        User.query.all()
        return True
    except Exception:
        #  We only need this on first run
        #  Wipe everything
        # flash(str(err))
        try:
            db.drop_all()
        except Exception:
            app.logger.debug("couldn't drop all")
        try:
            #  Recreate everything
            db.metadata.create_all(db.engine)
            db.create_all()
            db.session.commit()
            #  push the database version arm is looking for
            user = Alembic_version('e688fe04d305')
            db.session.add(user)
            db.session.commit()
            return True
        except Exception:
            app.logger.debug("couldn't create all")
            return False


def search(search_query):
    """ Queries ARMui db for the movie/show matching the query"""
    search = re.sub('[^a-zA-Z0-9]', '', search_query)
    search = "%{}%".format(search)
    app.logger.debug("search - q=" + str(search))
    posts = db.session.query(Job).filter(Job.title.like(search)).all()
    app.logger.debug("search - posts=" + str(posts))
    r = {}
    i = 0
    for p in posts:
        app.logger.debug("job obj = " + str(p.get_d()))
        x = p.get_d().items()
        r[i] = {}
        for key, value in iter(x):
            r[i][str(key)] = str(value)
            app.logger.debug(str(key) + "= " + str(value))
        i += 1
    return {'success': True, 'mode': 'search', 'results': r}


def get_omdb_poster(title=None, year=None, imdbID=None, plot="short"):
    """ Queries OMDbapi.org for the poster for movie/show """
    omdb_api_key = cfg['OMDB_API_KEY']
    title_info = {}
    if imdbID:
        strurl = f"http://www.omdbapi.com/?i={imdbID}&plot={plot}&r=json&apikey={omdb_api_key}"
    elif title:
        strurl = f"http://www.omdbapi.com/?s={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
        strurl2 = f"http://www.omdbapi.com/?t={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
    else:
        app.logger.debug("no params")
        return None, None
    from requests.utils import requote_uri
    r = requote_uri(strurl)
    r2 = requote_uri(strurl2)
    # app.logger.info("OMDB string query - " + str(r))
    # app.logger.debug("omdb - " + str(f))
    try:
        title_info_json = urllib.request.urlopen(r).read()
    except Exception as e:
        app.logger.debug(f"Failed to reach OMdb - {e}")
        return None, None
    else:
        title_info = json.loads(title_info_json.decode())
        # app.logger.debug("omdb - " + str(title_info))
        if 'Error' not in title_info:
            return title_info['Search'][0]['Poster'], title_info['Search'][0]['imdbID']
        else:
            try:
                title_info_json2 = urllib.request.urlopen(r2).read()
            except Exception as e:
                app.logger.debug(f"Failed to reach OMdb - {e}")
                return None, None
            else:
                title_info2 = json.loads(title_info_json2.decode())
                # app.logger.debug("omdb - " + str(title_info2))
                if 'Error' not in title_info2:
                    return title_info2['Poster'], title_info2['imdbID']

    return None, None


def job_dupe_check(crc_id):
    """
    function for checking the database to look for jobs that have completed
    successfully with the same crc

    :param crc_id: The job obj so we can use the crc/title etc
    :return: True if we have found dupes with the same crc
              - Will also return a dict of all the jobs found.
             False if we didnt find any with the same crc
              - Will also return None as a secondary param
    """
    # TODO possibly only grab hasnicetitles ?
    jobs = Job.query.filter_by(crc_id=crc_id, status="success")
    # app.logger.debug("search - posts=" + str(jobs))
    r = {}
    i = 0
    for j in jobs:
        app.logger.debug("job obj= " + str(j.get_d()))
        x = j.get_d().items()
        r[i] = {}
        for key, value in iter(x):
            r[i][str(key)] = str(value)
            # logging.debug(str(key) + "= " + str(value))
        i += 1

    app.logger.debug(r)
    app.logger.debug("r len=" + str(len(r)))
    if jobs is not None and len(r) > 0:
        app.logger.debug("jobs is none or len(r) - we have jobs")
        return True, r
    else:
        app.logger.debug("jobs is none or len(r) is 0 - we have no jobs")
        return False, None


def get_x_jobs(job_status):
    """
    function for getting all failed or successful jobs from the database

    :return: True if we have found dupes with the same crc
              - Will also return a dict of all the jobs found.
             False if we didnt find any with the same crc
              - Will also return None as a secondary param
    """
    jobs = Job.query.filter_by(status=job_status)
    r = {}
    i = 0
    for j in jobs:
        app.logger.debug("job obj= " + str(j.get_d()))
        x = j.get_d().items()
        r[i] = {}
        for key, value in iter(x):
            r[i][str(key)] = str(value)
            # logging.debug(str(key) + "= " + str(value))
        i += 1

    if jobs is not None and len(r) > 0:
        app.logger.debug("jobs is none or len(r)>0 - we have jobs")
        return {'success': True, 'mode': job_status, 'results': r}
    else:
        app.logger.debug("jobs is none or len(r) is 0 - we have no jobs")
        return {'success': False, 'mode': job_status, 'results': {}}
