# Service file for use in Ubuntu 18.04  - Last Tested 2022-04-19


```
[Unit]
Description=Arm service
## Added to force armui to wait for network
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=arm
Group=arm
## These dont work on on 18
StandardOutput=append:/home/arm/logs/WebUI.log
StandardError=append:/home/arm/logs/WebUI.log
Restart=always
RestartSec=3
ExecStart=/bin/sh -c 'exec /usr/bin/python3 /opt/arm/arm/runui.py >/home/arm/logs/web.log 2>/home/arm/logs/web.log'
[Install]
WantedBy=multi-user.target

```