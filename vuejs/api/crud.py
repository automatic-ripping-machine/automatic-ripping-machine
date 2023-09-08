import datetime
import os
import platform
import random
import re
from typing import List

import bcrypt
import psutil
import yaml
from sqlalchemy.orm import Session

from exceptions import JobAlreadyExistError, JobNotFoundError
from models import Job, Notifications, UISettings, RipperConfig, AppriseConfig, User
from schemas import CreateAndUpdateJob
import requests
import json

from utils.utils import check_hw_transcode_support


# Function to get list of jobs
def get_all_jobs(session: Session, limit: int, offset: int) -> List[Job]:
    return session.query(Job).offset(offset).limit(limit).all()


# Function to  get info of a particular job
def get_job_info_by_id(session: Session, _id: int) -> Job:
    job_info = session.query(Job).get(_id)
    if job_info is None:
        raise JobNotFoundError
    return job_info


# Function to add a new job info to the database
def create_job(session: Session, job_info: CreateAndUpdateJob) -> Job:
    job_details = session.query(Job).filter(Job.pid_hash == job_info.pid_hash).first()
    if job_details is not None:
        raise JobAlreadyExistError
    print(job_details)
    print(job_info.dict())
    new_job_info = Job(**job_info.dict())
    session.add(new_job_info)
    session.commit()
    session.refresh(new_job_info)
    return new_job_info


# Function to update details of the job
def update_job_info(session: Session, _id: int, info_update: CreateAndUpdateJob) -> Job:
    job_info = get_job_info_by_id(session, _id)

    if job_info is None:
        raise JobNotFoundError

    job_info.title = job_info.title_manual = info_update.title  # clean_for_filename(title)
    job_info.year = job_info.year_manual = info_update.year
    job_info.video_type = job_info.video_type_manual = info_update.video_type
    job_info.imdb_id = job_info.imdb_id_manual = info_update.imdb_id
    job_info.poster_url = job_info.poster_url_manual = info_update.poster_url
    job_info.hasnicetitle = True

    session.commit()
    session.refresh(job_info)

    return job_info


def abandon_job_crud(session: Session, _id: int, ) -> dict:
    job_info = get_job_info_by_id(session, _id)
    json_return = {}
    try:
        job_info.status = "fail"
        job_process = psutil.Process(job_info.pid)
        job_process.terminate()  # or p.kill()
        notification = Notifications(title=f"Job: {job_info.job_id} was Abandoned!",
                                     message=f'Job with id: {job_info.job_id} was successfully abandoned. No files were deleted!')
        session.add(notification)
        session.commit()
    except psutil.NoSuchProcess:
        session.rollback()
        json_return['Error'] = f"Couldn't find job.pid - {job_info.pid}! Reverting db changes."
        print(f"Couldn't find job.pid - {job_info.pid}! Reverting db changes.")
    except psutil.AccessDenied:
        session.rollback()
        json_return['Error'] = f"Access denied abandoning job: {job_info.pid}! Reverting db changes."
        print(f"Access denied abandoning job: {job_info.pid}! Reverting db changes.")
    except Exception as error:
        session.rollback()
        print(f"Job {job_info.job_id} couldn't be abandoned. - {error}")
        json_return["Error"] = str(error)
    if 'Error' in json_return:
        notification = Notifications(title=f"Job ERROR: {job_info.job_id} couldn't be abandoned",
                                     message=json_return["Error"])
        session.add(notification)
        session.commit()
    session.commit()
    session.refresh(job_info)
    if job_info is None:
        raise JobNotFoundError
    return json_return


# Function to delete a job info from the db
def delete_job_info(session: Session, _id: int):
    job_info = get_job_info_by_id(session, _id)

    if job_info is None:
        raise JobNotFoundError

    session.delete(job_info)
    session.commit()

    return True


def send_job_to_remote_api(session: Session, _id: int):
    job = get_job_info_by_id(session, _id)
    return_dict = {}
    api_key = 'ARM_API_KEY'

    # This allows easy updates to the API url
    base_url = "https://1337server.pythonanywhere.com"
    url = f"{base_url}/api/v1/?mode=p&api_key={api_key}&crc64={job.crc_id}&t={job.title}" \
          f"&y={job.year}&imdb={job.imdb_id}" \
          f"&hnt={job.hasnicetitle}&l={job.label}&vt={job.video_type}"
    response = requests.get(url)
    req = json.loads(response.text)
    job_dict = job.get_d().items()
    return_dict['config'] = job.config.get_d()
    for key, value in iter(job_dict):
        return_dict[str(key)] = str(value)
    if req['success']:
        return_dict['status'] = "success"
    else:
        return_dict['error'] = req['Error']
        return_dict['status'] = "fail"
    return return_dict


