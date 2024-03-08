#!/usr/bin/env bash

###################################################
###################################################
#              Scripting Settings                 #
###################################################
###################################################

#Run apt in non-interactive mode, assume default answers.
export DEBIAN_FRONTEND=noninteractive
#Cause the script to fail if and error code is provided (set -e)
#Cause the script to fail if an error code is provided while pipping commands (set -o pipefail)
#Cause the script to fail when encountering undefined variable (set -u)
#DEBUG MODE for Development only, Cause the script to print out every command executed (set -x)
set -eux -o pipefail

###################################################
###################################################
#               Global Variables                  #
###################################################
###################################################

#Text Color and Formatting Variables
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

#Script Error Codes
readonly ERROR_INSUFFICIENT_USER_PRIVILEGES=1
readonly ERROR_USER_PROVIDED_PASSWORD_MISMATCH=2
readonly ERROR_ATTEMPTED_TO_RUN_SCRIPT_IN_UNTESTED_DISTRO=3
readonly ERROR_MISSING_CONTRIB_REPOSITORY=4

#Script Variables
##  $SUDO_FLAG  Is a Readonly Variable that is set in the Script Eligibility Code Section below (near the bottom).
#               It is used throughout the script to choose between using sudo when calling a function or not.

###################################################
###################################################
#             Function Definitions                #
###################################################
###################################################

###################################################
#         Script eligibility functions            #
###################################################

#Confirm this script is running on Debian 12 (Bookworm).  Return boolean values 'true' or 'false'.
function IsDebian12Distro() {
  if [[ $(lsb_release -i | grep -o "Debian") == "Debian" ]] && [[ $(lsb_release -r | grep -o "12") -eq 12 ]] ; then
    true
  else
    false
  fi
}

#Determine if we are effectively a root user.  Return boolean values 'true' or 'false'.
function Is_Effective_Root_User() {
  USERID=$(id -u)
  if [[ ${USERID} == 0 ]] ;  then
    true
  else
    false
  fi
}

#Confirm the presence of required package libraries.
function IsContribRepoAvailable() {
  #This functions is dependant on running "Debian 12 (Bookworm)"
  #This function MUST be modified for any other version of Debian or other distributions of Linux
  if [[ $(apt-cache policy | grep -o "bookworm/contrib") == "bookworm/contrib" ]] ; then
    IncludesBookwormContrib=true
  else
    IncludesBookwormContrib=false
  fi

  if [[ $(apt-cache policy | grep -o "bookworm-updates/contrib") == "bookworm-updates/contrib" ]] ; then
    IncludesBookwormUpdatesContrib=true
  else
    IncludesBookwormUpdatesContrib=false
  fi

  if [[ $(apt-cache policy | grep -o "bookworm-security/contrib") == "bookworm-security/contrib" ]] ; then
    IncludesBookwormSecurityContrib=true
  else
    IncludesBookwormSecurityContrib=false
  fi

  if $IncludesBookwormContrib && $IncludesBookwormUpdatesContrib && $IncludesBookwormSecurityContrib ; then
    true
  else
    false
  fi
}

###################################################
#               Utility functions                 #
###################################################

###################################################
#     User and Group related functions            #
###################################################

#Call all user and group related functions.
function CreateArmUserAndGroup() {
  echo -e "${YELLOW}Adding arm user & group${NC}"
  CreateArmGroup
  CreateArmUser
  MakeArmUserPartOfRequiredGroups
}

#If the group exists, do nothing, if it does not exist create it.
function CreateArmGroup() {
  if ! [[ $(getent group arm) ]]; then
    if ${SUDO_FLAG}; then
      sudo groupadd arm;
    else
      groupadd arm;
    fi
    echo -e "${GREEN}Group 'arm' successfully created. \n${NC}"
  else
    echo -e "${GREEN}'arm' group already exists, skipping...\n${NC}"
  fi
}

#If user exists, do nothing, if it does not exist create the user with default settings.
function CreateArmUser() {
  if ! id arm > /dev/null 2>&1 ; then
    if ${SUDO_FLAG}; then
      sudo useradd -m arm -g arm -s /bin/bash -c "Automatic Ripping Machine"
    else
      useradd -m arm -g arm -s /bin/bash -c "Automatic Ripping Machine"
    fi
    echo -e "${GREEN}User 'arm' successfully created. \n${NC}"
    PasswordProtectArmUser
  else
    echo -e "${GREEN}'arm' user already exists, skipping creation...${NC}"
  fi
}

