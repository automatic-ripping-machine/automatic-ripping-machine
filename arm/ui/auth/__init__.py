from flask import Blueprint

route_auth = Blueprint('route_auth', __name__,
                       template_folder='templates',
                       static_folder='../static')

from ui.auth import routes  # noqa: E402, F401
