#!/bin/bash

# Setup automatic-ripping-machine (ARM) for Debian systems.
# Taken from pull #429  - User: TechnologyClassroom

# Exit on error.
set -e

RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${RED}Adding arm user${NC}"
groupadd arm
useradd -m arm -g arm -G cdrom
# If a password was specified use that, otherwise prompt
if [ -n "$1" ]; then
    echo "$1" | passwd --stdin arm
else
    passwd arm
fi

echo -e "${RED}Installing git${NC}"
apt update
apt install git

echo -e "${RED}Installing required build tools${NC}"
apt install build-essential pkg-config libc6-dev libssl-dev libexpat1-dev libavcodec-dev libgl1-mesa-dev qtbase5-dev zlib1g-dev

echo -e "${RED}Installing wget${NC}"
apt install wget

echo -e "${RED}Installing curl${NC}"
apt install curl

echo -e "${RED}Setting up directories and getting makeMKV files${NC}"
mkdir -p /makeMKV
cd /makeMKV

echo -e "${RED}Finding current MakeMKV version${NC}"
mmv=$(curl -s https://www.makemkv.com/download/ | grep -o [0-9.]*.txt | sed 's/.txt//')

echo -e "${RED}Downloading MakeMKV sha, bin, and oss${NC}"
wget https://www.makemkv.com/download/makemkv-sha-$mmv.txt
wget https://www.makemkv.com/download/makemkv-bin-$mmv.tar.gz
wget https://www.makemkv.com/download/makemkv-oss-$mmv.tar.gz

echo -e "${RED}Checking checksums${NC}"
grep "makemkv-bin-$mmv.tar.gz" makemkv-sha-$mmv.txt | sha256sum -c
# grep "makemkv-oss-$mmv.tar.gz" makemkv-sha-$mmv.txt | sha256sum -c  # DEBUG
# Their makemkv-oss-1.16.3.tar.gz checksum did not match???
# Remove these comments and enable the grep line above when it does match.

echo -e "${RED}Extracting MakeMKV${NC}"
tar xvzf makemkv-oss-$mmv.tar.gz
tar xvzf makemkv-bin-$mmv.tar.gz

cd makemkv-oss-$mmv
echo -e "${RED}Installing MakeMKV${NC}"
./configure
make
make install

cd ../makemkv-bin-$mmv
make
make install

echo -e "${RED}Installing ffmpeg${NC}"
apt install ffmpeg

echo -e "${RED}Installing ARM requirments${NC}"
apt install handbrake-cli libavcodec-extra
apt install libdvdcss2
apt install abcde flac imagemagick glyrc cdparanoia
apt install at
apt install python3 python3-pip
apt install libcurl4-openssl-dev libssl-dev
apt install libdvd-pkg
apt install  lsdvd
wget http://download.videolan.org/pub/debian/stable/libdvdcss2_1.2.13-0_amd64.deb
wget http://download.videolan.org/pub/debian/stable/libdvdcss_1.2.13-0.debian.tar.gz
wget http://ftp.us.debian.org/debian/pool/contrib/libd/libdvd-pkg/libdvd-pkg_1.4.0-1-2_all.deb
sudo dpkg -i libdvdcss2_1.2.13-0_amd64.deb
sudo dpkg -i libdvd-pkg_1.4.0-1-2_all.deb
apt -f install
dpkg-reconfigure libdvd-pkg
apt install default-jre-headless
apt install eject

echo -e "${RED}Installing ARM:Automatic Ripping Machine${NC}"
cd /opt
mkdir -p arm
chown arm:arm arm
chmod 775 arm
##my updated version
git clone https://github.com/1337-server/automatic-ripping-machine.git arm
###stock
#git clone https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm
chown -R arm:arm arm
cd arm
pip3 install -U setuptools
apt install python3-dev python3-pip python3-venv python3-wheel
pip3 install -U wheel
pip3 install -r requirements.txt
ln -s /opt/arm/setup/51-automedia.rules /lib/udev/rules.d/
ln -s /opt/arm/setup/.abcde.conf /home/arm/
cp docs/arm.yaml.sample arm.yaml
sudo chown arm:arm arm.yaml
mkdir -p /etc/arm/
ln -s /opt/arm/arm.yaml /etc/arm/
sudo chmod +x /opt/arm/scripts/arm_wrapper.sh
sudo chmod +x /opt/arm/scripts/update_key.sh

######## Adding new line to fstab, needed for the autoplay to work.
######## also creating mount points (why loop twice)
echo -e "${RED}Adding fstab entry and creating mount points${NC}"
for dev in /dev/sr?; do
   echo -e "\n${dev}  /mnt${dev}  udf,iso9660  users,noauto,exec,utf8  0  0 \n" >> /etc/fstab
   mkdir -p /mnt$dev
done

##### Add sysctl.d rule to prevent auto-unejecting cd tray
cat > /etc/sysctl.d/arm-uneject-fix.conf <<-EOM
# Fix issue with DVD tray being autoclosed after rip is complete

dev.cdrom.autoclose=0
EOM

##### Add syslog rule to route all ARM system logs to /var/log/arm.log
cat > /etc/rsyslog.d/arm.conf <<-EOM
:programname, isequal, "ARM" /var/log/arm.log
EOM

##### Run the ARM UI as a service.
echo -e "${RED}Installing ARM service${NC}"
cat > /etc/systemd/system/armui.service <<- EOM
[Unit]
Description=Arm service
## Added to force armui to wait for network.
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=arm
Group=arm
## Add your path to your logfiles if you want to enable logging.
## Remember to remove the # at the start of the line.
#StandardOutput=append:/PATH-TO-MY-LOGFILES/WebUI.log
#StandardError=append:/PATH-TO-MY-LOGFILES/WebUI.log
Restart=always
RestartSec=3
ExecStart=python3 /opt/arm/arm/runui.py

[Install]
WantedBy=multi-user.target
EOM

# Reload the daemon, sysctl, and then start UI.
systemctl enable armui
systemctl start armui
systemctl daemon-reload
sysctl -p

#advise to reboot
echo
echo -e "${RED}We recommend rebooting your system at this time.${NC}"
echo
