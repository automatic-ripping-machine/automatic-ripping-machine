"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Main

Covers
    - index [GET]
"""
import datetime
from flask import render_template, redirect
from flask import current_app as app

from ui.main import route_main
from models.ui_settings import UISettings


# @route_main.route('/')
# @route_main.route('/index.html')
# @route_main.route('/index')
# # @login_required
# def home():
#
#     ui_settings = UISettings().query.first()
#     app.logger.debug(ui_settings)
#
#     return render_template('base_simple.html')
