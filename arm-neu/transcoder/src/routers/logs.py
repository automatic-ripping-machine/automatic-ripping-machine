"""Log file endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import get_current_user

router = APIRouter()


@router.get("/logs")
async def list_logs(_role: Annotated[str, Depends(get_current_user)]):
    """List available log files."""
    from log_reader import list_logs as _list_logs
    return _list_logs()


@router.get("/logs/{filename}/structured", responses={404: {"description": "Log file not found"}})
async def get_structured_log(
    filename: str,
    _role: Annotated[str, Depends(get_current_user)],
    mode: str = Query("tail", pattern="^(tail|full)$"),
    lines: int = Query(100, ge=1, le=10000),
    level: str | None = Query(None),
    search: str | None = Query(None),
):
    """Read a structured (JSON lines) log file with optional filtering."""
    from log_reader import read_structured_log
    result = read_structured_log(filename, mode=mode, lines=lines, level=level, search=search)
    if result is None:
        raise HTTPException(status_code=404, detail="Log file not found")
    return result


@router.get("/logs/{filename}", responses={404: {"description": "Log file not found"}})
async def get_log(
    filename: str,
    _role: Annotated[str, Depends(get_current_user)],
    mode: str = Query("tail", pattern="^(tail|full)$"),
    lines: int = Query(100, ge=1, le=10000),
):
    """Read a log file's content."""
    from log_reader import read_log
    result = read_log(filename, mode=mode, lines=lines)
    if result is None:
        raise HTTPException(status_code=404, detail="Log file not found")
    return result
