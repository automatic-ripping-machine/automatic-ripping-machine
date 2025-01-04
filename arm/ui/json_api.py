"""
Basic json api for access to A.R.M UI
Also used to connect to both omdb and tmdb
"""
import os
import subprocess
import re
import html
from pathlib import Path
import datetime
import psutil
from flask import request

import arm.config.config as cfg
from arm.models.config import Config
from arm.models.job import Job
from arm.models.notifications import Notifications
from arm.models.track import Track
from arm.models.ui_settings import UISettings
from arm.ui import app, db
from arm.ui.forms import ChangeParamsForm
from arm.ui.utils import job_id_validator, database_updater, authenticated_state
from arm.ui.settings import DriveUtils as drive_utils # noqa E402


def get_notifications():
    """Get all current notifications"""
    all_notification = Notifications.query.filter_by(seen=False)
    notification = [a.get_d() for a in all_notification]
    return notification


def get_x_jobs(job_status):
    """
    function for getting all Failed/Successful jobs \n
    or\n
    currently active jobs from the database\n

    :return: dict/json
    """
    success = False
    if job_status in ("success", "fail"):
        jobs = Job.query.filter_by(status=job_status)
    else:
        # Get running jobs
        jobs = db.session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()

    job_results = {}
    i = 0
    for j in jobs:
        job_results[i] = {}
        job_log = os.path.join(cfg.arm_config['LOGPATH'], str(j.logfile))
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

    # Get authentication state
    authenticated = authenticated_state()

    return {"success": success,
            "mode": job_status,
            "results": job_results,
            "arm_name": cfg.arm_config['ARM_NAME'],
            "authenticated": authenticated}


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
        job_results = process_makemkv_logfile(job, job_results)
    elif job.disctype == "music":
        app.logger.debug("using audio disc")
        process_audio_logfile(job.logfile, job, job_results)
    else:
        app.logger.debug("using handbrake")
        job_results = process_handbrake_logfile(logfile, job, job_results)
    return job_results


def percentage(part, whole):
    """percent calculator"""
    percent = 100 * float(part) / float(whole)
    return percent


def process_makemkv_logfile(job, job_results):
    """
    Process the logfile and find current status and job progress percent\n
    :return: job_results dict
    """
    progress_log = os.path.join(job.config.LOGPATH, 'progress', str(job.job_id)) + '.log'
    lines = read_log_line(progress_log)
    # Correctly get last entry for progress bar
    for line in lines:
        job_progress_status = re.search(r"PRGV:(\d{3,}),(\d+),(\d{3,})", str(line))
        job_stage_index = re.search(r"PRGC:\d+,(\d+),\"([\w -]{2,})\"", str(line))
        if job_progress_status:
            job_progress = f"{percentage(job_progress_status.group(1), job_progress_status.group(3)):.2f}"
            job.progress = job_results['progress'] = job_progress
            job.progress_round = percentage(job_progress_status.group(1),
                                            job_progress_status.group(3))
        if job_stage_index:
            try:
                current_index = f"{(int(job_stage_index.group(1)) + 1)}/{job.no_of_titles} - {job_stage_index.group(2)}"
                job.stage = job_results['stage'] = current_index
                db.session.commit()
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
    job_status = None
    job_status_index = None
    lines = read_log_line(logfile)
    for line in lines:
        # This correctly get the very last ETA and %
        job_status = re.search(r"Encoding: task (\d of \d), (\d{1,3}\.\d{2}) %.{0,40}"
                               r"ETA ([\dhms]*?)\)(?!\\rEncod)", str(line))
        job_status_index = re.search(r"Processing track #(\d{1,2}) of (\d{1,2})"
                                     r"(?!.*Processing track #)", str(line))
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


