# Ubuntu Manual Install Guide

> [!CAUTION]
> This installation method is not supported or maintained by the ARM Developers.
> For full support and continued maintenance,
> we recommend installing ARM via the supported [Docker Container](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).
> This installation method was developed for those that wish to use ARM without Docker.
>
> **Use at your own risk** 

## Pre-Install (only if necessary)

If you have a new DVD drive that you haven't used before, some require setting the region before they can play anything.  Be aware most DVD players only let you change the region a handful (4 or 5?) of times then lockout any further changes.  If your region is already set or you have a region free DVD drive you can skip this step.

```bash
sudo apt-get install regionset
sudo regionset /dev/sr0
```

## Install

### Setup 'arm' user and ubuntu basics:

Sets up graphics drivers, does Ubuntu update & Upgrade, gets Ubuntu to auto set up driver, and finally installs and setups up avahi-daemon
```bash
sudo apt update -y && sudo apt upgrade -y 
***optional (was not required for me): sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt install avahi-daemon -y && sudo systemctl restart avahi-daemon
sudo apt install ubuntu-drivers-common -y && sudo ubuntu-drivers install 
sudo reboot
# Installation of drivers seems to install a full gnome desktop, and it seems to set up hibernation modes.
# It is optional to run the below line (Hibernation may be something you want.)
	sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
sudo groupadd arm
sudo useradd -m arm -g arm -G cdrom
sudo passwd arm 
  <enter new password>
```

### Set up repos and install dependencies

```bash
sudo apt-get install git lsdvd -y
sudo add-apt-repository ppa:heyarje/makemkv-beta

NumOnly=$(cut -f2 <<< `lsb_release -r`) && case $NumOnly in "16.04" ) sudo add-apt-repository ppa:mc3man/xerus-media;; "18.04" ) sudo add-apt-repository ppa:mc3man/bionic-prop;; "20.04" ) sudo add-apt-repository ppa:mc3man/focal6;; *) echo "error in finding release version";; esac

sudo apt update -y && \
sudo apt install makemkv-bin makemkv-oss -y && \
sudo apt install handbrake-cli libavcodec-extra -y && \
sudo apt install abcde flac imagemagick glyrc cdparanoia -y && \
sudo apt install at -y && \
sudo apt install python3 python3-pip -y && \
sudo apt-get install libcurl4-openssl-dev libssl-dev -y && \
sudo apt-get install libdvd-pkg -y && \
sudo dpkg-reconfigure libdvd-pkg && \
sudo apt install default-jre-headless -y
```

### Install and setup ARM

```bash
cd /opt
sudo mkdir arm
sudo chown arm:arm arm
sudo chmod 775 arm
sudo git clone --recurse-submodules https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm
sudo chown -R arm:arm arm
cd arm
sudo pip3 install -r requirements.txt 
sudo cp /opt/arm/setup/51-automedia.rules /etc/udev/rules.d/
sudo cp docs/arm.yaml.sample arm.yaml
sudo chown arm:arm arm.yaml
sudo mkdir /etc/arm/
sudo ln -s /opt/arm/arm.yaml /etc/arm/
sudo chmod +x /opt/arm/scripts/arm_wrapper.sh
sudo chmod +x /opt/arm/scripts/update_key.sh

cp --no-clobber "/opt/arm/setup/.abcde.conf" "/etc/.abcde.conf"
chown arm:arm "/etc/.abcde.conf"
sudo mkdir -p /etc/arm/config
su - arm -c "ln -sf /etc/.abdce.conf /etc/arm/config/abcde.conf"

```

### Set up drives

  Create a mount point for each dvd drive.
  If you don't know the device name, try running `dmesg | grep -i -E '\b(dvd|cd)\b'`.  The mountpoint needs to be /mnt/dev/<device name>.
  So if your device name is `sr0`, set the mountpoint with this command:
  ```bash
  sudo mkdir -p /mnt/dev/sr0
  ```
  Repeat this for each device you plan on using with ARM.

  Create entries in /etc/fstab to allow non-root to mount dvd-roms
  Example (create for each optical drive you plan on using for ARM):
  ```
  /dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8  0  0
  ```


### Installing the ARMui service

    
Create folders required to run the ARM service
```sudo -u arm mkdir -p /home/arm/logs```

Create a new service file
```sudo nano /etc/systemd/system/armui.service ``` 

Then put this in the file
```
[Unit]
Description=Arm service
## Added to force armui to wait for network
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=arm
Group=arm
## Add your path to your logfiles if you want to enable logging
## Remember to remove the # at the start of the line
#StandardOutput=append:/home/arm/logs/WebUI.log
#StandardError=append:/home/arm/logs/WebUI.log
Restart=always
RestartSec=3
ExecStart=python3 /opt/arm/arm/runui.py
[Install]
WantedBy=multi-user.target
```

Now we can reload the rules and start the arm service with
```
sudo systemctl daemon-reload
sudo systemctl enable armui
sudo systemctl start armui
```

Setup is now almost complete! Reboot...

## Post install
You may need to fix permissions in the arm home directory
`sudo chmod -R 775 /home/arm`
				
The default username and password is

- Username: admin 
- Password: password

Alternatively, you can insert a disc or trigger it manually by running 
```
/usr/bin/python3 /opt/arm/arm/ripper/main.py -d sr0 | at now
```
in a terminal/ssh