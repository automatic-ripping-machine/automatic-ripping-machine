import os
from config import config as cfg


def is_docker() -> bool:
    """
    Test to check if running inside a docker/container

    input: None
    returns: Boolean
    """
    path = '/proc/self/cgroup'
    return (
            os.path.exists('/.dockerenv') or
            os.path.isfile(path) and any('docker' in line for line in open(path))
    )


def host_ip(host) -> str:
    """
    Check if auto ip address 'x.x.x.x' or if inside docker
    set internal ip from host and use WEBSERVER_IP for notify

    input: None
    returns: Boolean
    """
    host_ip = '127.0.0.1'

    if host == 'x.x.x.x' or is_docker():
        # autodetect host IP address
        from netifaces import interfaces, ifaddresses, AF_INET
        ip_list = []
        for interface in interfaces():
            inet_links = ifaddresses(interface).get(AF_INET, [])
            for link in inet_links:
                ip = link['addr']
                if ip != '127.0.0.1':
                    ip_list.append(ip)
        if len(ip_list) > 0:
            host_ip = ip_list[0]
    else:
        host_ip = host

    return host_ip


class UIConfig:
    """
    ARM UI Flask Configuration Class
    Class configures the Flask config variables required based on input from the arm.yml config file

    input: None
    returns: None all values called within Class
    """
    # Define the ARM Server UI
    APP_NAME: str = "Automatic Ripping Machine - User Interface"
    SERVER_HOST: str = host_ip(cfg.arm_config['WEBSERVER_IP'])
    SERVER_PORT: int = int(cfg.arm_config['WEBSERVER_PORT'])

    # Define system logs
    LOG_DIR: str = '/home/arm/logs'
    LOG_FILENAME: str = 'arm.log'

    # Define Flask system state
    FLASK_DEBUG: bool = True
    WERKZEUG_DEBUG: bool = True
    ENV: str = 'development'
    LOGIN_DISABLED: bool = cfg.arm_config['DISABLE_LOGIN']
    TESTING: bool = False

    # Flask keys
    SECRET_KEY: str = "Big secret key"
    WERKZEUG_DEBUG_PIN: str = "12345"

    # Define the database configuration for ARM
    # sqlitefile: str = 'sqlite:///' + cfg.arm_config['DBFILE']

    mysql_connector: str = 'mysql+mysqlconnector://'
    mysql_ip: str = os.getenv("MYSQL_IP", "127.0.0.1")
    mysql_user: str = os.getenv("MYSQL_USER", "arm")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "example")
    mysql_database: str = "arm"
    mysql_charset: str = '?charset=utf8mb4'
    SQLALCHEMY_DATABASE_URI_SANITISED: str = mysql_connector + mysql_user + ':*******' + '@' + mysql_ip \
                                             + '/' + mysql_database + mysql_charset

    SQLALCHEMY_DATABASE_URI: str = mysql_connector + mysql_user + ':' + mysql_password + '@' + mysql_ip \
                                   + '/' + mysql_database + mysql_charset
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ARM UI configuration
    # HOME_PAGE = '/index'
    # ERROR_PAGE = 'error.html'
    # ERROR_REDIRECT = "/error"
    # SETUP_STAGE_2 = '/setup'
    # NO_ADMIN_ACCOUNT = "No admin account found"
    # NO_JOB = "No job supplied"
    # JSON_TYPE = "application/json"


class Development(UIConfig):
    """
    ARM Flask Development config
    """

    # DEBUG = True
    # ENV = 'dev'
    # TESTING = True
    #
    # mysql_ip = os.getenv("MYSQL_IP", "127.0.0.1")
    # mysql_user = os.getenv("MYSQL_USER", "arm")
    # mysql_password = os.getenv("MYSQL_PASSWORD", "example")
    # mysql_database = "arm"
    #
    # SQLALCHEMY_DATABASE_URI: str = mysql_connector + mysql_user + ':' + mysql_password \
    #                                + '@' + mysql_ip + '/' + mysql_database + mysql_charset


class Staging(UIConfig):
    """
    ARM Flask Staging config
    """

    DEBUG = True
    ENV = 'staging'
    TESTING = True


class Production(UIConfig):
    """
    ARM Flask Production config
    """

    DEBUG = False
    ENV = 'production'
    TESTING = False


config = {
    'development': Development,
    'staging': Staging,
    'production': Production,
}
