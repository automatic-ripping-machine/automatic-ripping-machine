#!/bin/bash -i

export DEBIAN_FRONTEND=noninteractive
set -eo pipefail

function usage() {
    echo -e "\nUsage: Debian-11-install.sh [OPTIONS]"
    echo -e "\t-d\t\tInstall the ARM Development Environment"
    echo -e "\t-p [PORT]\tOverwrite the default WEBSERVER_PORT"
    echo -e "\t-t [password]\tSet the password for arm user - default is 1234"
}

RED='\033[1;31m'
GREEN='\033[1;32m'
NC='\033[0m' # No Color

dev_env_flag=
port_flag=
PORT=8080
pass=1234
while getopts 'dpt:' OPTION
do
    case $OPTION in
    d)    dev_env_flag=1
          ;;
    t)    pass="$OPTARG"
          ;;
    p)    port_flag=1
          PORT=$OPTARG
          # test if port is valid (DOES NOT WORK WITH `set -u` DECLARED)
          if ! [[ $PORT -gt 0 && $PORT -le 65535 ]]; then
              echo -e "\nERROR: ${PORT} is not a port"
              usage
              exit 1
          fi
          ;;
    ?)    usage
          exit 1
          ;;
    esac
done

function add_arm_user() {
    echo -e "${RED}Adding arm user${NC}"
    # create arm group if it doesn't already exist
    if ! [[ $(getent group arm) ]]; then
        groupadd arm
    else
        echo -e "${RED}arm group already exists, skipping...${NC}"
    fi

    # create arm user if it doesn't already exist
    if ! id arm >/dev/null 2>&1; then
        useradd -m arm -g arm
        # If a password was specified use that, otherwise use default
        if [ "$pass" != "1234" ]; then
            echo "Password was supplied, using it."
        else
            echo "Password was not supplied, using 1234"
        fi
        echo -e "$pass\n$pass\n" | passwd arm
    else
        echo -e "${RED}arm user already exists, skipping creation...${NC}"
    fi
    usermod -aG cdrom,video arm
}

function install_arm_build_tools(){
    echo -e "${RED}Installing git and wget${NC}"
    apt update
    apt install -qqy git wget
    echo -e "${RED}Installing required build tools${NC}"
    apt install -qqy build-essential pkg-config libc6-dev libssl-dev libexpat1-dev libavcodec-dev libgl1-mesa-dev qtbase5-dev zlib1g-dev curl
}

function install_arm_requirements() {
    mkdir -p /home/arm
    mkdir -p /etc/arm/config
    install_arm_build_tools
    echo -e "${RED}Installing ARM requirements${NC}"
    apt update -qqy
    apt-get install -qqy \
        build-essential \
        libcurl4-openssl-dev libssl-dev \
        libudev-dev \
        udev \
        python3 \
        python3-dev \
        python3-pip \
        python3-wheel \
        python3-psutil \
        python3-pyudev \
        python3-testresources \
        build-essential \
        libssl-dev \
        libffi-dev \
        python-dev \
        abcde \
        eyed3 \
        atomicparsley \
        cdparanoia \
        eject \
        ffmpeg \
        flac \
        glyrc \
        default-jre-headless \
        libavcodec-extra \
        net-tools

    apt install -qqy \
        imagemagick \
        at \
        libdvd-pkg lsdvd
    dpkg-reconfigure --frontend noninteractive libdvd-pkg
    build_makemkv
    build_handbrakecli
}

function build_handbrakecli(){
    if [ -d "./HandBrake" ] 
    then
        echo "HandBrake build exists. Removing!" 
        rm -R HandBrake
    fi
    sudo apt-get install -yqq appstream autoconf automake autopoint build-essential cmake git libass-dev libbz2-dev libfontconfig1-dev libfreetype6-dev libfribidi-dev libharfbuzz-dev libjansson-dev liblzma-dev libmp3lame-dev libnuma-dev libogg-dev libopus-dev libsamplerate-dev libspeex-dev libtheora-dev libtool libtool-bin libturbojpeg0-dev libvorbis-dev libx264-dev libxml2-dev libvpx-dev m4 make meson nasm ninja-build patch pkg-config python tar zlib1g-dev  libva-dev libdrm-dev
    ## Handbrake -  we use this one for the VCE preset 
    git clone https://github.com/HandBrake/HandBrake.git && cd HandBrake
    # Only uncomment if you need vce_h264
    # wget https://raw.githubusercontent.com/1337-server/HandBrake/master/libhb/handbrake/preset_builtin.h libhb/handbrake/preset_builtin.h 
    ./configure --disable-gtk --enable-qsv --enable-vce --launch-jobs=$(nproc) --launch
    sudo make -j$(nproc) --directory=build install
    cd .. && rm -R HandBrake
    #sudo apt-get -yqq remove appstream autoconf automake autopoint build-essential cmake git libass-dev libbz2-dev libfontconf

}

