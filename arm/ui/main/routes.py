"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Main

Covers
- index [GET]

"""
import datetime
from flask import render_template, redirect

from ui.main import route_main


@route_main.route('/')
@route_main.route('/index.html')
@route_main.route('/index')
# @login_required
def home():


    return render_template('base_simple.html')
