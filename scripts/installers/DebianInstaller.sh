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
LinuxDistribution=''
LinuxDistributionRelease=0
LinuxDistributionCodename=''
PreviousInstallationFound=false
UseExistingConfigFiles=false


#Text Color and Formatting Variables
RED='\033[1;31m'
GREEN='\033[1;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

#Script Error Codes
readonly ERROR_INSUFFICIENT_USER_PRIVILEGES=201
readonly ERROR_USER_PROVIDED_PASSWORD_MISMATCH=202
readonly ERROR_ATTEMPTED_TO_RUN_SCRIPT_IN_UNTESTED_DISTRO=203
readonly ERROR_MISSING_CONTRIB_REPOSITORY=204
readonly ERROR_USER_DID_NOT_ACCEPT_SCRIPT_DISCLAIMER=205
readonly ERROR_SUDO_NOT_INSTALLED=206
readonly ERROR_SCRIPT_PORT_OPTION_INVALID=207
readonly ERROR_SCRIPT_UNKNOWN_OPTION=208
readonly ERROR_FOUND_ARM_DIRECTORY_COULD_NOT_PROCEED=209
readonly ERROR_GIT_REPO_FORK_DOES_NOT_EXIST=211
readonly ERROR_GIT_REPO_TAG_DOES_NOT_EXIST=212
readonly ERROR_FOUND_ACTIVE_ARMUI_SERVICE=213
readonly ERROR_FOUND_INACTIVE_AMRUI_SERVICE_USER_DECLINED_TO_CONTINUE=214


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
        if [[ ${Port} -ne 8080 ]]; then
          echo "Using Non-Standard Port ${Port}"
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
  Disclaimer="${RED}
************************************************************************************************************************
** ${NC}                                                                                                                   ${RED}**
** ${GREEN}                                           Automatic Ripping Machine (ARM)                                         ${RED}**
** ${GREEN}                                           Installation Script for Debian                                          ${RED}**
** ${YELLOW}  WARNING - ${NC}This installation method is no longer supported by the ARM development team. This script is provided   ${RED}**
** ${NC} as is, without support.  If you experience issues with your ARM installation, you will need to reproduce it using ${RED}**
** ${NC} an official ARM docker image before opening up an Issue on GitHub.  The installation instructions for ARM using   ${RED}**
** ${NC} Docker can be found here: https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker      ${RED}**
** ${NC}                                                                                                                   ${RED}**
** ${NC} ARM uses MakeMKV. As of January 2025, MakeMKV is still in Beta and free to use while in Beta.                     ${RED}**
** ${NC} You may, optionally, purchase a licence for MakeMKV at https://makemkv.com/buy/ Once purchased, you can go into   ${RED}**
** ${NC} the ARM settings and paste in your key.  Instructions for entering your permanent key for MakeMKV in ARM can      ${RED}**
** ${NC} be found here: https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/MakeMKV-Info           ${RED}**
** ${NC}                                                                                                                   ${RED}**
** ${NC} ARM is Open Source software licenced with the MIT licence:                                                        ${RED}**
** ${NC} https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/LICENSE                          ${RED}**
** ${NC}                                                                                                                   ${RED}**
************************************************************************************************************************

${BLUE} Do you wish to proceed with this unsupported installation? Y/n :${NC}
"

  if ! IsUserAnsweredYesToPrompt "${Disclaimer}" ; then
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

  if [ "${Tag}" != "latest" ] ; then
    echo "Custom Tag passed to the script, testing for existence"
    GitLsRemoteURL="https://github.com/${Fork}/automatic-ripping-machine.git"
    GitLsRemoteOutput=$(git ls-remote --quiet "${GitLsRemoteURL}" "${Tag}")
    if [[ ${GitLsRemoteOutput} == "" ]] ; then
      echo -e "${RED}The Tag or Branch ${Tag} was not found, exiting the script...${NC}\n"
      exit ${ERROR_GIT_REPO_TAG_DOES_NOT_EXIST}
    fi
  fi
}

function IsUserAnsweredYesToPrompt() {
  local Prompt=$1
  local Response
  echo ""
  read -p "$(echo -e "${Prompt}")" -r Response
  echo -e ""
  if [[ "${Response}" == "y" || "${Response}" == "Y" ]] ; then
    echo ""
    true
  else
    echo ""
    false
  fi

}

