from flask import Blueprint

route_notifications = Blueprint('route_notifications', __name__,
                                template_folder='templates',
                                static_folder='../static')

from arm.ui.notifications import routes  # noqa: E402, F401
