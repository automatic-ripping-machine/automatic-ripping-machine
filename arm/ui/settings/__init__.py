from flask import Blueprint

route_settings = Blueprint('route_settings', __name__,
                           template_folder='templates',
                           static_folder='../static')

from arm.ui.main import routes  # noqa: E402, F401
