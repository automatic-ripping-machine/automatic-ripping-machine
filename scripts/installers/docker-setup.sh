#!/usr/bin/env bash
set -eo pipefail

GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m' # No Color
FORK=automaticrippingmachine
TAG=latest

if [[ -f /etc/os-release ]]; then
# shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="$ID"
fi

function usage() {
    echo -e "\nUsage: docker_setup.sh [OPTIONS]"
    echo -e " -f <fork>\tSpecify the fork to pull from on DockerHub. \n\t\tDefault is \"$FORK\""
    echo -e " -t <tag>\tSpecify the tag to pull from on DockerHub. \n\t\tDefault is \"$TAG\""
}

while getopts 'f:t:' OPTION
do
    case $OPTION in
    f)    FORK=$OPTARG
          ;;
    t)    TAG=$OPTARG
          ;;
    ?)    usage
          exit 2
          ;;
    esac
done
IMAGE="$FORK/automatic-ripping-machine:$TAG"

function install_reqs() {
    case "$OS_ID" in
        debian|ubuntu)
            apt update -y && apt upgrade -y
            apt install -y curl lsscsi
            ;;
        arch|cachyos|manjaro)
            pacman -Syu --noconfirm curl lsscsi
            ;;
        fedora)
            dnf install -y curl lsscsi
            ;;
        rhel|centos|rocky|almalinux)
            yum install -y curl lsscsi
            ;;
        alpine)
            apk add --no-cache curl lsscsi
            ;;
        *)
            echo "${RED}Unsupported Linux distro: $ID"
            exit 2
            ;;
    esac
}

function add_arm_user() {
    echo -e "${GREEN}Adding arm user${NC}"
    # create arm group if it doesn't already exist
    if ! [[ "$(getent group arm)" ]]; then
        groupadd arm
    else
        echo -e "${GREEN}arm group already exists, skipping...${NC}"
    fi

    # create arm user if it doesn't already exist
    if ! id arm >/dev/null 2>&1; then
        useradd -m arm -g arm
        passwd arm
    else
        echo -e "${GREEN}arm user already exists, skipping...${NC}"
    fi
    
    getent group cdrom >/dev/null || groupadd cdrom
    getent group video >/dev/null || groupadd video
    usermod -aG cdrom,video arm && echo -e "${GREEN}Adds user arm to cdrom, video group${NC}"
}

function launch_setup() {
    # install docker
    if [ -e /usr/bin/docker ]; then
        echo -e "${GREEN}Docker installation detected, skipping...${NC}"
        usermod -aG docker arm && echo -e "${GREEN}Adds user arm to docker user group${NC}"
    else
        echo -e "${GREEN}Installing Docker${NC}"
        # the convenience script auto-detects OS and handles install accordingly
        case "$OS_ID" in
            debian|ubuntu|fedora|rhel|centos|rocky|almalinux)
                curl -sSL https://get.docker.com | bash
                usermod -aG docker arm && echo -e "${GREEN}Adds user arm to docker user group${NC}"
                ;;
            arch|cachyos|manjaro)
                pacman -S docker iptables-nft
                systemctl enable --now docker.service
                systemctl start docker.service
                ;;
            alpine)
                apk add docker
                rc-update add docker default
                /etc/init.d/docker start
                ;;
            *)
                echo -e "${RED} Error when attempting to install Docker."
                exit 2
                ;;
        esac
    fi
}

function pull_image() {
    echo -e "${GREEN}Pulling image from $IMAGE${NC}"
    sudo -u arm docker pull "$IMAGE" || { echo -e "${RED} Download of docker images failed ${NC}\n"; exit 2; } 
}

function setup_mountpoints() {
    echo -e "${GREEN}Creating mount points${NC}"
    for dev in /dev/sr?; do
        mkdir -p "/mnt$dev"
    done
    chown arm:arm /mnt/dev/sr*
}

function save_start_command() {
    url="https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/scripts/docker/start_arm_container.sh"
    cd ~arm
    if [ -e start_arm_container.sh ]
    then
        echo -e "'start_arm_container.sh' already exists. Backing up..."
        sudo mv ./start_arm_container.sh ./start_arm_container.sh.bak
    fi
    sudo -u arm curl -fsSL "$url" -o start_arm_container.sh
    chmod +x start_arm_container.sh
    sed -i "s|IMAGE_NAME|${IMAGE}|" start_arm_container.sh
}


# start here
install_reqs
add_arm_user
launch_setup
pull_image
setup_mountpoints
save_start_command

ARM_HOME=$(eval echo ~arm)
echo -e "${GREEN}Installation complete. A template command to run the ARM container is located in: $ARM_HOME ${NC}"
