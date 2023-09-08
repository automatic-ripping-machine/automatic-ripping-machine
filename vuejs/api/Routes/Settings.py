# Settings/Stats
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi_utils.cbv import cbv
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


# Example of Class based view
@cbv(router)
class Settings:
    session: Session = Depends(get_db)

    @router.put("/settings/update_password")
    def change_admin_password(self, post_json: UpdatePassword):
        print(post_json)
        response = update_password(self.session, post_json)
        return response

    # API to get stats of the server
    @router.get("/settings/stats")
    def get_stats_for_server(self):
        response = get_stats(self.session)
        return response

    # Get ripper settings
    @router.get("/settings/ripper")
    def get_ripper_settings(self):
        response = {"cfg": get_ripper_settings(self.session), 'comments': generate_comments()}
        return response

    # Save ripper settings
    @router.put("/settings/ripper")
    def save_ripper_settings(self, new_info: CreateAndUpdateRipper):
        try:
            ripper_settings = update_ripper_settings(self.session, new_info)
            return ripper_settings
        except JobException as cie:
            raise HTTPException(**cie.__dict__)

    # Get abcde config
    @router.get("/settings/get_abcde")
    def get_abcde(self):
        return get_abcde_settings(self.session)

    # Save abcde config
    @router.put("/settings/get_abcde")
    def save_abcde_config(self):
        return {"message": "Hello, get_abcde"}

    # Get apprise config
    @router.get("/settings/get_apprise")
    def get_apprise(self):
        return { 'cfg': get_apprise_settings(self.session), 'comments': generate_comments()}

    # Save apprise config
    @router.put("/settings/get_apprise")
    def save_apprise_config(self, new_info: CreateAndUpdateApprise):
        return { 'cfg': update_apprise_settings(self.session, new_info), 'comments': generate_comments()}

    # Get ui config
    @router.get("/settings/get_ui_conf")
    def get_ui_conf(self):
        return {'cfg': get_ui_settings(self.session), 'comments': generate_comments()}


# Save ui config
@router.put("/settings/get_ui_conf")
async def save_ui_conf(new_info: CreateAndUpdateUISettings, session: Session = Depends(get_db)):
    try:
        return update_ui_settings(session, new_info)
    except JobException as cie:
        raise HTTPException(**cie.__dict__)