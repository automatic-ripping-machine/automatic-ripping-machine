# Jobs.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from utils.ServerUtil import ServerUtil
from crud import get_all_jobs, create_job, get_job_info_by_id, update_job_info, delete_job_info, abandon_job_crud, \
    send_job_to_remote_api, search, get_jobs_by_status, crud_get_notifications, get_dvd_jobs
from database import get_db
from exceptions import JobException
from models import SystemInfo
from schemas import JobSchemas, CreateAndUpdateJob, PaginatedJobList, JobListWithStats
from utils.utils import check_hw_transcode_support

router = APIRouter()


# API to get the list of jobs currently running
@router.get("/jobs", response_model=JobListWithStats)
def list_active_jobs(session: Session = Depends(get_db)):
    try:
        print("/jobs - list active jobs")
        server = session.query(SystemInfo).filter_by(id="1").first()
        serverutil = ServerUtil()
        return {
            "results": get_jobs_by_status(session, "active"),
            "server": server.__dict__ if server else None,
            "serverutil": serverutil.__dict__,
            "notes": crud_get_notifications(session),
            "hwsupport": check_hw_transcode_support(),
        }
    except JobException as cie:
        raise HTTPException(**cie.__dict__)

# API endpoint to add a job info to the database
@router.post("/jobs", response_model=JobSchemas)
def add_job(job_info: CreateAndUpdateJob, session: Session = Depends(get_db)):
    try:
        return create_job(session, job_info)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)


# API endpoint to get info of a particular job
@router.get("/jobs/{job_id}", response_model=JobSchemas)
def get_job_info(job_id: int, session: Session = Depends(get_db)):
    try:
        return get_job_info_by_id(session, job_id)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)


# API to update an existing job info
@router.put("/jobs/{job_id}", response_model=JobSchemas)
def update_job(job_id: int, new_info: CreateAndUpdateJob, session: Session = Depends(get_db)):
    try:
        return update_job_info(session, job_id, new_info)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)


# API to delete a job info from the database
@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, session: Session = Depends(get_db)):
    try:
        return delete_job_info(session, job_id)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)


@router.get("/jobs/{job_id}/abandon")
async def abandon_job(job_id: int, session: Session = Depends(get_db)):
    try:
        job_info = abandon_job_crud(session, job_id)
        json_compatible_item_data = jsonable_encoder(job_info)
        return JSONResponse(content=json_compatible_item_data)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)


@router.get("/jobs/{job_id}/send_to_remote_db")
async def send_to_remote_db(job_id: int, session: Session = Depends(get_db)):
    try:
        result = send_job_to_remote_api(session, job_id)
        json_compatible_item_data = jsonable_encoder(result)
        return JSONResponse(content=json_compatible_item_data)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)


@router.get("/list/dvds")
async def get_list_of_dvds_for_remote(session: Session = Depends(get_db)):
    try:
        return get_dvd_jobs(session)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)


@router.get("/jobs/{job_id}/fix_perms")
async def fix_job_permissions(job_id: int, ):
    return {"message": f"Hello, {job_id}"}


@router.get("/jobs/search/{query}")
async def search_the_db_for_jobs(query: str, session: Session = Depends(get_db)):
    try:
        search_results = search(session, query)
        json_compatible_item_data = jsonable_encoder(search_results)
        return JSONResponse(content=json_compatible_item_data)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)


@router.get("/database", response_model=PaginatedJobList)
async def get_jobs_by_mode(session: Session = Depends(get_db), mode: str = "database", limit: int = 10,
                           offset: int = 0):
    try:
        if mode is None or mode == "database" or mode == "":
            print("database/None or unset")
            search_results = get_all_jobs(session, limit, offset)
        else:
            print("database/job by status")
            search_results = get_jobs_by_status(session, mode)

        return {"limit": limit, "offset": offset, "results": search_results}
    except JobException as cie:
        raise HTTPException(**cie.__dict__)
