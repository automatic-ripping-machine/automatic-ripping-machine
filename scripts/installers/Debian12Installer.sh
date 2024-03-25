#!/bin/bash

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
set -eu -o pipefail

###################################################
###################################################
#               Global Variables                  #
###################################################
###################################################

PortFlag=false
Port=8080
Fork='automatic-ripping-machine'
Tag='latest'


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
readonly ERROR_USER_DID_NOT_ACCEPT_SCRIPT_DISCLAIMER=5
readonly ERROR_SUDO_NOT_INSTALLED=6
readonly ERROR_SCRIPT_PORT_OPTION_INVALID=7
readonly ERROR_SCRIPT_UNKNOWN_OPTION=8
readonly ERROR_FOUND_ARM_DIRECTORY_COULD_NOT_PROCEED=9
readonly ERROR_SCRIPT_PORT_IS_SYSTEM_RESERVED=10
readonly ERROR_GIT_REPO_FORK_DOES_NOT_EXIST=11
readonly ERROR_GIT_REPO_TAG_DOES_NOT_EXIST=12


###################################################
###################################################
#         Usage Function and While Loop           #
###################################################
###################################################

#Note that the Function must be defined before the while loop.

#Usage Function.  Used to display useful error messages to the user
#and to explain to the user how to use this script.
#The function also exits the script.
#Accepts one Parameter, ERROR_CODE an integer representing the error code generated.
function usage() {
  local ERROR_CODE=${1}
  UsageMessage="\nDebian 12 ARM Installer Script

Usage: ./Debian12Installer.sh [-f <Fork_Name>] [-t <Tag_or_Branch_Name>] [-p <Port_Number>] [-h] [-H]

-f  <Fork_Name>
   The name of the fork or Automatic Ripping Machine to use for the installation
   ***The Fork must be available publicly on GitHub***
   Default: \"automatic-ripping-machine\"

-t <Tag_or_Branch_Name>
   The name of the tag or branch to checkout
   Default: \"latest\"

-p <Port_Number>
  The port number to use to access ARM
  **Must be greater than or equal to 1024**
  **Must be less than or equal to 65535**
  Default: 8080

-h or -H
  This Help Message"


  case $ERROR_CODE in
    0) #An Error Code of zero means that no errors were generated, therefore this function was called
      #as a result of passing the -h or -H option to the script, asking for the help message.
      echo -e "${UsageMessage}"
      ;;

    "${ERROR_SCRIPT_PORT_IS_SYSTEM_RESERVED}")
      #This Error Code indicates that the user selected the port option and then supplied a port
      #between 0 and 1024.  While valid ports these are system reserved ports.
      #An explanation in the wiki article explaining this script's usage will explain
      #How one may set a system reserved port as a port for ARM.  It is outside the scope of this
      #Script.
      echo -e "${RED}ERROR: Port (-p <Port_Number>) cannot be a system-reserved port.
Acceptable values are between 1024 and 65535 inclusively.${NC}"
      ;;

    "${ERROR_SCRIPT_PORT_OPTION_INVALID}")
      #The user used the port option but supplied an invalid port (less than or equal to 0 or
      #greater than or equal to 65536)
      echo -e "${RED}ERROR: Port (-p <Port_Number>) must be a valid port number.
Acceptable values are between 1024 and 65535 inclusively.${NC}"
      ;;

    "${ERROR_SCRIPT_UNKNOWN_OPTION}")
      #The user supplied an option that was unknown to this function.  Throw and error
      #and display the help message.
      echo -e "${RED}ERROR: The option that was passed to this script is unknown. Please used a valid option.${NC}"
      echo -e "\n${UsageMessage}"
      ;;
  esac

  #Exit the script using the supplied Error Code.
  exit "${ERROR_CODE}"
}

