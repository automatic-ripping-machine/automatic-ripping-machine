import os
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

mysql_user = os.getenv("MYSQL_USER", "root")
mysql_password = os.getenv("MYSQL_PASSWORD", "example")
mysql_ip = os.getenv("MYSQL_IP", "127.0.0.1")
DATABASE_URL = 'mysql+mysqlconnector://' + mysql_user + ':' + mysql_password + '@' + mysql_ip + '/arm'

db_engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

Base = declarative_base()


def get_db():
    """
    Function to generate db session\n
    :return: Session
    """
    db = None
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


async def init_db():
    try:
        # Create the tables
        Base.metadata.create_all(bind=db_engine)
        # Connect to the database
        db = SessionLocal()
        # Mysql needs this here as data doesn't get added from the upgrade path
        add_database_version(db)
        add_server_info(db)
        add_ui_settings(db)
        add_default_user(db)
        db.close()
    except Exception as e:
        print(e)
        raise e


def add_server_info(db):
    try:
        from models import SystemInfo
        # Create the server info
        server = SystemInfo()
        # Add the server details
        db.add(server)
        # Commit and close connection
        db.commit()
    except Exception:
        db.rollback()


def add_default_user(db):
    try:
        from models import User
        hashed = bcrypt.gensalt(12)
        # Add the primary user
        db.add(User(username="admin", password=bcrypt.hashpw("password".encode('utf-8'), hashed),
                    hash=hashed, disabled=False))
        db.commit()
    except Exception:
        db.rollback()


def add_ui_settings(db):
    try:
        from models import UISettings
        ui_config = UISettings(1, 1, "spacelab", "en", 2000, 200)
        db.add(ui_config)
    except Exception:
        db.rollback()


def add_database_version(db):
    try:
        from models import AlembicVersion
        version = AlembicVersion('2e0dc31fcb2e')
        db.add(version)
        db.commit()
    except Exception:
        db.rollback()