function IsEligibleDistro() {
  if ! IsDebianDistro; then

    NotDebian12Prompt="${YELLOW}WARNING, you are attempting to run this script in a environment other than Debian 11 or 12
This script was tested exclusively on Debian 12 (Bookworm) and Debian 11 (Bullseye)
Running it on another Linux distro may have unpredictable side effects.

${BLUE}Do you wish to Continue? Y/n :${NC}"

    if IsUserAnsweredYesToPrompt "${NotDebian12Prompt}" ; then
      echo -e "${YELLOW}Running Script in Linux Distro Other than Debian 12 (Bookworm)${NC}"
    else
      exit ${ERROR_ATTEMPTED_TO_RUN_SCRIPT_IN_UNTESTED_DISTRO}
    fi
  else
    #Confirm availability of contrib repository
    if ! IsContribRepoAvailable ; then
      echo -e "${RED}One or more of the contrib repositories;
are missing please add them to your installation and run the script again.
You can learn how to add the necessary repository here: https://wiki.debian.org/SourcesList

Exiting....${NC}"
      exit ${ERROR_MISSING_CONTRIB_REPOSITORY}
    fi
  fi
}

#Confirm this script is running on Debian 12 (Bookworm).  Return boolean values 'true' or 'false'.
function IsDebianDistro() {
  LinuxDistribution=$(lsb_release -a | grep 'Distributor ID:' | awk '{print $3}')
  LinuxDistributionRelease=$(lsb_release -a | grep 'Release:' | awk '{print $2}')
  LinuxDistributionCodename=$(lsb_release -a | grep 'Codename:' | awk '{print $2}')
  if [[ ${LinuxDistribution} == "Debian" ]] ; then
    case ${LinuxDistributionRelease} in
      '11' | '12' )
        true
        ;;
      ?)
        false
        ;;
    esac
  else
    false
  fi
}



#Confirm the presence of required package libraries.
function IsContribRepoAvailable() {
  local IncludesContrib
  local IncludesUpdatesContrib
  local IncludesSecurityContrib
  local Prompt

  ## TEST for the presence of the Repos.
  if [[ $(apt-cache policy | grep -o "${LinuxDistributionCodename}/contrib") == "${LinuxDistributionCodename}/contrib" ]] ; then
    IncludesContrib=true
  else
    IncludesContrib=false
  fi

  if [[ $(apt-cache policy | grep -o "${LinuxDistributionCodename}-updates/contrib") == "${LinuxDistributionCodename}-updates/contrib" ]] ; then
    IncludesUpdatesContrib=true
  else
    IncludesUpdatesContrib=false
  fi

  if [[ $(apt-cache policy | grep -o "${LinuxDistributionCodename}-security/contrib") == "${LinuxDistributionCodename}-security/contrib" ]] ; then
    IncludesSecurityContrib=true
  else
    IncludesSecurityContrib=false
  fi

  #The only required Repo is the Contrib repo.  Updates/Contrib and Security/Contrib are strongly recommended but not
  # required.  (This test is only relevant for Debian 12.  Since I did not find a way to test for Debian 11 and Debian 10
  # Does not appear to have a contrib repo...
  if $IncludesContrib ; then

    #If this is Debian 12, test for the availability of the updates/contrib and security/contrib repos.  I have not
    #Found a way to test for those repose with Debian 11 or 10.
    if [[ "${LinuxDistributionRelease}" -eq 12 ]] ; then
      Prompt=""
      #Contrib repo is present, check for the optional ones, if one or both are missing, create a prompt to advice the user
      #of the missing optional repo and confirm they with to proceed.
      if ! $IncludesUpdatesContrib && ! $IncludesSecurityContrib ; then
        echo -e "${RED}Missing ${LinuxDistributionCodename}-udpates/contrib and ${LinuxDistributionCodename}-security/contrib repository.${NC}"
        Prompt="${YELLOW}WARNING: The \"updates/contrib\" and \"security/contrib\" repositories are missing. It is recommended
that these repositories be present in order to keep A.R.M. dependencies up to date with the latest security fixes.

${BLUE}Do you wish to Continue? Y/n: ${NC}"
      elif ! $IncludesUpdatesContrib ; then
        echo -e "${RED}Missing ${LinuxDistributionCodename}-updates/contrib repository.${NC}"
        Prompt="${YELLOW}WARNING: The updates/contrib repository is missing. It is recommended that this repository
be present in order to keep A.R.M. dependencies up to date.

${BLUE}Do you wish to Continue? Y/n: ${NC}"
      elif ! $IncludesSecurityContrib ; then
        echo -e "${RED}Missing ${LinuxDistributionCodename}-security/contrib repository.${NC}"
        Prompt="${YELLOW}WARNING: The security/contrib repository is missing. It is recommended that this repository
be present in order to keep A.R.M. dependencies up to date with the latest security fixes.

${BLUE}Do you wish to Continue? Y/n: ${NC}"
      fi

      if [[ "${Prompt}" == "" ]] || IsUserAnsweredYesToPrompt "${Prompt}" ; then
        #No Repos are missing OR User wishes to proceed with missing repo(s)
        true
      else
        #User wishes to cancel the installation.
        false
      fi
    else
      #Not Debian 12, therefore only test we care for is the main/contrib repo, which passed.
      true
    fi
  else
    #Contrib repo is missing, return false.
    echo -e "${RED}Missing ${LinuxDistributionCodename}/contrib repository.${NC}"
    false
  fi
}


