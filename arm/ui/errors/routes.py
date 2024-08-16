"""
Automatic Ripping Machine - User Interface (UI) - Blueprint
    Errors

Covers
- error_404 [GET] - page not found
- error_500 [GET] - server error
- error_general Errors [GET] - general or other server error
"""
from flask import abort, render_template, request

from ui.errors import route_error


@route_error.app_errorhandler(404)
def not_found(e):
    # Requested URL
    requested_url = request.url
    error_title = "404"
    error_message = "When convention and science offer us no answers, might we not finally turn to the fantastic as a plausibility?"

    return render_template("error.html",
                           error_title=error_title,
                           error_message=error_message,
                           error=e,
                           requested_url=requested_url), 404


@route_error.app_errorhandler(500)
def error_500(e):
    error_title = "500"
    error_message = "Server Error - I am sorry Dave, I'm afraid I can't do that! "

    return render_template("error.html",
                           error_title=error_title,
                           error_message=error_message,
                           error=e,
                           ), 500


@route_error.route('/error')
def error_general(error=None):
    """
    Catch all error page
    :return: error.html
    """
    abort(500)
