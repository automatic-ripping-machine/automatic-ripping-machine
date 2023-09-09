"""Main arm ui file"""
import os

from getpass import getpass  # noqa: F401
from flask import Flask, logging, current_app  # noqa: F401
from flask.logging import default_handler  # noqa: F401
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
app = Flask(__name__)

mysql_user = os.getenv("MYSQL_USER", "root")
mysql_password = os.getenv("MYSQL_PASSWORD", "example")
mysql_ip = os.getenv("MYSQL_IP", "127.0.0.1")

app.config['SQLALCHEMY_DATABASE_URI'] = ('mysql+mysqlconnector://' + mysql_user + ':'
                                         + mysql_password + '@' + mysql_ip + '/arm')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy()
db.init_app(app)
app.app_context().push()
migrate = Migrate(app, db)

# Remove GET/page loads from logging
import logging  # noqa: E402,F811
logging.getLogger('werkzeug').setLevel(logging.ERROR)