while getopts ':f:hHp:t:' OPTION
do
  case ${OPTION} in
    p)
        Port=$OPTARG
        if ! [[ ${Port} -gt 0 && ${Port} -le 65535 ]]; then
          usage ${ERROR_SCRIPT_PORT_OPTION_INVALID}
        fi
        if [[ ${Port} -gt 0 && ${Port} -lt 1024 ]]; then
          usage ${ERROR_SCRIPT_PORT_IS_SYSTEM_RESERVED}
        fi
        if ! [[ ${Port} -eq 8080 ]]; then
          PortFlag=true
        fi
        ;;
    f)
        Fork=$OPTARG
        ;;
    t)
        Tag=$OPTARG
        ;;
    h | H )
        usage 0
        ;;
    ?)  usage ${ERROR_SCRIPT_UNKNOWN_OPTION} "${OPTION}"
  esac
done


###################################################
###################################################
#             Function Definitions                #
###################################################
###################################################

###################################################
#         Script eligibility functions            #
###################################################

#This script installs ARM in an unsupported and untested environment.
#The task of supporting every environment is too great for the dev team. Therefore
#inform the user that while this script does exist, if any bugs appear as a result of
#it's use, the user must be able to reproduce the bug in the Docker Official Image
#Before creating a bug report.  Take the opportunity to also mention the MIT licence
#and to mention that MakeMKV is still in Beta.
#
#Get the user to agree to the conditions of using this script before continuing.
function UserAcceptedConditions() {
  ##TODO Create Wiki entry explaining now to enter the permanent MakeMKV licence in ARM.
  Disclaimer="${RED}
************************************************************************************************************************
** ${NC}                                                                                                                   ${RED}**
** ${GREEN}                                           Automatic Ripping Machine (ARM)                                         ${RED}**
** ${GREEN}                                    Installation Script for Debian 12 (Bookworm)                                   ${RED}**
** ${YELLOW}  WARNING - ${NC}This installation method is no longer supported by the ARM development team. This script is provided   ${RED}**
** ${NC} as is, without support.  If you experience issues with your ARM installation, you will need to reproduce it using ${RED}**
** ${NC} an official ARM docker image before opening up an Issue on GitHub.  The installation instructions for ARM using   ${RED}**
** ${NC} Docker can be found here: https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker      ${RED}**
** ${NC}                                                                                                                   ${RED}**
** ${NC} ARM uses MakeMKV. As of March 2024, MakeMKV is still in Beta and free to use while in Beta.                       ${RED}**
** ${NC} You may, optionally, purchase a licence for MakeMKV at https://makemkv.com/buy/ Once purchased, you can go into   ${RED}**
** ${NC} the ARM settings and paste in your key.  Instructions for entering your permanent key for MakeMKV in ARM can      ${RED}**
** ${NC} be found here: [Wiki Link to instructions yet to be written]                                                      ${RED}**
** ${NC}                                                                                                                   ${RED}**
** ${NC} ARM is Open Source software licenced with the MIT licence:                                                        ${RED}**
** ${NC} https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/LICENSE                          ${RED}**
** ${NC}                                                                                                                   ${RED}**
************************************************************************************************************************

${YELLOW} Do you wish to proceed with this unsupported installation? Y/n :${NC}
"

  read -p "$(echo -e "${Disclaimer}")" -r -n 1 ProceedWithScriptExecution
  echo -e ""
  if ! [[ "${ProceedWithScriptExecution}" == "y"  ||  "${ProceedWithScriptExecution}" == "Y" ]] ; then
    echo -e "${RED} Exiting Installation Script, No changes were made...${NC}"
    exit ${ERROR_USER_DID_NOT_ACCEPT_SCRIPT_DISCLAIMER}
  fi

}

#Function to confirm that the sudo package is installed. (Not eccentrically true for LXC containers.)
#Even running this script as an effective root user, the Sudo Command is still required for the script
#to run successfully.
#Return true or false
function IsSudoInstalled() {
  if ! dpkg -s sudo > /dev/null 2>&1 ; then
    true
  else
    false
  fi
}

