# Ubuntu 25.04 Manual Install Guide

> [!CAUTION]
> This installation method is not supported or maintained by the ARM Developers.
> For full support and continued maintenance,
> we recommend installing ARM via the supported [Docker Container](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).
> This installation method was developed for those that wish to use ARM without Docker.
>
> **Use at your own risk** 

This guide was tested starting from an Ubuntu 25.04 minimal installation, so it should cover installing all of the dependencies you would need with
any 25.04 install.

## Pre-Install (only if necessary)

If you have a new DVD drive that you haven't used before, some require setting the region before they can play anything.  Be aware most DVD players only let you change the region a handful (4 or 5?) of times then lockout any further changes.  If your region is already set or you have a region free DVD drive you can skip this step.

```bash
sudo apt-get install regionset
sudo regionset /dev/sr0
```

## Install

### Setup 'arm' user

Sets up the `arm` user that will run the ARM processes.
```bash
sudo groupadd arm
sudo useradd -m arm -g arm -G cdrom
```

### Set up repos and install dependencies

```bash
sudo add-apt-repository ppa:heyarje/makemkv-beta # add repository for makemkv binary
sudo apt update -y
sudo apt install git python3.13-venv libcurl4-gnutls-dev gcc python3-dev libffi-dev libdiscid0 handbrake-cli eject lsdvd at makemkv-bin
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
sudo cp /opt/arm/setup/51-automatic-ripping-machine-venv.rules /etc/udev/rules.d/
sudo chmod +x /opt/arm/scripts/thickclient/arm_venv_wrapper.sh
sudo cp setup/arm.yaml arm.yaml
sudo chown arm:arm arm.yaml
sudo mkdir -p /etc/arm/config
sudo ln -s /opt/arm/arm.yaml /etc/arm/config
sudo cp /opt/arm/setup/apprise.yaml /etc/arm/config
sudo cp --no-clobber /opt/arm/setup/.abcde.conf /etc/.abcde.conf
sudo chown arm:arm /etc/.abcde.conf
sudo ln -sf /etc/.abcde.conf /etc/arm/config/abcde.conf

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

    
Create folders required to run the ARM service:
```bash
sudo -u arm mkdir -p /home/arm/logs/progress
sudo -u arm mkdir -p /home/arm/media/raw
sudo -u arm mkdir -p /home/arm/media/transcode
sudo -u arm mkdir -p /home/arm/media/completed
```

Edit python dependencies to fix incompatibilities with latest Ubuntu. Some of the dependencies are too old to run with the latest Ubuntu,
but updating them to newer versions seems to work fine.

- Edit `/opt/arm/arm-dependencies/requirements.txt`
- Remove the version specifier for `cffi`
- Remove the version specifier for `SQLAlchemy`

Set up a python `venv` and install the necessary dependencies:
```bash
sudo -u arm bash
cd /opt/arm
python3 -m venv venv
source venv/bin/activate
pip install -r arm-dependencies/requirements.txt
```

Create the systemd service file
```
sudo cp /opt/arm/setup/armui.service /etc/systemd/system/armui.service
```

Now we can reload the rules and start the arm service with
```
sudo systemctl daemon-reload
sudo systemctl enable armui
sudo systemctl start armui
```

## Post install
You should now have the ARM UI running at http://localhost:8080

The default username and password is

- Username: admin 
- Password: password

Alternatively, you can insert a disc or trigger it manually by running 
```
/opt/arm/venv/bin/python3 /opt/arm/arm/ripper/main.py -d sr0 | at now
```
in a terminal/ssh
