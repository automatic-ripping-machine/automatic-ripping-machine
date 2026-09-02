"""
Automatic Ripping Machine - User Interface (UI)
    UI Flask Configuration Settings

    Functions:
    - is_docker - test if ARM running in docker container
    - host_ip - return the host's IP address

    Class
    - UIConfig - Config class for the Flask Settings
"""
import os
from config import config as cfg
from common.server_ip import detect_ip


def is_docker() -> bool:
    """
    Determines if the current environment is a Docker container.

    This function checks specific system files and paths to identify whether the code is running
    inside a Docker container.
    It does this by checking for the presence of the `/.dockerenv` file
    and by examining the `/proc/self/cgroup` file for references to Docker.

    Returns:
        bool: `True` if running inside a Docker container, `False` otherwise.
    """
    path = '/proc/self/cgroup'
    return (
            os.path.exists('/.dockerenv') or
            os.path.isfile(path) and any('docker' in line for line in open(path))
    )


def host_ip(host) -> str:
    """
    Determines the appropriate IP address to use based on the input host and the Docker environment.

    This function checks if the application is running inside a Docker container.
    If it is not in Docker and the provided host is 'x.x.x.x', it attempts to autodetect the host's IP address.
    Otherwise, it returns the provided host IP.

    Args:
        host (str): The input host IP address. If this is 'x.x.x.x', the function will attempt to autodetect
                    the actual IP address.

    Returns:
        ip (str): The determined IP address. If autodetection fails or if running inside Docker, the default
                    '0.0.0.0' may be returned.
    """
    arm_ip = '0.0.0.0'

    if not is_docker():
        if host == 'x.x.x.x':
            arm_ip = detect_ip()
        else:
            arm_ip = host

    return arm_ip


def host_port(port) -> int:
    """
    Determines the appropriate port to use based on the input port and the Docker environment.

    This function checks if the application is running inside a Docker container.
    If it is not in Docker, the function will use the provided port.
    Otherwise, it defaults to port 8080.

    Args:
        port (int): The input port number to use.
                    If the application is not running inside Docker, this port will be returned.

    Returns:
        port (int): The determined port number.
                    If the application is running inside Docker, default port 8080 is returned.
    """
    arm_port = 8080
    if not is_docker():
        arm_port = port

    return arm_port


