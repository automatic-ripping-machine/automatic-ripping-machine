# pylint: disable=wrong-import-position
"""Main run page for armui"""
import os
import sys
import signal

# set the PATH to /arm/arm, so we can handle imports properly
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import arm.config.config as cfg  # noqa E402
import arm.ui.routes  # noqa E402
import arm.ui.settings.DriveUtils  # noqa E402
import arm.ui.utils  # noqa E402

from arm.ui import app  # noqa E402

shutdown_requested = False


def startup():
    """ARM UI Startup check on database config"""
    db_update = arm.ui.utils.arm_db_check()
    if db_update["db_current"]:
        app.logger.info("Updating Optical Drives")
        arm.ui.settings.DriveUtils.drives_update(startup=True)


def handle_shutdown(signum, frame):
    """ARM handle SIGTERM/SIGINT for graceful shutdown"""
    global shutdown_requested
    shutdown_requested = True
    app.logger.info("Received shutdown signal (%s). Shutting down ARM-UI.", signum)
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)      # systemd shutdown command
signal.signal(signal.SIGINT, handle_shutdown)       # keyboard interrupt


def is_docker():
    """
    Test to check if running inside a docker/container
    returns: Boolean
    """
    path = '/proc/self/cgroup'

    if os.path.exists('/.dockerenv'):
        return True

    if os.path.isfile(path):
        with open(path) as f:
            return any('docker' in line for line in f)

    return False


def get_host():
    host = cfg.arm_config['WEBSERVER_IP']
    # Check if auto ip address 'x.x.x.x' or if inside docker - set internal ip from host and use WEBSERVER_IP for notify
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
            host = ip_list[0]
        else:
            host = '127.0.0.1'
    return host


# Start ARM using waitress, default number of threads is "4", set ARM count to "40"
# Higher thread count to accommodate slow blocking processes when the UI is polling the ripper during ripping
if __name__ == '__main__':
    host = get_host()
    port = cfg.arm_config['WEBSERVER_PORT']
    app.logger.info("Starting ARM-UI on interface address - %s:%s", host, port)

    # Run ARM Startup
    startup()

    from waitress import serve

    try:
        serve(app, host=host, port=port, threads=40)
    except KeyboardInterrupt:
        app.logger.info("Keyboard interrupt received, shutting down ARM-UI.")
    finally:
        app.logger.info("ARM-UI shutdown complete.")
