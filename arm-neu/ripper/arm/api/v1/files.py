"""API v1 — File browser endpoints.

All handlers use sync def (not async def) so FastAPI runs them in a
threadpool via anyio.to_thread.run_sync().  This prevents blocking the
event loop during heavy filesystem I/O (shutil.move, shutil.rmtree,
recursive os.walk + chown).

Request bodies use Pydantic BaseModel instead of raw Request objects,
which eliminates the need for async def + await request.json().
"""
import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from arm.services import file_browser

log = logging.getLogger(__name__)

_ACCESS_DENIED = "Access denied"
_PATH_NOT_FOUND = "Path not found"

router = APIRouter(prefix="/api/v1", tags=["files"])


class RenameRequest(BaseModel):
    path: str
    new_name: str


class MoveRequest(BaseModel):
    path: str
    destination: str


class MkdirRequest(BaseModel):
    path: str
    name: str


class PathRequest(BaseModel):
    path: str


@router.get('/files/roots')
def get_roots():
    """Return all configured media root directories."""
    return file_browser.get_roots()


@router.get('/files/list')
def list_directory(path: str = Query(..., description="Directory path to list")):
    """List contents of a directory."""
    try:
        return file_browser.list_directory(path)
    except ValueError:
        return JSONResponse({"success": False, "error": _ACCESS_DENIED}, status_code=403)
    except FileNotFoundError:
        return JSONResponse({"success": False, "error": _PATH_NOT_FOUND}, status_code=404)
    except NotADirectoryError:
        return JSONResponse({"success": False, "error": "Not a directory"}, status_code=400)
    except OSError as exc:
        log.error("Error listing directory %s: %s", path, exc)
        return JSONResponse({"success": False, "error": "Failed to list directory"}, status_code=500)


@router.post('/files/rename')
def rename_item(req: RenameRequest):
    """Rename a file or directory."""
    try:
        return file_browser.rename_item(req.path, req.new_name)
    except ValueError:
        return JSONResponse({"success": False, "error": _ACCESS_DENIED}, status_code=403)
    except FileNotFoundError:
        return JSONResponse({"success": False, "error": _PATH_NOT_FOUND}, status_code=404)
    except FileExistsError:
        return JSONResponse({"success": False, "error": "Target already exists"}, status_code=409)
    except OSError as exc:
        log.error("Error renaming %s: %s", req.path, exc)
        return JSONResponse({"success": False, "error": "Failed to rename item"}, status_code=500)


@router.post('/files/move')
def move_item(req: MoveRequest):
    """Move a file or directory to a new location."""
    try:
        return file_browser.move_item(req.path, req.destination)
    except ValueError:
        return JSONResponse({"success": False, "error": _ACCESS_DENIED}, status_code=403)
    except FileNotFoundError:
        return JSONResponse({"success": False, "error": _PATH_NOT_FOUND}, status_code=404)
    except (NotADirectoryError, FileExistsError):
        return JSONResponse({"success": False, "error": "Target already exists or is not a directory"}, status_code=409)
    except OSError as exc:
        log.error("Error moving %s: %s", req.path, exc)
        return JSONResponse({"success": False, "error": "Failed to move item"}, status_code=500)


@router.post('/files/mkdir')
def create_directory(req: MkdirRequest):
    """Create a new directory."""
    try:
        return file_browser.create_directory(req.path, req.name)
    except ValueError:
        return JSONResponse({"success": False, "error": _ACCESS_DENIED}, status_code=403)
    except FileNotFoundError:
        return JSONResponse({"success": False, "error": _PATH_NOT_FOUND}, status_code=404)
    except (NotADirectoryError, FileExistsError):
        return JSONResponse({"success": False, "error": "Directory already exists or parent is not a directory"}, status_code=409)
    except OSError as exc:
        log.error("Error creating directory in %s: %s", req.path, exc)
        return JSONResponse({"success": False, "error": "Failed to create directory"}, status_code=500)


@router.post('/files/fix-permissions')
def fix_permissions(req: PathRequest):
    """Fix ownership and permissions for a file or directory."""
    try:
        return file_browser.fix_item_permissions(req.path)
    except ValueError:
        return JSONResponse({"success": False, "error": _ACCESS_DENIED}, status_code=403)
    except FileNotFoundError:
        return JSONResponse({"success": False, "error": _PATH_NOT_FOUND}, status_code=404)
    except OSError as exc:
        log.error("Error fixing permissions on %s: %s", req.path, exc)
        return JSONResponse({"success": False, "error": "Failed to fix permissions"}, status_code=500)


@router.delete('/files/delete')
def delete_item(req: PathRequest):
    """Delete a file or directory."""
    try:
        return file_browser.delete_item(req.path)
    except ValueError:
        return JSONResponse({"success": False, "error": _ACCESS_DENIED}, status_code=403)
    except FileNotFoundError:
        return JSONResponse({"success": False, "error": _PATH_NOT_FOUND}, status_code=404)
    except OSError as exc:
        log.error("Error deleting %s: %s", req.path, exc)
        return JSONResponse({"success": False, "error": "Failed to delete item"}, status_code=500)
