import os
import shutil

import subprocess
from time import strftime, localtime, time
import urllib
import json
import re
import psutil
import requests
import bcrypt  # noqa: F401
import html
import yaml

from pathlib import Path
from arm.config.config import cfg
from flask.logging import default_handler  # noqa: F401

from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, AlembicVersion, UISettings  # noqa: F401
from flask import Flask, render_template, flash, request  # noqa: F401

TMDB_YEAR_REGEX = "-[0-9]{0,2}-[0-9]{0,2}"


def database_updater(args, job, wait_time=90):
    """
    Try to update our db for x seconds and handle it nicely if we cant

    :param args: This needs to be a Dict with the key being the job.method you want to change and the value being
    the new value.

    :param job: This is the job object
    :param wait_time: The time to wait in seconds
    :return: Nothing
    """
    # Loop through our args and try to set any of our job variables
    for (key, value) in args.items():
        setattr(job, key, value)
        app.logger.debug(str(key) + "= " + str(value))
    for i in range(wait_time):  # give up after the users wait period in seconds
        try:
            db.session.commit()
        except Exception as e:
            if "locked" in str(e):
                time.sleep(1)
                app.logger.debug(f"database is locked - trying in 1 second {i}/{wait_time} - {e}")
            else:
                app.logger.debug("Error: " + str(e))
                raise RuntimeError(str(e))
        else:
            app.logger.debug("successfully written to the database")
            return True


def check_db_version(install_path, db_file):
    """
    Check if db exists and is up to date.
    If it doesn't exist create it.  If it's out of date update it.
    """
    from alembic.script import ScriptDirectory
    from alembic.config import Config
    import sqlite3
    import flask_migrate

    mig_dir = os.path.join(install_path, "arm/migrations")

    config = Config()
    config.set_main_option("script_location", mig_dir)
    script = ScriptDirectory.from_config(config)

    # create db file if it doesn't exist
    if not os.path.isfile(db_file):
        app.logger.info("No database found.  Initializing arm.db...")
        make_dir(os.path.dirname(db_file))
        with app.app_context():
            flask_migrate.upgrade(mig_dir)

        if not os.path.isfile(db_file):
            app.logger.debug("Can't create database file.  This could be a permissions issue.  Exiting...")

    # check to see if db is at current revision
    head_revision = script.get_current_head()
    app.logger.debug("Head is: " + head_revision)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    c.execute("SELECT {cn} FROM {tn}".format(cn="version_num", tn="alembic_version"))
    db_version = c.fetchone()[0]
    app.logger.debug("Database version is: " + db_version)
    if head_revision == db_version:
        app.logger.info("Database is up to date")
    else:
        app.logger.info(
            "Database out of date. Head is " + head_revision + " and database is " + db_version
            + ".  Upgrading database...")
        with app.app_context():
            ts = round(time() * 100)
            app.logger.info("Backuping up database '" + db_file + "' to '" + db_file + str(ts) + "'.")
            shutil.copy(db_file, db_file + "_" + str(ts))
            flask_migrate.upgrade(mig_dir)
        app.logger.info("Upgrade complete.  Validating version level...")

        c.execute("SELECT {cn} FROM {tn}".format(tn="alembic_version", cn="version_num"))
        db_version = c.fetchone()[0]
        app.logger.debug("Database version is: " + db_version)
        if head_revision == db_version:
            app.logger.info("Database is now up to date")
        else:
            app.logger.error(
                "Database is still out of date. Head is " + head_revision + " and database is " + db_version
                + ".  Exiting arm.")
            # sys.exit()


def make_dir(path):
    """
    Make a directory\n
    path = Path to directory\n

    returns success True if successful
        false if the directory already exists
    """
    if not os.path.exists(path):
        app.logger.debug("Creating directory: " + path)
        try:
            os.makedirs(path)
            return True
        except OSError:
            err = "Couldn't create a directory at path: " + path + " Probably a permissions error.  Exiting"
            app.logger.error(err)
    else:
        return False


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
    return string


def getsize(path):
    st = os.statvfs(path)
    free = (st.f_bavail * st.f_frsize)
    freegb = free / 1073741824
    return freegb


