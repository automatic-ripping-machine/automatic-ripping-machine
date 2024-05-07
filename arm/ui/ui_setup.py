"""
Automatic Ripping Machine - User Interface (UI)
    UI Flask reference module loader
"""
from flask_sqlalchemy import SQLAlchemy
# from flask_alembic import Alembic
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from flask_login import LoginManager

# Set up the database
db = SQLAlchemy()

# Initialise Flask Alembic
# alembic = Alembic()

# Initialise Flask Migrations
migrate = Migrate()

# Initialise Cross-Site Request Forgery Protection
csrf = CSRFProtect()

# Initialise the login manager
login_manager = LoginManager()
