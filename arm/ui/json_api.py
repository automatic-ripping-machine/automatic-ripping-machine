"""
Basic json api for access to A.R.M UI
Also used to connect to both omdb and tmdb
"""
import os
import subprocess
import re
import html
from pathlib import Path
import psutil
from arm.config.config import cfg
from arm.ui import app, db
from arm.models.models import Job, Config, Track
from arm.ui.utils import job_id_validator


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

    job_results = {}
    i = 0
    for j in jobs:
        job_results[i] = {}
        job_log = cfg['LOGPATH'] + j.logfile
        process_logfile(job_log, j, job_results[i])
        try:
            job_results[i]['config'] = j.config.get_d()
        except AttributeError:
            job_results[i]['config'] = "config not found"
            app.logger.debug("couldn't get config")

        for key, value in j.get_d().items():
            if key != "config":
                job_results[i][str(key)] = str(value)
        i += 1
    if jobs:
        app.logger.debug("jobs  - we have " + str(len(job_results)) + " jobs")
        success = True
    return {"success": success, "mode": job_status,
            "results": job_results, "arm_name": cfg['ARM_NAME']}


def process_logfile(logfile, job, job_results):
    """
        Decide if we need to process HandBrake or MakeMKV
        :param logfile: the logfile for parsing
        :param job: the Job class
        :param job_results: the {} of
        :return: should be dict for the json api
    """
    app.logger.debug(job.status)
    if job.status == "ripping":
        app.logger.debug("using mkv - " + logfile)
        job_results = process_makemkv_logfile(logfile, job, job_results)
    else:
        app.logger.debug("using handbrake")
        job_results = process_handbrake_logfile(logfile, job, job_results)
    return job_results


def percentage(part, whole):
    """percent calculator"""
    percent = 100 * float(part) / float(whole)
    return percent


def process_makemkv_logfile(logfile, job, job_results):
    """
    Process the logfile and find current status\n
    :return: job_results dict
    """
    line = read_all_log_lines(logfile)
    # PRGC:5057,3,"Analyzing seamless segments"
    # Correctly get last entry for progress bar
    for one_line in line:
        job_progress_status = re.search(r"PRGV:([\d]{3,}),([\d]+),([\d]{3,})$", str(one_line))
        job_stage_index = re.search(r"PRGC:[\d]+,([\d]+),\"([\w -]{2,})\"$", str(one_line))
        if job_progress_status:
            job_progress = f"{percentage(job_progress_status.group(1), job_progress_status.group(3)):.2f}"
            job.progress = job_results['progress'] = job_progress
            job.progress_round = percentage(job_progress_status.group(1),
                                            job_progress_status.group(3))
        if job_stage_index:
            try:
                current_index = f"{job_stage_index.group(2)} - {(int(job_stage_index.group(1)) + 1)}/{job.no_of_titles}"
                job.stage = job_results['stage'] = current_index
            except Exception as error:
                job.stage = f"Unknown -  {error}"
    job.eta = "Unknown"
    return job_results


def process_handbrake_logfile(logfile, job, job_results):
    """
    process a logfile looking for HandBrake progress
    :param logfile: the logfile for parsing
    :param job: the Job class
    :param job_results: the {} of
    :return: should be dict for the json api
    """
    line = read_log_line(logfile)
    # This correctly get the very last ETA and %
    job_status = re.search(r"Encoding: task ([0-9] of [0-9]), ([0-9]{1,3}\.[0-9]{2}) %.{0,40}"
                           r"ETA ([0-9hms]*?)\)(?!\\rEncod)", str(line))

    if job_status:
        app.logger.debug(job_status.group())
        job.stage = job_status.group(1)
        job.progress = job_status.group(2)
        job.eta = job_status.group(3)
        job.progress_round = int(float(job.progress))
        job_results['stage'] = job.stage
        job_results['progress'] = job.progress
        job_results['eta'] = job.eta
        job_results['progress_round'] = int(float(job_results['progress']))

    # INFO ARM: handbrake.handbrake_all Processing track #1 of 42. Length is 8602 seconds.
    line = read_all_log_lines(logfile)
    job_status_index = re.search(r"Processing track #([0-9]{1,2}) of ([0-9]{1,2})"
                                 r"(?!.*Processing track #)", str(line))
    if job_status_index:
        try:
            current_index = int(job_status_index.group(1))
            job.stage = job_results['stage'] = f"{job.stage} - {current_index}/{job.no_of_titles}"
        except Exception as error:
            app.logger.debug(f"Problem finding the current track {error}")
            job.stage = f"{job.stage} - %0%/%0%"
    else:
        app.logger.debug("Cant find index")

    return job_results


def read_log_line(log_file):
    """
    Try to catch if the logfile gets delete before the job is finished\n
    :param log_file:
    :return:
    """
    try:
        line = subprocess.check_output(['tail', '-n', '1', log_file])
    except subprocess.CalledProcessError:
        app.logger.debug("Error while reading logfile for ETA")
        line = ""
    return line


