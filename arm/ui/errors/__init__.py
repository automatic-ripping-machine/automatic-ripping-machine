from flask import Blueprint

route_error = Blueprint('errors', __name__,
                        template_folder='templates',
                        static_folder='../static')

from arm.ui.errors import routes  # noqa: E402, F401
