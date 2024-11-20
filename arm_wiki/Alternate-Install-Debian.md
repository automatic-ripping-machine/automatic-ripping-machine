# IMPORTANT

***
This installation method is not supported or maintained by the ARM Developers.
For full support and continued maintenance,
recommend installing ARM via the supported [Docker Container](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).
This installation guide has been left within the Wiki, as some users do not install via docker.

**Use at your own risk** 

***

## Manual Installation Guide

## Pre-Install (only if necessary)

If you have a new DVD drive that you haven't used before, some require setting the region before they can play anything.  Be aware most DVD players only let you change the region a handful (4 or 5?) of times, then lockout any further changes.  If your region is already set, or you have a region free DVD drive, you can skip this step.

```bash
sudo apt-get install regionset
sudo regionset /dev/sr0
```

## Install

**Setup 'arm' user and Ubuntu basics:**

Sets up graphics drivers, does Ubuntu update & Upgrade, gets Ubuntu to auto set up driver, and finally installs and setups up avahi-daemon
```
sudo groupadd arm
sudo useradd -m arm -g arm -G cdrom
sudo passwd arm
echo -e "${RED}Installing git${NC}"
sudo apt-get install git wget
sudo apt-get install build-essential pkg-config libc6-dev libssl-dev libexpat1-dev libavcodec-dev libgl1-mesa-dev qtbase5-dev zlib1g-dev

```

## Set up repos and install dependencies

```
mkdir /makeMKV
cd /makeMKV
# see https://forum.makemkv.com/forum/viewtopic.php?f=3&t=224 for latest version number replace 1.16.7 with latest version
wget https://www.makemkv.com/download/makemkv-bin-1.16.7.tar.gz
wget https://www.makemkv.com/download/makemkv-oss-1.16.7.tar.gz

echo -e "${RED}Extracting MakeMKV${NC}"
tar xvzf makemkv-oss-1.16.7.tar.gz
tar xvzf makemkv-bin-1.16.7.tar.gz

cd makemkv-oss-1.16.7
./configure
make
sudo make install

cd ../makemkv-bin-1.16.7
make
sudo make install
sudo apt install ffmpeg
sudo apt install handbrake-cli libavcodec-extra
sudo apt install libdvdcss2
sudo apt install abcde flac imagemagick glyrc cdparanoia
sudo apt install at
sudo apt install python3 python3-pip python3-libdiscid
sudo apt install libcurl4-openssl-dev libssl-dev  
sudo apt install libdvd-pkg
wget http://download.videolan.org/pub/debian/stable/libdvdcss2_1.2.13-0_amd64.deb
wget http://download.videolan.org/pub/debian/stable/libdvdcss_1.2.13-0.debian.tar.gz
wget http://ftp.us.debian.org/debian/pool/contrib/libd/libdvd-pkg/libdvd-pkg_1.4.0-1-2_all.deb
sudo dpkg -i libdvdcss2_1.2.13-0_amd64.deb
sudo dpkg -i libdvd-pkg_1.4.0-1-2_all.deb
sudo apt --fix-broken install
dpkg-reconfigure libdvd-pkg
sudo apt install default-jre-headless
sudo apt install eject

```

## Install and setup ARM

```
cd /opt
mkdir arm
chown arm:arm arm
chmod 775 arm
git clone https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm
chown -R arm:arm arm
cd arm
pip3 install setuptools
apt-get install python3-dev python3-pip python3-venv python3-wheel -y
pip3 install wheel
pip3 install -r requirements.txt 
ln -s /opt/arm/setup/51-automedia.rules /lib/udev/rules.d/
ln -s /opt/arm/setup/.abcde.conf /home/arm/
cp docs/arm.yaml.sample arm.yaml
sudo chown arm:arm arm.yaml
mkdir /etc/arm/
ln -s /opt/arm/arm.yaml /etc/arm/
sudo chmod +x /opt/arm/scripts/arm_wrapper.sh
sudo chmod +x /opt/arm/scripts/update_key.sh

```

## Set up drives

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
  OR as root
  ```
  echo -e "\n/dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8  0  0 \n" >> /etc/fstab
  ```

## Installing the ARMui service
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
#StandardOutput=append:/PATH-TO-MY-LOGFILES/WebUI.log
#StandardError=append:/PATH-TO-MY-LOGFILES/WebUI.log
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




Setup is almost complete! Reboot...

### Setting up the database
You will need to visit your http://WEBSERVER_IP:WEBSERVER_PORT/setup  
							&#x26A0; &#x26A0; **!!!WARNING!!!** &#x26A0; &#x26A0;  					

Visiting this page will delete your current database and create a new db file. You WILL lose jobs/tracks/etc from your database
This will setup the new database, and ask you to make an admin account. Because of the changes to the ARMui it's not possible to view/change/delete entries without logging in. 
Due to these large number of changes to the database it's not currently possible to upgrade without creating a new database, this may change later
but for now you will lose all previous jobs/tracks/configs.

Once it has deleted the current database, it will redirect you to sign in. The default username and password is

- Username: admin 
- Password: password


Alternatively, you can insert a disc or trigger it manually by running 
```
/usr/bin/python3 /opt/arm/arm/ripper/main.py -d sr0 | at now
```
in a terminal/ssh