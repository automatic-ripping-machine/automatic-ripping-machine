from flask import Blueprint

route_database = Blueprint('route_database', __name__,
                           template_folder='templates',
                           static_folder='../static')

from ui.database import routes  # noqa: E402, F401
