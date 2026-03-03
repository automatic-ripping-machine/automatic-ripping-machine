#!/usr/bin/env bash
set -eo pipefail

RED='\033[1;31m'
NC='\033[0m' # No Color
FORK=uprightbass360
TAG=latest
function usage() {
    echo -e "\nUsage: docker_setup.sh [OPTIONS]"
    echo -e " -f <fork>\tSpecify the fork to pull from on DockerHub. \n\t\tDefault is \"$FORK\""
    echo -e " -t <tag>\tSpecify the tag to pull from on DockerHub. \n\t\tDefault is \"$TAG\""
    return 0
}

while getopts 'f:t:' OPTION
do
    case $OPTION in
    f)    FORK=$OPTARG
          ;;
    t)    TAG=$OPTARG
          ;;
    *)    usage
          exit 2
          ;;
    esac
done
IMAGE="$FORK/automatic-ripping-machine:$TAG"

function install_reqs() {
    apt update -y && apt upgrade -y
    apt install -y curl lsscsi
    return 0
}

function add_arm_user() {
    echo -e "${RED}Adding arm user${NC}"
    # create arm group if it doesn't already exist
    if ! [[ "$(getent group arm)" ]]; then
        groupadd arm
    else
        echo -e "${RED}arm group already exists, skipping...${NC}"
    fi

    # create arm user if it doesn't already exist
    if ! id arm >/dev/null 2>&1; then
        useradd -m arm -g arm
        passwd arm
    else
        echo -e "${RED}arm user already exists, skipping...${NC}"
    fi
    usermod -aG cdrom,video arm
    return 0
}

function launch_setup() {
    # install docker
    if [[ -e /usr/bin/docker ]]; then
        echo -e "${RED}Docker installation detected, skipping...${NC}"
        echo -e "${RED}Adding user arm to docker user group${NC}"
        usermod -aG docker arm
    else
        echo -e "${RED}Installing Docker${NC}"
        # the convenience script auto-detects OS and handles install accordingly
        curl -sSL https://get.docker.com | bash
        echo -e "${RED}Adding user arm to docker user group${NC}"
        usermod -aG docker arm
    fi
    return 0
}

function pull_image() {
    echo -e "${RED}Pulling image from $IMAGE${NC}"
    sudo -u arm docker pull "$IMAGE"
    return 0
}

function setup_mountpoints() {
    echo -e "${RED}Creating mount points${NC}"
    for dev in /dev/sr?; do
        mkdir -p "/mnt$dev"
    done
    chown arm:arm /mnt/dev/sr*
    return 0
}

function save_start_command() {
    echo -e "${RED}Use docker-compose for deployment. See: https://github.com/uprightbass360/automatic-ripping-machine-neu#quick-start${NC}"
    return 0
}


# start here
install_reqs
add_arm_user
launch_setup
pull_image
setup_mountpoints
save_start_command

echo -e "${RED}Installation complete. A template command to run the ARM container is located in: $(echo ~arm) ${NC}"
