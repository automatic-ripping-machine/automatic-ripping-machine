"""Main run page for armui"""
import os  # noqa: F401
import sys

# set the PATH to /arm/arm, so we can handle imports properly
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import arm.config.config as cfg  # noqa E402
from arm.ui import app  # noqa E402
import arm.ui.routes  # noqa E402


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
    app.logger.info(f"Starting ARMUI on interface address - {host}:{cfg.arm_config['WEBSERVER_PORT']}")

if __name__ == '__main__':
    from waitress import serve
    serve(app, host=host, port=cfg.arm_config['WEBSERVER_PORT'])
