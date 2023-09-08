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

from sqlalchemy.orm import Session

from utils.metadata import metadata_selector
from models import Job, Notifications, UISettings


def search_remote(title, year, mode, job_id, cfg: Session):
    search_results = metadata_selector("search", cfg, title, year)
    if search_results is None or 'Error' in search_results or (
            'Search' in search_results and len(search_results['Search']) < 1):
        print("No results found. Trying without year")
        search_results = metadata_selector("search", cfg, title, "")

    if search_results is None or 'Error' in search_results or (
            'Search' in search_results and len(search_results['Search']) < 1):
        print(f"No search results found for {title}")
    if search_results:
        for result in search_results['Search']:
            print(result)
            result['details'] = metadata_selector("get_details", cfg, title, year, result['imdbID'])
    return {'title': title, 'year': year, 'success': True, 'mode': mode,
            'job id': job_id, 'search_results': search_results}


def get_job_details(job_id, mode):
    job = Job.query.get(job_id)
    jobs = job.get_d()
    jobs['config'] = job.config.get_d()
    tracks = job.tracks.all()
    i=0
    track_results={}
    for track in tracks:
        track_results[i] = {}
        for key, value in track.get_d().items():
            if key != "config":
                track_results[i][str(key)] = str(value)
        i += 1
    print(job.get_d())
    search_results = metadata_selector("get_details", job.title, job.year, job.imdb_id)
    if search_results:
        jobs['plot'] = search_results['Plot'] if 'Plot' in search_results else "There was a problem getting the plot"
        jobs['background'] = 'url('+search_results['background_url'] + ')' if 'background_url' in search_results else None
    return {'jobs': jobs, 'tracks': track_results, 'search_results': search_results, 'success': True, 'mode': mode, 'job id': job_id}


def process_logfile(logfile, job, job_results):
    """
        Decide if we need to process HandBrake or MakeMKV
        :param logfile: the logfile for parsing
        :param job: the Job class
        :param job_results: the {} of
        :return: should be dict for the json api
    """
    print(job.status)
    if job.status == "ripping":
        print("using mkv - " + logfile)
        job_results = process_makemkv_logfile(job, job_results)
    elif job.disctype == "music":
        print("using audio disc")
        process_audio_logfile(job.logfile, job, job_results)
    else:
        print("using handbrake")
        job_results = process_handbrake_logfile(logfile, job, job_results)
    return job_results


def percentage(part, whole):
    """percent calculator"""
    percent = 100 * float(part) / float(whole)
    return percent


def process_makemkv_logfile(job, job_results, session):
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
                session.commit()
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
        print(job_status.group())
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
            print(f"Problem finding the current track {error}")
            job.stage = f"{job.stage} - %0%/%0%"
    else:
        print("Cant find index")

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
    line = read_all_log_lines(os.path.join("LOGPATH", logfile))
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
                print(f"Error processing abcde logfile. Error dump {error}")#,
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
        print("Failed to calculate processing time - Resetting to now, time wont be accurate!")
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
        print("Error while reading logfile for ETA")
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


def generate_log(logpath, mode, logfile, job_id, session):
    """
    Generate log for json api and return it in a valid form\n
    :param str logpath:
    :param str job_id:
    :return:
    """
    from models import Job
    try:
        job = session.query(Job).get(int(job_id))
    except Exception:
        print(f"Cant find job {job_id} ")
        job = None

    print("in logging")
    if job is None or job.logfile is None or job.logfile == "":
        print(f"Cant find the job {job_id}")
        #return {'success': False, 'job': job_id, 'log': 'Not found'}
        # Hack to get around that we have no Job from database
        class Job:
            logfile = ""
        job = Job()
        job.logfile = logfile
        job.title = "Unknown"
        job.year = "unknown"
        print(logpath)
    # Assemble full path
    fullpath = os.path.join(logpath, job.logfile)
    # Check if the logfile exists
    my_file = Path(fullpath)
    if not my_file.is_file():
        # logfile doesnt exist throw out error template
        print("Couldn't find the logfile requested, Possibly deleted/moved")
        return {'success': False, 'job': job_id, 'log': 'File not found', 'mode': mode}
    try:
        with open(fullpath) as full_log:
            read_log = full_log.read()
    except Exception:
        try:
            with open(fullpath, encoding="utf8", errors='ignore') as full_log:
                read_log = full_log.read()
        except Exception:
            print("Cant read logfile. Possibly encoding issue")
            return {'success': False, 'job': job_id, 'log': 'Cant read logfile'}
    html_escaped_log = html.escape(read_log)
    title_year = str(job.title) + " (" + str(job.year) + ") - file: " + str(job.logfile)
    return {'success': True, 'job': job_id, 'mode': 'logfile', 'log': html_escaped_log,
            'escaped': True, 'job_title': title_year}


def get_notify_timeout():
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

def check_hw_transcode_support():
    cmd = "nice HandBrakeCLI"

    print(f"Sending command: {cmd}")
    hw_support_status = {
        "nvidia": False,
        "intel": False,
        "amd": False
    }
    try:
        hand_brake_output = subprocess.run(f"{cmd}", capture_output=True, shell=True, check=True)

        # NVENC
        if re.search(r'nvenc: version ([0-9\\.]+) is available', str(hand_brake_output.stderr)):
            print("NVENC supported!")
            hw_support_status["nvidia"] = True
        # Intel QuickSync
        if re.search(r'qsv:\sis(.*?)available\son', str(hand_brake_output.stderr)):
            print("Intel QuickSync supported!")
            hw_support_status["intel"] = True
        # AMD VCN
        if re.search(r'vcn:\sis(.*?)available\son', str(hand_brake_output.stderr)):
            print("AMD VCN supported!")
            hw_support_status["amd"] = True
        print("Handbrake call successful")
        # Dump the whole CompletedProcess object
        print(hand_brake_output)
    except subprocess.CalledProcessError as hb_error:
        err = f"Call to handbrake failed with code: {hb_error.returncode}({hb_error.output})"
        print(err)
    return hw_support_status
