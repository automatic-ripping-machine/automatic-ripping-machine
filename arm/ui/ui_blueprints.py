"""
Automatic Ripping Machine - User Interface (UI)
    UI Flask Blueprints
"""
from arm.ui.main import route_main
from arm.ui.errors import route_error
from arm.ui.settings import route_settings
from arm.ui.logs import route_logs
from arm.ui.auth import route_auth
from arm.ui.database import route_database
from arm.ui.history import route_history
from arm.ui.jobs import route_jobs
from arm.ui.sendmovies import route_sendmovies
from arm.ui.notifications import route_notifications


def register_blueprints(app):
    app.register_blueprint(route_main)
    app.register_blueprint(route_error)
    app.register_blueprint(route_settings)
    app.register_blueprint(route_logs)
    app.register_blueprint(route_auth)
    app.register_blueprint(route_database)
    app.register_blueprint(route_history)
    app.register_blueprint(route_jobs)
    app.register_blueprint(route_sendmovies)
    app.register_blueprint(route_notifications)
