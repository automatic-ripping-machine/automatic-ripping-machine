# Logs
import os.path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from crud import get_all_logs, delete_log
from database import get_db
from schemas import PaginatedJobList

from crud import get_ripper_settings
from utils.file_system import get_info, log_list

router = APIRouter()


router = APIRouter()

@router.get("/logs", response_model=PaginatedJobList)
def list_jobs(
    limit: int = 10,
    offset: int = 0,
    session: Session = Depends(get_db),
):
    cfg = get_ripper_settings(session).__dict__
    return {
        "limit": limit,
        "offset": offset,
        "files": log_list(cfg),
    }


@router.get("/logs/full/{logfile}/{job_id}")
async def get_log(logfile: str, job_id: int):
    """Try to catch if the logfile gets delete before the job is finished"""
    try:
        log_file = os.path.join("/home/arm/logs", logfile)
        with open(log_file, encoding="utf8", errors='ignore') as read_log_file:
            line = read_log_file.readlines()
    except FileNotFoundError:
        line = "File not found!"
    return {"message": f"{job_id} {log_file} - {line}",
            "log": "".join(line),
            "job_title": logfile,
            "job_id": job_id}


@router.get("/logs/armcat/{logfile}/{job_id}")
async def get_log_cat(logfile: str, job_id: int):
    return {"message": f"Hello {logfile} - {job_id}"}


@router.get("/logs/tail/{logfile}/{job_id}")
async def get_log_tail(logfile: str, job_id: int):
    return {"message": f"Hello {logfile} - {job_id}"}


@router.delete("/logs/delete/{logfile}/{job_id}")
async def delete_log_file(logfile: str, job_id: int):
    delete_log(logfile)
    return {"message": f"Hello {logfile} - {job_id}"}
