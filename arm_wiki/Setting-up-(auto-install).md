## Overview

There are various ways to setup ARM, the simplest would be to use the scripts inside the scrips folder. However these are not perfect and can sometimes fail.
The best way to setup ARM for a new user is to follow along from here [Debian](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Setting-up-ARM-manually-(Debian-OMV)) or [Ubuntu](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Setting-up-ARM-manually-(Ubuntu))

## Install Script For OpenMediaVault/Debian/Ubuntu 20, 22.04 24.02(Alpha)

**For the attended install use:**
 ```
 sudo apt install wget
 wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/scripts/installers/DebianInstaller.sh
 sudo chmod +x DebianInstaller.sh
 sudo ./DebianInstaller.sh
 ```

Then ```reboot```  to complete installation.