function ServiceExists() {
    local ServiceName=$1
    if [[ $(systemctl list-units --all -t service --full --no-legend "$ServiceName.service" | sed 's/^\s*//g' | cut -f1 -d' ') == $ServiceName.service ]]; then
        return 0
    else
        return 1
    fi
}

function FoundPreviousInstallation() {
  ##TODO There is an error here that I need to track down.
  if ServiceExists armui  ; then
    echo "Found Armui Service"
    if systemctl is-active --quiet armui ; then
      echo -e "${RED}The installation script found that there is an armui service running under SystemD. Which seems
to indicate that you are currently running an ARM installation and it is active.  It is recommended to not run
the installation script on a machine that is already running ARM.  It may have unpredictable effects.  However,
if you wish to continue, you must first manually stop and disable the armui service and run this script again.
Doing so will erase your /opt/arm directory to install a fresh copy, and you may loose your configurations as
well. ${NC}"
      exit ${ERROR_FOUND_ACTIVE_ARMUI_SERVICE}
    fi

    Prompt="${YELLOW}WARNING, Found the armui service in SystemD but it is currently inactive.  Proceeding with this
installation may have unpredictable effects and is not recommended.

${BLUE}Do you wish to proceed? Y/n ${NC}"

    if IsUserAnsweredYesToPrompt "${Prompt}" ; then
      if [[ -d "/opt/arm" ]] ; then
        echo "Found Arm Installation Directory"
        AlertUserOfExistenceOfAmrDirectory="${YELLOW}WARNING, the script found that the directory /opt/arm already exists.
If you are attempting to update your arm installation, please us git to checkout the latest release.
In order to proceed, this script needs to delete the /opt/arm directory and checkout a fresh copy of arm
from the GitHub repository.  This is a non-reversible change.

${BLUE}Do you wish to Continue? Y/n :${NC}"
        if IsUserAnsweredYesToPrompt "${AlertUserOfExistenceOfAmrDirectory}" ; then
          PreviousInstallationFound=true
          AskUserIfConfigFilesShouldBeSetDefault="${BLUE} Keep existing A.R.M. config files? Y/n :${NC}"
          if IsUserAnsweredYesToPrompt "${AskUserIfConfigFilesShouldBeSetDefault}" ; then
            UseExistingConfigFiles=true
          fi
        else
          echo -e "${RED} Exiting Script...${NC}"
          exit ${ERROR_FOUND_ARM_DIRECTORY_COULD_NOT_PROCEED}
        fi
      fi
    else
      echo -e "${RED} Exiting Script...${NC}"
      exit ${ERROR_FOUND_INACTIVE_AMRUI_SERVICE_USER_DECLINED_TO_CONTINUE}
    fi
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
  if $NewUser ; then
    PasswordQuestion="${BLUE}Do you wish to provide a custom password for the 'arm' user? Y/n : ${NC}"
  else
    PasswordQuestion="${BLUE}The 'arm' user was already on the system.
Do you wish to change it's password? Y/n : ${NC}"
  fi
  local PasswordConfirmed=false
  if IsUserAnsweredYesToPrompt "${PasswordQuestion}" ; then
    #The User wishes to provide a custom password.  Give the user 3 times to provide one,
    #This attempt limit is to prevent an infinite loop.
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
    if ! $PasswordConfirmed ; then
      #This is the 3rd attempt.  Exit script.
      echo -e "${RED}\nThe Passwords did not match 3 consecutive times, exiting...\n${NC}"
      if $NewUser ; then
        echo -e "${YELLOW}Deleting newly created arm User Account.\n${NC}"
        DeleteArmUser
      else
        echo -e "${YELLOW}Password for the arm user was not changed.\n${NC}"
      fi
      exit ${ERROR_USER_PROVIDED_PASSWORD_MISMATCH}
    fi
  elif $NewUser; then
    echo -e "${YELLOW}Using default password '1234' it is recommended that you change it after script's completion. \n${NC}"
    Password_1=1234
    Password_2=1234
  fi
  if ($NewUser) || (! $NewUser && $PasswordConfirmed); then
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
  InstallMakeMKVBuildEnvironment
  BuildAndInstallMakeMKV
}

