import os
import subprocess
from time import strftime, localtime
import urllib
import json
import re
import requests
import bcrypt  # noqa: F401
import html

from pathlib import Path
from arm.config.config import cfg
from flask.logging import default_handler  # noqa: F401
from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, Alembic_version  # noqa: F401
from flask import Flask, render_template, flash, jsonify  # noqa: F401


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
    try:
        title_info_json = urllib.request.urlopen(strurl).read()
        title_info = json.loads(title_info_json.decode())
        app.logger.debug("omdb - " + str(title_info))
    except urllib.error.HTTPError as e:
        app.logger.debug(f"omdb call failed with error - {e}")
        return {}
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
    if job_status == "success" or job_status == "fail":
        jobs = Job.query.filter_by(status=job_status)
    else:
        jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()

    r = {}
    i = 0
    for j in jobs:
        r[i] = {}
        job_log = cfg['LOGPATH'] + j.logfile
        r[i]['config'] = j.config.get_d()
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
        app.logger.debug("job obj.items= " + str(j.get_d().items()))
        for key, value in x:
            if key != "config":
                r[i][str(key)] = str(value)
            # logging.debug(str(key) + "= " + str(value))
        i += 1
    app.logger.debug("Stuff = " + str(r))
    if jobs:
        app.logger.debug("jobs  - we have jobs")
        return {"success": True, "mode": job_status, "results": r}
    else:
        app.logger.debug("jobs is none or len(r) is 0 - we have no jobs")
        return {"success": False, "mode": job_status, "results": {}}


