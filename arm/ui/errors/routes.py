"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Errors

Covers
- error_404 [GET] - page not found
- error_500 [GET] - server error
- error_general Errors [GET] - general or other server error
"""
import werkzeug
from flask import render_template

from ui.errors import route_error


@route_error.app_errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@route_error.app_errorhandler(werkzeug.exceptions.InternalServerError)
def error_500():
    return render_template("500.html"), 500


@route_error.route('/error')
def error_general(error=None):
    """
    Catch all error page
    :return: Error page
    """
    return render_template("error.html", error=error), 500
