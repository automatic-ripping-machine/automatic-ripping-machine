# Settings/Stats
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from crud import create_job, get_ripper_settings, update_ui_settings, get_ui_settings, get_apprise_settings, \
    get_abcde_settings, get_stats, update_ripper_settings, update_apprise_settings, update_password
from database import get_db
from exceptions import JobException
from schemas import CreateAndUpdateJob, CreateAndUpdateUISettings, UISettingsSchemas, CreateAndUpdateConfig, \
    CreateAndUpdateRipper, CreateAndUpdateApprise, UpdatePassword
from utils.file_system import generate_comments

router = APIRouter()


# Change admin password
@router.put("/settings/update_password")
def change_admin_password(post_json: UpdatePassword, session: Session = Depends(get_db)):
    print(post_json)
    response = update_password(session, post_json)
    return response

# Get server stats
@router.get("/settings/stats")
def get_stats_for_server(session: Session = Depends(get_db)):
    return get_stats(session)

# Get ripper settings
@router.get("/settings/ripper")
def get_ripper_settings_route(session: Session = Depends(get_db)):
    return {"cfg": get_ripper_settings(session), "comments": generate_comments()}

# Save ripper settings
@router.put("/settings/ripper")
def save_ripper_settings(new_info: CreateAndUpdateRipper, session: Session = Depends(get_db)):
    try:
        ripper_settings = update_ripper_settings(session, new_info)
        return ripper_settings
    except JobException as cie:
        raise HTTPException(**cie.__dict__)

# Get abcde config
@router.get("/settings/get_abcde")
def get_abcde(session: Session = Depends(get_db)):
    return get_abcde_settings(session)

# Save abcde config (placeholder)
@router.put("/settings/get_abcde")
def save_abcde_config(session: Session = Depends(get_db)):
    return {"message": "Hello, get_abcde"}

# Get apprise config
@router.get("/settings/get_apprise")
def get_apprise(session: Session = Depends(get_db)):
    return {"cfg": get_apprise_settings(session), "comments": generate_comments()}

# Save apprise config
@router.put("/settings/get_apprise")
def save_apprise_config(new_info: CreateAndUpdateApprise, session: Session = Depends(get_db)):
    return {"cfg": update_apprise_settings(session, new_info), "comments": generate_comments()}

# Get UI config
@router.get("/settings/get_ui_conf")
def get_ui_conf(session: Session = Depends(get_db)):
    return {"cfg": get_ui_settings(session), "comments": generate_comments()}



# Save ui config
@router.put("/settings/get_ui_conf")
async def save_ui_conf(new_info: CreateAndUpdateUISettings, session: Session = Depends(get_db)):
    try:
        return update_ui_settings(session, new_info)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)
