from flask import render_template
import datetime

from ui.main import route_main

from models.alembic_version import AlembicVersion
from models.config import Config
from models.job import Job
from models.notifications import Notifications
from models.system_drives import SystemDrives
from models.system_info import SystemInfo
from models.track import Track
from models.ui_settings import UISettings
from models.user import User


@route_main.route('/')
def main():

    message = f"Hello World - the code is working - current time: [{datetime.datetime.now()}]"

    return message