#Determine if we are effectively a root user.  Return boolean values 'true' or 'false'.
#If the function is about to return false, the function exits the script with the
#appropriate error code.
function IsEffectiveRootUser() {
  USERID=$(id -u)
  if [[ ${USERID} == 0 ]] ;  then
    true
    if IsSudoInstalled ; then
      echo -e "${RED} \nThis script requires the that « sudo » be installed.
Please install sudo and run the script again.

Exiting Installation Script, No changes were made...${NC}"
      exit ${ERROR_SUDO_NOT_INSTALLED}
    fi

  else
    #Cannot confirm sudo privileges, alert the user and exit the script with error code.
    echo -e "${RED}\nFor this script to accomplish it's task, it requires elevated privileges.
Please run this script with « sudo /[path_to_script]/Debian12Installer.sh »

Exiting Installation Script, No changes were made...${NC}"
    exit ${ERROR_INSUFFICIENT_USER_PRIVILEGES}
    false
  fi
}

#If a Fork or Tag was passed to the script, we need to test for the existence of the fork and/or tag.
#If either do not exist, exit the script with an error code and message.
function RepositoryExists() {
  local NotFound
  local GitHubAPICall
  local GitLsRemoteOutput
  local GitLsRemoteURL

  if [ "${Fork}" != "automatic-ripping-machine" ] ; then
    echo "Custom Fork passed to the script, testing for existence..."
    NotFound='"message": "Not Found",'
    GitHubAPICall="https://api.github.com/repos/${Fork}/automatic-ripping-machine"
    if [[ $(curl -s "${GitHubAPICall}" | grep -o "${NotFound}") == "${NotFound}" ]] ; then
      echo -e "${RED}The Fork ${Fork} was not found, exitring the script...${NC}\n"
      exit ${ERROR_GIT_REPO_FORK_DOES_NOT_EXIST}
    fi
  fi

  #if [ "${Tag}" != "latest" ] ; then
    echo "Custom Tag passed to the script, testing for existence"
    GitLsRemoteURL="https://github.com/${Fork}/automatic-ripping-machine.git"
    GitLsRemoteOutput=$(git ls-remote --quiet "${GitLsRemoteURL}" "${Tag}")
    if [[ ${GitLsRemoteOutput} == "" ]] ; then
      echo -e "${RED}The Tag or Branch ${Tag} was not found, exiting the script...${NC}\n"
      exit ${ERROR_GIT_REPO_TAG_DOES_NOT_EXIST}
    fi
  #fi
}

function IsEligibleDistro() {
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
}

#Confirm this script is running on Debian 12 (Bookworm).  Return boolean values 'true' or 'false'.
function IsDebian12Distro() {
  if [[ $(lsb_release -i | grep -o "Debian") == "Debian" ]] && [[ $(lsb_release -r | grep -o "12") -eq 12 ]] ; then
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
  if (CreateArmGroup && CreateArmUser) ; then
    PasswordProtectArmUser true
  else
    PasswordProtectArmUser false
  fi
  MakeArmUserPartOfRequiredGroups
}

#If the group exists, do nothing, if it does not exist create it.
function CreateArmGroup() {
  echo "Creating Groups...."
  if ! [[ $(getent group arm) ]]; then
    groupadd arm
    echo -e "${GREEN}Group 'arm' successfully created. \n${NC}"
    true
  else
    echo -e "${GREEN}'arm' group already exists, skipping...\n${NC}"
    false
  fi
}

#If user exists, do nothing, if it does not exist create the user with default settings.
function CreateArmUser() {
  if ! id arm > /dev/null 2>&1 ; then
    useradd -m arm -g arm -s /bin/bash -c "Automatic Ripping Machine"
    echo -e "${GREEN}User 'arm' successfully created. \n${NC}"
    true
  else
    echo -e "${GREEN}'arm' user already exists, skipping creation...${NC}"
    false
  fi
}

function DeleteArmUser() {
  userdel arm
  rm -R /home/arm
}