def process_audio_logfile(logfile, job, job_results):
    """
    Process audio disc logs to show current ripping tracks
    :param logfile: will come in as only the bare logfile, no path
    :param job: current job, so we can update the stage
    :param job_results:
    :return:
    """
    # \((track[^[]+)(?!track)
    line = read_all_log_lines(os.path.join(cfg.arm_config["LOGPATH"], logfile))
    for one_line in line:
        job_stage_index = re.search(r"\(track([^[]+)", str(one_line))
        if job_stage_index:
            try:
                current_index = f"Track: {job_stage_index.group(1)}/{job.no_of_titles}"
                job.stage = job_results['stage'] = current_index
                job.eta = calc_process_time(job.start_time, job_stage_index.group(1), job.no_of_titles)
                job.progress = round(percentage(job_stage_index.group(1), job.no_of_titles + 1))
                job.progress_round = round(job.progress)
            except Exception as error:
                app.logger.debug("Error processing abcde logfile. Error dump"
                                 f"-  {error}", exc_info=True)
                job.stage = "Unknown"
                job.eta = "Unknown"
                job.progress = job.progress_round = 0
    return job_results


def calc_process_time(starttime, cur_iter, max_iter):
    """Modified from stackoverflow
    Get a rough estimate of ETA, return formatted String"""
    try:
        time_elapsed = datetime.datetime.now() - starttime
        time_estimated = (time_elapsed.seconds / int(cur_iter)) * int(max_iter)
        finish_time = (starttime + datetime.timedelta(seconds=int(time_estimated)))
        test = finish_time - datetime.datetime.now()
    except TypeError:
        app.logger.error("Failed to calculate processing time - Resetting to now, time wont be accurate!")
        test = time_estimated = time_elapsed = finish_time = datetime.datetime.now()
    return f"{str(test).split('.', maxsplit=1)[0]} - @{finish_time.strftime('%H:%M:%S')}"


def read_log_line(log_file):
    """
    Try to catch if the logfile gets delete before the job is finished\n
    :param log_file:
    :return:
    """
    try:
        line = subprocess.check_output(['tail', '-n', '20', log_file]).splitlines()
    except subprocess.CalledProcessError:
        app.logger.debug("Error while reading logfile for ETA")
        line = ["", ""]
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
    safe_search = re.sub(r'[^a-zA-Z\d]', '', search_query)
    safe_search = f"%{safe_search}%"
    app.logger.debug('-' * 30)

    # app.logger.debug("search - q=" + str(search))
    posts = db.session.query(Job).filter(Job.title.like(safe_search)).all()
    # app.logger.debug("search - posts=" + str(posts))
    search_results = {}
    i = 0
    for jobs in posts:
        # app.logger.debug("job obj = " + str(p.get_d()))
        search_results[i] = {}
        try:
            search_results[i]['config'] = jobs.config.get_d()
        except AttributeError:
            search_results[i]['config'] = "config not found"
            app.logger.debug("couldn't get config")

        for key, value in iter(jobs.get_d().items()):
            if key != "config":
                search_results[i][str(key)] = str(value)
            # app.logger.debug(str(key) + "= " + str(value))
        i += 1
    return {'success': True, 'mode': 'search', 'results': search_results}


