from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from armui.config import cfg

print("DBFILE = " + cfg['DBFILE'])
sqlitefile = 'sqlite:///' + cfg['DBFILE']
# sqlitefile = 'sqlite:///C:\\\\etc\\\\arm\\\\db\\\\arm.db'
print("sqlitefile = " + sqlitefile)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
migrate = Migrate(app, db)

import armui.routes  # noqa: E402
import armui.models  # noqa: E402
import armui.config  # noqa: E402
import armui.utils  # noqa: E402,F401