# Make sure the 'arm' user is part of the 'cdrom', 'video' and 'render' groups.
function MakeArmUserPartOfRequiredGroups() {
  usermod -aG cdrom,video,render arm
}

#Give the User the option of setting a custom password.  The User may decline, in which event
#a default password of value '1234' is created.
#If the default password value is used, advise the user to change the password at the next opportunity.
function PasswordProtectArmUser() {
  local NewUser=$1
  #Determine what the password is going to be and save it in the variables $Password_1 & $Password_2
  #Make these variables explicitly local, to prevent the variables escaping this function.
  local Password_1=''
  local Password_2=''
  if ($NewUser) ; then
    PasswordQuestion="Do you wish to provide a custom password for the 'arm' user? Y/n : "
  else
    PasswordQuestion="The 'arm' user was already on the system.
Do you wish to change it's password? Y/n : "
  fi
  read -ep "$(echo -e "${PasswordQuestion}")" -r -n 1 UserWishesToEnterPassword
  if [[ "${UserWishesToEnterPassword}" == "y"  ||  "${UserWishesToEnterPassword}" == "Y" ]] ; then
    #The User wishes to provide a custom password.  Give the user 3 times to provide one,
    #This attempt limit is to prevent an infinite loop.
    local PasswordConfirmed=false
    for (( i = 0 ; i < 3 ; i++ )); do
      read -ep "$(echo -e "Please Enter Password? : ")" -r -s Password_1
      read -ep "$(echo -e "Please Confirm Password? : ")" -r -s Password_2
      if [[ "${Password_1}" == "${Password_2}" ]] ; then
        echo -e "\n${GREEN}Password matched, running \`passwd\` utility. \n${NC}"
        PasswordConfirmed=true
        break;
      else
        echo -e "\n${YELLOW}Passwords do not match, please try again\n${NC}"
      fi
    done
    if ! ($PasswordConfirmed) ; then
      #This is the 3rd attempt.  Exit script.
      echo -e "${RED}\nThe Passwords did not match 3 consecutive times, exiting...\n${NC}"
      if ($NewUser) ; then
        echo -e "${YELLOW}Deleting newly created arm User Account.\n${NC}"
        DeleteArmUser
      else
        echo -e "${YELLOW}Password for the arm user was not changed.\n${NC}"
      fi
      exit ${ERROR_USER_PROVIDED_PASSWORD_MISMATCH}
    fi
  elif ! ($NewUser); then
    echo -e "${YELLOW}Using default password '1234' it is recommended that you change it after script's completion. \n${NC}"
    Password_1=1234
    Password_2=1234
  fi
  if ($NewUser) || (! ($NewUser) && $PasswordConfirmed); then
    echo -e "${Password_1}\n${Password_2}\n" | passwd -q arm > /dev/null 2>&1
  fi

}

###################################################
#             Install Download Tools              #
###################################################

function InstallDownloadTools () {
  apt update && apt install -y curl git wget lsb-release
}

###################################################
#            Build & Install MakeMKV              #
###################################################

function InstallMakeMKV() {
  InstallBuildEnvironment
  BuildAndInstallMakeMKV
}

function InstallBuildEnvironment() {
  apt install -y  build-essential \
                  pkg-config \
                  libc6-dev \
                  libssl-dev \
                  libexpat1-dev \
                  libavcodec-dev \
                  libgl1-mesa-dev \
                  qtbase5-dev \
                  zlib1g-dev
}

function BuildAndInstallMakeMKV() {
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

  cd ../makemkv-bin-"${LatestMakeMKVVersion}"
  mkdir -p ./tmp
  echo "yes" >> ./tmp/eula_accepted
  make -s
  make install

  chown -R arm:arm "${MakeMKVBuildFilesDirectory}"
}

###################################################
#           Install Arm Dependencies              #
###################################################

