#!/bin/bash
sudo apt upgrade -y && sudo apt update -yqq 
#***optional (was not required for me): sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt install avahi-daemon -y && sudo systemctl restart avahi-daemon
sudo apt install ubuntu-drivers-common -yqq && sudo ubuntu-drivers install 
#sudo reboot
# Installation of drivers seems to install a full gnome desktop, and it seems to set up hibernation modes.
# It is optional to run the below line (Hibernation may be something you want.)
#sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
sudo groupadd arm
sudo useradd -m arm -g arm -G cdrom
sudo useradd -G arm video
sudo passwd arm 

sudo apt-get install git -yqq
sudo add-apt-repository ppa:heyarje/makemkv-beta
sudo add-apt-repository ppa:stebbins/handbrake-releases

NumOnly=$(cut -f2 <<< `lsb_release -r`) && case $NumOnly in "16.04" ) sudo add-apt-repository ppa:mc3man/xerus-media;; "18.04" ) sudo add-apt-repository ppa:mc3man/bionic-prop;; "20.04" ) sudo add-apt-repository ppa:mc3man/focal6;; *) echo "error in finding release version";; esac

sudo apt update -yqq && \
sudo apt install makemkv-bin makemkv-oss -yqq && \
sudo apt install handbrake-cli libavcodec-extra -yqq && \
sudo apt install abcde flac imagemagick glyrc cdparanoia -yqq && \
sudo apt install at -yqq && \
sudo apt install python3 python3-pip -yqq && \
sudo apt-get install libcurl4-openssl-dev libssl-dev -yqq && \
sudo apt-get install libdvd-pkg -yqq && \
sudo dpkg-reconfigure libdvd-pkg && \
sudo apt install default-jre-headless -yqq

cd /opt
sudo mkdir arm
sudo chown arm:arm arm
sudo chmod 775 arm
sudo git clone https://github.com/1337-server/automatic-ripping-machine.git arm
sudo chown -R arm:arm arm
cd arm
sudo pip3 install -r requirements.txt 
sudo cp /opt/arm/setup/51-automedia.rules /etc/udev/rules.d/
sudo ln -s /opt/arm/setup/.abcde.conf /home/arm/
sudo cp docs/arm.yaml.sample arm.yaml
sudo mkdir /etc/arm/
sudo ln -s /opt/arm/arm.yaml /etc/arm/
sudo chmod +x /opt/arm/scripts/arm_wrapper.sh

sudo mkdir -p /mnt/dev/sr0

######## adding new line to fstab, needed for the autoplay to work
echo -e "${RED}Adding fstab entry${NC}"
sudo echo -e "\n/dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8  0  0 \n" >> /etc/fstab

#####run the ARM ui as a service
echo -e "${RED}Installing ARM service${NC}"
sudo cat > /etc/systemd/system/armui.service <<- EOM
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

sudo chmod u+x /etc/systemd/system/armui.service
sudo chmod 700 /etc/systemd/system/armui.service
#reload the daemon and then start ui
sudo sudo systemctl start armui.service 
sudo systemctl enable armui.service

