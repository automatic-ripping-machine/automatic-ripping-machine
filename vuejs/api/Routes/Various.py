# Various
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crud import crud_get_notifications, crud_read_notification, crud_get_all_notifications
from database import get_db
from models import RipperConfig, Notifications, Job
from utils.utils import search_remote

router = APIRouter()

@router.get("/read_notification/{notify_id}")
async def read_notification(notify_id: str, session: Session = Depends(get_db)):
    print(notify_id)
    return crud_read_notification(session, notify_id)

@router.get("/notify_timeout")
async def notify_timeout(notify_timeout: str,):
    return {"message": f"Hello, {notify_timeout}"}

@router.get("/get_notifications")
async def get_notifications(session: Session = Depends(get_db)):
    return crud_get_notifications(session)

@router.get("/get_all_notifications")
async def get_all_notifications(session: Session = Depends(get_db)):
    return crud_get_all_notifications(session)

@router.get("/search_remote/{title}/{year}/{job_id}")
async def search_remote_for_metadata(job_id: str, title: str, year: str = None, session: Session = Depends(get_db)):
    cfg = session.query(RipperConfig).first()
    return search_remote(title, year,"search", job_id, cfg)


@router.get("/enable_dev_mode")
async def enable_dev_mode():
    return {"message": "Hello, {job_id}"}

@router.get("/update_title/{job_id}")
def update_title(job_id: int, session: Session = Depends(get_db), title: str = "",
                 year: str = "", type: str = "", imdb_id: str ="", poster: str = ""):
    """
    used to save the details from the search
    """
    job = session.query(Job).get(job_id)
    old_title = job.title
    old_year = job.year
    job.title = job.title_manual = title # clean_for_filename(title)
    job.year = job.year_manual = year
    job.video_type = job.video_type_manual = type
    job.imdb_id = job.imdb_id_manual = imdb_id
    job.poster_url = job.poster_url_manual = poster
    job.hasnicetitle = True
    notification = Notifications(title=f"Job: {job.job_id} was updated",
                                        message=f'Title: {old_title} ({old_year}) was updated to '
                                                f'{title} ({year})')
    session.add(notification)
    session.commit()
    return {'title': job.title, 'year': job.year, 'success': True,
            'job id': job.job_id,'imdb_id':job.imdb_id}

@router.get("/change_params/{job_id}")
def change_job_params(job_id, session: Session = Depends(get_db),
                      DISCTYPE: str = "dvd", MINLENGTH: int = 600,
                      MAXLENGTH: int = 99999, RIPMETHOD:str = "mkv",
                      MAINFEATURE: bool = False):
    """Update parameters for job    """
    job = session.query(Job).get(job_id)
    config = job.config
    job.disctype = DISCTYPE
    config.MINLENGTH = MINLENGTH
    config.MAXLENGTH = MAXLENGTH
    config.RIPMETHOD = RIPMETHOD
    # must be 1 for True 0 for False
    config.MAINFEATURE = 1 if MAINFEATURE else 0
    message = f'Parameters changed. Rip Method={config.RIPMETHOD},Main Feature={config.MAINFEATURE},' \
              f'Minimum Length={config.MINLENGTH}, Maximum Length={config.MAXLENGTH}, Disctype={job.disctype}'
    # We don't need to set the config as they are set with job commit
    notification = Notifications(title=f"Job: {job.job_id} Config updated!", message=message)
    session.add(notification)
    session.commit()
    return {'message': message, 'form': 'change_job_params', "success": True}
