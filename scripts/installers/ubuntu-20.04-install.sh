#!/bin/bash

RED='\033[1;31m'
NC='\033[0m' # No Color

dev_env_flag=
while getopts 'd' OPTION
do
    case $OPTION in
    d)    dev_env_flag=1
          ;;
    ?)    echo "Usage: ubuntu-20.04-install.sh [ -d ]"
          return 2
          ;;
    esac
done

function install_os_tools() {
    sudo apt update -y && sudo apt upgrade -y
    sudo apt install alsa -y # this will install sound drivers on ubuntu server, preventing a crash
    sudo apt install lsscsi net-tools -y
    sudo apt install avahi-daemon -y && sudo systemctl restart avahi-daemon
    sudo apt install ubuntu-drivers-common -y && sudo ubuntu-drivers install
    sudo apt install git -y
}

function add_arm_user() {
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
}

function install_arm_requirements() {
    echo -e "${RED}Installing ARM requirments${NC}"
    sudo add-apt-repository ppa:mc3man/focal6 -y
    sudo add-apt-repository ppa:heyarje/makemkv-beta -y
    sudo add-apt-repository ppa:stebbins/handbrake-releases -y
    sudo apt update -y

    sudo apt install -y \
        build-essential \
        libcurl4-openssl-dev libssl-dev \
        libudev-dev \
        udev \
        python3 \
        python3-dev \
        python3-pip \
        python3-wheel \
        python-psutil \
        python3-pyudev \
        abcde \
        eyed3 \
        atomicparsley \
        cdparanoia \
        eject \
        ffmpeg \
        flac \
        glyrc \
        default-jre-headless \
        libavcodec-extra

    sudo apt install -y \
        handbrake-cli makemkv-bin makemkv-oss \
        imagemagick \
        at \
        libdvd-pkg lsdvd

    sudo dpkg-reconfigure libdvd-pkg
}

function remove_existing_arm() {
    ##### Check if the ArmUI service exists in any state and remove it
    if sudo systemctl list-unit-files --type service | grep -F armui.service; then
        echo -e "${RED}Previous installation of ARM service found. Removing...${NC}"
        service=armui.service
        sudo systemctl stop $service && sudo systemctl disable $service
        sudo find /etc/systemd/system/$service -delete
        sudo systemctl daemon-reload && sudo systemctl reset-failed
    fi
}

function clone_arm() {
    cd /opt
    if [ -d arm ]; then
        echo -e "${RED}Existing ARM installation found, removing...${NC}"
        sudo rm -rf arm
    fi

    git clone --recurse-submodules https://github.com/shitwolfymakes/automatic-ripping-machine.git arm
    
    cd arm
    git submodule update --init --recursive
    git submodule update --recursive --remote
    cd ..
    
    sudo chown -R arm:arm /opt/arm
    sudo find /opt/arm/scripts/ -type f -iname "*.sh" -exec chmod +x {} \;
}

function install_arm_dev_env() {
    ##### Install ARM development stack
    echo -e "${RED}Installing ARM for Development${NC}"
    clone_arm

    # install docker
    sudo apt install apt-transport-https ca-certificates curl software-properties-common -y
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable" -y
    apt-cache policy docker-ce
    sudo apt update -y
    sudo apt install docker-ce docker-ce-cli containerd.io -y
    sudo usermod -aG docker arm

    # install pycharm
    sudo snap install pycharm-community --classic
}

function install_arm_live_env() {
    ##### Install ARM live environment
    echo -e "${RED}Installing Automatic Ripping Machine${NC}"
    clone_arm

    sudo cp /opt/arm/setup/51-automedia.rules /etc/udev/rules.d/
    sudo udevadm control --reload
}

function setup_config_files() {
    ##### Setup ARM config files if not found
    sudo mkdir -p /etc/arm/config
    CONFS="arm.yaml apprise.yaml .abcde.conf"
    for conf in $CONFS; do
        thisConf="/etc/arm/config/${conf}"
        if [[ ! -f "${thisConf}" ]] ; then
            echo "creating config file ${thisConf}"
            # Don't overwrite with defaults during reinstall
            cp --no-clobber "/opt/arm/setup/${conf}" "${thisConf}"
        fi
    done
    chown -R arm:arm /etc/arm/
}

function setup_autoplay() {
    ##### Add new line to fstab, needed for the autoplay to work.
    echo -e "${RED}Adding fstab entry and creating mount points${NC}"
    for dev in /dev/sr?; do
        if grep -q "${dev}  /mnt${dev}  udf,iso9660  users,noauto,exec,utf8  0  0" /etc/fstab; then
            echo -e "${RED}fstab entry for ${dev} already exists. Skipping...${NC}"
        else
            echo -e "\n${dev}  /mnt${dev}  udf,iso9660  users,noauto,exec,utf8  0  0 \n" | sudo tee -a /etc/fstab
        fi
        sudo mkdir -p /mnt$dev
        sudo chown arm:arm /mnt$dev
    done
}

function setup_syslog_rule() {
    ##### Add syslog rule to route all ARM system logs to /var/log/arm.log
    if [ -f /etc/rsyslog.d/30-arm.conf ]; then
        echo -e "${RED}ARM syslog rule found. Overwriting...${NC}"
        sudo rm /etc/rsyslog.d/30-arm.conf
    fi
    sudo cp ./setup/30-arm.conf /etc/rsyslog.d/30-arm.conf
    sudo chown arm:arm /etc/rsyslog.d/30-arm.conf
}

function install_armui_service() {
    ##### Install the ArmUI service
    echo -e "${RED}Installing ARM service${NC}"
    sudo mkdir -p /etc/systemd/system
    sudo cp /opt/arm/setup/armui.service /etc/systemd/system/armui.service
    sudo chmod 644 /etc/systemd/system/armui.service

    # reload the daemon and then start service
    sudo systemctl daemon-reload
    sudo systemctl start armui.service
    sudo systemctl enable armui.service
    sudo sysctl -p
}

function launch_setup() {
    echo -e "${RED}Launching ArmUI first-time setup${NC}"
    site_addr=`sudo netstat -tlpn | awk '{ print $4 }' | grep .*:8080`
    if [ -z $site_addr ]; then
        echo -e "${RED}ERROR: ArmUI site is not running. Run \"sudo systemctl status armui\" to find out why${NC}"
    else
        echo -e "${RED}ArmUI site is running on http://$site_addr. Launching setup...${NC}"
        sudo -u arm nohup xdg-open http://$site_addr/setup > /dev/null 2>&1 &
    fi
}

# start here
install_os_tools
add_arm_user
install_arm_requirements
remove_existing_arm

if [ "$dev_env_flag" ]; then
    install_arm_dev_env
else
    install_arm_live_env
fi

setup_config_files
setup_autoplay
setup_syslog_rule
install_armui_service
launch_setup

#advise to reboot
echo
echo -e "${RED}We recommend rebooting your system at this time.${NC}"
echo