# Make sure the 'arm' user is part of the 'cdrom', 'video' and 'render' groups.
function MakeArmUserPartOfRequiredGroups() {
  if ${SUDO_FLAG}; then
    sudo usermod -aG cdrom,video,render arm
  else
    usermod -aG cdrom,video,render arm
  fi
}

#Give the User the option of setting a custom password.  The User may decline, in which event
#a default password of value '1234' is created.
#If the default password value is used, advise the user to change the password at the next opportunity.
function PasswordProtectArmUser() {
  #Determine what the password is going to be and save it in the variables $Password_1 & $Password_2
  PasswordQuestion="Do you wish to provide a custom password for the 'arm' user? Y/n : "
  read -ep "$(echo -e "${PasswordQuestion}")" -r -n 1 UserWishesToEnterPassword
  if [[ "${UserWishesToEnterPassword}" == "y"  ||  "${UserWishesToEnterPassword}" == "Y" ]] ; then
    for (( i = 0 ; i < 3 ; i++ )); do
      read -ep "$(echo -e "Please Enter Password_1? : ")" -r -s Password_1
      read -ep "$(echo -e "Please Confirm Password_1? : ")" -r -s Password_2
      if [[ "${Password_1}" == "${Password_2}" ]] ; then
        echo -e "\n${GREEN}Password matched, running \`passwd\` utility. \n${NC}"
        break;
      elif [[ $i -eq 2 ]] ; then
        echo -e "${RED}\nThe Passwords did not match 3 consecutive times, exiting...\n"
        exit ${ERROR_USER_PROVIDED_PASSWORD_MISMATCH}
      else
        echo -e "\n${YELLOW}Passwords do not match, please try again\n${NC}"
      fi
    done
  else
    echo -e "${YELLOW}Using default password '1234' it is recommended that you change it after script's completion. \n${NC}"
    Password_1=1234
    Password_2=1234
  fi
  #Set User Password.
  if ${SUDO_FLAG}; then
    echo -e "${Password_1}\n${Password_2}\n" | sudo passwd -q arm
  else
    echo -e "${Password_1}\n${Password_2}\n" | passwd -q arm
  fi
}

###################################################
#             Install Download Tools              #
###################################################

function InstallDownloadTools () {
  if ${SUDO_FLAG}; then
    sudo apt update && sudo apt -y install  curl git wget
  else
    apt update && apt install -y curl git wget
  fi
}

###################################################
#            Build & Install MakeMKV              #
###################################################

function InstallMakeMKV() {
  InstallBuildEnvironment
  BuildAndInstallMakeMKV
}

function InstallBuildEnvironment() {
  if ${SUDO_FLAG}; then
    sudo apt install -y build-essential \
                        pkg-config \
                        libc6-dev \
                        libssl-dev \
                        libexpat1-dev \
                        libavcodec-dev \
                        libgl1-mesa-dev \
                        qtbase5-dev \
                        zlib1g-dev \
                        checkinstall
  else
    apt install -y  build-essential \
                    pkg-config \
                    libc6-dev \
                    libssl-dev \
                    libexpat1-dev \
                    libavcodec-dev \
                    libgl1-mesa-dev \
                    qtbase5-dev \
                    zlib1g-dev \
                    checkinstall
  fi
}

