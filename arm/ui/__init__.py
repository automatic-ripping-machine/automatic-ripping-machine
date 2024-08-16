"""
Automatic Ripping Machine - User Interface (UI)
    Flask factory
"""
import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import upgrade

from ui.setuplog import setuplog
from ui.ui_initialise import initialise_arm
from ui.ui_setup import db, migrate, csrf, login_manager
from ui_config import config_classes


def create_app(config_name=os.getenv("FLASK_ENV", "production")):
    # Define the ui_config class
    config_class = config_classes.get(config_name.lower())

    # Setup logging
    dictConfig = setuplog(config_class)

    app = Flask(__name__)
    app.config.from_object(config_class)
    csrf.init_app(app)
    CORS(app, resources={r"/*": {"origins": "*", "send_wildcard": "False"}})

    # Report system state for debugging
    app.logger.debug(f"Starting ARM in [{config_class.ENV}] mode")
    app.logger.debug(f'Debugging pin: {app.config["WERKZEUG_DEBUG_PIN"]}')
    app.logger.debug(f'Mysql configuration: {config_class.mysql_uri_sanitised}')
    app.logger.debug(f'SQLite Configuration: {config_class.sqlitefile}')
    app.logger.debug(f'Login Disabled: {app.config["LOGIN_DISABLED"]}')
    app.logger.info(f'Starting ARM UI on interface address - {app.config["SERVER_HOST"]}:{app.config["SERVER_PORT"]}')

    # Set log level per arm.yml config
    app.logger.info(f"Setting log level to: {app.config['LOGLEVEL']}")
    app.logger.setLevel(app.config['LOGLEVEL'])

    db.init_app(app)  # Initialise database
    app.logger.debug(f'Alembic Migration Folder: {config_class.alembic_migrations_dir}')
    migrate.init_app(app, db, directory=config_class.alembic_migrations_dir)

    # Initialise the Database and Flask Alembic
    with app.app_context():
        # Upgrade or load the ARM database to the latest head/version
        upgrade(directory=config_class.alembic_migrations_dir,
                revision='head')

        # Initialise the Flask-Login manager
        login_manager.init_app(app)

        # Register route blueprints
        from ui.ui_blueprints import register_blueprints
        register_blueprints(app)

        # Initialise ARM and ensure tables are set, when not in Test
        if not config_class.TESTING:
            initialise_arm(app, db)

        return app
