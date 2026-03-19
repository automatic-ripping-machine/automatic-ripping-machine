# pylint: disable=wrong-import-position
"""Main run page for ARM API server."""
import logging
import os
import sys

# set the PATH to /arm/arm, so we can handle imports properly
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import arm.config.config as cfg  # noqa E402
from arm.database import db  # noqa E402
from arm.services import config as svc_config  # noqa E402
from arm.services import drives as svc_drives  # noqa E402


def _clear_stale_pause():
    """Clear ripping_paused flag left over from a previous container run."""
    try:
        from arm.models.app_state import AppState
        state = AppState.get()
        if state.ripping_paused:
            state.ripping_paused = False
            db.session.commit()
            logging.info("Cleared stale ripping_paused flag from previous run.")
    except Exception:
        pass  # Table may not exist yet (pre-migration)


def startup():
    db.init_engine('sqlite:///' + cfg.arm_config['DBFILE'])
    try:
        svc_config.check_db_version(
            cfg.arm_config['INSTALLPATH'],
            cfg.arm_config['DBFILE'],
        )
    except Exception as e:
        logging.error("Database initialization failed: %s", e)
    _clear_stale_pause()
    db_update = svc_config.arm_db_check()
    if db_update["db_current"]:
        logging.info("Updating Optical Drives")
        svc_drives.drives_update(startup=True)


def is_docker():
    """
    Test to check if running inside a docker/container
    returns: Boolean
    """
    path = '/proc/self/cgroup'
    return (
            os.path.exists('/.dockerenv') or
            os.path.isfile(path) and any('docker' in line for line in open(path))
    )


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


if __name__ == '__main__':
    host = get_host()
    port = cfg.arm_config['WEBSERVER_PORT']
    logging.info("Starting ARM API on interface address - %s:%s", host, port)
    startup()
    import uvicorn
    from arm.app import app  # noqa E402
    uvicorn.run(app, host=host, port=int(port), workers=1)
