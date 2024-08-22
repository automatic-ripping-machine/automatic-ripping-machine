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
from netifaces import interfaces, ifaddresses, AF_INET


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


def detect_ip() -> str:
    """
    Autodetect the host's IP address, excluding the loopback address ('127.0.0.1').

    This function scans all network interfaces on the host machine and collects non-loopback IPv4 addresses.
    If multiple IP addresses are detected, the first one in the list is returned.

    Returns:
        ip (str): The detected IP address.
                    If no suitable IP is found, the default
                    loopback address ('127.0.0.1') is returned.

    Example:
        If the host machine has an IP address of '192.168.1.100', the function
        will return that address, provided it is not the loopback address.
    """
    arm_ip = '127.0.0.1'
    # autodetect host IP address
    ip_list = []
    for interface in interfaces():
        inet_links = ifaddresses(interface).get(AF_INET, [])
        for link in inet_links:
            ip = link['addr']
            if ip != '127.0.0.1':
                ip_list.append(ip)
    if len(ip_list) > 0:
        arm_ip = ip_list[0]

    return arm_ip


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
        FLASK_DEBUG (bool): Enable Flask's debug mode if `True`.
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
        SQLALCHEMY_BINDS (dict): A dictionary of database URIs for different database connections (e.g., SQLite and MySQL).
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): If `False`, disables tracking of modifications to objects, which can save memory.
        alembic_migrations_dir (str): Directory where Alembic migration scripts are stored.
    """
    # Define the ARM Server UI
    APP_NAME: str = "Automatic Ripping Machine - User Interface"
    SERVER_HOST: str = host_ip(cfg.arm_config['WEBSERVER_IP'])
    SERVER_PORT: int = host_port(int(cfg.arm_config['WEBSERVER_PORT']))
    DOCKER: bool = is_docker()

    # Define system logs
    LOG_DIR: str = '/home/arm/logs'
    LOG_FILENAME: str = 'arm.log'

    # Define Flask system state
    FLASK_DEBUG: bool = True
    WERKZEUG_DEBUG: bool = True
    ENV: str = 'default'
    LOGIN_DISABLED: bool = cfg.arm_config['DISABLE_LOGIN']
    TESTING: bool = False

    LOGLEVEL: str = cfg.arm_config['LOGLEVEL']

    # Flask keys
    SECRET_KEY: str = "Big secret key"
    WERKZEUG_DEBUG_PIN: str = "12345"

    # Define the database configuration for ARM
    sqlitefile: str = 'sqlite:///' + cfg.arm_config['DBFILE']
    mysql_connector: str = 'mysql+mysqlconnector://'
    mysql_ip: str = os.getenv("MYSQL_IP", "127.0.0.1")
    mysql_user: str = os.getenv("MYSQL_USER", "arm")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "example")
    mysql_database: str = "arm"
    mysql_charset: str = '?charset=utf8mb4'
    mysql_uri: str = mysql_connector + mysql_user + ':' + mysql_password + '@' + mysql_ip \
                                   + '/' + mysql_database + mysql_charset
    mysql_uri_sanitised: str = mysql_connector + mysql_user + ':*******' + '@' + mysql_ip \
                               + '/' + mysql_database + mysql_charset

    # Default database connection is MYSQL, required for Alembic
    SQLALCHEMY_DATABASE_URI: str = mysql_uri
    # Create binds for swapping between databases during imports
    SQLALCHEMY_BINDS = {
        'sqlite':   sqlitefile,
        'mysql':    mysql_uri
    }
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Alembic config
    alembic_migrations_dir: str = "ui/migrations"


class Development(UIConfig):
    """
    ARM Flask Development config
    """
    FLASK_DEBUG: bool = True
    WERKZEUG_DEBUG: bool = True
    ENV: str = 'development'
    LOGIN_DISABLED: bool = True


class Testing(UIConfig):
    """
    ARM Flask Development config
    """
    FLASK_DEBUG: bool = True
    WERKZEUG_DEBUG: bool = True
    ENV: str = 'testing'
    LOGIN_DISABLED: bool = True
    TESTING: bool = True


class Production(UIConfig):
    """
    ARM Flask Production config
    """
    DEBUG = False
    ENV = 'production'
    TESTING = False


config_classes = {
    'development': Development,
    'testing': Testing,
    'production': Production,
}