def read_all_log_lines(log_file):
    """Try to catch if the logfile gets delete before the job is finished"""
    try:
        with open(log_file, encoding="utf8", errors='ignore') as read_log_file:
            line = read_log_file.readlines()
    except FileNotFoundError:
        line = ""
    return line


def search(search_query):
    """ Queries ARMui db for the movie/show matching the query"""
    safe_search = re.sub('[^a-zA-Z0-9]', '', search_query)
    safe_search = f"%{safe_search}%"
    app.logger.debug('-' * 30)

    # app.logger.debug("search - q=" + str(search))
    posts = db.session.query(Job).filter(Job.title.like(safe_search)).all()
    # app.logger.debug("search - posts=" + str(posts))
    search_results = {}
    i = 0
    app.logger.debug(f"000000000000 FOUND - {len(posts)}")
    for jobs in posts:
        # app.logger.debug("job obj = " + str(p.get_d()))
        search_results[i] = {}
        search_results[i]['config'] = jobs.config.get_d()
        for key, value in iter(jobs.get_d().items()):
            search_results[i][str(key)] = str(value)
            # app.logger.debug(str(key) + "= " + str(value))
        i += 1
    return {'success': True, 'mode': 'search', 'results': search_results}


def delete_job(job_id, mode):
    """
    json api version of delete jobs\n
    :param job_id: job id to delete || str "all"/"title"
    :param str mode: should always be delete
    :return: json/dict to be returned if success or fail
    """
    try:
        json_return = {}
        app.logger.debug(f"job_id= {job_id}")
        # Find the job the user wants to delete
        if mode == 'delete' and job_id is not None:
            # User wants to wipe the whole database
            # Make a backup and everything
            # The user can only access this by typing it manually
            if job_id == 'all':
                #  # if this gets put in final, the DB will need optimised
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
                json_return = {'success': True, 'job': job_id, 'mode': mode}
            elif job_id == "title":
                #  The user can only access this by typing it manually
                #  This shouldn't be left on when on a full server
                # This causes db corruption!
                # logfile = request.args['title']
                # Job.query.filter_by(title=logfile).delete()
                # db.session.commit()
                # app.logger.debug("Admin is requesting to delete all jobs with (x) title.")
                json_return = {'success': True, 'job': job_id, 'mode': mode}
                # Not sure this is the greatest way of handling this
            else:
                try:
                    post_value = int(job_id)
                    app.logger.debug(f"Admin requesting delete job {job_id} from database!")
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
                    json_return = {'success': True, 'job': job_id, 'mode': mode}
    # If we run into problems with the datebase changes
    # error out to the log and roll back
    except Exception as err:
        db.session.rollback()
        app.logger.error(f"Error:db-1 {err}")
        json_return = {'success': False}

    return json_return


def generate_log(logpath, job_id):
    """
    Generate log for json api and return it in a valid form\n
    :param str logpath:
    :param int job_id:
    :return:
    """
    try:
        job = Job.query.get(int(job_id))
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
        with open(fullpath) as full_log:
            read_log = full_log.read()
    except Exception:
        try:
            with open(fullpath, encoding="utf8", errors='ignore') as full_log:
                read_log = full_log.read()
        except Exception:
            app.logger.debug("Cant read logfile. Possibly encoding issue")
            return {'success': False, 'job': job_id, 'log': 'Cant read logfile'}
    html_escaped_log = html.escape(read_log)
    title_year = str(job.title) + " (" + str(job.year) + ") - file: " + str(job.logfile)
    return {'success': True, 'job': job_id, 'mode': 'logfile', 'log': html_escaped_log,
            'escaped': True, 'job_title': title_year}


def abandon_job(job_id):
    """
    json api abondon job\n
    :param int job_id: the job id
    :return: json/dict
    """
    json_return = {
        'success': False,
        'job': job_id,
        'mode': 'abandon'
    }
    if not job_id_validator(job_id):
        return json_return

    try:
        job = Job.query.get(int(job_id))
        job.status = "fail"
        job_process = psutil.Process(job.pid)
        job_process.terminate()  # or p.kill()
        db.session.commit()
        json_return['success'] = True
        app.logger.debug(f"Job {job_id} was abandoned successfully")
        job.eject()
    except psutil.NoSuchProcess:
        db.session.rollback()
        json_return['Error'] = f"Couldn't find job.pid - {job.pid}! Reverting db changes."
        app.logger.debug(f"Couldn't find job.pid - {job.pid}! Reverting db changes.")
    except psutil.AccessDenied:
        db.session.rollback()
        json_return['Error'] = f"Access denied abandoning job: {job.pid}! Reverting db changes."
        app.logger.debug(f"Access denied abandoning job: {job.pid}! Reverting db changes.")
    except Exception as error:
        db.session.rollback()
        app.logger.debug(f"Job {job_id} couldn't be abandoned. ")
        json_return["Error"] = str(error)

    return json_return
