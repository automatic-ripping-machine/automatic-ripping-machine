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
from flask.logging import default_handler  # noqa: F401
from getpass import getpass  # noqa: F401

from flask_login import LoginManager
import bcrypt  # noqa: F401
import arm.config.config as cfg

sqlitefile = 'sqlite:///' + cfg.arm_config['DBFILE']

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s ARM: %(module)s.%(funcName)s %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)
csrf = CSRFProtect()
csrf.init_app(app)
CORS(app, resources={r"/*": {"origins": "*", "send_wildcard": "False"}})

login_manager = LoginManager()
login_manager.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# We should really generate a key for each system
app.config['SECRET_KEY'] = "Big secret key"
app.config['LOGIN_DISABLED'] = cfg.arm_config['DISABLE_LOGIN']

db = SQLAlchemy(app)

migrate = Migrate(app, db)
