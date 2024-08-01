from flask import Blueprint

route_main = Blueprint('main', __name__,
                       template_folder='templates')

from arm.ui.main import routes  # noqa: E402, F401
