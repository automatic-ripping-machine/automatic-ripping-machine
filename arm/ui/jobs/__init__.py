from flask import Blueprint

route_jobs = Blueprint('route_jobs', __name__,
                       template_folder='templates',
                       static_folder='../static')

from ui.jobs import routes  # noqa: E402, F401
