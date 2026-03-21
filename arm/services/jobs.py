"""
Job management services — extracted from arm/ui/json_api.py.

All app.logger calls replaced with standard logging.
"""
import os
import subprocess
import re
import html
from pathlib import Path
import datetime
import logging

import psutil

import arm.config.config as cfg
from arm.models.job import Job, JobState, JOB_STATUS_FINISHED
from arm.models.notifications import Notifications
from arm.models.track import Track
from arm.models.ui_settings import UISettings
from arm.database import db
from arm.services.files import database_updater, job_id_validator

log = logging.getLogger(__name__)


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
    if job_status == "joblist":
        jobs = db.session.query(Job).filter(~Job.finished).all()
    elif JobState(job_status) in JOB_STATUS_FINISHED:
        jobs = Job.query.filter_by(status=job_status)
    else:
        raise ValueError(f"{job_status} is not a valid option")

    job_results = {}
    i = 0
    for j in jobs:
        job_results[i] = {}
        if j.logfile:
            job_log = os.path.join(cfg.arm_config['LOGPATH'], str(j.logfile))
            process_logfile(job_log, j, job_results[i])
        try:
            job_results[i]['config'] = j.config.get_d()
        except AttributeError:
            job_results[i]['config'] = "config not found"
            log.debug("couldn't get config")

        for key, value in j.get_d().items():
            if key != "config":
                job_results[i][str(key)] = str(value)

        # Include per-track status summary for music jobs
        if j.disctype == "music":
            tracks = Track.query.filter_by(job_id=j.job_id).all()
            track_list = []
            for t in tracks:
                track_list.append({
                    'track_number': t.track_number,
                    'status': t.status or 'pending',
                    'ripped': bool(t.ripped),
                    'filename': t.filename or '',
                })
            job_results[i]['tracks'] = track_list
            ripped_count = sum(1 for t in tracks if t.ripped)
            job_results[i]['tracks_ripped'] = f"{ripped_count}/{len(tracks)}"

        i += 1
    if jobs:
        log.debug("jobs  - we have " + str(len(job_results)) + " jobs")
        success = True

    return {"success": success,
            "mode": job_status,
            "results": job_results,
            "arm_name": cfg.arm_config['ARM_NAME']}


def process_logfile(logfile, job, job_results):
    """
        Parse MakeMKV or abcde progress from the job logfile.
        :param logfile: the logfile for parsing
        :param job: the Job class
        :param job_results: the {} of
        :return: should be dict for the json api
    """
    log.debug(f"Disc Type: {job.disctype}, Status: {job.status}")
    if job.disctype in {"dvd", "bluray", "bluray4k"} and job.status == JobState.VIDEO_RIPPING.value:
        log.debug("using mkv - " + logfile)
        return process_makemkv_logfile(job, job_results)
    if job.disctype == "music" and job.status == JobState.AUDIO_RIPPING.value:
        log.debug("using audio disc")
        return process_audio_logfile(job.logfile, job, job_results)
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
    job_progress_status = None
    job_stage_index = None
    lines = read_log_line(os.path.join(cfg.arm_config['LOGPATH'], job.logfile))
    # Correctly get last entry for progress bar
    for line in lines:
        job_progress_status = re.search(r"PRGV:(\d{3,}),(\d+),(\d{3,})", str(line))
        job_stage_index = re.search(r"PRGC:\d+,(\d+),\"([\w -]{2,})\"", str(line))

    if job_progress_status is not None:
        log.debug(f"job_progress_status: {job_progress_status}")
        job.progress = job_results['progress'] = \
            f"{percentage(job_progress_status.group(1), job_progress_status.group(3)):.2f}"
        job.progress_round = percentage(job_progress_status.group(1),
                                        job_progress_status.group(3))
    else:
        log.debug(f"Job [{job.job_id}] MakeMKV status not defined - setting progress to 0%")
        job.progress = job.progress_round = job_results['progress'] = 0

    if job_stage_index is not None:
        try:
            current_index = f"{(int(job_stage_index.group(1)) + 1)}/{job.no_of_titles} - {job_stage_index.group(2)}"
            job.stage = job_results['stage'] = current_index
            db.session.commit()
        except Exception as error:
            job.stage = f"Unknown -  {error}"

    job.eta = "Unknown"

    return job_results