function InstallArmDependencies() {
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
                  lsdvd \
                  python3 \
                  python3-venv \
                  python3-libdiscid \
                  python3-pip

  DEBIAN_FRONTEND=noninteractive apt -y install libdvd-pkg
  dpkg-reconfigure --frontend noninteractive libdvd-pkg
}

###################################################
#                Download Arm                     #
###################################################

function DownloadArm () {
  local AlertUserOfExistenceOfAmrDirectory
  local ProceedWithScriptExecution
  local ExistingArmYamlFile
  local ExistingAbcdeConfFile
  local ExistingAppriseYamlFile

  #Get current version number of ARM
  if ${Tag} == 'latest' ; then
    Tag=$(curl --silent 'https://github.com/automatic-ripping-machine/automatic-ripping-machine/releases' \
                        | grep 'automatic-ripping-machine/tree/*' | head -n 1 | sed -e 's/[^0-9\.]*//g')
  fi

  cd /opt
  if [ -d arm ]; then
    #Found a directory that may contain a repo.

    #Query User, asking for permission to delete the directory and install arm.
    AlertUserOfExistenceOfAmrDirectory="${YELLOW}WARNING, the script found that the directory /opt/arm already exists.
    If you are attempting to update your arm installation, please us git to checkout the latest release.
    In order to proceed, this script needs to delete the /opt/arm directory and checkout a fresh copy of arm
    from the GitHub repository.  This is a non-reversible change.

    ${NC}Do you wish to Continue? Y/n :"
    read -p "$(echo -e "${AlertUserOfExistenceOfAmrDirectory}")" -r -n 1 ProceedWithScriptExecution
    echo -e ""
    if [[ "${ProceedWithScriptExecution}" == "y"  ||  "${ProceedWithScriptExecution}" == "Y" ]] ; then
      #Since we know the /opt/arm directory exists.  There is a very strong possibility of previous config files
      #existing.  We want to back these files up to give the user the chance to use those instead of the default ones.


      ##TODO Test this behaviour!!!

      ExistingArmYamlFile="/etc/arm/config/arm.yaml"
      ExistingAbcdeConfFile="/etc/arm/config/abcde.conf"
      ExistingAppriseYamlFile="/etc/arm/config/apprise.yaml"

      if [[ -f ${ExistingAbcdeConfFile} ]] ; then
        cp "${ExistingAbcdeConfFile}" "${ExistingAbcdeConfFile}.bck"
      fi

      if [[ -f ${ExistingArmYamlFile} ]] ; then
        cp "${ExistingArmYamlFile}" "${ExistingArmYamlFile}.bck"
      fi

      if [[ -f ${ExistingAppriseYamlFile} ]] ; then
        cp "${ExistingAppriseYamlFile}" "${ExistingAppriseYamlFile}.bck"
      fi

      echo -e "${RED} Deleting /opt/arm directory...${NC}"
      rm -R /opt/arm
    else
      echo -e "${RED} Exiting Script, MakeMKV is installed, Arm is not installed...${NC}"
      exit ${ERROR_FOUND_ARM_DIRECTORY_COULD_NOT_PROCEED}
    fi

  fi

  #Clone git repo, pin to latest release tag
  mkdir arm
  chown -R arm:arm arm

  sudo -u arm git clone --recurse-submodules --branch "${Tag}" \
    "https://github.com/${Fork}/automatic-ripping-machine"  arm


  #Copy clean copies of config files to etc folder.
  mkdir -p /etc/arm/config
  cp /opt/arm/setup/arm.yaml /etc/arm/config/arm.yaml
  cp /opt/arm/setup/apprise.yaml /etc/arm/config/apprise.yaml
  cp /opt/arm/setup/.abcde.conf /etc/arm/config/abcde.conf

  if [[ $PortFlag ]] ; then
    echo -e "${RED}Non-default port specified, updating arm config...${NC}"
    # replace the default 8080 port with the specified port
    sudo sed -e s"/\(^WEBSERVER_PORT:\) 8080/\1 ${Port}/" -i /etc/arm/config/arm.yaml
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
  cp /opt/arm/setup/.abcde.conf /etc/arm/config/abcde.conf.default
}