class UIConfig:
    """
    ARM UI Flask Configuration Class.

    This class configures the Flask application by setting up various configuration variables
    required for the Automatic Ripping Machine (ARM) User Interface, based on the input from
    the `arm.yml` configuration file.

    Attributes:
        APP_NAME (str): The name of the ARM UI application.
        SERVER_HOST (str): The host IP address for the ARM UI server.
        SERVER_PORT (int): The port on which the ARM UI server will run.
        DOCKER (bool): Indicates whether the application is running inside a Docker container.
        LOG_DIR (str): Directory where system logs are stored.
        LOG_FILENAME (str): Filename for the ARM log file.
        LOG_PATH (str): Directory and filename for the ARM log file.
        LOG_SIZE (int): Maximum size of the ARM log file in MB.
        LOG_COUNT (int): Maximum number of logs to keep, for log rotation.
        FLASK_ENV (str): The name of the environment to use for the application.
        FLASK_DEBUG (bool): Enable Flask's debug mode if `True`.
        DEBUG (bool): Flask debug mode if `True`.
        WERKZEUG_DEBUG (bool): Enables Werkzeug's debug mode if `True`.
        ENV (str): The environment setting for Flask (e.g., 'development', 'production').
        LOGIN_DISABLED (bool): Disables login authentication if `True`.
        TESTING (bool): Indicates if the Flask application is in testing mode.
        LOGLEVEL (str): The logging level for the application (e.g., 'DEBUG', 'INFO').
        SECRET_KEY (str): The secret key used by Flask for session management and other security features.
        WERKZEUG_DEBUG_PIN (str): The pin for Werkzeug's debug mode.
        sqlitefile (str): URI for the SQLite database.
        mysql_connector (str): URI prefix for the MySQL connector.
        mysql_ip (str): The IP address of the MySQL database.
        mysql_user (str): The MySQL database username.
        mysql_password (str): The MySQL database password.
        mysql_database (str): The name of the MySQL database to connect to.
        mysql_charset (str): The character set used by the MySQL database.
        mysql_uri (str): Full URI for connecting to the MySQL database.
        mysql_uri_sanitised (str): Sanitised URI for MySQL connection, with the password obscured.
        SQLALCHEMY_DATABASE_URI (str): The default database URI for SQLAlchemy.
        SQLALCHEMY_BINDS (dict): A dictionary of database URIs for different database connections
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): If `False`, disables tracking of mods to objects, which can save memory.
        alembic_migrations_dir (str): Directory where Alembic migration scripts are stored.
    """
    def __init__(self):
        # Define the ARM Server UI
        self.APP_NAME: str = "Automatic Ripping Machine - User Interface"
        self.SERVER_HOST: str = host_ip(cfg.arm_config['WEBSERVER_IP'])
        self.SERVER_PORT: int = host_port(int(cfg.arm_config['WEBSERVER_PORT']))
        self.DOCKER: bool = is_docker()

        # Define system logs
        self.LOG_DIR: str = os.getenv("ARM_HOME", "/arm")
        self.LOG_FILENAME: str = 'arm_ui.log'
        self.LOG_PATH: str = os.path.join(self.LOG_DIR, "logs", self.LOG_FILENAME)
        self.LOG_SIZE: int = 5
        self.LOG_COUNT: int = 2

        # Define Flask system state
        self.FLASK_ENV: str = "production"
        self.FLASK_DEBUG: bool = False
        self.DEBUG: bool = False
        self.WERKZEUG_DEBUG: bool = False
        self.ENV: str = 'default'
        self.LOGIN_DISABLED: bool = cfg.arm_config['DISABLE_LOGIN']
        self.ENABLE_DEVTOOLS: bool = cfg.arm_config.get('ENABLE_DEVTOOLS', False)
        self.TESTING: bool = False

        self.LOGLEVEL: str = cfg.arm_config['LOGLEVEL']

        # Flask keys
        self.SECRET_KEY: str = "Big secret key"
        self.WERKZEUG_DEBUG_PIN: str = "12345"

        # Alembic config
        self.alembic_migrations_dir: str = "/opt/arm/arm/ui/migrations"

        # Define the database configuration for ARM
        self.sqlitefile: str = 'sqlite:///' + cfg.arm_config['DBFILE']
        self.mysql_connector: str = 'mysql+mysqlconnector://'
        self.mysql_ip: str = os.getenv("MYSQL_IP", "127.0.0.1")
        self.mysql_user: str = os.getenv("MYSQL_USER", "arm")
        self.mysql_password: str = os.getenv("MYSQL_PASSWORD", "example")
        self.MYSQL_DATABASE: str = "arm"
        self.mysql_charset: str = '?charset=utf8mb4'
        self.mysql_uri: str = (
            self.mysql_connector + self.mysql_user + ':' + self.mysql_password + '@' + self.mysql_ip
            + '/' + self.MYSQL_DATABASE + self.mysql_charset
        )
        self.mysql_uri_sanitised: str = (
            self.mysql_connector + self.mysql_user + ':*******' + '@' + self.mysql_ip
            + '/' + self.MYSQL_DATABASE + self.mysql_charset
        )

        # Default database connection is MYSQL, required for Alembic
        self.SQLALCHEMY_DATABASE_URI: str = self.mysql_uri
        # Create binds for swapping between databases during imports
        self.SQLALCHEMY_BINDS = {
            'sqlite': self.sqlitefile,
            'mysql': self.mysql_uri
        }
        self.SQLALCHEMY_TRACK_MODIFICATIONS: bool = False


class Development(UIConfig):
    """
    ARM Flask Development config
    """
    def __init__(self):
        super().__init__()

        self.FLASK_ENV = "development"
        self.FLASK_DEBUG = True
        self.DEBUG = True
        self.WERKZEUG_DEBUG: bool = True
        self.ENV: str = 'development'
        self.LOGIN_DISABLED: bool = True
        self.LOGLEVEL = "DEBUG"


class Testing(UIConfig):
    """
    ARM Flask Development config
    """
    def __init__(self):
        super().__init__()

        self.FLASK_ENV = "development"
        self.FLASK_DEBUG = True
        self.DEBUG = True
        self.WERKZEUG_DEBUG: bool = True
        self.ENV: str = 'testing'
        self.LOGIN_DISABLED: bool = True
        self.TESTING: bool = True
        self.LOGLEVEL = "DEBUG"

        self.MYSQL_DATABASE = "arm_testing"

        self.mysql_uri: str = (
            self.mysql_connector + self.mysql_user + ':' + self.mysql_password + '@' + self.mysql_ip
            + '/' + self.MYSQL_DATABASE + self.mysql_charset
        )
        self.mysql_uri_sanitised: str = (
            self.mysql_connector + self.mysql_user + ':*******' + '@' + self.mysql_ip
            + '/' + self.MYSQL_DATABASE + self.mysql_charset
        )

        # Default database connection is MYSQL, required for Alembic
        self.SQLALCHEMY_DATABASE_URI: str = self.mysql_uri
        # Create binds for swapping between databases during imports
        self.SQLALCHEMY_BINDS = {
            'sqlite': self.sqlitefile,
            'mysql': self.mysql_uri
        }
        self.SQLALCHEMY_TRACK_MODIFICATIONS: bool = False


class Production(UIConfig):
    """
    ARM Flask Production config
    """
    def __init__(self):
        super().__init__()

        self.DEBUG = False
        self.ENV = 'production'
        self.TESTING = False


config_classes = {
    'development': Development,
    'testing': Testing,
    'production': Production,
}