function build_makemkv(){
    echo -e "${RED}Setting up directories and getting makeMKV files${NC}"
    mkdir -p /makeMKV && cd /makeMKV

    echo -e "${RED}Finding current MakeMKV version${NC}"
    mmv=$(curl -s https://www.makemkv.com/download/ | grep -o [0-9.]*.txt | sed 's/.txt//')
    echo -e "MakeMKV Current Version: ${mmv}"
    echo -e "${RED}Downloading MakeMKV sha, bin, and oss${NC}"
    # As MakeMKV is currently suspended I've included links to the wayback machine
    # echo -e "https://web.archive.org/web/20220418212102/https://www.makemkv.com/download/makemkv-bin-${mmv}.tar.gz"
    # echo -e "https://web.archive.org/web/20220418212102/https://www.makemkv.com/download/makemkv-oss-${mmv}.tar.gz"
    wget -q -nc --show-progress https://www.makemkv.com/download/makemkv-sha-$mmv.txt
    wget -q -nc --show-progress https://www.makemkv.com/download/makemkv-bin-$mmv.tar.gz
    wget -q -nc --show-progress https://www.makemkv.com/download/makemkv-oss-$mmv.tar.gz

    echo -e "${RED}Checking checksums${NC}"
    grep "makemkv-bin-$mmv.tar.gz" makemkv-sha-$mmv.txt | sha256sum -c
    # grep "makemkv-oss-$mmv.tar.gz" makemkv-sha-$mmv.txt | sha256sum -c  # DEBUG
    # Their makemkv-oss-1.16.3.tar.gz checksum did not match???
    # Remove these comments and enable the grep line above when it does match.

    echo -e "${RED}Extracting MakeMKV${NC}"
    tar xzf makemkv-oss-$mmv.tar.gz
    tar xzf makemkv-bin-$mmv.tar.gz

    cd makemkv-oss-$mmv
    mkdir -p ./tmp
    echo -e "${RED}Installing MakeMKV${NC}"
    ./configure 2>&1 >/dev/null
    make -s -j$(nproc)
    make install

    cd ../makemkv-bin-$mmv
    mkdir -p ./tmp
    echo "yes" >> ./tmp/eula_accepted
    make -s -j$(nproc)
    make install
    cd ~
    rm -R /makeMKV
}

function remove_existing_arm() {

    if [ -d "/opt/arm" ]
    then
        echo "ARM install path exists. Removing!"
        rm -R /opt/arm
    fi
    ##### Check if the ArmUI service exists in any state and remove it
    if systemctl list-unit-files --type service | grep -F armui.service; then
        echo -e "${RED}Previous installation of ARM service found. Removing...${NC}"
        service=armui.service
        systemctl stop $service && systemctl disable $service
        find /etc/systemd/system/$service -delete
        systemctl daemon-reload && systemctl reset-failed
    fi
}

function clone_arm() {

    ARM_LATEST=$(curl --silent 'https://github.com/automatic-ripping-machine/automatic-ripping-machine/releases' | grep 'automatic-ripping-machine/tree/*' | head -n 1 | sed -e 's/[^0-9\.]*//g')
    echo -e "Arm latest stable version is v$ARM_LATEST. Pulling v$ARM_LATEST"
    git clone --recurse-submodules https://github.com/automatic-ripping-machine/automatic-ripping-machine --branch "v$ARM_LATEST" arm
    cd arm
    git checkout v2_master
    git submodule update --init --recursive
    git submodule update --recursive --remote
    cd ..
    chown -R arm:arm /opt/arm
    find /opt/arm/scripts/ -type f -iname "*.sh" -exec chmod +x {} \;
}

function create_abcde_symlink() {
    if ! [[ -z $(find /home/arm/ -type l -ls | grep ".abcde.conf") ]]; then
        rm /home/arm/.abcde.conf
    fi
    cp --no-clobber /opt/arm/setup/.abcde.conf /etc/arm/config/abcde.conf

}

function create_arm_config_symlink() {
    if [[ $port_flag ]]; then
        echo -e "${RED}Non-default port specified, updating arm config...${NC}"
        # replace the default 8080 port with the specified port
        sed -e s"/\(^WEBSERVER_PORT:\) 8080/\1 ${PORT}/" -i /etc/arm/config/arm.yaml
    fi
    cp --no-clobber /opt/arm/setup/arm.yaml /etc/arm/config/arm.yaml
}

function install_arm_live_env() {
    echo -e "${GREEN}Installing ARM:Automatic Ripping Machine${NC}"
    cd /opt
    clone_arm
    cd arm
    pip3 install -r requirements.txt
    cp ./setup/51-automedia.rules /etc/udev/rules.d/
    create_abcde_symlink
    cp --no-clobber ./setup/arm.yaml /etc/arm/config/arm.yaml
    cp --no-clobber ./setup/apprise.yaml /etc/arm/config/apprise.yaml
    chown arm:arm /etc/arm/config/arm.yaml
    chown arm:arm /etc/arm/config
    create_arm_config_symlink
    chmod +x /opt/arm/scripts/thickclient/arm_wrapper.sh
    chmod +x /opt/arm/scripts/update_key.sh
}


function install_python_requirements {
    ##### Install the python tools and requirements
    echo -e "${RED}Installing up python requirements${NC}"
    cd /opt/arm
    # running pip with sudo can result in permissions errors, run as arm
    sudo -u arm pip3 install --upgrade pip wheel setuptools psutil pyudev
    sudo -u arm pip3 install --ignore-installed --prefer-binary -r requirements.txt
}

function setup_autoplay() {
    ######## Adding new line to fstab, needed for the autoplay to work.
    ######## also creating mount points (why loop twice)
    echo -e "${RED}Adding fstab entry and creating mount points${NC}"
    for dev in /dev/sr?; do
        if grep -q "${dev}    /mnt${dev}    udf,iso9660    users,noauto,exec,utf8    0    0" /etc/fstab; then
            echo -e "${RED}fstab entry for ${dev} already exists. Skipping...${NC}"
        else
            echo -e "\n${dev}    /mnt${dev}    udf,iso9660    users,noauto,exec,utf8    0    0 \n" | sudo tee -a /etc/fstab
        fi
        mkdir -p "/mnt$dev"
    done
}

function setup_syslog_rule() {
    ##### Add syslog rule to route all ARM system logs to /var/log/arm.log
    if [ -f /etc/rsyslog.d/30-arm.conf ]; then
        echo -e "${RED}ARM syslog rule found. Overwriting...${NC}"
        rm /etc/rsyslog.d/30-arm.conf
    fi
    cp ./setup/30-arm.conf /etc/rsyslog.d/30-arm.conf
}

function install_armui_service() {
    ##### Run the ARM UI as a service
    echo -e "${RED}Installing ARM service${NC}"
    mkdir -p /etc/systemd/system
    cp ./setup/armui.service /etc/systemd/system/armui.service

    systemctl daemon-reload
    chmod u+x /etc/systemd/system/armui.service
    chmod 600 /etc/systemd/system/armui.service

    #reload the daemon and then start ui
    systemctl start armui.service
    systemctl enable armui.service
    sysctl -p
}

function launch_setup() {
    echo -e "${RED}Launching ArmUI first-time setup${NC}"
    site_addr=$(sudo netstat -tlpn | awk '{ print $4 }' | grep ".*:${PORT}")
    if [[ -z "$site_addr" ]]; then
        echo -e "${RED}ERROR: ArmUI site is not running. Run \"sudo systemctl status armui\" to find out why${NC}"
    else
        echo -e "${GREEN}ArmUI site is running on http://$site_addr\n${RED}Launching setup...${NC}"
        sudo -u arm nohup xdg-open "http://$site_addr/setup" > /dev/null 2>&1 &
    fi
}

# start here
add_arm_user
install_arm_requirements
remove_existing_arm
install_arm_live_env
install_python_requirements
setup_autoplay
setup_syslog_rule
install_armui_service
if [[ ! -z "${GITHUB_ACTIONS}" ]]; then
  echo -e "${RED}GITHUB ACTIONS.${NC}"
  launch_setup
fi

#advise to reboot
echo
echo -e "${RED}We recommend rebooting your system at this time.${NC}"
echo
