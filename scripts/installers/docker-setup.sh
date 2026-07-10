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
else
    echo "${RED}Cannot determine operating system.${NC}"
    exit 1
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
        debian|ubuntu|linuxmint)
            apt update
            apt install -y curl lsscsi
            ;;
        arch|cachyos|manjaro)
            pacman -Syu --noconfirm curl lsscsi
            ;;
        fedora|rocky|almalinux)
            dnf install -y curl lsscsi
            ;;
        centos|rhel)
            if command -v dnf >/dev/null 2>&1; then
                dnf install -y curl lsscsi
            else
                yum install -y curl lsscsi
            fi
            ;;
        *)
            echo "${RED}Unsupported Linux distro: $OS_ID ${NC}"
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
        usermod -aG arm arm
        passwd arm
    else
        echo -e "${GREEN}arm user already exists, skipping...${NC}"
    fi
    
    getent group cdrom >/dev/null || groupadd cdrom
    getent group video >/dev/null || groupadd video
    usermod -aG cdrom,video arm && echo -e "${GREEN}Added user 'arm' to 'cdrom' and 'video' group${NC}"
}

function launch_setup() {
    # install docker
    if [ -e /usr/bin/docker ]; then
        echo -e "${GREEN}Docker installation detected, skipping...${NC}"
        usermod -aG docker arm && echo -e "${GREEN}Added user 'arm' to 'docker' user group${NC}"
    else
        echo -e "${GREEN}Installing Docker${NC}"
        # the convenience script auto-detects OS and handles install accordingly
        case "$OS_ID" in
            debian|ubuntu|linuxmint|fedora|rhel|centos|rocky|almalinux)
                curl -sSL https://get.docker.com | bash
                usermod -aG docker arm && echo -e "${GREEN}Added user 'arm' to 'docker' user group${NC}"
                ;;
            arch|cachyos|manjaro)
                pacman -S docker iptables-nft
                systemctl enable --now docker.service
                systemctl start docker.service
                ;;
            *)
                echo -e "${RED} Error when attempting to install Docker.${NC}"
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

ARM_HOME=~arm
echo -e "${GREEN}Installation complete. A template command to run the ARM container is located in: $ARM_HOME ${NC}"