def process_audio_logfile(logfile, job, job_results):
    """
    Process audio disc logs to show current ripping/encoding progress.
    :param logfile: will come in as only the bare logfile, no path
    :param job: current job, so we can update the stage
    :param job_results:
    :return:
    """
    content = "\n".join(read_all_log_lines(os.path.join(cfg.arm_config["LOGPATH"], logfile)))

    # Use same patterns as _poll_music_progress in arm/ripper/utils.py
    grabbing = {int(m.group(1)) for m in re.finditer(r"Grabbing track (\d+):", content)}
    encoding = {int(m.group(1)) for m in re.finditer(r"Encoding track (\d+) of", content)}
    tagging = {int(m.group(1)) for m in re.finditer(r"Tagging track (\d+) of", content)}

    # Determine highest completed track and current phase
    all_seen = grabbing | encoding | tagging
    if not all_seen:
        return job_results

    try:
        total = job.no_of_titles or len(all_seen)
        completed = len(tagging)
        current_track = max(all_seen)

        if tagging:
            phase = "tagged"
        elif encoding:
            phase = "encoding"
        else:
            phase = "ripping"

        current_index = f"{completed}/{total} - {phase} track {current_track}"
        job.stage = job_results['stage'] = current_index
        job.eta = calc_process_time(job.start_time, max(completed, 1), total)
        job.progress = round(percentage(completed, total))
        job.progress_round = round(job.progress)
        db.session.commit()
    except Exception as error:
        log.debug("Error processing abcde logfile. Error dump"
                  f"-  {error}", exc_info=True)
        job.stage = "Unknown"
        job.eta = "Unknown"
        job.progress = job.progress_round = 0

    return job_results


def calc_process_time(starttime, cur_iter, max_iter):
    """Modified from stackoverflow
    Get a rough estimate of ETA, return formatted String"""
    try:
        cur = int(cur_iter)
        mx = int(max_iter)
        if cur <= 0 or mx <= 0 or starttime is None:
            raise ValueError("Invalid ETA parameters")
        time_elapsed = datetime.datetime.now() - starttime
        time_estimated = (time_elapsed.total_seconds() / cur) * mx
        finish_time = (starttime + datetime.timedelta(seconds=int(time_estimated)))
        test = finish_time - datetime.datetime.now()
    except (TypeError, ValueError, ZeroDivisionError):
        log.debug("Cannot calculate processing time — waiting for progress data")
        finish_time = datetime.datetime.now()
        test = datetime.timedelta(0)
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
        log.debug(f"Error while reading {log_file}, unable to calculate ETA")
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
    log.debug('-' * 30)

    posts = db.session.query(Job).filter(Job.title.like(safe_search)).all()
    search_results = {}
    i = 0
    for job in posts:
        search_results[i] = {}
        try:
            search_results[i]['config'] = job.config.get_d()
        except AttributeError:
            search_results[i]['config'] = "config not found"
            log.debug("couldn't get config")

        for key, value in iter(job.get_d().items()):
            if key != "config":
                search_results[i][str(key)] = str(value)
        i += 1
    return {'success': True, 'mode': 'search', 'results': search_results}


