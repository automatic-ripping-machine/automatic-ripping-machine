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
#Accepts one Parameter, error_code an integer representing the error code generated.
function usage() {
  local error_code=${1}
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


  case $error_code in
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
      echo -e "${RED}ERROR: The option that was passed to this script is unknown. Please used a valid option.${NC}" >&2
      echo -e "\n${UsageMessage}"
      ;;
    *)
      echo -e "${RED}ERROR: Unexpected error code: ${error_code}${NC}" >&2
      ;;
  esac

  #Exit the script using the supplied Error Code.
  exit "${error_code}"
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
    *)  usage ${ERROR_SCRIPT_UNKNOWN_OPTION} "${OPTION}"
        ;;
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
function user_accepted_conditions() {
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

  if ! is_user_answered_yes_to_prompt "${Disclaimer}" ; then
    echo -e "${RED} Exiting Installation Script, No changes were made...${NC}"
    exit ${ERROR_USER_DID_NOT_ACCEPT_SCRIPT_DISCLAIMER}
  fi
  return 0
}

#Function to confirm that the sudo package is installed. (Not eccentrically true for LXC containers.)
#Even running this script as an effective root user, the Sudo Command is still required for the script
#to run successfully.
#Return true or false
function is_sudo_installed() {
  if ! dpkg -s sudo > /dev/null 2>&1 ; then
    return 0
  else
    return 1
  fi
}

#Determine if we are effectively a root user.  Return boolean values 'true' or 'false'.
#If the function is about to return false, the function exits the script with the
#appropriate error code.
function is_effective_root_user() {
  USERID=$(id -u)
  if [[ ${USERID} == 0 ]] ;  then
    if is_sudo_installed ; then
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
  fi
  return 0
}

#If a Fork or Tag was passed to the script, we need to test for the existence of the fork and/or tag.
#If either do not exist, exit the script with an error code and message.
function repository_exists() {
  local not_found
  local git_hub_api_call
  local git_ls_remote_output
  local git_ls_remote_url

  if [[ "${Fork}" != "automatic-ripping-machine" ]] ; then
    echo "Custom Fork passed to the script, testing for existence..."
    not_found='"message": "Not Found",'
    git_hub_api_call="https://api.github.com/repos/${Fork}/automatic-ripping-machine"
    if [[ $(curl -s "${git_hub_api_call}" | grep -o "${not_found}") == "${not_found}" ]] ; then
      echo -e "${RED}The Fork ${Fork} was not found, exitring the script...${NC}\n"
      exit ${ERROR_GIT_REPO_FORK_DOES_NOT_EXIST}
    fi
  fi

  if [[ "${Tag}" != "latest" ]] ; then
    echo "Custom Tag passed to the script, testing for existence"
    git_ls_remote_url="https://github.com/${Fork}/automatic-ripping-machine.git"
    git_ls_remote_output=$(git ls-remote --quiet "${git_ls_remote_url}" "${Tag}")
    if [[ ${git_ls_remote_output} == "" ]] ; then
      echo -e "${RED}The Tag or Branch ${Tag} was not found, exiting the script...${NC}\n"
      exit ${ERROR_GIT_REPO_TAG_DOES_NOT_EXIST}
    fi
  fi
  return 0
}

function is_user_answered_yes_to_prompt() {
  local prompt=$1
  local response
  echo ""
  read -p "$(echo -e "${prompt}")" -r response
  echo -e ""
  if [[ "${response}" == "y" || "${response}" == "Y" ]] ; then
    echo ""
    return 0
  else
    echo ""
    return 1
  fi
}

