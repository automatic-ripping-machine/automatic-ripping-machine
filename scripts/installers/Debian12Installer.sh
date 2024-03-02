#!/usr/bin/env bash

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

dev_env_flag=
port_flag=
PORT=8080
pass=1234
Sudo_Flag=false

#---
# Function Definitions
#---

#This script requires elevated privileges.
#This function confirms that we can obtain needed privileges or that we already have them.
function Has_Sudo_Privileges() {
  #Is the script running as root (or effectively as root, meaning it was called with sudo)
  USERID=$(id -u)
  if [[ ${USERID} == 0 ]] ;  then
    true
    return
  else
    #Script was not run with elevated privileges, Request user for said privileges...
    #Ask for Sudo Access
    sudo -v -p 'Please Enter your SUDO Password: '
    SudoRequestResult=$?
    #Confirm we have Sudo Privileges...
    if [[ ${SudoRequestResult} == 0 ]] ; then
      Sudo_Flag=true
      true
      return
    fi
  fi
  false
}

#Confirm we can run this script.
if ! (Has_Sudo_Privileges); then
  echo -e "${RED}For this script to accomplish it's task, it requires elevated privileges.
The current user doesn't have Sudo rights.
Please contact an administrator to ask for Sudo rights or switch to a user with Sudo rights before running this script.${NC}"
  exit ${ERROR_INSUFFICIENT_USER_PRIVILEGES}
fi


