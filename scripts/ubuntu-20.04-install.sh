#!/bin/bash

set -eo pipefail

RED='\033[1;31m'
NC='\033[0m' # No Color
PORT=8080

function usage() {
    echo -e "\nUsage: ubuntu-20.04-install.sh [OPTIONS]"
    echo -e " -p <port>\tSpecify the port arm will serve on. \n\t\tDefault is \"$PORT\""
}

port_flag=
while getopts 'p:' OPTION
do
    case $OPTION in
    p)    port_flag=1
          PORT=$OPTARG
          # test if port is valid (DOES NOT WORK WITH `set -u` DECLARED)
          if ! [[ $PORT -gt 0 && $PORT -le 65535 ]]; then
              echo -e "\nERROR: ${PORT} is not a port"
              usage
              exit 2
          fi
          ;;
    ?)    usage
          exit 1
          ;;
    esac
done

function install_os_tools() {
    sudo apt update -y && sudo apt upgrade -y
    sudo apt install alsa -y # this will install sound drivers on ubuntu server, preventing a crash
    sudo apt install lsscsi net-tools -y
    sudo apt install avahi-daemon -y && sudo systemctl restart avahi-daemon
    sudo apt install ubuntu-drivers-common -y && sudo ubuntu-drivers install
    sudo apt install git curl shellcheck -y
}

function add_arm_user() {
    echo -e "${RED}Adding arm user${NC}"
    # create arm group if it doesn't already exist
    if ! [[ "$(getent group arm)" ]]; then
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
        python3-testresources \
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
    
    # create folders required to run the ARM service
    sudo -u arm mkdir -p /home/arm/logs
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

    git clone --recurse-submodules https://github.com/automatic-ripping-machine/automatic-ripping-machine --branch "main" arm

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
    if [ -e /usr/bin/docker ]; then
        echo -e "${RED}Docker installation detected, skipping...${NC}"
    else
        echo -e "${RED}Installing Docker${NC}"
        # the convenience script auto-detects OS and handles install accordingly
        curl -sSL https://get.docker.com | bash
        sudo usermod -aG docker arm
    fi

    # install pycharm community, if professional not installed already
    # shellcheck disable=SC2230
    if [[ -z $(which pycharm-professional) ]]; then
        sudo snap install pycharm-community --classic
    fi
}

function setup_config_files() {
    ##### Setup ARM-specific config files if not found
    sudo mkdir -p /etc/arm/config
    CONFS="arm.yaml apprise.yaml"
    for conf in $CONFS; do
        thisConf="/etc/arm/config/${conf}"
        if [[ ! -f "${thisConf}" ]] ; then
            echo "creating config file ${thisConf}"
            # Don't overwrite with defaults during reinstall
            cp --no-clobber "/opt/arm/setup/${conf}" "${thisConf}"
        fi
    done
    chown -R arm:arm /etc/arm/

    # abcde.conf is expected in /etc by the abcde installation
    cp --no-clobber "/opt/arm/setup/.abcde.conf" "/etc/.abcde.conf"
    chown arm:arm "/etc/.abcde.conf"
    # link to the new install location so runui.py doesn't break
    sudo -u arm ln -sf /etc/.abcde.conf /etc/arm/config/abcde.conf 

    if [[ $port_flag ]]; then
        echo -e "${RED}Non-default port specified, updating arm config...${NC}"
        # replace the default 8080 port with the specified port
        sed -E s"/(^WEBSERVER_PORT:) 8080/\1 ${PORT}/" -i /etc/arm/config/arm.yaml
    else
        # reset the port number in the config since it's no longer being
        # overwritten which each run of this installer
        sed -E s"/(^WEBSERVER_PORT:) [0-9]+/\1 8080/" -i /etc/arm/config/arm.yaml
    fi
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
        sudo mkdir -p "/mnt$dev"
        sudo chown arm:arm "/mnt$dev"
    done
}

function setup_syslog_rule() {
    ##### Add syslog rule to route all ARM system logs to /var/log/arm.log
    if [ -f /etc/rsyslog.d/30-arm.conf ]; then
        echo -e "${RED}ARM syslog rule found. Overwriting...${NC}"
        sudo rm /etc/rsyslog.d/30-arm.conf
    fi
    sudo cp /opt/arm/setup/30-arm.conf /etc/rsyslog.d/30-arm.conf
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
    echo "Giving ArmUI a moment to start, standby..."
    sleep 30
    site_addr=$(sudo netstat -tlpn | awk '{ print $4 }' | grep ".*:${PORT}") || true
    if [[ -z "$site_addr" ]]; then
        echo -e "${RED}ERROR: ArmUI site is not running. Run \"sudo systemctl status armui\" to find out why${NC}"
    else
        echo -e "${RED}ArmUI site is running on http://$site_addr. Launching setup...${NC}"
        sudo -u arm nohup xdg-open "http://$site_addr/setup" > /dev/null 2>&1 &
    fi
}

function create_folders() {
    echo -e "${RED}Creating ARM folders${NC}"
    arm_mkdir "/home/arm/media/transcode"
    arm_mkdir "/home/arm/media/completed"
    arm_mkdir "/home/arm/media/raw"
    arm_mkdir "/home/arm/logs/progress"
}

function arm_mkdir() {
    echo -e "Creating $1"
    su - arm -c "mkdir -p -v $1"
}

# start here
install_os_tools
add_arm_user
install_arm_requirements
remove_existing_arm

install_arm_dev_env

setup_config_files
setup_autoplay
setup_syslog_rule
install_armui_service
create_folders
launch_setup

#advise to reboot
echo
echo -e "${RED}We recommend rebooting your system at this time.${NC}"
echo