function is_eligible_distro() {
  if ! is_debian_distro; then

    NotDebian12Prompt="${YELLOW}WARNING, you are attempting to run this script in a environment other than Debian 11 or 12
This script was tested exclusively on Debian 12 (Bookworm) and Debian 11 (Bullseye)
Running it on another Linux distro may have unpredictable side effects.

${BLUE}Do you wish to Continue? Y/n :${NC}"

    if is_user_answered_yes_to_prompt "${NotDebian12Prompt}" ; then
      echo -e "${YELLOW}Running Script in Linux Distro Other than Debian 12 (Bookworm)${NC}"
    else
      exit ${ERROR_ATTEMPTED_TO_RUN_SCRIPT_IN_UNTESTED_DISTRO}
    fi
  else
    #Confirm availability of contrib repository
    if ! is_contrib_repo_available ; then
      echo -e "${RED}One or more of the contrib repositories;
are missing please add them to your installation and run the script again.
You can learn how to add the necessary repository here: https://wiki.debian.org/SourcesList

Exiting....${NC}"
      exit ${ERROR_MISSING_CONTRIB_REPOSITORY}
    fi
  fi
  return 0
}

#Confirm this script is running on Debian 12 (Bookworm).  Return boolean values 'true' or 'false'.
function is_debian_distro() {
  LinuxDistribution=$(lsb_release -a | grep 'Distributor ID:' | awk '{print $3}')
  LinuxDistributionRelease=$(lsb_release -a | grep 'Release:' | awk '{print $2}')
  LinuxDistributionCodename=$(lsb_release -a | grep 'Codename:' | awk '{print $2}')
  if [[ ${LinuxDistribution} == "Debian" ]] ; then
    case ${LinuxDistributionRelease} in
      '11' | '12' )
        return 0
        ;;
      *)
        return 1
        ;;
    esac
  else
    return 1
  fi
}

