"""
Automatic Ripping Machine - User Interface (UI)
    UI Flask Blueprints
"""
from ui.main import route_main
from ui.errors import route_error
from ui.settings import route_settings
from ui.logs import route_logs
from ui.auth import route_auth
from ui.database import route_database
from ui.history import route_history
from ui.jobs import route_jobs
from ui.sendmovies import route_sendmovies
from ui.notifications import route_notifications


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
    # Developer JSON API - registered only when enabled in arm.yaml
    if app.config.get('ENABLE_DEVTOOLS', False):
        from ui.devtools import create_blueprint
        app.register_blueprint(create_blueprint())