def delete_job(job_id, mode):
    """
    json api version of delete jobs\n
    :param job_id: job id to delete || str "all"/"title"
    :param str mode: should always be 'delete'
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
                #  if os.path.isfile(cfg.arm_config['DBFILE']):  # noqa: S125
                #    # Make a backup of the database file
                #    cmd = f"cp {cfg.arm_config['DBFILE']} {cfg.arm_config['DBFILE'])}.bak"
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
                    notification = Notifications(f"Job: {job_id} couldn't be Deleted!",
                                                 "Couldn't find a job with that ID")
                    db.session.add(notification)
                    db.session.commit()
                    return {'success': False, 'job': 'invalid', 'mode': mode, 'error': 'Not a valid job'}
                else:
                    app.logger.debug("No errors: job_id=" + str(post_value))
                    drive_utils.job_cleanup(job_id)
                    Track.query.filter_by(job_id=job_id).delete()
                    Job.query.filter_by(job_id=job_id).delete()
                    Config.query.filter_by(job_id=job_id).delete()
                    notification = Notifications(f"Job: {job_id} was Deleted!",
                                                 f'Job with id: {job_id} was successfully deleted from the database')
                    db.session.add(notification)
                    db.session.commit()
                    app.logger.debug(f"Admin deleting  job {job_id} was successful")
                    json_return = {'success': True, 'job': job_id, 'mode': mode}
    # If we run into problems with the database changes
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
    :param str job_id:
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
    json api abandon job\n
    :param str job_id: the job id
    :return: json/dict
    """
    json_return = {
        'success': False,
        'job': job_id,
        'mode': 'abandon'
    }
    job = None
    if not job_id_validator(job_id):
        notification = Notifications(f"Job: {job_id} isn't a valid job!",
                                     f'Job with id: {job_id} doesnt match anything in the database')
        db.session.add(notification)
        db.session.commit()
        return json_return

    try:
        job = Job.query.get(int(job_id))
        job.status = "fail"
        job_process = psutil.Process(job.pid)
        job_process.terminate()  # or p.kill()
        notification = Notifications(f"Job: {job_id} was Abandoned!",
                                     f'Job with id: {job_id} was successfully abandoned. No files were deleted!')
        db.session.add(notification)
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
        app.logger.debug(f"Job {job_id} couldn't be abandoned. - {error}")
        json_return["Error"] = str(error)
    if 'Error' in json_return:
        notification = Notifications(f"Job ERROR: {job_id} couldn't be abandoned", json_return["Error"])
        db.session.add(notification)
        db.session.commit()
    return json_return


def change_job_params(config_id):
    """Update values for job"""
    job = Job.query.get(config_id)
    config = job.config
    form = ChangeParamsForm(request.args, meta={'csrf': False})
    app.logger.debug("Before valid")
    if form.validate():
        app.logger.debug("Valid")
        job.disctype = format(form.DISCTYPE.data)
        cfg.arm_config["MINLENGTH"] = config.MINLENGTH = format(form.MINLENGTH.data)
        cfg.arm_config["MAXLENGTH"] = config.MAXLENGTH = format(form.MAXLENGTH.data)
        cfg.arm_config["RIPMETHOD"] = config.RIPMETHOD = format(form.RIPMETHOD.data)
        # must be 1 for True 0 for False
        cfg.arm_config["MAINFEATURE"] = config.MAINFEATURE = 1 if format(form.MAINFEATURE.data).lower() == "true" else 0
        args = {'disctype': job.disctype}
        message = f'Parameters changed. Rip Method={config.RIPMETHOD}, Main Feature={config.MAINFEATURE},' \
                  f'Minimum Length={config.MINLENGTH}, Maximum Length={config.MAXLENGTH}, Disctype={job.disctype}'
        # We don't need to set the config as they are set with job commit
        notification = Notifications(f"Job: {job.job_id} Config updated!", message)
        db.session.add(notification)
        database_updater(args, job)

        return {'message': message, 'form': 'change_job_params', "success": True}
    return {'return': '', 'success': False}


def read_notification(notify_id):
    """Read notification, disable it from being show"""
    return_json = {'success': False, 'mode': 'read_notification', 'message': ""}
    notification = Notifications.query.filter_by(id=notify_id, seen=0).first()
    if notification:
        database_updater({'seen': 1, 'dismiss_time': datetime.datetime.now()}, notification)
        return_json['success'] = True
    else:
        return_json['message'] = "Notification already read or not found!"
    return return_json


def get_notify_timeout(notify_timeout):
    """Return the notification timeout UI setting"""

    return_json = {'success': True,
                   'mode': 'notify_timeout',
                   'notify_timeout': ''}

    armui_cfg = UISettings.query.first()

    if armui_cfg:
        return_json['notify_timeout'] = armui_cfg.notify_refresh
    else:
        return_json['notify_timeout'] = '6500'

    return return_json


def restart_ui():
    app.logger.debug("Arm ui shutdown....")
    shutdown_code = subprocess.check_output(
        "pkill python3",
        shell=True
    ).decode("utf-8")
    # Nothing should work past here as the ui will die after running code above
    app.logger.debug(f"Arm ui shutdown ran into a problem... exit code: {shutdown_code}")
    return_json = {'success': False, 'error': f"Shutting down A.R.M UI....exit code: {shutdown_code}"}
    return return_json
