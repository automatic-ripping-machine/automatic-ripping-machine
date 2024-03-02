#!/usr/bin/env bash

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

dev_env_flag=
port_flag=
PORT=8080
pass=1234
UseSudo=false


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
      UseSudo=true
      true
      return
    fi
  fi
  false
}

if Has_Sudo_Privileges; then
  echo "Privileges Confirmed!!"
else
  echo "User does not have required privileges"
fi

if ${UseSudo}; then
  echo "Script will need to invoke Sudo for certain commands..."
else
  echo "SUDO use not required!!!!"
fi

