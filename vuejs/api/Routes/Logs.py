# Logs
from fastapi import APIRouter, Depends, HTTPException
from fastapi_utils.cbv import cbv
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from crud import get_all_logs, delete_log
from database import get_db
from schemas import PaginatedJobList

router = APIRouter()

# Example of Class based view
@cbv(router)
class Logs:
    session: Session = Depends(get_db)

    # API to get the list of jobs
    @router.get("/logs", response_model=PaginatedJobList)
    def list_jobs(self, limit: int = 10, offset: int = 0):

        log_list = get_all_logs()
        response = {"limit": limit, "offset": offset, "data": log_list}
        json_compatible_item_data = jsonable_encoder(response)
        return JSONResponse(content=json_compatible_item_data)

@router.get("/logs/full/{logfile}/{job_id}")
async def get_log(logfile: str, job_id: int):
    return {"message": f"Hello {logfile}- {job_id}"}


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