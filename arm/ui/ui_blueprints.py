"""
Automatic Ripping Machine - User Interface (UI)
    UI Flask Blueprints
"""
from ui.main import route_main
from ui.errors import route_error
from ui.settings import route_settings
# from arm.ui.logs.logs import route_logs  # noqa: E402,F811
# from arm.ui.auth.auth import route_auth  # noqa: E402,F811
# from arm.ui.database.database import route_database  # noqa: E402,F811
# from arm.ui.history.history import route_history  # noqa: E402,F811
# from arm.ui.jobs.jobs import route_jobs  # noqa: E402,F811
# from arm.ui.sendmovies.sendmovies import route_sendmovies  # noqa: E402,F811
from arm.ui.notifications import route_notifications  # noqa: E402,F811


def register_blueprints(app):
    app.register_blueprint(route_main)
    app.register_blueprint(route_error)
    app.register_blueprint(route_settings)
    # app.register_blueprint(route_logs)
    # app.register_blueprint(route_auth)
    # app.register_blueprint(route_database)
    # app.register_blueprint(route_history)
    # app.register_blueprint(route_jobs)
    # app.register_blueprint(route_sendmovies)
    app.register_blueprint(route_notifications)
