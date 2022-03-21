import os
import subprocess
import re
import psutil
import html

from pathlib import Path
from arm.config.config import cfg
from arm.ui import app, db
from arm.models.models import Job, Config, Track, User, AlembicVersion, UISettings  # noqa: F401
from flask import Flask, render_template, flash, request  # noqa: F401


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
        process_logfile(job_log, j, r[i])
        try:
            r[i]['config'] = j.config.get_d()
        except AttributeError:
            r[i]['config'] = "config not found"
            app.logger.debug("couldn't get config")

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

    return {"success": success, "mode": job_status, "results": r, "arm_name": cfg['ARM_NAME']}


def process_logfile(logfile, job, r):
    """
    Breaking out the log parser to its own function.
    This is used to search the log for ETA and current stage

    :param logfile: the logfile for parsing
    :param job: the Job class
    :param r: the {} of
    :return: r should be dict for the json api
    """
    # Try to catch if the logfile gets delete before the job is finished
    try:
        line = subprocess.check_output(['tail', '-n', '1', logfile])
    except subprocess.CalledProcessError:
        app.logger.debug("Error while reading logfile for ETA")
        line = ""
    # This correctly get the very last ETA and %
    job_status = re.search(r"Encoding: task ([0-9] of [0-9]), ([0-9]{1,3}\.[0-9]{2}) %.{0,40}"
                           r"ETA ([0-9hms]*?)\)(?!\\rEncod)", str(line))

    if job_status:
        app.logger.debug(job_status.group())
        job.stage = job_status.group(1)
        job.progress = job_status.group(2)
        job.eta = job_status.group(3)
        x = job.progress
        job.progress_round = int(float(x))
        r['stage'] = job.stage
        r['progress'] = job.progress
        r['eta'] = job.eta
        r['progress_round'] = int(float(r['progress']))

    # INFO ARM: handbrake.handbrake_all Processing track #1 of 42. Length is 8602 seconds.
    # Try to catch if the logfile gets delete before the job is finished
    try:
        with open(logfile, encoding="utf8", errors='ignore') as f:
            line = f.readlines()
    except FileNotFoundError:
        line = ""
    job_status_index = re.search(r"Processing track #([0-9]{1,2}) of ([0-9]{1,2})(?!.*Processing track #)", str(line))
    if job_status_index:
        try:
            current_index = int(job_status_index.group(1))
            job.stage = r['stage'] = f"{job.stage} - {current_index}/{job.no_of_titles}"
        except Exception as e:
            app.logger.debug("Problem finding the current track " + str(e))
            job.stage = f"{job.stage} - %0%/%0%"
    else:
        app.logger.debug("Cant find index")

    return r


def search(search_query):
    """ Queries ARMui db for the movie/show matching the query"""
    search = re.sub('[^a-zA-Z0-9]', '', search_query)
    search = "%{}%".format(search)
    app.logger.debug('-' * 30)

    # app.logger.debug("search - q=" + str(search))
    posts = db.session.query(Job).filter(Job.title.like(search)).all()
    # app.logger.debug("search - posts=" + str(posts))
    r = {}
    i = 0
    app.logger.debug(f"000000000000 FOUND - {len(posts)}")
    for p in posts:
        # app.logger.debug("job obj = " + str(p.get_d()))
        x = p.get_d().items()
        r[i] = {}
        r[i]['config'] = p.config.get_d()
        for key, value in iter(x):
            r[i][str(key)] = str(value)
            # app.logger.debug(str(key) + "= " + str(value))
        i += 1
    return {'success': True, 'mode': 'search', 'results': r}


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
                #  if os.path.isfile(cfg['DBFILE']):  # noqa: S125
                #    # Make a backup of the database file
                #    cmd = f"cp {cfg['DBFILE']} {cfg['DBFILE'])}.bak"
                #    app.logger.info(f"cmd  -  {cmd}")
                #    os.system(cmd)
                #  Track.query.delete()
                #  Job.query.delete()
                #  Config.query.delete()
                #  db.session.commit()
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
        job.eject()
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
