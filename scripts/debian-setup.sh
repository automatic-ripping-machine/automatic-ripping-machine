#!/bin/bash
RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${RED}Adding arm user${NC}"
groupadd arm
useradd -m arm -g arm -G cdrom
passwd arm
echo -e "${RED}Installing git${NC}"
apt-get install git
echo -e "${RED}Installing required build tools${NC}"
apt-get install build-essential pkg-config libc6-dev libssl-dev libexpat1-dev libavcodec-dev libgl1-mesa-dev qtbase5-dev zlib1g-dev
echo -e "${RED}Installing wget${NC}"
apt-get install wget

echo -e "${RED}Setting up directories and getting makeMKV files${NC}"
mkdir /makeMKV
cd /makeMKV

wget https://www.makemkv.com/download/makemkv-bin-1.15.4.tar.gz
wget https://www.makemkv.com/download/makemkv-oss-1.15.4.tar.gz

echo -e "${RED}Extracting MakeMKV${NC}"
tar xvzf makemkv-oss-1.15.4.tar.gz
tar xvzf makemkv-bin-1.15.4.tar.gz

cd makemkv-oss-1.15.4
echo -e "${RED}Installing MakeMKV${NC}"
./configure
make
make install

cd ../makemkv-bin-1.15.4
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
wget http://download.videolan.org/pub/debian/stable/libdvdcss2_1.2.13-0_amd64.deb
wget http://download.videolan.org/pub/debian/stable/libdvdcss_1.2.13-0.debian.tar.gz
wget http://ftp.us.debian.org/debian/pool/contrib/libd/libdvd-pkg/libdvd-pkg_1.4.0-1-2_all.deb
sudo dpkg -i libdvdcss2_1.2.13-0_amd64.deb
sudo dpkg -i libdvd-pkg_1.4.0-1-2_all.deb
apt --fix-broken install
dpkg-reconfigure libdvd-pkg
apt install default-jre-headless
apt install eject

echo -e "${RED}Installing ARM:Automatic Ripping Machine${NC}"
cd /opt
mkdir arm
chown arm:arm arm
chmod 775 arm
git clone https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm
chown -R arm:arm arm
cd arm
pip3 install setuptools
apt-get install python3-dev python3-pip python3-venv python3-wheel -y
pip3 install wheel
pip3 install -r requirements.txt 
ln -s /opt/arm/setup/51-automedia.rules /lib/udev/rules.d/
ln -s /opt/arm/setup/.abcde.conf /home/arm/
cp docs/arm.yaml.sample arm.yaml
mkdir /etc/arm/
ln -s /opt/arm/arm.yaml /etc/arm/

mkdir -p /mnt/dev/sr0

######## adding new line to fstab, needed for the autoplay to work
echo -e "${RED}Adding fstab entry${NC}"
echo -e "\n/dev/sr0  /mnt/dev/sr0  udf,iso9660  user,noauto,exec,utf8  0  0 \n" >> /etc/fstab

#####run the ARM ui as a service
echo -e "${RED}Installing ARM service${NC}"
cat > /etc/systemd/system/armui.service <<- EOM
[Unit]
Description=Arm service
## Added to force armui to wait for network
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
## Add your path to your logfiles if you want to enable logging
## Remember to remove the # at the start of the line
#StandardOutput=append:/PATH-TO-MY-LOGFILES/WebUI.log
#StandardError=append:/PATH-TO-MY-LOGFILES/WebUI.log
Restart=always
RestartSec=3
ExecStart=python3 /opt/arm/arm/runui.py

[Install]
WantedBy=multi-user.target
EOM

#reload the daemon and then start ui
systemctl enable armui
systemctl start armui
systemctl daemon-reload

