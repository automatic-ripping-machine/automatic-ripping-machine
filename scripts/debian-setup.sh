#!/bin/bash

groupadd arm
useradd -m arm -g arm -G cdrom
passwd arm 
  <enter new password>

sudo apt-get install git

sudo apt-get install build-essential pkg-config libc6-dev libssl-dev libexpat1-dev libavcodec-dev libgl1-mesa-dev qtbase5-dev zlib1g-dev

sudo apt-get install wget

mkdir /makeMKV

cd /makeMKV

wget https://www.makemkv.com/download/makemkv-bin-1.15.3.tar.gz
wget https://www.makemkv.com/download/makemkv-oss-1.15.3.tar.gz

tar xvzf makemkv-oss-1.15.3.tar.gz
tar xvzf makemkv-bin-1.15.3.tar.gz

cd makemkv-oss-1.15.3
./configure
make
make install

cd ../makemkv-bin-1.15.3
make
make install

#cd ../..
#mkdir ffmpeg
#cd ffmpeg

apt-get install ffmpeg

apt install handbrake-cli libavcodec-extra
apt install libdvdcss2
apt install abcde flac imagemagick glyrc cdparanoia
apt install at
apt install python3 python3-pip
apt-get install libcurl4-openssl-dev libssl-dev  
apt-get install libdvd-pkg
### wget http://download.videolan.org/pub/debian/stable/libdvdcss2_1.2.13-0_amd64.deb
### wget http://download.videolan.org/pub/debian/stable/libdvdcss_1.2.13-0.debian.tar.gz
## wget http://ftp.us.debian.org/debian/pool/contrib/libd/libdvd-pkg/libdvd-pkg_1.4.0-1-2_all.deb
sudo dpkg -i libdvdcss2_1.2.13-0_amd64.deb
sudo dpkg -i libdvd-pkg_1.4.0-1-2_all.deb
apt --fix-broken install
dpkg-reconfigure libdvd-pkg
apt install default-jre-headless
apt install eject

cd /opt
mkdir arm
chown arm:arm arm
chmod 775 arm
##my updated version
git clone https://github.com/1337-server/automatic-ripping-machine.git arm
###stock
git clone https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm
chown -R arm:arm arm
cd arm
# TODO: Remove below line before merging to master
git checkout v2.1_dev
pip3 install setuptools
sudo apt-get install python3-dev python3-pip python3-venv python3-wheel -y
pip3 install wheel
pip3 install -r requirements.txt 
ln -s /opt/arm/setup/51-automedia.rules /lib/udev/rules.d/
ln -s /opt/arm/setup/.abcde.conf /home/arm/
cp docs/arm.yaml.sample arm.yaml
mkdir /etc/arm/
ln -s /opt/arm/arm.yaml /etc/arm/

mkdir -p /mnt/dev/sr0

nano /etc/fstab
########
/dev/sr0  /mnt/dev/sr0  udf,iso9660  user,noauto,exec,utf8  0  0

#####run the ui , set as cron or service
 python3 /opt/arm/arm/runui.py
