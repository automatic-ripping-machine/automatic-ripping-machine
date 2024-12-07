"""Main arm ui file"""
import sys  # noqa: F401
import os  # noqa: F401
from getpass import getpass  # noqa: F401
from logging.config import dictConfig
from flask import Flask, logging, current_app  # noqa: F401
from flask.logging import default_handler  # noqa: F401
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf import CSRFProtect

from flask_login import LoginManager
import bcrypt  # noqa: F401
import arm.config.config as cfg

sqlitefile = 'sqlite:///' + cfg.arm_config['DBFILE']

# Setup logging, but because of werkzeug issues, we need to set up that later down file
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s ARM: %(module)s.%(funcName)s %(message)s',
    }},
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        "console": {"class": "logging.StreamHandler", "level": "INFO"},
        "null": {"class": "logging.NullHandler"},
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    },
})

app = Flask(__name__)
csrf = CSRFProtect()
csrf.init_app(app)
CORS(app, resources={r"/*": {"origins": "*", "send_wildcard": "False"}})

login_manager = LoginManager()
login_manager.init_app(app)

# Set log level per arm.yml config
app.logger.info(f"Setting log level to: {cfg.arm_config['LOGLEVEL']}")
app.logger.setLevel(cfg.arm_config['LOGLEVEL'])

# Set Flask database connection configurations
app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# We should really generate a key for each system
app.config['SECRET_KEY'] = "Big secret key"  # TODO: make this random!
# Set the global Flask Login state, set to True will ignore any @login_required
app.config['LOGIN_DISABLED'] = cfg.arm_config['DISABLE_LOGIN']
app.logger.debug(f"Disable Login: {cfg.arm_config['DISABLE_LOGIN']}")
# Set debug pin as it is hidden normally
os.environ["WERKZEUG_DEBUG_PIN"] = "12345"  # make this random!
app.logger.debug("Debugging pin: " + os.environ["WERKZEUG_DEBUG_PIN"])

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Register route blueprints
# loaded post database declaration to avoid circular loops
from arm.ui.settings.settings import route_settings  # noqa: E402,F811
from arm.ui.logs.logs import route_logs  # noqa: E402,F811
from arm.ui.auth.auth import route_auth  # noqa: E402,F811
from arm.ui.database.database import route_database  # noqa: E402,F811
from arm.ui.history.history import route_history  # noqa: E402,F811
from arm.ui.jobs.jobs import route_jobs  # noqa: E402,F811
from arm.ui.sendmovies.sendmovies import route_sendmovies  # noqa: E402,F811
from arm.ui.notifications.notifications import route_notifications  # noqa: E402,F811
app.register_blueprint(route_settings)
app.register_blueprint(route_logs)
app.register_blueprint(route_auth)
app.register_blueprint(route_database)
app.register_blueprint(route_history)
app.register_blueprint(route_jobs)
app.register_blueprint(route_sendmovies)
app.register_blueprint(route_notifications)

# Remove GET/page loads from logging
import logging  # noqa: E402,F811
logging.getLogger('werkzeug').setLevel(logging.ERROR)
