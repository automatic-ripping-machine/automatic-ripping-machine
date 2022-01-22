#!/bin/bash

# Exit on error.
#set -e

RED='\033[1;31m'
NC='\033[0m' # No Color

sudo apt install alsa -y # this will install sound drivers on ubuntu server, preventing a crash
sudo apt upgrade -y && sudo apt update -y 
#***optional (was not required for me): sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt install lsscsi && sudo apt install net-tools
sudo apt install avahi-daemon -y && sudo systemctl restart avahi-daemon
sudo apt install ubuntu-drivers-common -y && sudo ubuntu-drivers install

#sudo reboot
# Installation of drivers seems to install a full gnome desktop, and it seems to set up hibernation modes.
# It is optional to run the below line (Hibernation may be something you want.)
#sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

echo -e "${RED}Adding arm user${NC}"
# create arm group if it doesn't already exist
if ! [ $(getent group arm) ]; then
  sudo groupadd arm
else
  echo -e "${RED}arm group already exists, skipping...${NC}"
fi

# create arm user if it doesn't already exist
if ! id arm >/dev/null 2>&1; then
  sudo useradd -m arm -g arm
  sudo passwd arm
else
  echo -e "${RED}arm user already exists, skipping creation...${NC}"
fi
sudo usermod -aG cdrom,video arm

echo -e "${RED}Installing git${NC}"
sudo apt-get install git -y
sudo add-apt-repository ppa:heyarje/makemkv-beta

NumOnly=$(cut -f2 <<< `lsb_release -r`) && case $NumOnly in "16.04" ) sudo add-apt-repository ppa:mc3man/xerus-media;; "18.04" ) sudo add-apt-repository ppa:mc3man/bionic-prop;; "20.04" ) sudo add-apt-repository ppa:mc3man/focal6;; *) echo "error in finding release version";; esac

echo -e "${RED}Installing ARM requirments${NC}"
sudo apt update -y
sudo apt install makemkv-bin makemkv-oss -y
sudo apt install handbrake-cli libavcodec-extra -y
sudo apt install abcde flac imagemagick glyrc cdparanoia -y
sudo apt install at -y
sudo apt install python3 python3-pip -y
sudo apt install libcurl4-openssl-dev libssl-dev -y
sudo apt install libdvd-pkg -y
sudo apt install lsdvd -y
sudo dpkg-reconfigure libdvd-pkg
sudo apt install default-jre-headless -y

echo -e "${RED}Installing ARM:Automatic Ripping Machine${NC}"
cd /opt
sudo mkdir -p arm
sudo chown arm:arm arm
sudo chmod 775 arm
##my updated version
#sudo git clone https://github.com/1337-server/automatic-ripping-machine.git arm
sudo git clone https://github.com/shitwolfymakes/automatic-ripping-machine.git arm
sudo git checkout ubuntu_scripts_update
###stock
#git clone https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm
sudo chown -R arm:arm arm
cd arm
sudo pip3 install -r requirements.txt 
sudo cp /opt/arm/setup/51-automedia.rules /etc/udev/rules.d/
sudo ln -sf /opt/arm/setup/.abcde.conf /home/arm/
sudo cp docs/arm.yaml.sample arm.yaml
sudo mkdir -p /etc/arm/
sudo ln -sf /opt/arm/arm.yaml /etc/arm/
sudo chmod +x /opt/arm/scripts/arm_wrapper.sh

######## Adding new line to fstab, needed for the autoplay to work.
######## also creating mount points (why loop twice)
echo -e "${RED}Adding fstab entry and creating mount points${NC}"
for dev in /dev/sr?; do
   echo -e "\n${dev}  /mnt${dev}  udf,iso9660  users,noauto,exec,utf8  0  0 \n" | sudo tee -a /etc/fstab
   sudo mkdir -p /mnt$dev
done

##### Add syslog rule to route all ARM system logs to /var/log/arm.log
cat <<EOM | sudo tee /etc/rsyslog.d/30-arm.conf
:programname, isequal, "ARM" /var/log/arm.log
EOM

##### Run the ARM UI as a service
echo -e "${RED}Installing ARM service${NC}"
cat <<EOM | sudo tee /etc/systemd/system/armui.service
[Unit]
Description=Arm service
## Added to force armui to wait for network
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=arm
Group=arm
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

sudo systemctl daemon-reload
sudo chmod u+x /etc/systemd/system/armui.service
sudo chmod 700 /etc/systemd/system/armui.service

#reload the daemon and then start ui
sudo systemctl start armui.service 
sudo systemctl enable armui.service
sudo sysctl -p

#advise to reboot
echo
echo -e "${RED}We recommend rebooting your system at this time.${NC}"
echo
