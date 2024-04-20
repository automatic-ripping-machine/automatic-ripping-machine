from flask import render_template
import datetime

from ui.main import route_main


@route_main.route('/')
def main():

    message = f"Hello World - the code is working - current time: [{datetime.datetime.now()}]"

    return message
