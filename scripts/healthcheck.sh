#!/bin/sh

if [ ! -f /etc/arm/arm.yaml ]; then cp /opt/arm/migrations/config/arm.yaml /etc/arm/arm.yaml; fi || exit 1
if [ ! -f /etc/arm/apprise.yaml ]; then cp /opt/arm/migrations/config/apprise.yaml /etc/arm/apprise.yaml; fi || exit 1
if [ ! -f /etc/arm/abcde.conf ]; then cp /opt/arm/migrations/config/abcde.conf /etc/arm/abcde.conf; fi || exit 1
chown -R root:arm /etc/arm/* /var/lib/arm /var/log/arm || exit 1
chmod -R ug=rw,o=r /etc/arm/* /var/lib/arm /var/log/arm || exit 1
chmod +x /etc/arm /var/lib/arm /var/lib/arm/data /var/log/arm || exit 1
cp -n /opt/arm/devtools/* /opt/arm/tools/ || exit 1

curl --fail "http://$(hostname -i):8080" || exit 1
ps -e | pgrep systemd-udevd || exit 1
makemkvcon | grep www.makemkv.com/developers || exit 1
HandBrakeCLI --version || exit 1
abcde -v || exit 1

exit 0