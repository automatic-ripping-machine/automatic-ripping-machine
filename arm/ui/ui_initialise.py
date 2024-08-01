"""
Automatic Ripping Machine - User Interface (UI)
    UI Initiation

    initialise_arm - functions to setup ARM
"""
import bcrypt

from models.ui_settings import UISettings
from models.user import User


def initialise_arm(app, db):
    # Check database - User
    create_admin = False
    try:
        with app.app_context():
            admins = User.query.all()
        app.logger.debug(f"User count: {len(admins)}")
        if len(admins) > 0:
            return True
    except Exception:
        app.logger.debug("Couldn't find User Table")
        create_admin = True
    else:
        app.logger.debug("Found table but no data ...")
        create_admin = True

    if create_admin:
        app.logger.debug("Adding Default ARM User")
        hashed = bcrypt.gensalt(12)
        default_user = User("admin",
                            bcrypt.hashpw("password".encode('utf-8'), hashed).decode('utf-8'),
                            hashed.decode('utf-8'),
                            )
        with app.app_context():
            db.session.add(default_user)
            db.session.commit()

    # Check database - UISettings
    create_uisettings = False
    try:
        with app.app_context():
            uisettings = UISettings.query.all()
        app.logger.debug(f"UISettings count: {len(uisettings)}")
        if len(uisettings) > 0:
            return True
    except Exception:
        app.logger.debug("Couldn't find UISettings Table")
        create_uisettings = True
    else:
        app.logger.debug("Found table but no data ...")
        create_uisettings = True

    if create_uisettings:
        ui_config = UISettings(True,
                               True,
                               "spacelab",
                               "en",
                               2000,
                               200
                               )
        with app.app_context():
            db.session.add(ui_config)
            db.session.commit()
