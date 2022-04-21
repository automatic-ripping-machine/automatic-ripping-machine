"""Main arm ui file"""
import sys  # noqa: F401
import os  # noqa: F401
from getpass import getpass  # noqa: F401
from flask import Flask, logging, current_app  # noqa: F401
from flask.logging import default_handler  # noqa: F401
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf import CSRFProtect
from flask_login import LoginManager
import bcrypt  # noqa: F401
from arm.config.config import cfg

sqlitefile = 'sqlite:///' + cfg['DBFILE']

app = Flask(__name__)
csrf = CSRFProtect()
csrf.init_app(app)
CORS(app, resources={r"/*": {"origins": "*", "send_wildcard": "False"}})

login_manager = LoginManager()
login_manager.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# We should really gen a key for each system
app.config['SECRET_KEY'] = "Big secret key"
app.config['LOGIN_DISABLED'] = cfg['DISABLE_LOGIN']

db = SQLAlchemy(app)

migrate = Migrate(app, db)
