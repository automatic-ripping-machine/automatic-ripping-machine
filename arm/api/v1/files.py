"""API v1 — File browser endpoints."""
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from arm.services import file_browser

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["files"])


@router.get('/files/roots')
def get_roots():
    """Return all configured media root directories."""
    return file_browser.get_roots()


@router.get('/files/list')
def list_directory(path: str = Query(..., description="Directory path to list")):
    """List contents of a directory."""
    try:
        return file_browser.list_directory(path)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=403)
    except FileNotFoundError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)
    except NotADirectoryError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)
    except OSError as exc:
        log.error("Error listing directory %s: %s", path, exc)
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@router.post('/files/rename')
async def rename_item(request: Request):
    """Rename a file or directory."""
    body = await request.json()
    path = body.get('path')
    new_name = body.get('new_name')
    if not path or not new_name:
        return JSONResponse(
            {"success": False, "error": "Both 'path' and 'new_name' are required"},
            status_code=400,
        )
    try:
        return file_browser.rename_item(path, new_name)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=403)
    except FileNotFoundError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)
    except FileExistsError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except OSError as exc:
        log.error("Error renaming %s: %s", path, exc)
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@router.post('/files/move')
async def move_item(request: Request):
    """Move a file or directory to a new location."""
    body = await request.json()
    path = body.get('path')
    destination = body.get('destination')
    if not path or not destination:
        return JSONResponse(
            {"success": False, "error": "Both 'path' and 'destination' are required"},
            status_code=400,
        )
    try:
        return file_browser.move_item(path, destination)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=403)
    except FileNotFoundError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)
    except (NotADirectoryError, FileExistsError) as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except OSError as exc:
        log.error("Error moving %s: %s", path, exc)
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@router.post('/files/mkdir')
async def create_directory(request: Request):
    """Create a new directory."""
    body = await request.json()
    path = body.get('path')
    name = body.get('name')
    if not path or not name:
        return JSONResponse(
            {"success": False, "error": "Both 'path' and 'name' are required"},
            status_code=400,
        )
    try:
        return file_browser.create_directory(path, name)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=403)
    except FileNotFoundError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)
    except (NotADirectoryError, FileExistsError) as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=409)
    except OSError as exc:
        log.error("Error creating directory in %s: %s", path, exc)
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@router.delete('/files/delete')
async def delete_item(request: Request):
    """Delete a file or directory."""
    body = await request.json()
    path = body.get('path')
    if not path:
        return JSONResponse(
            {"success": False, "error": "'path' is required"},
            status_code=400,
        )
    try:
        return file_browser.delete_item(path)
    except ValueError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=403)
    except FileNotFoundError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=404)
    except OSError as exc:
        log.error("Error deleting %s: %s", path, exc)
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
