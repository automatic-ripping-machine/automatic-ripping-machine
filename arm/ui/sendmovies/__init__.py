from flask import Blueprint

route_sendmovies = Blueprint('route_sendmovies', __name__,
                             template_folder='templates',
                             static_folder='../static')

from arm.ui.sendmovies import routes  # noqa: E402, F401
