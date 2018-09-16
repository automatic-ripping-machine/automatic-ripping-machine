from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from armui.config import cfg
import omdb


sqlitefile = 'sqlite:///' + cfg['DBFILE']

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "Big secret key"
db = SQLAlchemy(app)
migrate = Migrate(app, db)

omdb.set_default('apikey', cfg['OMDB_API_KEY'])

import armui.routes  # noqa: E402
import armui.models  # noqa: E402
import armui.config  # noqa: E402
import armui.utils  # noqa: E402,F401