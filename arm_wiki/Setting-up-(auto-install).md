## Overview

There are various ways to setup ARM, the simplest would be to use the scripts inside the scrips folder. However these are not perfect and can sometimes fail.
The best way to setup ARM for a new user is to follow along from here [Debian](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Setting-up-ARM-manually-(Debian-OMV)) or [Ubuntu](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Setting-up-ARM-manually-(Ubuntu))

## Install Script For OpenMediaVault/Debian

**For the attended install use:**
 ```
 sudo apt install wget
 wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/v2_devel/scripts/debian-setup.sh
 sudo chmod +x debian-setup.sh
 sudo ./debian-setup.sh
 ```
 
 **For the silent install use**
  ```
 sudo apt -qqy install wget
 wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/v2_devel/scripts/deb-install-quiet.sh
 sudo chmod +x deb-install-quiet.sh
 sudo ./deb-install-quiet.sh
 ```

Then ```reboot```  to complete installation.


## Install Script For Ubuntu 20.04

 ```
sudo apt install wget
 wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/v2_devel/scripts/ubuntu-20.04-install.sh
sudo chmod +x ubuntu-20.04-install.sh
sudo ./ubuntu-20.04-install.sh
 ```

Then ```reboot```  to complete installation.