def get_dvd_jobs(session: Session):
    job_list = session.query(Job).filter_by(hasnicetitle=True, disctype="dvd").all()
    return [job.job_id for job in job_list]

def search(session: Session, search_query: str):
    """ Queries ARMui db for the movie/show matching the query"""
    safe_search = re.sub(r'[^a-zA-Z\d]', '', search_query)
    safe_search = f"%{safe_search}%"
    print('-' * 30)

    posts = session.query(Job).filter(Job.title.like(safe_search)).all()
    search_results = {}
    i = 0
    for jobs in posts:
        search_results[i] = {}
        try:
            search_results[i]['config'] = jobs.config.get_d()
        except AttributeError:
            search_results[i]['config'] = "config not found"
            print("couldn't get config")

        for key, value in iter(jobs.get_d().items()):
            if key != "config":
                search_results[i][str(key)] = str(value)
            # print(str(key) + "= " + str(value))
        i += 1
    return {'success': True, 'mode': 'search', 'results': search_results}


def get_jobs_by_status(session: Session, job_status: str)-> List[Job]:
    if job_status in ("success", "fail"):
        jobs = session.query(Job).filter_by(status=job_status).all()
    else:
        print("Get running jobs")
        jobs = session.query(Job).filter(Job.status.notin_(['fail', 'success'])).all()
    if jobs:
        print("jobs  - we have jobs", jobs)
    return jobs


################################ logs #####################################################
def get_all_logs():
    return None


def delete_log(logfile):
    print(logfile)
    return None


################################# Settings ################################################

def update_password(session, post_json):
    return_json = {'success': False }
    print(post_json.username, post_json.old_password, post_json.new_password)
    user = session.query(User).filter_by(username=post_json.username).first()
    print(user.__dict__)
    # Old pass/hash still needs encoded from string to bytes
    password = user.password.encode('utf-8')
    hashed = user.hash.encode('utf-8')
    # Hash old password from post hashed to compare with user password from database
    old_password_hashed = bcrypt.hashpw(post_json.old_password.encode('utf-8'), hashed)
    if password == old_password_hashed:
        user.password = bcrypt.hashpw(post_json.new_password.encode('utf-8'), hashed)
        user.hash = hashed
        try:
            session.commit()
            return_json['success'] = True
        except Exception as error:
            return_json['error'] = f"Error in updating password: {error}"
    else:
        return_json['error'] = "Password not updated, issue with old password"
    return return_json

def get_ripper_settings(session) -> RipperConfig:
    ripper_settings = session.query(RipperConfig).first()
    print(ripper_settings)
    # If not ripper settings create and insert default values
    if not ripper_settings:
        import requests
        import urllib
        # NOT SAFE DO NOT LINK REMOTE!
        link = 'https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/setup/arm.yaml'
        f = urllib.request.urlopen(link)
        config = yaml.safe_load(f.read())
        print(config)
        ripper_settings = RipperConfig()
        for (key, value) in config.items():
            setattr(ripper_settings, key, value)
            print(f"Setting {key}: {value}")

        print("successfully written to the database")

        session.add(ripper_settings)
        session.commit()
    print(ripper_settings)
    return ripper_settings


def update_ripper_settings(session, new_settings):
    ripper_settings = session.query(RipperConfig).get(0)
    print(new_settings)
    for key, value in new_settings:
        print(f"setting {key} = {value}")
        setattr(ripper_settings, key, value)
    session.commit()
    return ripper_settings


def update_apprise_settings(session, new_settings):
    apprise_settings = session.query(AppriseConfig).get(1)
    print(new_settings)
    for key, value in new_settings:
        print(f"setting {key} = {value}")
        setattr(apprise_settings, key, value)
    session.commit()
    return apprise_settings
def get_ui_settings(session: Session) -> UISettings:
    """
    Update/create the ui settings if needed
    :param session: Current db session
    :return: The ui settings
    """
    ui_settings = session.query(UISettings).first()
    if ui_settings is None:
        ui_settings = UISettings(**{'use_icons': False, 'save_remote_images': False, 'bootstrap_skin': 'spacelab',
                                    'language': 'en', 'index_refresh': 2000,
                                    'database_limit': 20, 'notify_refresh': 2000})
        session.add(ui_settings)
        session.commit()
    return session.query(UISettings).first()


