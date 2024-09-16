from flask import Blueprint

route_logs = Blueprint('route_logs', __name__,
                       template_folder='templates',
                       static_folder='../static')

from ui.logs import routes  # noqa: E402, F401
