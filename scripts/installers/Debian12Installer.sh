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

#This script requires elevated privileges.
#This function confirms that we can obtain needed privileges or that we already have them.
function Is_Effective_Root_User() {
  #Is the script running as root (or effectively as root, meaning it was called with sudo)
  USERID=$(id -u)
  if [[ ${USERID} == 0 ]] ;  then
    true
  else
    false
  fi
}

function add_arm_user() {
    echo -e "${YELLOW}Adding arm user & group${NC}"
    # create arm group if it doesn't already exist
    if ! [[ $(getent group arm) ]]; then
        if ${Sudo_Flag}; then
          sudo groupadd arm;
        else
          groupadd arm;
        fi
        echo -e "${YELLOW}Group 'arm' successfully created. \n${NC}"
    else
        echo -e "${YELLOW}arm group already exists, skipping...\n${NC}"
    fi

    # create arm user if it doesn't already exist
    if ! id arm > /dev/null 2>&1 ; then
      if ${Sudo_Flag}; then
        sudo useradd -m arm -g arm -s /bin/bash -c "Automatic Ripping Machine"
      else
        useradd -m arm -g arm -s /bin/bash -c "Automatic Ripping Machine"
      fi

      echo -e "${YELLOW}User 'arm' successfully created. \n${NC}"
      read -ep "$(echo -e "${YELLOW}Do you wish to provide a custom password for the 'arm' user? Y/n : ${NC}")" -r -n 1 UserWishesToEnterPassword
      if [[ "${UserWishesToEnterPassword}" == "y"  ||  "${UserWishesToEnterPassword}" == "Y" ]] ; then
        for (( i = 0 ; i < 3 ; i++ )); do
          read -ep "$(echo -e "${YELLOW}Please Enter Password? : ${NC}")" -r -s pass
          read -ep "$(echo -e "${YELLOW}Please Confirm Password? : ${NC}")" -r -s pass2
          if [[ "${pass}" == "${pass2}" ]] ; then
            break;
          elif [[ $i -eq 2 ]] ; then
            echo -e "${RED}\nThe Passwords did not match 3 consecutive times, exiting...\n"
            exit ${ERROR_USER_PROVIDED_PASSWORD_MISMATCH}
          else
            echo -e "\n${RED}Passwords do not match, please try again\n${NC}"
          fi
        done
      else
        echo -e "${YELLOW}Using default password '1234' it is recommended that you change it after script completion. \n${NC}"
        pass=1234
        pass2=1234
      fi

      if ${Sudo_Flag}; then
        echo -e "${pass}\n${pass2}\n" | sudo passwd -q arm
      else
        echo -e "${pass}\n${pass2}\n" | passwd -q arm
      fi

    else
        echo -e "${YELLOW}'arm' user already exists, skipping creation...${NC}"
    fi

    # Make sure the 'arm' user is part of the 'cdrom', 'video' and 'render' groups.
    if ${Sudo_Flag}; then
        sudo usermod -aG cdrom,video arm
      else
        usermod -aG cdrom,video arm
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
  sudo -v -p 'Please Enter your SUDO Password: '
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
add_arm_user