def delete_job(job_id, mode):
    """
    json api version of delete jobs\n
    :param job_id: job id to delete || str "all"/"title"
    :param str mode: should always be 'delete'
    :return: json/dict to be returned if success or fail
    """
    from arm.models.config import Config
    from arm.models.track import Track
    from arm.services.drives import job_cleanup

    try:
        json_return = {}
        log.debug(f"job_id= {job_id}")
        # Find the job the user wants to delete
        if mode == 'delete' and job_id is not None:
            if job_id == 'all':
                log.debug("Admin is requesting to delete all jobs from database!!! No deletes went to db")
                json_return = {'success': True, 'job': job_id, 'mode': mode}
            elif job_id == "title":
                json_return = {'success': True, 'job': job_id, 'mode': mode}
            else:
                try:
                    post_value = int(job_id)
                    log.debug(f"Admin requesting delete job {job_id} from database!")
                except ValueError:
                    log.debug("Admin is requesting to delete a job but didnt provide a valid job ID")
                    notification = Notifications(f"Job: {job_id} couldn't be Deleted!",
                                                 "Couldn't find a job with that ID")
                    db.session.add(notification)
                    db.session.commit()
                    return {'success': False, 'job': 'invalid', 'mode': mode, 'error': 'Not a valid job'}
                else:
                    log.debug("No errors: job_id=" + str(post_value))
                    job_cleanup(job_id)
                    Track.query.filter_by(job_id=job_id).delete()
                    Job.query.filter_by(job_id=job_id).delete()
                    Config.query.filter_by(job_id=job_id).delete()
                    notification = Notifications(f"Job: {job_id} was Deleted!",
                                                 f'Job with id: {job_id} was successfully deleted from the database')
                    db.session.add(notification)
                    db.session.commit()
                    log.debug(f"Admin deleting  job {job_id} was successful")
                    json_return = {'success': True, 'job': job_id, 'mode': mode}
    except Exception as err:
        db.session.rollback()
        log.error(f"Error:db-1 {err}")
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
        log.debug(f"Cant find job {job_id} ")
        job = None

    log.debug("in logging")
    if job is None or job.logfile is None or job.logfile == "":
        log.debug(f"Cant find the job {job_id}")
        return {'success': False, 'job': job_id, 'log': 'Not found'}
    # Assemble full path
    fullpath = os.path.join(logpath, job.logfile)
    # Check if the logfile exists
    my_file = Path(fullpath)
    if not my_file.is_file():
        log.debug("Couldn't find the logfile requested, Possibly deleted/moved")
        return {'success': False, 'job': job_id, 'log': 'File not found'}
    try:
        with open(fullpath) as full_log:
            read_log = full_log.read()
    except Exception:
        try:
            with open(fullpath, encoding="utf8", errors='ignore') as full_log:
                read_log = full_log.read()
        except Exception:
            log.debug("Cant read logfile. Possibly encoding issue")
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
    if not job_id_validator(job_id):
        notification = Notifications(f"Job: {job_id} isn't a valid job!",
                                     f'Job with id: {job_id} doesnt match anything in the database')
        db.session.add(notification)
        db.session.commit()
        return json_return

    # Kill the process id
    job = Job.query.get(int(job_id))
    job.status = JobState.FAILURE.value
    try:
        terminate_process(job.pid)
    except Exception as err:
        db.session.rollback()
        json_return["Error"] = str(err)
        json_return['success'] = False
        title = f"Job ERROR: {job.pid} couldn't be abandoned."
        message = json_return['Error']
        log.debug(f"{title} - Reverting db changes - {message}")
        notification = Notifications(title, message)
    else:
        job.eject()
        json_return['success'] = True
        title = f"Job: {job.pid} was Abandoned!"
        message = f'Job with id: {job.pid} was successfully abandoned. No files were deleted!'
        notification = Notifications(title, message)
    db.session.add(notification)
    db.session.commit()
    return json_return


def terminate_process(pid):
    """
    Terminates the process associated with a given pid.
    :param pid: Process ID (int)
    :raises: ValueError if access is denied
    """
    if pid is None:
        message = "PID not found for job."
        log.warning(message)
        return
    try:
        job_process = psutil.Process(pid)
        job_process.terminate()
    except psutil.NoSuchProcess:
        message = f"Process id {pid} was not found. Job has already been terminated."
        log.warning(message)
    except psutil.AccessDenied as err:
        message = f"Access denied abandoning job: {pid}!"
        log.error(message)
        raise ValueError(message) from err
    else:
        log.debug(f"Job with PID {pid} was terminated.")


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
    log.debug("Arm ui shutdown....")
    shutdown_code = subprocess.check_output(
        "pkill python3",
        shell=True
    ).decode("utf-8")
    log.debug(f"Arm ui shutdown ran into a problem... exit code: {shutdown_code}")
    return_json = {'success': False, 'error': f"Shutting down A.R.M UI....exit code: {shutdown_code}"}
    return return_json