function BuildAndInstallMakeMKV() {
  if ${SUDO_FLAG}; then
    ArmUserHomeFolder=~arm
    LatestMakeMKVVersion=$(curl -s https://www.makemkv.com/download/ | grep -o '[0-9.]*.txt' | sed 's/.txt//')
    MakeMKVBuildFilesDirectory="${ArmUserHomeFolder}"/MakeMKVBuildFiles/"${LatestMakeMKVVersion}"
    sudo -u arm mkdir -p "${MakeMKVBuildFilesDirectory}"
    cd "${MakeMKVBuildFilesDirectory}"
    sudo wget -nc -q --show-progress https://www.makemkv.com/download/makemkv-sha-"${LatestMakeMKVVersion}".txt
    sudo wget -nc -q --show-progress https://www.makemkv.com/download/makemkv-bin-"${LatestMakeMKVVersion}".tar.gz
    sudo wget -nc -q --show-progress https://www.makemkv.com/download/makemkv-oss-"${LatestMakeMKVVersion}".tar.gz
    grep "makemkv-bin-${LatestMakeMKVVersion}.tar.gz" "makemkv-sha-${LatestMakeMKVVersion}.txt" | sha256sum -c
    grep "makemkv-bin-${LatestMakeMKVVersion}.tar.gz" "makemkv-sha-${LatestMakeMKVVersion}.txt" | sha256sum -c
    sudo -u arm tar xzf makemkv-bin-"${LatestMakeMKVVersion}".tar.gz
    sudo -u arm tar xzf makemkv-oss-"${LatestMakeMKVVersion}".tar.gz

    cd makemkv-oss-"${LatestMakeMKVVersion}"
    sudo mkdir -p ./tmp
    sudo chmod 777 ./tmp
    sudo ./configure >> /dev/null  2>&1
    sudo make -s
    sudo make install
    sudo checkinstall -y

    cd ../makemkv-bin-"${LatestMakeMKVVersion}"
    sudo mkdir -p ./tmp
    sudo chmod 777 ./tmp
    sudo echo "yes" | sudo tee ./tmp/eula_accepted
    sudo make -s
    sudo make install
    sudo checkinstall -y


    sudo chown -R arm:arm "${MakeMKVBuildFilesDirectory}"
  else
    ArmUserHomeFolder=~arm
    LatestMakeMKVVersion=$(curl -s https://www.makemkv.com/download/ | grep -o '[0-9.]*.txt' | sed 's/.txt//')
    MakeMKVBuildFilesDirectory="${ArmUserHomeFolder}"/MakeMKVBuildFiles/"${LatestMakeMKVVersion}"
    mkdir -p "${MakeMKVBuildFilesDirectory}"
    cd "${MakeMKVBuildFilesDirectory}"
    wget -nc -q --show-progress https://www.makemkv.com/download/makemkv-sha-"${LatestMakeMKVVersion}".txt
    wget -nc -q --show-progress https://www.makemkv.com/download/makemkv-bin-"${LatestMakeMKVVersion}".tar.gz
    wget -nc -q --show-progress https://www.makemkv.com/download/makemkv-oss-"${LatestMakeMKVVersion}".tar.gz
    grep "makemkv-bin-${LatestMakeMKVVersion}.tar.gz" "makemkv-sha-${LatestMakeMKVVersion}.txt" | sha256sum -c
    grep "makemkv-bin-${LatestMakeMKVVersion}.tar.gz" "makemkv-sha-${LatestMakeMKVVersion}.txt" | sha256sum -c
    tar xzf makemkv-bin-"${LatestMakeMKVVersion}".tar.gz
    tar xzf makemkv-oss-"${LatestMakeMKVVersion}".tar.gz

    cd makemkv-oss-"${LatestMakeMKVVersion}"
    mkdir -p ./tmp
    ./configure >> /dev/null  2>&1
    make -s
    make install
    checkinstall -y

    cd ../makemkv-bin-"${LatestMakeMKVVersion}"
    mkdir -p ./tmp
    echo "yes" >> ./tmp/eula_accepted
    make -s
    make install
    checkinstall -y

    chown -R arm:arm "${MakeMKVBuildFilesDirectory}"
  fi

}

###################################################
#           Install Arm Dependencies              #
###################################################

function InstallArmDependencies() {
  if ${SUDO_FLAG}; then
    sudo apt install -y abcde \
                        at \
                        cdparanoia \
                        default-jre-headless \
                        eject \
                        ffmpeg \
                        flac \
                        glyrc \
                        handbrake-cli \
                        imagemagick \
                        libavcodec-extra \
                        libcurl4-openssl-dev \
                        libdvdcss2 \
                        libssl-dev \
                        python3 \
                        python3-libdiscid \
                        python3-pip

    sudo DEBIAN_FRONTEND=noninteractive apt -y install libdvd-pkg
    sudo dpkg-reconfigure --frontend noninteractive libdvd-pkg

  else
    apt install -y  abcde \
                    at \
                    cdparanoia \
                    default-jre-headless \
                    eject \
                    ffmpeg \
                    flac \
                    glyrc \
                    handbrake-cli \
                    imagemagick \
                    libavcodec-extra \
                    libcurl4-openssl-dev \
                    libdvdcss2 \
                    libssl-dev \
                    python3 \
                    python3-libdiscid \
                    python3-pip

    DEBIAN_FRONTEND=noninteractive apt -y install libdvd-pkg
    dpkg-reconfigure --frontend noninteractive libdvd-pkg
  fi
}

###################################################
#                Download Arm                     #
###################################################

function DownloadArm () {
  #Get current version number of ARM
  readonly ARM_LATEST=$(curl --silent 'https://github.com/automatic-ripping-machine/automatic-ripping-machine/releases' \
                        | grep 'automatic-ripping-machine/tree/*' | head -n 1 | sed -e 's/[^0-9\.]*//g')
  if ${SUDO_FLAG}; then
    cd /opt
    if [ -d arm ]; then
      #Arm Installation found.
      #Confirm it is a Git repo
      #If Git Repo, update the repo to current release

      #I chose git fetch and git checkout, but I am unsure if this could cause some issues...
      #this method depends on the user not modifying the repo between running this script
      #A big assumption.

      #The Other method is to delete the directory completely and do a fresh git pull at the current branch.
      #The problem here is that it would also delete the Python Virtual Environment that is created later in this script.
      #It would force an update of Python, which I am unsure if it is the best option.

      echo -e "${GREEN}Previous Arm Installation Found${NC}"

      cd arm
      sudo -u arm git fetch

      if ! sudo -u arm git checkout "${ARM_LATEST}" ; then
        #Git Checkout failed, likely because of a change in the repo.
        #Running Git Restore all files and folders will return the repo to the state it was
        #at the tagged checkout but will destroy all modifications added to the repo.

        #Prompt User to confirm first
        RestoreRepoPrompt="${YELLOW}WARNING, A previous installation of ARM was found on the system,
        it's repository contains uncommitted changes.  These changes will be lost

        ${NC}Do you wish to Continue? Y/n :"
        read -p "$(echo -e "${RestoreRepoPrompt}")" -r -n 1 ProceedWithScriptExecution
        echo -e ""
        if [[ "${ProceedWithScriptExecution}" == "y"  ||  "${ProceedWithScriptExecution}" == "Y" ]] ; then
          echo -e "${GREEN}Restoring Repository...${NC}"
          #Restore Repo
          sudo -u arm git restore .
          #Git Checkout the latest release branch
          sudo -u arm git checkout "${ARM_LATEST}"
        else
          exit ${ERROR_ATTEMPTED_TO_RUN_SCRIPT_IN_UNTESTED_DISTRO}
        fi
      fi
    else
      #Fresh Arm installation
      #Clone git repo, pin to latest release tag
      sudo mkdir arm
      sudo chown -R arm:arm arm

      sudo -u arm git clone --recurse-submodules --branch "${ARM_LATEST}" \
        https://github.com/automatic-ripping-machine/automatic-ripping-machine  arm

      #Copy clean copies of config files to etc folder.
      sudo mkdir -p /etc/arm/config
      sudo cp /opt/arm/setup/arm.yaml /etc/arm/config/arm.yaml
      sudo cp /opt/arm/setup/apprise.yaml /etc/arm/config/apprise.yaml
      sudo cp /opt/arm/setup/.abcde.conf /etc/arm/config/.abcde.conf

    fi

    #Fix File and Folder Permissions
    #chown -R arm:arm /opt/arm
    sudo find /opt/arm/scripts/ -type f -iname "*.sh" -exec chmod +x {} \;
    sudo chown -R arm:arm /etc/arm

    #Copy clean copies of the config files to /etc/arm/config/*.default
    #This is so that the user can find clean versions of each of the config files for references.
    #It helps incase of a broken config file due to error, or some future update changes.

    #Remove old (and possibly outdated) config default files.
    sudo rm -f /etc/arm/config/*.default

    sudo cp /opt/arm/setup/arm.yaml /etc/arm/config/arm.yaml.default
    sudo cp /opt/arm/setup/apprise.yaml /etc/arm/config/apprise.yaml.default
    sudo cp /opt/arm/setup/.abcde.conf /etc/arm/config/.abcde.conf.default
  else
    cd /opt
    if [ -d arm ]; then
      #Arm Installation found.
      #Confirm it is a Git repo
      #If Git Repo, update the repo to current release

      #I chose git fetch and git checkout, but I am unsure if this could cause some issues...
      #this method depends on the user not modifying the repo between running this script
      #A big assumption.

      #The Other method is to delete the directory completely and do a fresh git pull at the current branch.
      #The problem here is that it would also delete the Python Virtual Environment that is created later in this script.
      #It would force an update of Python, which I am unsure if it is the best option.

      echo -e "${GREEN}Previous Arm Installation Found${NC}"

      cd arm
      sudo -u arm git fetch

      if ! sudo -u arm git checkout "${ARM_LATEST}" ; then
        #Git Checkout failed, likely because of a change in the repo.
        #Running Git Restore all files and folders will return the repo to the state it was
        #at the tagged checkout but will destroy all modifications added to the repo.

        #Prompt User to confirm first
        RestoreRepoPrompt="${YELLOW}WARNING, A previous installation of ARM was found on the system,
        it's repository contains uncommitted changes.  These changes will be lost

        ${NC}Do you wish to Continue? Y/n :"
        read -p "$(echo -e "${RestoreRepoPrompt}")" -r -n 1 ProceedWithScriptExecution
        echo -e ""
        if [[ "${ProceedWithScriptExecution}" == "y"  ||  "${ProceedWithScriptExecution}" == "Y" ]] ; then
          echo -e "${GREEN}Restoring Repository...${NC}"
          #Restore Repo
          sudo -u arm git restore .
          #Git Checkout the latest release branch
          sudo -u arm git checkout "${ARM_LATEST}"
        else
          exit ${ERROR_ATTEMPTED_TO_RUN_SCRIPT_IN_UNTESTED_DISTRO}
        fi
      fi
    else
      #Fresh Arm installation
      #Clone git repo, pin to latest release tag
      mkdir arm
      chown -R arm:arm arm

      sudo -u arm git clone --recurse-submodules --branch "${ARM_LATEST}" \
        https://github.com/automatic-ripping-machine/automatic-ripping-machine  arm

      #Copy clean copies of config files to etc folder.
      mkdir -p /etc/arm/config
      cp /opt/arm/setup/arm.yaml /etc/arm/config/arm.yaml
      cp /opt/arm/setup/apprise.yaml /etc/arm/config/apprise.yaml
      cp /opt/arm/setup/.abcde.conf /etc/arm/config/.abcde.conf

    fi

    #Fix File and Folder Permissions
    #chown -R arm:arm /opt/arm
    find /opt/arm/scripts/ -type f -iname "*.sh" -exec chmod +x {} \;
    chown -R arm:arm /etc/arm

    #Copy clean copies of the config files to /etc/arm/config/*.default
    #This is so that the user can find clean versions of each of the config files for references.
    #It helps incase of a broken config file due to error, or some future update changes.

    #Remove old (and possibly outdated) config default files.
    rm -f /etc/arm/config/*.default

    cp /opt/arm/setup/arm.yaml /etc/arm/config/arm.yaml.default
    cp /opt/arm/setup/apprise.yaml /etc/arm/config/apprise.yaml.default
    cp /opt/arm/setup/.abcde.conf /etc/arm/config/.abcde.conf.default
  fi
}

###################################################
###################################################
#         Procedural Code Starts Here             #
###################################################
###################################################

###################################################
#            Script eligibility code              #
###################################################

#Confirm we are in a Debian 12 (Bookworm) Linux Distro.
if ! (IsDebian12Distro); then
  NotDebian12Prompt="${YELLOW}WARNING, you are attempting to run this script in a environment other than Debian 12 (Bookworm)
  This script was tested exclusively on Debian 12 (Bookworm)
  Running it on another Linux distro may have unpredictable side effects.

  ${NC}Do you wish to Continue? Y/n :"
  read -p "$(echo -e "${NotDebian12Prompt}")" -r -n 1 ProceedWithScriptExecution
  echo -e ""
  if [[ "${ProceedWithScriptExecution}" == "y"  ||  "${ProceedWithScriptExecution}" == "Y" ]] ; then
    echo -e "Running Script in Linux Distro Other than Debian 12 (Bookworm)"
  else
    exit ${ERROR_ATTEMPTED_TO_RUN_SCRIPT_IN_UNTESTED_DISTRO}
  fi
else
  #Confirm availability of contrib repository
  if ! (IsContribRepoAvailable) ; then
    echo -e "${RED}This script requires the presence of the contrib repositories;
bookworm/contrib, bookworm-updates/contrib and bookworm-security/contrib
Please add them to your installation and run the script again.
You can learn how to add the necessary repository here: https://wiki.debian.org/SourcesList
Exiting....${NC}"
    exit ${ERROR_MISSING_CONTRIB_REPOSITORY}
  fi
fi

#Confirm we can run this script.
if ! (Is_Effective_Root_User); then
  #Script was not run with elevated privileges, Request user for said privileges...
  #Ask for Sudo Access and confirm we have Sudo Privileges.
  if [[ $(sudo -v -p 'Please Enter your SUDO Password: ') -eq 0 ]] ; then
    #Set $SUDO_FLAG Global Constant that will be used for the rest of the script.
    readonly SUDO_FLAG=true
  else
    #Cannot confirm sudo privileges, alert the user and exit the script with error code.
    echo -e "${RED}For this script to accomplish it's task, it requires elevated privileges.
The current user doesn't have Sudo rights.
Please contact an administrator to ask for Sudo rights or switch to a user with Sudo rights before running this script.
Exiting....${NC}"
    exit ${ERROR_INSUFFICIENT_USER_PRIVILEGES}
  fi
else
  readonly SUDO_FLAG=false
fi

#Confirm existence of / create arm user and group
CreateArmUserAndGroup

#Install Required Download Tools
InstallDownloadTools

#Build and Install MakeMKV
InstallMakeMKV

#Install Arm Dependencies
InstallArmDependencies

#Install Arm
DownloadArm

#Post Arm Installation