function InstallMakeMKVBuildEnvironment() {
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
  local ArmUserHomeFolder=~arm
  local LatestMakeMKVVersion
  local MakeMKVBuildFilesDirectory
  local cpuCount

  ArmUserHomeFolder=~arm
  LatestMakeMKVVersion=$(curl -s https://www.makemkv.com/download/ | grep -o '[0-9.]*.txt' | sed 's/.txt//')
  MakeMKVBuildFilesDirectory="${ArmUserHomeFolder}"/MakeMKVBuildFiles/"${LatestMakeMKVVersion}"
  cpuCount=$(nproc --all)

  mkdir -p "${MakeMKVBuildFilesDirectory}"
  cd "${MakeMKVBuildFilesDirectory}"
  curl -# -o makemkv-sha-"${LatestMakeMKVVersion}".txt  \
    https://www.makemkv.com/download/makemkv-sha-"${LatestMakeMKVVersion}".txt
  curl -# -o makemkv-bin-"${LatestMakeMKVVersion}".tar.gz \
    https://www.makemkv.com/download/makemkv-bin-"${LatestMakeMKVVersion}".tar.gz
  curl -# -o makemkv-oss-"${LatestMakeMKVVersion}".tar.gz \
    https://www.makemkv.com/download/makemkv-oss-"${LatestMakeMKVVersion}".tar.gz
  grep "makemkv-bin-${LatestMakeMKVVersion}.tar.gz" "makemkv-sha-${LatestMakeMKVVersion}.txt" | sha256sum -c
  grep "makemkv-oss-${LatestMakeMKVVersion}.tar.gz" "makemkv-sha-${LatestMakeMKVVersion}.txt" | sha256sum -c
  tar xzf makemkv-bin-"${LatestMakeMKVVersion}".tar.gz
  tar xzf makemkv-oss-"${LatestMakeMKVVersion}".tar.gz

  cd makemkv-oss-"${LatestMakeMKVVersion}"
  mkdir -p ./tmp
  ./configure >> /dev/null  2>&1
  make -s -j"${cpuCount}"
  make install

  cd ../makemkv-bin-"${LatestMakeMKVVersion}"
  mkdir -p ./tmp
  echo "yes" >> ./tmp/eula_accepted
  make -s -j"${cpuCount}"
  make install

  chown -R arm:arm "${MakeMKVBuildFilesDirectory}"
}

###################################################
#           Build & Install HandBrake             #
###################################################

function InstallHandBrakeCLI() {
  InstallHandBrakeCLIBuildEnvironment
  BuildAndInstallHandBrakeCLI
}

function InstallHandBrakeCLIBuildEnvironment() {
  apt install -y  autoconf \
                  automake \
                  build-essential \
                  cmake \
                  git \
                  libass-dev \
                  libbz2-dev \
                  libdrm-dev \
                  libfontconfig-dev \
                  libfreetype6-dev \
                  libfribidi-dev \
                  libharfbuzz-dev \
                  libjansson-dev \
                  liblzma-dev \
                  libmp3lame-dev \
                  libnuma-dev \
                  libogg-dev \
                  libopus-dev \
                  libsamplerate0-dev \
                  libspeex-dev \
                  libtheora-dev \
                  libtool \
                  libtool-bin \
                  libturbojpeg0-dev \
                  libva-dev \
                  libvorbis-dev \
                  libx264-dev \
                  libxml2-dev \
                  libvpx-dev \
                  m4 \
                  make \
                  meson \
                  nasm \
                  ninja-build \
                  patch \
                  pkg-config \
                  python3 \
                  tar \
                  zlib1g-dev
                  ## Note that the packages libva-dev and libdrm-dev are for Intel QuickSync Support only.
}

function BuildAndInstallHandBrakeCLI() {
  local ArmUserHomeFolder=~arm
  local HandBrakeCLIBuildFilesDirectory
  local cpuCount

  ArmUserHomeFolder=~arm
  HandBrakeCLIBuildFilesDirectory="${ArmUserHomeFolder}"/HandBrakeCLIBuildFiles/
  cpuCount=$(nproc --all)

  mkdir -p "${HandBrakeCLIBuildFilesDirectory}"
  cd "${HandBrakeCLIBuildFilesDirectory}"
  git clone https://github.com/HandBrake/HandBrake.git
  cd HandBrake
  ./configure --launch-jobs="${cpuCount}" --launch --enable-qsv --enable-vce --disable-gtk
  make --directory=build install
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
  local ExistingArmYamlFile
  local ExistingAbcdeConfFile
  local ExistingAppriseYamlFile

  #Get current version number of ARM
  if [[ ${Tag} == 'latest' ]] ; then
    Tag=$(curl --silent 'https://github.com/automatic-ripping-machine/automatic-ripping-machine/releases' \
                        | grep 'automatic-ripping-machine/tree/*' | head -n 1 | sed -e 's/[^0-9\.]*//g')
  fi

  cd /opt

  if $PreviousInstallationFound ; then

    ExistingArmYamlFile="/etc/arm/config/arm.yaml"
    ExistingAbcdeConfFile="/etc/arm/config/abcde.conf"
    ExistingAppriseYamlFile="/etc/arm/config/apprise.yaml"

    if [[ -f ${ExistingAbcdeConfFile} ]] && [[ "${UseExistingConfigFiles}" = false ]] ; then
      echo "Backing up ABCDE.conf"
      cp "${ExistingAbcdeConfFile}" "${ExistingAbcdeConfFile}.bck"
    fi

    if [[ -f ${ExistingArmYamlFile} ]] && [[ "${UseExistingConfigFiles}" = false ]] ; then
      echo "Backing up ARM.Yaml"
      cp "${ExistingArmYamlFile}" "${ExistingArmYamlFile}.bck"
    fi

    if [[ -f ${ExistingAppriseYamlFile} ]] && [[ "${UseExistingConfigFiles}" = false ]] ; then
      echo "Backing up Apprise.yaml"
      cp "${ExistingAppriseYamlFile}" "${ExistingAppriseYamlFile}.bck"
    fi

    echo -e "${RED} Deleting /opt/arm directory...${NC}"
    rm -R /opt/arm

  fi

  #Clone git repo, pin to latest release tag

  mkdir arm
  chown -R arm:arm arm

  sudo -u arm git clone --recurse-submodules --branch "${Tag}" \
    "https://github.com/${Fork}/automatic-ripping-machine"  arm


  #Copy clean copies of config files to etc folder.
  mkdir -p /etc/arm/config

  if ! $UseExistingConfigFiles ; then
    echo "Copying Clean Config Files"
    cp /opt/arm/setup/arm.yaml /etc/arm/config/arm.yaml
    cp /opt/arm/setup/apprise.yaml /etc/arm/config/apprise.yaml
    cp /opt/arm/setup/.abcde.conf /etc/arm/config/abcde.conf
  fi

  if $PortFlag ; then
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
        echo -e "${dev}    /mnt${dev}    udf,iso9660    users,noauto,exec,utf8    0    0 " | tee -a /etc/fstab
    fi
    mkdir -p "/mnt$dev"
  done
}

function SetupFolders() {
  sudo -u arm mkdir -p ~arm/logs/
  sudo -u arm mkdir -p ~arm/logs/progress/
  sudo -u arm mkdir -p ~arm/media/transcode/
  sudo -u arm mkdir -p ~arm/media/completed/
  sudo -u arm mkdir -p ~arm/media/raw/
}

function CreateAndStartService() {
  echo -e "${RED}Installing ARM service${NC}"
  cp /opt/arm/setup/arm.service /lib/systemd/system/armui.service
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
  echo "${site_addr}"
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

#######Inform the user that this is an unsupported installation method.  Inform them of the existence of the preferred
########method, being the Docker image.
UserAcceptedConditions

######Confirm tha the script was called with sudo or was run as root user.
IsEffectiveRootUser

#######Install Required Download Tools (wget, curl, lsb-release and git)
InstallDownloadTools

######Test for the existence of the repository, fork and tab/branch
RepositoryExists

#######Test to see if there is a previous installation of ARM
FoundPreviousInstallation

#Test the Linux Distribution, if Debian 12, confirm presence of Contribs repos, if not, Give
#User the option of attempting the installation anyway, even if it may fail.
#(Reason for target Distro of Debian 12, is because of the known presence of the required
#packages)
IsEligibleDistro

######Confirm existence of / create arm user and group
CreateArmUserAndGroup

#######Build and Install MakeMKV
InstallMakeMKV

#######Build and Install HandBrakeCLI  (The version packaged with Debian is OLD)
InstallHandBrakeCLI

#######Install Arm Dependencies
InstallArmDependencies

#######Install Arm
DownloadArm
CreatePythonVirtualEnvironmentAndInstallArmPythonDependencies

#######Post Arm Installation
CreateUDEVRules
MountDrives
SetupFolders
CreateAndStartService
LaunchSetup