def get_tmdb_poster(search_query=None, year=None):
    """ Queries api.themoviedb.org for the poster/backdrop for movie """
    tmdb_api_key = cfg['TMDB_API_KEY']
    if year:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}&year={year}"
        # url_clean = f"https://api.themoviedb.org/3/search/movie?api_key=hidden&query={search_query}&year={year}"
    else:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}"
        # url_clean = f"https://api.themoviedb.org/3/search/movie?api_key=hidden&query={search_query}"
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
            if s['poster_path'] is not None:
                if 'release_date' in s:
                    x = re.sub("-[0-9]{0,2}-[0-9]{0,2}", "", s['release_date'])
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
                reg = "-[0-9]{0,2}-[0-9]{0,2}"
                s['Year'] = re.sub(reg, "", s['first_air_date']) if 'first_air_date' in s else \
                    re.sub(reg, "", s['release_date'])
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
        # url_clean = f"https://api.themoviedb.org/3/search/movie?api_key=hidden&query={search_query}&year={year}"
    else:
        url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_api_key}&query={search_query}"
        # url_clean = f"https://api.themoviedb.org/3/search/movie?api_key=hidden&query={search_query}"
    # Valid poster sizes
    # "w92", "w154", "w185", "w342", "w500", "w780", "original"
    poster_size = "original"
    poster_base = f"http://image.tmdb.org/t/p/{poster_size}"
    # Making a get request
    response = requests.get(url)
    p = json.loads(response.text)
    # if status_code is in p we know there was an error
    if 'status_code' in p:
        app.logger.debug(f"get_tmdb_poster failed with error -  {p['status_message']}")
        return {}
    # x = json.dumps(response.json(), indent=4, sort_keys=True)
    # print(x)
    x = {}
    if p['total_results'] > 0:
        app.logger.debug(f"tmdb_search - found {p['total_results']} movies")
        for s in p['results']:
            s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
            s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
            s['imdbID'] = tmdb_get_imdb(s['id'])
            s['Year'] = re.sub("-[0-9]{0,2}-[0-9]{0,2}", "", s['release_date'])
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
        # v = json.dumps(response.json(), indent=4, sort_keys=True)
        # app.logger.debug(v)
        x = {}
        if p['total_results'] > 0:
            app.logger.debug(p['total_results'])
            for s in p['results']:
                app.logger.debug(s)
                s['poster_path'] = s['poster_path'] if s['poster_path'] is not None else None
                s['release_date'] = '0000-00-00' if 'release_date' not in s else s['release_date']
                s['imdbID'] = tmdb_get_imdb(s['id'])
                reg = "-[0-9]{0,2}-[0-9]{0,2}"
                s['Year'] = re.sub(reg, "", s['first_air_date']) if 'first_air_date' in s else \
                    re.sub(reg, "", s['release_date'])
                s['Title'] = s['title'] if 'title' in s else s['name']  # This isnt great
                s['Type'] = "series"
                app.logger.debug(f"{s['Title']} ({s['Year']})- {poster_base}{s['poster_path']}")
                s['Poster'] = f"{poster_base}{s['poster_path']}"  # print(poster_url)
                s['background_url'] = f"{poster_base}{s['backdrop_path']}"
                s["Plot"] = s['overview']
                app.logger.debug(s['background_url'])
                search_query_pretty = re.sub(r"\+", " ", search_query)
                app.logger.debug(f"trying {search_query_pretty.capitalize()} == {s['Title'].capitalize()}")
                """if search_query_pretty.capitalize() == s['Title'].capitalize():
                    s['Search'] = s
                    app.logger.debug("x=" + str(x))
                    s['Response'] = True
                    # global new_year
                    new_year = s['Year']
                    # new_year = job.year_auto = job.year = str(x['Year'])
                    title = clean_for_filename(s['Title'])
                    app.logger.debug("Webservice successful.  New title is " + title + ".  New Year is: " + new_year)
                    args = {
                        'year_auto': str(new_year),
                        'year': str(new_year),
                        'title_auto': title,
                        'title': title,
                        'video_type_auto': s['Type'],
                        'video_type': s['Type'],
                        'imdb_id_auto': s['imdbID'],
                        'imdb_id': s['imdbID'],
                        'poster_url_auto': s['Poster'],
                        'poster_url': s['Poster'],
                        'hasnicetitle': True
                    }
                    # database_updater(args, job)
                    return s
                """
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
        x = re.sub("-[0-9]{0,2}-[0-9]{0,2}", "", s['results'][0]['release_date'])
        app.logger.debug(f"{s['results'][0]['title']} ({x})- {poster_base}{s['results'][0]['poster_path']}")
        s['poster_url'] = f"{poster_base}{s['results'][0]['poster_path']}"
        s["Plot"] = s['results'][0]['overview']
        s['background_url'] = f"{poster_base}{s['results'][0]['backdrop_path']}"
        s['Type'] = "movie"
        s['imdbID'] = imdb_id
        s['Type'] = "movie"
        s['Poster'] = s['poster_url']
        s['Year'] = x
        s['Title'] = s['results'][0]['title']
    else:
        # We want to push out everything even if we dont use it right now, it may be used later.
        s = {'results': p['tv_results']}
        x = re.sub("-[0-9]{0,2}-[0-9]{0,2}", "", s['results'][0]['first_air_date'])
        app.logger.debug(f"{s['results'][0]['name']} ({x})- {poster_base}{s['results'][0]['poster_path']}")
        s['poster_url'] = f"{poster_base}{s['results'][0]['poster_path']}"
        s["Plot"] = s['results'][0]['overview']
        s['background_url'] = f"{poster_base}{s['results'][0]['backdrop_path']}"
        s['Type'] = "movie"
        s['imdbID'] = imdb_id
        s['Type'] = "series"
        s['Poster'] = s['poster_url']
        s['Year'] = x
        s['Title'] = s['results'][0]['name']
    return s


def metadata_selector(func, query=None, year=None, imdb_id=None):
    if cfg['METADATA_PROVIDER'].lower() == "tmdb":
        app.logger.debug("provider tmdb")
        if func == "search":
            return tmdb_search(query, year)
        elif func == "get_details":
            if query:
                return get_tmdb_poster(query) if year is None else get_tmdb_poster(query, year)
            elif imdb_id:
                return tmdb_find(imdb_id)

    elif cfg['METADATA_PROVIDER'].lower() == "omdb":
        app.logger.debug("provider omdb")
        if func == "search":
            return call_omdb_api(query, year)
        elif func == "get_details":
            s = call_omdb_api(title=query, year=year, imdbID=imdb_id, plot="full")
            s['background_url'] = None
            return s
    else:
        app.logger.debug(cfg['METADATA_PROVIDER'])
        app.logger.debug("unknown provider - doing nothing, saying nothing. Getting Kryten")