def call_omdb_api(title=None, year=None, imdb_id=None, plot="short"):
    """ Queries OMDbapi.org for title information and parses if it's a movie
        or a tv series """
    omdb_api_key = cfg['OMDB_API_KEY']

    if imdb_id:
        strurl = "http://www.omdbapi.com/?i={1}&plot={2}&r=json&apikey={0}".format(omdb_api_key, imdb_id, plot)
    elif title:
        # try:
        title = urllib.parse.quote(title)
        year = urllib.parse.quote(year)
        strurl = "http://www.omdbapi.com/?s={1}&y={2}&plot={3}&r=json&apikey={0}".format(omdb_api_key,
                                                                                         title, year, plot)
    else:
        # app.logger.debug("no params")
        return None
    # app.logger.debug(f"omdb - {strurl}")
    try:
        title_info_json = urllib.request.urlopen(strurl).read()
        title_info = json.loads(title_info_json.decode())
        title_info['background_url'] = None
        app.logger.debug(f"omdb - {title_info}")
    except urllib.error.HTTPError as e:
        app.logger.debug(f"omdb call failed with error - {e}")
        return None
    app.logger.debug("omdb - call was successful")
    return title_info


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
    if job is None or job.logfile is None or job.logfile == "":
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
    try:
        job = Job.query.get(job_id)
        job.status = "fail"
        db.session.commit()
        app.logger.debug("Job {} was abandoned successfully".format(job_id))
        t = {'success': True, 'job': job_id, 'mode': 'abandon'}
    except Exception as e:
        db.session.rollback()
        app.logger.debug("Job {} couldn't be abandoned ".format(job_id))
        return {'success': False, 'job': job_id, 'mode': 'abandon', "Error": str(e)}
    try:
        p = psutil.Process(job.pid)
        p.terminate()  # or p.kill()
    except psutil.NoSuchProcess:
        t['Error'] = f"couldnt find job.pid - {job.pid}"  # This is a soft error db changes still went through
        app.logger.debug(f"couldnt find job.pid - {job.pid}")
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
                #    cmd = f"cp {cfg['DBFILE']} {cfg['DBFILE'])}.bak"
                #    app.logger.info(f"cmd  -  {cmd}")
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
                # This causes db corruption!
                # logfile = request.args['title']
                # Job.query.filter_by(title=logfile).delete()
                # db.session.commit()
                # app.logger.debug("Admin is requesting to delete all jobs with (x) title.")
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
                    Track.query.filter_by(job_id=job_id).delete()
                    Job.query.filter_by(job_id=job_id).delete()
                    Config.query.filter_by(job_id=job_id).delete()
                    db.session.commit()
                    app.logger.debug("Admin deleting  job {} was successful")
                    t = {'success': True, 'job': job_id, 'mode': mode}
    # If we run into problems with the datebase changes
    # error out to the log and roll back
    except Exception as err:
        db.session.rollback()
        app.logger.error("Error:db-1 {0}".format(err))
        t = {'success': False}

    return t


def setup_database():
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
            user = AlembicVersion('6dfe7244b18e')
            ui_config = UISettings(1, 1, "spacelab", "en", 10, 200)
            db.session.add(ui_config)
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