#Confirm the presence of required package libraries.
function is_contrib_repo_available() {
  local includes_contrib=false
  local includes_updates_contrib=false
  local includes_security_contrib=false
  local prompt=""

  # Debian often exposes bookworm-updates as "stable-updates" (and bookworm as "stable") in Release metadata.
  # Accept both codename-based and stable-based suite names to avoid false negatives.
  _suite_regex() {
    local s="$1"
    case "$s" in
      "${LinuxDistributionCodename}") echo "^(${LinuxDistributionCodename}|stable)$" ;;
      "${LinuxDistributionCodename}-updates") echo "^(${LinuxDistributionCodename}-updates|stable-updates)$" ;;
      "${LinuxDistributionCodename}-security") echo "^(${LinuxDistributionCodename}-security|stable-security)$" ;;
      *) echo "^(${s})$" ;;
    esac
    return 0
  }

  # Preferred: ask APT what index targets it actually has configured.
  _apt_has_suite_component_indextargets() {
    local suite="$1"
    local component="$2"
    local suite_re
    suite_re="$(_suite_regex "$suite")"

    apt-get -o Debug::NoLocking=1 indextargets 2>/dev/null \
      | awk -v suite_re="$suite_re" -v comp_need="$component" '
          BEGIN { found=0; cod=""; sui=""; comp="" }
          $1=="Codename:"  { cod=$2 }
          $1=="Suite:"     { sui=$2 }
          $1=="Component:" { comp=$2 }
          /^$/ {
            if ((cod ~ suite_re || sui ~ suite_re) && comp==comp_need) found=1
            cod=""; sui=""; comp=""
          }
          END {
            if ((cod ~ suite_re || sui ~ suite_re) && comp==comp_need) found=1
            exit(found?0:1)
          }'
    return 0
  }

  # Fallback 1: parse deb822 sources (*.sources).
  _apt_has_suite_component_deb822() {
    local suite="$1"
    local component="$2"
    local suite_re
    suite_re="$(_suite_regex "$suite")"

    local files=()
    shopt -s nullglob
    files+=(/etc/apt/sources.list.d/*.sources)
    shopt -u nullglob

    [[ ${#files[@]} -eq 0 ]] && return 1

    awk -v suite_re="$suite_re" -v comp_need="$component" '
      BEGIN { found=0; suites=""; comps="" }
      /^[[:space:]]*Suites:[[:space:]]*/ {
        sub(/^[[:space:]]*Suites:[[:space:]]*/, "", $0)
        suites=$0
      }
      /^[[:space:]]*Components:[[:space:]]*/ {
        sub(/^[[:space:]]*Components:[[:space:]]*/, "", $0)
        comps=$0
      }
      /^$/ {
        if (suites != "" && comps != "") {
          n=split(suites, a, /[[:space:]]+/)
          m=split(comps,  b, /[[:space:]]+/)
          hasSuite=0; hasComp=0
          for (i=1;i<=n;i++) if (a[i] ~ suite_re) hasSuite=1
          for (j=1;j<=m;j++) if (b[j] == comp_need) hasComp=1
          if (hasSuite && hasComp) found=1
        }
        suites=""; comps=""
      }
      END {
        if (!found && suites != "" && comps != "") {
          n=split(suites, a, /[[:space:]]+/)
          m=split(comps,  b, /[[:space:]]+/)
          hasSuite=0; hasComp=0
          for (i=1;i<=n;i++) if (a[i] ~ suite_re) hasSuite=1
          for (j=1;j<=m;j++) if (b[j] == comp_need) hasComp=1
          if (hasSuite && hasComp) found=1
        }
        exit(found?0:1)
      }' "${files[@]}"
  }

  # Fallback 2: parse classic sources.list / *.list lines (deb ... suite components...).
  _apt_has_suite_component_list() {
    local suite="$1"
    local component="$2"
    local suite_re
    suite_re="$(_suite_regex "$suite")"

    local files=()
    shopt -s nullglob
    [[ -f /etc/apt/sources.list ]] && files+=(/etc/apt/sources.list)
    files+=(/etc/apt/sources.list.d/*.list)
    shopt -u nullglob

    [[ ${#files[@]} -eq 0 ]] && return 1

    awk -v suite_re="$suite_re" -v comp_need="$component" '
      function ok_suite(s) { return (s ~ suite_re) }
      function has_comp(start, end,   i) {
        for (i=start; i<=end; i++) if ($i == comp_need) return 1
        return 0
      }
      /^[[:space:]]*#/ { next }
      /^[[:space:]]*$/ { next }
      $1=="deb" || $1=="deb-src" {
        # format: deb [opts] uri suite comp1 comp2 ...
        # If [opts] exists, suite is field 4, else suite is field 3.
        suiteField=3
        if ($2 ~ /^\[/) suiteField=4
        s=$suiteField
        if (ok_suite(s) && has_comp(suiteField+1, NF)) { exit 0 }
      }
      END { exit 1 }' "${files[@]}"
  }

  _apt_has_suite_component() {
    local suite="$1"
    local component="$2"
    _apt_has_suite_component_indextargets "$suite" "$component" && return 0
    _apt_has_suite_component_deb822 "$suite" "$component" && return 0
    _apt_has_suite_component_list "$suite" "$component" && return 0
    return 1
  }

  ## TEST for the presence of the Repos.
  if _apt_has_suite_component "${LinuxDistributionCodename}" "contrib" ; then
    includes_contrib=true
  fi

  if _apt_has_suite_component "${LinuxDistributionCodename}-updates" "contrib" ; then
    includes_updates_contrib=true
  fi

  if _apt_has_suite_component "${LinuxDistributionCodename}-security" "contrib" ; then
    includes_security_contrib=true
  fi

  #The only required Repo is the Contrib repo.  Updates/Contrib and Security/Contrib are strongly recommended but not
  # required.  (This test is only relevant for Debian 12.  Since I did not find a way to test for Debian 11 and Debian 10
  # Does not appear to have a contrib repo...
  if $includes_contrib ; then

    #If this is Debian 12, test for the availability of the updates/contrib and security/contrib repos.
    if [[ "${LinuxDistributionRelease}" -eq 12 ]] ; then
      prompt=""

      if ! $includes_updates_contrib && ! $includes_security_contrib ; then
        echo -e "${RED}Missing ${LinuxDistributionCodename}-updates/contrib and ${LinuxDistributionCodename}-security/contrib repository.${NC}"
        prompt="${YELLOW}WARNING: The \"updates/contrib\" and \"security/contrib\" repositories are missing. It is recommended
that these repositories be present in order to keep A.R.M. dependencies up to date with the latest security fixes.

${BLUE}Do you wish to Continue? Y/n: ${NC}"
      elif ! $includes_updates_contrib ; then
        echo -e "${RED}Missing ${LinuxDistributionCodename}-updates/contrib repository.${NC}"
        prompt="${YELLOW}WARNING: The updates/contrib repository is missing. It is recommended that this repository
be present in order to keep A.R.M. dependencies up to date.

${BLUE}Do you wish to Continue? Y/n: ${NC}"
      elif ! $includes_security_contrib ; then
        echo -e "${RED}Missing ${LinuxDistributionCodename}-security/contrib repository.${NC}"
        prompt="${YELLOW}WARNING: The security/contrib repository is missing. It is recommended that this repository
be present in order to keep A.R.M. dependencies up to date with the latest security fixes.

${BLUE}Do you wish to Continue? Y/n: ${NC}"
      fi

      if [[ "${prompt}" == "" ]] || is_user_answered_yes_to_prompt "${prompt}" ; then
        true
      else
        false
      fi
    else
      true
    fi
  else
    echo -e "${RED}Missing ${LinuxDistributionCodename}/contrib repository.${NC}"
    false
  fi
}


function service_exists() {
    local service_name=$1
    if [[ $(systemctl list-units --all -t service --full --no-legend "$service_name.service" | sed 's/^\s*//g' | cut -f1 -d' ') == $service_name.service ]]; then
        return 0
    else
        return 1
    fi
}

function found_previous_installation() {
  ##TODO There is an error here that I need to track down.
  if service_exists armui  ; then
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

    prompt="${YELLOW}WARNING, Found the armui service in SystemD but it is currently inactive.  Proceeding with this
installation may have unpredictable effects and is not recommended.

${BLUE}Do you wish to proceed? Y/n ${NC}"

    if is_user_answered_yes_to_prompt "${prompt}" ; then
      if [[ -d "/opt/arm" ]] ; then
        echo "Found Arm Installation Directory"
        alert_user_of_existence_of_amr_directory="${YELLOW}WARNING, the script found that the directory /opt/arm already exists.
If you are attempting to update your arm installation, please us git to checkout the latest release.
In order to proceed, this script needs to delete the /opt/arm directory and checkout a fresh copy of arm
from the GitHub repository.  This is a non-reversible change.

${BLUE}Do you wish to Continue? Y/n :${NC}"
        if is_user_answered_yes_to_prompt "${alert_user_of_existence_of_amr_directory}" ; then
          PreviousInstallationFound=true
          AskUserIfConfigFilesShouldBeSetDefault="${BLUE} Keep existing A.R.M. config files? Y/n :${NC}"
          if is_user_answered_yes_to_prompt "${AskUserIfConfigFilesShouldBeSetDefault}" ; then
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


  return 0
}

###################################################
###################################################
#               Utility functions                 #
###################################################
###################################################

###################################################
#     User and Group related functions            #
###################################################

#Call all user and group related functions.
function create_arm_user_and_group() {
  echo -e "${YELLOW}Adding arm user & group${NC}"
  if (create_arm_group && create_arm_user) ; then
    password_protect_arm_user true
  else
    password_protect_arm_user false
  fi
  make_arm_user_part_of_required_groups
  return 0
}

#If the group exists, do nothing, if it does not exist create it.
function create_arm_group() {
  echo "Creating Groups...."
  if ! [[ $(getent group arm) ]]; then
    groupadd arm
    echo -e "${GREEN}Group 'arm' successfully created. \n${NC}"
    return 0
  else
    echo -e "${GREEN}'arm' group already exists, skipping...\n${NC}"
    return 1
  fi
}

#If user exists, do nothing, if it does not exist create the user with default settings.
function create_arm_user() {
  if ! id arm > /dev/null 2>&1 ; then
    useradd -m arm -g arm -s /bin/bash -c "Automatic Ripping Machine"
    echo -e "${GREEN}User 'arm' successfully created. \n${NC}"
    return 0
  else
    echo -e "${GREEN}'arm' user already exists, skipping creation...${NC}"
    return 1
  fi
}

function delete_arm_user() {
  userdel arm
  rm -R /home/arm
  return 0
}

# Make sure the 'arm' user is part of the 'cdrom', 'video' and 'render' groups.
function make_arm_user_part_of_required_groups() {
  usermod -aG cdrom,video,render arm
  return 0
}

#Give the User the option of setting a custom password.  The User may decline, in which event
#a default password of value '1234' is created.
#If the default password value is used, advise the user to change the password at the next opportunity.
function password_protect_arm_user() {
  local new_user=$1
  #Determine what the password is going to be and save it in the variables $password_1 & $password_2
  #Make these variables explicitly local, to prevent the variables escaping this function.
  local password_1=''
  local password_2=''
  if $new_user ; then
    PasswordQuestion="${BLUE}Do you wish to provide a custom password for the 'arm' user? Y/n : ${NC}"
  else
    PasswordQuestion="${BLUE}The 'arm' user was already on the system.
Do you wish to change it's password? Y/n : ${NC}"
  fi
  local password_confirmed=false
  if is_user_answered_yes_to_prompt "${PasswordQuestion}" ; then
    #The User wishes to provide a custom password.  Give the user 3 times to provide one,
    #This attempt limit is to prevent an infinite loop.
    for (( i = 0 ; i < 3 ; i++ )); do
      read -ep "$(echo -e "Please Enter Password? : ")" -r -s password_1
      read -ep "$(echo -e "Please Confirm Password? : ")" -r -s password_2
      if [[ "${password_1}" == "${password_2}" ]] ; then
        echo -e "\n${GREEN}Password matched, running \`passwd\` utility. \n${NC}"
        password_confirmed=true
        break;
      else
        echo -e "\n${YELLOW}Passwords do not match, please try again\n${NC}"
      fi
    done
    if ! $password_confirmed ; then
      #This is the 3rd attempt.  Exit script.
      echo -e "${RED}\nThe Passwords did not match 3 consecutive times, exiting...\n${NC}"
      if $new_user ; then
        echo -e "${YELLOW}Deleting newly created arm User Account.\n${NC}"
        delete_arm_user
      else
        echo -e "${YELLOW}Password for the arm user was not changed.\n${NC}"
      fi
      exit ${ERROR_USER_PROVIDED_PASSWORD_MISMATCH}
    fi
  elif $new_user; then
    echo -e "${YELLOW}Using default password '1234' it is recommended that you change it after script's completion. \n${NC}"
    password_1=1234
    password_2=1234
  fi
  if ($new_user) || (! $new_user && $password_confirmed); then
    echo -e "${password_1}\n${password_2}\n" | passwd -q arm > /dev/null 2>&1
  fi

  return 0
}

###################################################
#             Install Download Tools              #
###################################################

function install_download_tools () {
  apt update && apt install -y curl git wget lsb-release
  return 0
}

###################################################
#            Build & Install MakeMKV              #
###################################################

function install_make_mkv() {
  install_make_mkv_build_environment
  build_and_install_make_mkv
  return 0
}

function install_make_mkv_build_environment() {
  apt install -y  build-essential \
                  pkg-config \
                  libc6-dev \
                  libssl-dev \
                  libexpat1-dev \
                  libavcodec-dev \
                  libgl1-mesa-dev \
                  qtbase5-dev \
                  zlib1g-dev
  return 0
}

function build_and_install_make_mkv() {
  local arm_user_home_folder=~arm
  local latest_make_mkv_version
  local make_mkv_build_files_directory
  local cpu_count

  arm_user_home_folder=~arm
  latest_make_mkv_version=$(curl -s https://www.makemkv.com/download/ | grep -o '[0-9.]*.txt' | sed 's/.txt//')
  make_mkv_build_files_directory="${arm_user_home_folder}"/MakeMKVBuildFiles/"${latest_make_mkv_version}"
  cpu_count=$(nproc --all)

  mkdir -p "${make_mkv_build_files_directory}"
  cd "${make_mkv_build_files_directory}"
  curl -# -o makemkv-sha-"${latest_make_mkv_version}".txt  \
    https://www.makemkv.com/download/makemkv-sha-"${latest_make_mkv_version}".txt
  curl -# -o makemkv-bin-"${latest_make_mkv_version}".tar.gz \
    https://www.makemkv.com/download/makemkv-bin-"${latest_make_mkv_version}".tar.gz
  curl -# -o makemkv-oss-"${latest_make_mkv_version}".tar.gz \
    https://www.makemkv.com/download/makemkv-oss-"${latest_make_mkv_version}".tar.gz
  grep "makemkv-bin-${latest_make_mkv_version}.tar.gz" "makemkv-sha-${latest_make_mkv_version}.txt" | sha256sum -c
  grep "makemkv-oss-${latest_make_mkv_version}.tar.gz" "makemkv-sha-${latest_make_mkv_version}.txt" | sha256sum -c
  tar xzf makemkv-bin-"${latest_make_mkv_version}".tar.gz
  tar xzf makemkv-oss-"${latest_make_mkv_version}".tar.gz

  cd makemkv-oss-"${latest_make_mkv_version}"
  mkdir -p ./tmp
  ./configure >> /dev/null  2>&1
  make -s -j"${cpu_count}"
  make install

  cd ../makemkv-bin-"${latest_make_mkv_version}"
  mkdir -p ./tmp
  echo "yes" >> ./tmp/eula_accepted
  make -s -j"${cpu_count}"
  make install

  chown -R arm:arm "${make_mkv_build_files_directory}"
  return 0
}

###################################################
#           Build & Install HandBrake             #
###################################################

function install_hand_brake_cli() {
  install_hand_brake_cli_build_environment
  build_and_install_hand_brake_cli
  return 0
}

function install_hand_brake_cli_build_environment() {
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
  return 0
}

function build_and_install_hand_brake_cli() {
  local arm_user_home_folder=~arm
  local hand_brake_cli_build_files_directory
  local cpu_count

  arm_user_home_folder=~arm
  hand_brake_cli_build_files_directory="${arm_user_home_folder}"/HandBrakeCLIBuildFiles/
  cpu_count=$(nproc --all)

  mkdir -p "${hand_brake_cli_build_files_directory}"
  cd "${hand_brake_cli_build_files_directory}"
  git clone https://github.com/HandBrake/HandBrake.git
  cd HandBrake
  ./configure --launch-jobs="${cpu_count}" --launch --enable-qsv --enable-vce --disable-gtk
  make --directory=build install
  return 0
}

###################################################
#           Install Arm Dependencies              #
###################################################

function install_arm_dependencies() {
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
  return 0
}

###################################################
#                Download Arm                     #
###################################################

function download_arm () {
  local existing_arm_yaml_file
  local existing_abcde_conf_file
  local existing_apprise_yaml_file

  #Get current version number of ARM
  if [[ ${Tag} == 'latest' ]] ; then
    Tag=$(curl --silent 'https://github.com/automatic-ripping-machine/automatic-ripping-machine/releases' \
                        | grep 'automatic-ripping-machine/tree/*' | head -n 1 | sed -e 's/[^0-9\.]*//g')
  fi

  cd /opt

  if $PreviousInstallationFound ; then

    existing_arm_yaml_file="/etc/arm/config/arm.yaml"
    existing_abcde_conf_file="/etc/arm/config/abcde.conf"
    existing_apprise_yaml_file="/etc/arm/config/apprise.yaml"

    if [[ -f ${existing_abcde_conf_file} ]] && [[ "${UseExistingConfigFiles}" = false ]] ; then
      echo "Backing up ABCDE.conf"
      cp "${existing_abcde_conf_file}" "${existing_abcde_conf_file}.bck"
    fi

    if [[ -f ${existing_arm_yaml_file} ]] && [[ "${UseExistingConfigFiles}" = false ]] ; then
      echo "Backing up ARM.Yaml"
      cp "${existing_arm_yaml_file}" "${existing_arm_yaml_file}.bck"
    fi

    if [[ -f ${existing_apprise_yaml_file} ]] && [[ "${UseExistingConfigFiles}" = false ]] ; then
      echo "Backing up Apprise.yaml"
      cp "${existing_apprise_yaml_file}" "${existing_apprise_yaml_file}.bck"
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
  return 0
}

function create_python_venv_and_install_arm_python_deps() {
  cd /opt/arm
  sudo -u arm python3 -m venv venv
  sudo -u arm /opt/arm/venv/bin/pip3 install wheel
  sudo -u arm /opt/arm/venv/bin/pip3 install -r requirements.txt
  return 0
}

function create_udev_rules() {
  ln -sf /opt/arm/setup/51-automatic-ripping-machine-venv.rules /lib/udev/rules.d/
  return 0
}

function mount_drives() {
  ######## Adding new line to fstab, needed for the autoplay to work.
  ######## also creating mount points (why loop twice)
  echo -e "${RED}Adding fstab entry and creating mount points${NC}"
  for dev in /dev/sr?; do
    if grep -q "${dev}    /mnt${dev}    udf,iso9660    defaults,users,utf8,ro    0    0" /etc/fstab; then
        echo -e "${RED}fstab entry for ${dev} already exists. Skipping...${NC}"
    else
        echo -e "${dev}    /mnt${dev}    udf,iso9660    defaults,users,utf8,ro    0    0 " | tee -a /etc/fstab
    fi
    mkdir -p "/mnt$dev"
  done
  return 0
}

function setup_folders() {
  sudo -u arm mkdir -p ~arm/logs/
  sudo -u arm mkdir -p ~arm/logs/progress/
  sudo -u arm mkdir -p ~arm/media/transcode/
  sudo -u arm mkdir -p ~arm/media/completed/
  sudo -u arm mkdir -p ~arm/media/raw/
  return 0
}

function create_and_start_service() {
  echo -e "${RED}Installing ARM service${NC}"
  cp /opt/arm/setup/arm.service /lib/systemd/system/armui.service
  systemctl daemon-reload
  systemctl enable armui
  systemctl start armui
  return 0
}

function launch_setup() {
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
      echo -e "${RED}ERROR: ArmUI site is not running. Run \"sudo systemctl status armui\" to find out why${NC}" >&2
  else
      curl "http://${site_addr}/setup" -o /dev/null -s
      echo -e "${GREEN} Installation Complete
      Please click this link below to access your new Automatic Ripping Machine installation!
      http://${site_addr}${NC}\n"
  fi

  return 0
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
user_accepted_conditions

######Confirm tha the script was called with sudo or was run as root user.
is_effective_root_user

#######Install Required Download Tools (wget, curl, lsb-release and git)
install_download_tools

######Test for the existence of the repository, fork and tab/branch
repository_exists

#######Test to see if there is a previous installation of ARM
found_previous_installation

#Test the Linux Distribution, if Debian 12, confirm presence of Contribs repos, if not, Give
#User the option of attempting the installation anyway, even if it may fail.
#(Reason for target Distro of Debian 12, is because of the known presence of the required
#packages)
is_eligible_distro

######Confirm existence of / create arm user and group
create_arm_user_and_group

#######Build and Install MakeMKV
install_make_mkv

#######Build and Install HandBrakeCLI  (The version packaged with Debian is OLD)
install_hand_brake_cli

#######Install Arm Dependencies
install_arm_dependencies

#######Install Arm
download_arm
create_python_venv_and_install_arm_python_deps

#######Post Arm Installation
create_udev_rules
mount_drives
setup_folders
create_and_start_service
launch_setup