function CreatePythonVirtualEnvironmentAndInstallArmPythonDependencies() {
  cd /opt/arm
  sudo -u arm python3 -m venv venv
  sudo -u arm /opt/arm/venv/bin/pip3 install wheel
  sudo -u arm /opt/arm/venv/bin/pip3 install -r requirements.txt
}

function CreateUDEVRules() {
  ln -sf /opt/arm/setup/51-automatic-ripping-machine-venv.rules /lib/udev/rules.d/
}

function MountDrives() {
  ######## Adding new line to fstab, needed for the autoplay to work.
  ######## also creating mount points (why loop twice)
  echo -e "${RED}Adding fstab entry and creating mount points${NC}"
  for dev in /dev/sr?; do
    if grep -q "${dev}    /mnt${dev}    udf,iso9660    users,noauto,exec,utf8    0    0" /etc/fstab; then
        echo -e "${RED}fstab entry for ${dev} already exists. Skipping...${NC}"
    else
        echo -e "\n${dev}    /mnt${dev}    udf,iso9660    users,noauto,exec,utf8    0    0 \n" | tee -a /etc/fstab
    fi
    mkdir -p "/mnt$dev"
  done
}

function SetupFolders() {
  sudo -u arm mkdir -p /home/arm/logs/
  sudo -u arm mkdir -p /home/arm/logs/progress/
  sudo -u arm mkdir -p /home/arm/media/transcode/
  sudo -u arm mkdir -p /home/arm/media/completed/
  sudo -u arm mkdir -p /home/arm/media/raw/
}

function CreateAndStartService() {
  echo -e "${RED}Installing ARM service${NC}"
  ln -sf /opt/arm/setup/arm.service /lib/systemd/system/armui.service
  systemctl daemon-reload
  systemctl enable armui
  systemctl start armui
}

function LaunchSetup() {
  echo -e "${RED}Launching ArmUI first-time setup${NC}"

  sleep 5  # Waits 5 seconds, This gives time for service to start
  #Find the external IP address of this server by finding the route to cloudflare's DNS servers.
  site_addr=$(ip route get 1.1.1.1 | grep -oP 'src \K[^ ]+')
  if [[ $Port -ne 80 ]] ; then
    site_addr="${site_addr}:${Port}"
  fi
  echo site_addr
  ArmUIServiceActive=$(systemctl is-active --quiet armui)
  if [[ $ArmUIServiceActive -ne 0 ]]; then
      echo -e "${RED}ERROR: ArmUI site is not running. Run \"sudo systemctl status armui\" to find out why${NC}"
  else
      curl "http://${site_addr}/setup" -o /dev/null -s
      echo -e "${GREEN} Installation Complete
      Please click this link below to access your new Automatic Ripping Machine installation!
      http://${site_addr}${NC}\n"
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

#Inform the user that this is an unsupported installation method.  Inform them of the existence of the preferred
#method, being the Docker image.
UserAcceptedConditions

IsEffectiveRootUser

#Install Required Download Tools
InstallDownloadTools

#Test for the existence of the repository, fork and tab/branch
RepositoryExists

#Test the Linux Distribution, if Debian 12, confirm presence of Contribs repos, if not, Give
#User the option of attempting the installation anyway, even if it may fail.
#(Reason for target Distro of Debian 12, is because of the known presence of the required
#packages)
IsEligibleDistro

#Confirm existence of / create arm user and group
CreateArmUserAndGroup

#Build and Install MakeMKV
InstallMakeMKV

#Install Arm Dependencies
InstallArmDependencies

#Install Arm
DownloadArm
CreatePythonVirtualEnvironmentAndInstallArmPythonDependencies

#Post Arm Installation
CreateUDEVRules
MountDrives
SetupFolders
CreateAndStartService
LaunchSetup