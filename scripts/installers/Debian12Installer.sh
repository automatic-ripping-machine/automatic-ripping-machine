#!/usr/bin/env bash

#---
#Set Execution Environment
#---

#Run apt in non-interactive mode, assume default answers.
export DEBIAN_FRONTEND=noninteractive
#Cause the script to fail if and error code is provided (set -e)
#Cause the script to fail if an error code is provided while pipping commands (set -o pipefail)
#Cause the script to fail when encountering undefined variable (set -u)
#DEBUG MODE for Development only, Cause the script to print out every command executed (set -x)
set -u -o pipefail

#---
#Global Variables
#---

#Text Color and Formatting Variables
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

#Script Error Codes
ERROR_INSUFFICIENT_USER_PRIVILEGES=1
ERROR_USER_PROVIDED_PASSWORD_MISMATCH=2

#Script Variables
Sudo_Flag=false

#---
# Function Definitions
#---

###################################################
#         Script eligibility functions            #
###################################################

#Determine if we are effectively a root user.  Return boolean values 'true' or 'false'.
function Is_Effective_Root_User() {
  USERID=$(id -u)
  if [[ ${USERID} == 0 ]] ;  then
    true
  else
    false
  fi
}

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
    if ${Sudo_Flag}; then
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
    if ${Sudo_Flag}; then
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
  if ${Sudo_Flag}; then
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
  if ${Sudo_Flag}; then
    echo -e "${Password_1}\n${Password_2}\n" | sudo passwd -q arm
  else
    echo -e "${Password_1}\n${Password_2}\n" | passwd -q arm
  fi
}


#---
#Procedural Code Starts Here
#---

#Confirm we can run this script.
if ! (Is_Effective_Root_User); then
  #BASH has trouble setting Global Variables from inside functions, so we run this code procedurally :(
  #Script was not run with elevated privileges, Request user for said privileges...
  #Ask for Sudo Access
  sudo -v -p 'Please Enter your SUDO Password_1: '
  SudoRequestResult=$?
  #Confirm we have Sudo Privileges...
  if [[ ${SudoRequestResult} == 0 ]] ; then
    Sudo_Flag=true
    echo "Sudo Flag is ${Sudo_Flag}"
  else
    echo -e "${RED}For this script to accomplish it's task, it requires elevated privileges.
The current user doesn't have Sudo rights.
Please contact an administrator to ask for Sudo rights or switch to a user with Sudo rights before running this script.${NC}"
    exit ${ERROR_INSUFFICIENT_USER_PRIVILEGES}
  fi
fi

echo "Sudo Flag is ${Sudo_Flag}"

#Confirm existence of / create arm user and group
CreateArmUserAndGroup