def get_omdb_poster(title=None, year=None, imdb_id=None, plot="short"):
    """ Queries OMDbapi.org for the poster for movie/show """
    omdb_api_key = cfg['OMDB_API_KEY']
    title_info = {}
    if imdb_id:
        strurl = f"http://www.omdbapi.com/?i={imdb_id}&plot={plot}&r=json&apikey={omdb_api_key}"
        strurl2 = ""
    elif title:
        strurl = f"http://www.omdbapi.com/?s={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
        strurl2 = f"http://www.omdbapi.com/?t={title}&y={year}&plot={plot}&r=json&apikey={omdb_api_key}"
    else:
        app.logger.debug("no params")
        return None, None
    from requests.utils import requote_uri
    r = requote_uri(strurl)
    r2 = requote_uri(strurl2)
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
                title_info2 = json.loads(title_info_json2.decode())
                # app.logger.debug("omdb - " + str(title_info2))
                if 'Error' not in title_info2:
                    return title_info2['Poster'], title_info2['imdbID']
            except Exception as e:
                app.logger.debug(f"Failed to reach OMdb - {e}")
                return None, None

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
    if crc_id is None:
        return False, None
    jobs = Job.query.filter_by(crc_id=crc_id, status="success", hasnicetitle=True)
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
    function for getting all Failed/Successful jobs or currently active jobs from the database

    :return: True if we have found dupes with the same crc
              - Will also return a dict of all the jobs found.
             False if we didnt find any with the same crc
              - Will also return None as a secondary param
    """
    success = False
    if job_status in ("success", "fail"):
        jobs = Job.query.filter_by(status=job_status)
    else:
        jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()

    r = {}
    i = 0
    for j in jobs:
        r[i] = {}
        job_log = cfg['LOGPATH'] + j.logfile
        try:
            r[i]['config'] = j.config.get_d()
        except AttributeError:
            r[i]['config'] = "config not found"
            app.logger.debug("couldn't get config")
        # Try to catch if the logfile gets delete before the job is finished
        try:
            line = subprocess.check_output(['tail', '-n', '1', job_log])
        except subprocess.CalledProcessError:
            app.logger.debug("Error while reading logfile for ETA")
            line = ""
        app.logger.debug(line)
        job_status_bar = re.search(r"Encoding: task ([0-9] of [0-9]), ([0-9]{1,3}\.[0-9]{2}) %.{0,40}"
                                   r"ETA ([0-9hms]*?)\)(?!\\rEncod)", str(line))
        if job_status_bar:
            app.logger.debug(job_status_bar.group())
            r[i]['stage'] = job_status_bar.group(1)
            r[i]['progress'] = job_status_bar.group(2)
            r[i]['eta'] = job_status_bar.group(3)
            r[i]['progress_round'] = int(float(r[i]['progress']))

        app.logger.debug("job obj= " + str(j.get_d()))
        x = j.get_d().items()
        for key, value in x:
            if key != "config":
                r[i][str(key)] = str(value)
            # logging.debug(str(key) + "= " + str(value))
        i += 1
    if jobs:
        app.logger.debug("jobs  - we have " + str(len(r)) + " jobs")
        success = True

    return {"success": success, "mode": job_status, "results": r}


def get_tmdb_poster(search_query=None, year=None):
    """ Queries api.themoviedb.org for the poster/backdrop for movie """
    tmdb_api_key = cfg['TMDB_API_KEY']
    if year:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}&year={year}"
    else:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}"
    # Valid poster sizes
    # "w92", "w154", "w185", "w342", "w500", "w780", "original"
    poster_size = "original"
    poster_base = f"http://image.tmdb.org/t/p/{poster_size}"
    response = requests.get(url)
    p = json.loads(response.text)
    # if status_code is in p we know there was an error
    if 'status_code' in p:
        app.logger.debug(f"get_tmdb_poster failed with error -  {p['status_message']}")
        return {}
    x = json.dumps(response.json(), indent=4, sort_keys=True)
    print(x)
    if p['total_results'] > 0:
        app.logger.debug(p['total_results'])
        for s in p['results']:
            if s['poster_path'] is not None and 'release_date' in s:
                x = re.sub(TMDB_YEAR_REGEX, "", s['release_date'])
                app.logger.debug(f"{s['title']} ({x})- {poster_base}{s['poster_path']}")
                s['poster_url'] = f"{poster_base}{s['poster_path']}"
                s["Plot"] = s['overview']
                # print(poster_url)
                s['background_url'] = f"{poster_base}{s['backdrop_path']}"
                s['Type'] = "movie"
                app.logger.debug(s['background_url'])
                return s
    else:
        url = f"https://api.themoviedb.org/3/search/tv?api_key={tmdb_api_key}&query={search_query}"
        response = requests.get(url)
        p = json.loads(response.text)
        v = json.dumps(response.json(), indent=4, sort_keys=True)
        app.logger.debug(v)
        x = {}
        if p['total_results'] > 0:
            app.logger.debug(p['total_results'])
            for s in p['results']:
                app.logger.debug(s)
                s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
                s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
                s['imdbID'] = tmdb_get_imdb(s['id'])
                s['Year'] = re.sub(TMDB_YEAR_REGEX, "", s['first_air_date']) if 'first_air_date' in s else \
                    re.sub(TMDB_YEAR_REGEX, "", s['release_date'])
                s['Title'] = s['title'] if 'title' in s else s['name']  # This isnt great
                s['Type'] = "movie"
                app.logger.debug(f"{s['Title']} ({s['Year']})- {poster_base}{s['poster_path']}")
                s['Poster'] = f"{poster_base}{s['poster_path']}"  # print(poster_url)
                s['background_url'] = f"{poster_base}{s['backdrop_path']}"
                s["Plot"] = s['overview']
                app.logger.debug(s['background_url'])
                search_query_pretty = re.sub(r"\+", " ", search_query)
                app.logger.debug(f"trying {search_query.capitalize()} == {s['Title'].capitalize()}")
                if search_query_pretty.capitalize() == s['Title'].capitalize():
                    s['Search'] = s
                    app.logger.debug("x=" + str(x))
                    s['Response'] = True
                    return s
            x['Search'] = p['results']
            return x
        app.logger.debug("no results found")
        return None


def tmdb_search(search_query=None, year=None):
    """
        Queries api.themoviedb.org for movies close to the query

    """
    # https://api.themoviedb.org/3/movie/78?api_key=
    # &append_to_response=alternative_titles,changes,credits,images,keywords,lists,releases,reviews,similar,videos
    tmdb_api_key = cfg['TMDB_API_KEY']
    if year:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}&year={year}"
    else:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}"
    # Valid poster sizes
    # "w92", "w154", "w185", "w342", "w500", "w780", "original"
    poster_size = "original"
    poster_base = f"http://image.tmdb.org/t/p/{poster_size}"
    response = requests.get(url)
    p = json.loads(response.text)
    if 'status_code' in p:
        app.logger.debug(f"get_tmdb_poster failed with error -  {p['status_message']}")
        return None
    x = {}
    if p['total_results'] > 0:
        app.logger.debug(f"tmdb_search - found {p['total_results']} movies")
        for s in p['results']:
            s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
            s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
            s['imdbID'] = tmdb_get_imdb(s['id'])
            s['Year'] = re.sub(TMDB_YEAR_REGEX, "", s['release_date'])
            s['Title'] = s['title']
            s['Type'] = "movie"
            app.logger.debug(f"{s['title']} ({s['Year']})- {poster_base}{s['poster_path']}")
            s['Poster'] = f"{poster_base}{s['poster_path']}"
            s['background_url'] = f"{poster_base}{s['backdrop_path']}"
            app.logger.debug(s['background_url'])
        x['Search'] = p['results']
        return x
    else:
        # Search for tv series
        app.logger.debug("tmdb_search - movie not found, trying tv series ")
        url = f"https://api.themoviedb.org/3/search/tv?api_key={tmdb_api_key}&query={search_query}"
        response = requests.get(url)
        p = json.loads(response.text)
        x = {}
        if p['total_results'] > 0:
            app.logger.debug(p['total_results'])
            for s in p['results']:
                app.logger.debug(s)
                s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
                s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
                s['imdbID'] = tmdb_get_imdb(s['id'])
                s['Year'] = re.sub(TMDB_YEAR_REGEX, "", s['first_air_date']) if 'first_air_date' in s else \
                    re.sub(TMDB_YEAR_REGEX, "", s['release_date'])
                s['Title'] = s['title'] if 'title' in s else s['name']  # This isnt great
                s['Type'] = "series"
                app.logger.debug(f"{s['Title']} ({s['Year']})- {poster_base}{s['poster_path']}")
                s['Poster'] = f"{poster_base}{s['poster_path']}"  # print(poster_url)
                s['background_url'] = f"{poster_base}{s['backdrop_path']}"
                s["Plot"] = s['overview']
                app.logger.debug(s['background_url'])
                search_query_pretty = re.sub(r"\+", " ", search_query)
                app.logger.debug(f"trying {search_query_pretty.capitalize()} == {s['Title'].capitalize()}")
            x['Search'] = p['results']
            return x

    # We got to here with no results give nothing back
    app.logger.debug("tmdb_search - no results found")
    return None


def tmdb_get_imdb(tmdb_id):
    """
        Queries api.themoviedb.org for imdb_id by TMDB id

    """
    # https://api.themoviedb.org/3/movie/78?api_key=
    # &append_to_response=alternative_titles,changes,credits,images,keywords,lists,releases,reviews,similar,videos
    tmdb_api_key = cfg['TMDB_API_KEY']
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={tmdb_api_key}&" \
          f"append_to_response=alternative_titles,credits,images,keywords,releases,reviews,similar,videos,external_ids"
    url_tv = f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids?api_key={tmdb_api_key}"
    # Making a get request
    response = requests.get(url)
    p = json.loads(response.text)
    app.logger.debug(f"tmdb_get_imdb - {p}")
    # 'status_code' means id wasn't found
    if 'status_code' in p:
        # Try tv series
        response = requests.get(url_tv)
        tv = json.loads(response.text)
        app.logger.debug(tv)
        if 'status_code' not in tv:
            return tv['imdb_id']
    else:
        return p['external_ids']['imdb_id']


def tmdb_find(imdb_id):
    """
    basic function to return an object from tmdb from only the imdb id
    :param imdb_id: the imdb id to lookup
    :return: dict in the standard 'arm' format
    """
    tmdb_api_key = cfg['TMDB_API_KEY']
    url = f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={tmdb_api_key}&external_source=imdb_id"
    poster_size = "original"
    poster_base = f"http://image.tmdb.org/t/p/{poster_size}"
    # Making a get request
    response = requests.get(url)
    p = json.loads(response.text)
    app.logger.debug(f"tmdb_find = {p}")
    if len(p['movie_results']) > 0:
        # We want to push out everything even if we dont use it right now, it may be used later.
        s = {'results': p['movie_results']}
        x = re.sub(TMDB_YEAR_REGEX, "", s['results'][0]['release_date'])
        app.logger.debug(f"{s['results'][0]['title']} ({x})- {poster_base}{s['results'][0]['poster_path']}")
        s['poster_url'] = f"{poster_base}{s['results'][0]['poster_path']}"
        s["Plot"] = s['results'][0]['overview']
        s['background_url'] = f"{poster_base}{s['results'][0]['backdrop_path']}"
        s['Type'] = "movie"
        s['imdbID'] = imdb_id
        s['Poster'] = s['poster_url']
        s['Year'] = x
        s['Title'] = s['results'][0]['title']
    else:
        # We want to push out everything even if we dont use it right now, it may be used later.
        s = {'results': p['tv_results']}
        x = re.sub(TMDB_YEAR_REGEX, "", s['results'][0]['first_air_date'])
        app.logger.debug(f"{s['results'][0]['name']} ({x})- {poster_base}{s['results'][0]['poster_path']}")
        s['poster_url'] = f"{poster_base}{s['results'][0]['poster_path']}"
        s["Plot"] = s['results'][0]['overview']
        s['background_url'] = f"{poster_base}{s['results'][0]['backdrop_path']}"
        s['imdbID'] = imdb_id
        s['Type'] = "series"
        s['Poster'] = s['poster_url']
        s['Year'] = x
        s['Title'] = s['results'][0]['name']
    return s


def metadata_selector(func, query="", year="", imdb_id=""):
    """
    Used to switch between OMDB or TMDB as the metadata provider
    - TMDB returned queries are converted into the OMDB format

    :param func: the function that is being called - allows for more dynamic results
    :param query: this can either be a search string or movie/show title
    :param year: the year of movie/show release
    :param imdb_id: the imdb id to lookup

    :return: json/dict object
    """
    if cfg['METADATA_PROVIDER'].lower() == "tmdb":
        app.logger.debug("provider tmdb")
        if func == "search":
            return tmdb_search(str(query), str(year))
        elif func == "get_details":
            if query:
                return get_tmdb_poster(str(query), str(year))
            elif imdb_id:
                return tmdb_find(imdb_id)

    elif cfg['METADATA_PROVIDER'].lower() == "omdb":
        app.logger.debug("provider omdb")
        if func == "search":
            return call_omdb_api(str(query), str(year))
        elif func == "get_details":
            s = call_omdb_api(title=str(query), year=str(year), imdb_id=str(imdb_id), plot="full")
            return s
    app.logger.debug(cfg['METADATA_PROVIDER'])
    app.logger.debug("unknown provider - doing nothing, saying nothing. Getting Kryten")


def fix_permissions(j_id):
    """
    Json api

    ARM can sometimes have issues with changing the file owner, we can use the fact ARMui is run
    as a service to fix permissions.
    """
    try:
        job_id = int(j_id.strip())
    except AttributeError:
        return {"success": False, "mode": "fixperms", "Error": "AttributeError",
                "PrettyError": "No Valid Job Id Supplied"}
    job = Job.query.get(job_id)
    if not job:
        return {"success": False, "mode": "fixperms", "Error": "JobDeleted",
                "PrettyError": "Job Has Been Deleted From The Database"}
    job_log = os.path.join(cfg['LOGPATH'], job.logfile)
    if not os.path.isfile(job_log):
        return {"success": False, "mode": "fixperms", "Error": "FileNotFoundError",
                "PrettyError": "Logfile Has Been Deleted Or Moved"}

    # This is kind of hacky way to get around the fact we dont save the ts variable
    with open(job_log, 'r') as reader:
        for line in reader.readlines():
            ts = re.search("Operation not permitted: '([0-9a-zA-Z()/ -]*?)'", str(line))
            if ts:
                break
            # app.logger.debug(ts)
            # Operation not permitted: '([0-9a-zA-Z\(\)/ -]*?)'
    if ts:
        app.logger.debug(str(ts.group(1)))
        directory_to_traverse = ts.group(1)
    else:
        app.logger.debug("not found")
        directory_to_traverse = os.path.join(job.config.COMPLETED_PATH, str(job.title) + " (" + str(job.year) + ")")
    try:
        corrected_chmod_value = int(str(job.config.CHMOD_VALUE), 8)
        app.logger.info("Setting permissions to: " + str(job.config.CHMOD_VALUE) + " on: " + directory_to_traverse)
        os.chmod(directory_to_traverse, corrected_chmod_value)
        if job.config.SET_MEDIA_OWNER and job.config.CHOWN_USER and job.config.CHOWN_GROUP:
            import pwd
            import grp
            uid = pwd.getpwnam(job.config.CHOWN_USER).pw_uid
            gid = grp.getgrnam(job.config.CHOWN_GROUP).gr_gid
            os.chown(directory_to_traverse, uid, gid)

        for dirpath, l_directories, l_files in os.walk(directory_to_traverse):
            for cur_dir in l_directories:
                app.logger.debug("Setting path: " + cur_dir + " to permissions value: " + str(job.config.CHMOD_VALUE))
                os.chmod(os.path.join(dirpath, cur_dir), corrected_chmod_value)
                if job.config.SET_MEDIA_OWNER:
                    os.chown(os.path.join(dirpath, cur_dir), uid, gid)
            for cur_file in l_files:
                app.logger.debug("Setting file: " + cur_file + " to permissions value: " + str(job.config.CHMOD_VALUE))
                os.chmod(os.path.join(dirpath, cur_file), corrected_chmod_value)
                if job.config.SET_MEDIA_OWNER:
                    os.chown(os.path.join(dirpath, cur_file), uid, gid)
        d = {"success": True, "mode": "fixperms", "folder": str(directory_to_traverse)}
    except Exception as e:
        err = "Permissions setting failed as: " + str(e)
        app.logger.error(err)
        d = {"success": False, "mode": "fixperms", "Error": str(err), "ts": str(ts)}
    return d


def trigger_restart():
    """
    We update the file modified time to get flask to restart
    This only works if ARMui is running as a service & in debug mode
    """
    import datetime

    def set_file_last_modified(file_path, dt):
        dt_epoch = dt.timestamp()
        os.utime(file_path, (dt_epoch, dt_epoch))

    now = datetime.datetime.now()
    arm_main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "routes.py")
    set_file_last_modified(arm_main, now)


def get_settings(arm_cfg_file):
    """
    yaml file loader - is used for loading fresh arm.yaml config
    Args:
        arm_cfg_file: full path to arm.yaml

    Returns:
        cfg: the loaded yaml file
    """
    try:
        with open(arm_cfg_file, "r") as f:
            try:
                cfg = yaml.load(f, Loader=yaml.FullLoader)
            except Exception as e:
                app.logger.debug(e)
                cfg = yaml.safe_load(f)  # For older versions use this
    except FileNotFoundError as e:
        app.logger.debug(e)
        cfg = {}
    return cfg
