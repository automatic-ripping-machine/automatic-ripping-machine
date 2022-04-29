"""Main run page for armui"""
import os  # noqa: F401
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from arm.ui import app  # noqa E402
from arm.config.config import cfg  # noqa E402
import arm.ui.routes  # noqa E402

host = cfg['WEBSERVER_IP']
if host == 'x.x.x.x':
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

if __name__ == '__main__':
    app.run(host=host, port=cfg['WEBSERVER_PORT'], debug=True)
