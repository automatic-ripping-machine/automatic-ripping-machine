from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config.config import cfg
#import omdb


sqlitefile = 'sqlite:///' + cfg['DBFILE']

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "Big secret key"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#omdb.set_default('apikey', cfg['OMDB_API_KEY'])

import ui.routes  # noqa: E402
#import models.models  # noqa: E402
#import ui.config  # noqa: E402
#import ui.utils  # noqa: E402,F401
