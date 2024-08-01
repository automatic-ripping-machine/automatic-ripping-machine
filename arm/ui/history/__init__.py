from flask import Blueprint

route_history = Blueprint('route_history', __name__,
                          template_folder='templates',
                          static_folder='../static')

from arm.ui.history import routes  # noqa: E402, F401
