"""API v1 - Log endpoints."""
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse

from arm.services import jobs as svc_jobs
from arm.services import log_parser
import arm.config.config as cfg

router = APIRouter(prefix="/api/v1", tags=["logs"])


_NOT_FOUND = "Log file not found"


@router.get('/jobs/{job_id}/log')
def get_job_log(job_id: int):
    """Get the full log for a job."""
    return svc_jobs.generate_log(cfg.arm_config['LOGPATH'], str(job_id))


@router.get('/logs')
def list_logs():
    """List all log files in LOGPATH (newest first)."""
    return log_parser.list_logs()


@router.get('/logs/{filename}')
def read_log(
    filename: str,
    mode: Annotated[str, Query(pattern="^(tail|full)$")] = "tail",
    lines: Annotated[int, Query(ge=1, le=10000)] = 100,
):
    """Read a log file. mode=tail returns the last N lines (default);
    mode=full returns the whole file capped at 10 MB (truncated=true).
    """
    result = log_parser.read_log(filename, mode=mode, lines=lines)
    if result is None:
        return JSONResponse({"error": _NOT_FOUND}, status_code=404)
    return result


@router.get('/logs/{filename}/structured')
def read_structured_log(
    filename: str,
    mode: Annotated[str, Query(pattern="^(tail|full)$")] = "tail",
    lines: Annotated[int, Query(ge=1, le=10000)] = 100,
    level: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
):
    """Parsed log lines with optional level and substring filter."""
    result = log_parser.read_structured_log(
        filename, mode=mode, lines=lines, level=level, search=search,
    )
    if result is None:
        return JSONResponse({"error": _NOT_FOUND}, status_code=404)
    return result


@router.get('/logs/{filename}/download')
def download_log(filename: str):
    """Stream the raw log file as text/plain for download."""
    log_path = log_parser.resolve_log_path(filename)
    if log_path is None:
        return JSONResponse({"error": _NOT_FOUND}, status_code=404)
    return FileResponse(
        path=str(log_path),
        filename=log_path.name,
        media_type="text/plain",
    )


@router.delete('/logs/{filename}')
def delete_log(filename: str):
    """Delete a log file by name. Path traversal attempts are rejected."""
    if not log_parser.delete_log(filename):
        return JSONResponse({"error": _NOT_FOUND}, status_code=404)
    return {"success": True, "filename": filename}
