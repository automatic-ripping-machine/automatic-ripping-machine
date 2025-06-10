# IMPORTANT: This installation method is no longer supported. Please install ARM as a [Docker Container](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker) instead

# Automatically Install ARM on Ubuntu 20.04
The ARM installation script supports both Ubuntu Desktop 20.04 and Ubuntu Server 20.04
Initial testing on 24.02 has been successful.

## Installing Ubuntu
- Select the option to install all third-party drivers
- Make sure the username is `arm`

## Prepare Ubuntu
If running Ubuntu in a VM, make sure all disks are available to Ubuntu via hardware passthrough in the VM Hypervisor software and confirm all drives are showing up by running `lsscsi -g`

```
sudo apt install wget lsscsi
lsscsi -g
wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/scripts/installers/DebianInstaller.sh
chmod +x installers/DebianInstaller.sh
```

## Install ARM
The script defaults to installing a live version of ARM~~~, but includes a `-d` flag that can be specified to install ARM in a development environment.~~~

To install ARM LIVE: `sudo ./DebianInstaller.sh`  
~~To install ARM DEV: `sudo ./ubuntu-20.04-install.sh -d`~~

After the script finishes, Firefox should open to `http:<machine_ip>:8080/setup` and prompt the user to create an admin account. If this doesn't happen, check the installer console log for error messages.

## Post Install - LIVE
No live-specific post installation steps are needed

## Post Install - DEV
1. Open Pycharm, and accept the User Agreement.
    1. If you want to install PyCharm Professional, run `sudo snap install pycharm-professional --classic`
    2. Select `Projects > Open`
    3. Open `/opt/arm`
    4. Select "Trust Project"
    5. When the Creating Virtual Environment popup appears, click "OK"
2. In the Project pane, open `/arm/ripper/main.py`
3. Scroll down to `if __name__ == "__main__":`
    1. Right click on the green arrow and select "Modify Run Configuration..."
    2. In Parameters, type `-d sr0`
    3. Click "OK"
4. Insert a disk into the drive and wait for Ubuntu to show it
5. In the upper right hand corner, click the green button to run or the green bug to run inside PyCharm's debugger

### Notes
If you terminate a debugging run early, run `mount /dev/sr0` to make sure the disk is mounted before the next run. ARM will break if the disk is not mounted. 

The default username and password is

- Username: admin 
- Password: password