def update_ui_settings(session: Session, info_update, config_id:int  = 1):
    """
    Update/create the ui settings if needed
    :param config_id:
    :param session:
    :param info_update:
    :return:
    """
    ui_settings = session.query(UISettings).get(config_id)

    print(ui_settings)
    # If none found in ui settings create and add it to db
    if ui_settings is None:
        print("No ui settings found, creating....")
        ui_settings = UISettings(**info_update.dict())
        session.add(ui_settings)
    ui_settings.use_icons = info_update.use_icons
    ui_settings.save_remote_images = info_update.save_remote_images
    ui_settings.bootstrap_skin = info_update.bootstrap_skin
    ui_settings.language = info_update.language
    ui_settings.index_refresh = info_update.index_refresh
    ui_settings.database_limit = info_update.database_limit
    ui_settings.notify_refresh = info_update.notify_refresh

    session.commit()
    session.refresh(ui_settings)

    return ui_settings


def get_abcde_settings(session: Session) -> UISettings:
    """
    Update/create the ui settings if needed
    :param session: Current db session
    :return: The ui settings
    """
    return session.query(UISettings).first()


def get_apprise_settings(session: Session) -> AppriseConfig:
    """
    Update/create the ui settings if needed
    :param session: Current db session
    :return: The ui settings
    """
    apprise_settings = session.query(AppriseConfig).first()
    print(apprise_settings)
    # If not ripper settings create and insert default values
    if not apprise_settings:
        import requests
        import urllib
        # NOT SAFE DO NOT LINK REMOTE!
        link = 'https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/setup/apprise.yaml'
        f = urllib.request.urlopen(link)
        config = yaml.safe_load(f.read())
        print(config)
        apprise_settings = AppriseConfig()
        for (key, value) in config.items():
            setattr(apprise_settings, key, value)
            print(f"Setting {key}: {value}")

        print("successfully written to the database")

        session.add(apprise_settings)
        session.commit()
    print(apprise_settings)
    return apprise_settings


def enable_dev_mode(mode, session):
    jobs = session.query(Job).order_by(session.desc(Job.job_id)).order_by(Job.job_id.desc())
    print("Jobs number = " + str(jobs.count()))
    r1 = random.randrange(0, jobs.count())
    r2 = random.randrange(0, jobs.count())
    r3 = random.randrange(0, jobs.count())
    r4 = random.randrange(0, jobs.count())
    for j in jobs:
        if j.job_id == r1:
            j.status = 'active'
        if j.job_id == r2:
            j.status = 'ripping'
        if j.job_id == r3:
            j.status = 'transcoding'
        if j.job_id == r4:
            j.status = 'waiting'
        print(j.job_id)
        session.commit()
    return {'jobs': str(jobs), 'Mode': mode, 'count': jobs.count(), 'job_ids': [r1,r2,r3,r4]}

def crud_get_notifications(session):
    """Get all current notifications"""
    all_notification = session.query(Notifications).filter_by(seen=False)
    notification = [a.get_d() for a in all_notification]
    return notification

def crud_get_all_notifications(session):
    """Get all current notifications"""
    return session.query(Notifications).order_by(Notifications.id.desc()).all()

def crud_read_notification(session, notify_id):
    """Read notification, disable it from being show"""
    return_json = {'success': False, 'mode': 'read_notification', 'message': ""}
    notification = session.query(Notifications).filter_by(id=notify_id, seen=0).first()
    if notification:
        notification.seen = 1
        notification.dismiss_time = datetime.datetime.now()
        session.commit()
        return_json['success'] = True
    else:
        return_json['message'] = "Notification already read or not found!"
    return return_json

def get_stats(session):
    # stats for info page
    try:
        with open(os.path.join('/opt/arm', 'VERSION')) as version_file:
            version = version_file.read().strip()
    except FileNotFoundError:
        version = "Unknown"
    failed_rips = session.query(Job).filter_by(status="fail").count()
    total_rips = session.query(Job).filter_by().count()
    movies = session.query(Job).filter_by(video_type="movie").count()
    series = session.query(Job).filter_by(video_type="series").count()
    cds = session.query(Job).filter_by(disctype="music").count()
    stats = {'python_version': platform.python_version(),
             'arm_version': version,
             #'git_commit': get_git_revision_hash(),
             'movies_ripped': movies,
             'series_ripped': series,
             'cds_ripped': cds,
             'no_failed_jobs': failed_rips,
             'total_rips': total_rips,
             #'updated': git_check_updates(get_git_revision_hash()),
             'hw_support': check_hw_transcode_support(),
             }
    # form_drive = SystemInfoDrives(request.form)
    # System Drives (CD/DVD/Blueray drives)
    json_drives = {} # check_for_drives()
    return {'success': True, 'stats': stats, 'drives': json_drives}


def check_for_drives():
    from utils.DriveUtils import drives_check_status
    drives = drives_check_status()
    json_drives = {}
    i=0
    for drive in drives:
        json_drives[i] = {}
        for key, value in drive.get_d().items():
            json_drives[i][str(key)] = str(value)
            # Will trigger error if no previous
            json_drives[i]['job_previous'] = drive.job_previous.get_d()

        i += 1
    return json_drives