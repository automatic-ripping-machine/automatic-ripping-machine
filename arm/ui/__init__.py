import sys, os, bcrypt
from flask import Flask, logging , current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from arm.config.config import cfg
from flask.logging import default_handler
from getpass import getpass
# import omdb

from flask_login import LoginManager

sqlitefile = 'sqlite:///' + cfg['DBFILE']



app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)

app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
## We should really gen a key for each system
app.config['SECRET_KEY'] = "Big secret key"
db = SQLAlchemy(app)

migrate = Migrate(app, db)
# omdb.set_default('apikey', cfg['OMDB_API_KEY'])

# import arm.ui.routes  # noqa: E402,F401
# import models.models  # noqa: E402
# import ui.config  # noqa: E402
# import ui.utils  # noqa: E402,F401

##Make the ARM dir if it doesnt exist
if not os.path.exists(cfg['ARMPATH']):
    os.makedirs(cfg['ARMPATH'])
##Make the RAW dir if it doesnt exist
if not os.path.exists(cfg['RAWPATH']):
    os.makedirs(cfg['RAWPATH'])
##Make the Media dir if it doesnt exist
if not os.path.exists(cfg['MEDIA_DIR']):
    os.makedirs(cfg['MEDIA_DIR'])
