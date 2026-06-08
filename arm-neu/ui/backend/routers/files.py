"""File browser proxy - routes file operations through the ARM backend."""
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.models.files import DirectoryListing, FileRoot, OperationResult
from backend.services import arm_client

router = APIRouter(prefix="/api/files", tags=["files"])

_ARM_UI_UNREACHABLE = "ARM web UI is unreachable"


def _check_result(result: dict[str, Any] | list | None) -> dict[str, Any] | list:
    """Raise HTTPException if the ARM proxy result is None or reports failure."""
    if result is None:
        raise HTTPException(status_code=503, detail=_ARM_UI_UNREACHABLE)
    if isinstance(result, dict) and result.get("success") is False:
        detail = result.get("error") or result.get("Error") or "Action failed"
        raise HTTPException(status_code=502, detail=detail)
    return result


class RenameRequest(BaseModel):
    path: str
    new_name: str


class MoveRequest(BaseModel):
    path: str
    destination: str


class MkdirRequest(BaseModel):
    path: str
    name: str


class FixPermissionsRequest(BaseModel):
    path: str


class DeleteRequest(BaseModel):
    path: str


_503_ARM = {503: {"description": _ARM_UI_UNREACHABLE}}
_502_503_ARM = {502: {"description": "ARM action failed"}, 503: {"description": _ARM_UI_UNREACHABLE}}


@router.get("/roots", response_model=list[FileRoot], responses=_503_ARM)
async def get_roots() -> list[dict[str, Any]]:
    """Return configured media root directories."""
    return _check_result(await arm_client.get_file_roots())


@router.get("/list", response_model=DirectoryListing, responses=_502_503_ARM)
async def list_directory(path: str = Query(..., description="Directory path to list")) -> dict[str, Any]:
    """List contents of a directory."""
    return _check_result(await arm_client.list_files(path))


@router.post("/rename", response_model=OperationResult, responses=_502_503_ARM)
async def rename_file(body: RenameRequest) -> dict[str, Any]:
    """Rename a file or directory."""
    return _check_result(await arm_client.rename_file(body.path, body.new_name))


@router.post("/move", response_model=OperationResult, responses=_502_503_ARM)
async def move_file(body: MoveRequest) -> dict[str, Any]:
    """Move a file or directory."""
    return _check_result(await arm_client.move_file(body.path, body.destination))


@router.post("/mkdir", response_model=OperationResult, responses=_502_503_ARM)
async def create_directory(body: MkdirRequest) -> dict[str, Any]:
    """Create a new directory."""
    return _check_result(await arm_client.create_directory(body.path, body.name))


@router.post("/fix-permissions", response_model=OperationResult, responses=_502_503_ARM)
async def fix_permissions(body: FixPermissionsRequest) -> dict[str, Any]:
    """Fix ownership and permissions for a file or directory."""
    return _check_result(await arm_client.fix_file_permissions(body.path))


@router.delete("/delete", response_model=OperationResult, responses=_502_503_ARM)
async def delete_file(body: DeleteRequest) -> dict[str, Any]:
    """Delete a file or directory."""
    return _check_result(await arm_client.delete_file(body.path))
