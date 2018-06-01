# Automatic Ripping Machine (ARM)

[![Build Status](https://travis-ci.org/automatic-ripping-machine/automatic-ripping-machine.svg?branch=v2_master)](https://travis-ci.org/automatic-ripping-machine/automatic-ripping-machine)

## Overview

Insert an optical disc (Blu-Ray, DVD, CD) and checks to see if it's audio, video (Movie or TV), or data, then rips it.

See: https://b3n.org/automatic-ripping-machine


## Features

- Detects insertion of disc using udev
- Determines disc type...
  - If video (Blu-Ray or DVD)
    - Retrieve title from disc or Windows Media MetaServices API to name the folder "movie title (year)" so that Plex or Emby can pick it up
    - Determine if video is Movie or TV using OMDb API
    - Rip using MakeMKV or HandBrake (can rip all features or main feature)
    - Eject disc and queue up Handbrake transcoding when done
    - Transcoding jobs are asynchronusly batched from ripping
    - Send notification when done via IFTTT or Pushbullet
  - If audio (CD) - rip using abcde
  - If data (Blu-Ray, DVD, or CD) - make an ISO backup
- Headless, designed to be run from a server
- Can rip from multiple-optical drives in parallel


## Requirements

- Ubuntu Server 18.04 (should work with other Linux distros)
- One or more optical drives to rip Blu-Rays, DVDs, and CDs
- Lots of drive space (I suggest using a NAS like FreeNAS) to store your movies

## Install

If you have a new DVD drive that you haven't used before, some require setting the region before they can play anything.  Be aware most DVD players only let you change the region a handful (4 or 5?) of times then lockout any further changes.  If your region is already set or you have a region free DVD drive you can skip this step.

    sudo apt-get install regionset
    sudo regionset /dev/sr0

Setup 'arm' user:

    sudo groupadd arm
    sudo useradd -m arm -g arm -G cdrom
    sudo passwd arm 
      <enter new password>

Set up repos and install dependencies

    sudo apt-get install git
    sudo add-apt-repository ppa:heyarje/makemkv-beta
    sudo add-apt-repository ppa:stebbins/handbrake-releases
    sudo add-apt-repository ppa:mc3man/xerus-media * for Ubuntu 16.04
    sudo add-apt-repository ppa:mc3man/bionic-prop # for Ubuntu 18.04
    sudo apt update
    sudo apt install makemkv-bin makemkv-oss
    sudo apt install handbrake-cli libavcodec-extra
    sudo apt install abcde flac imagemagick glyrc cdparanoia
    sudo apt install python3 python3-pip
    sudo apt-get install libcurl4-openssl-dev libssl-dev
    sudo apt-get install libdvd-pkg
    sudo dpkg-reconfigure libdvd-pkg
    sudo apt install default-jre-headless

Install and setup arm

    cd /opt
    sudo mkdir arm
    sudo chown arm:arm arm
    sudo chmod 775 arm
    git clone https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm
    cd arm
    # TODO: Remove below line before merging to master
    git checkout v2_master
    sudo pip3 install -r requirements.txt 
    sudo ln -s /opt/arm/setup/51-automedia.rules /lib/udev/rules.d/
    sudo cp /opt/arm/setup/arm@.service /etc/systemd/system/
    ln -s /opt/arm/setup/.abcde.conf ~/
    cp docs/arm.yaml.sample arm.yaml
    sudo mkdir /etc/arm/
    sudo ln -s /opt/arm/arm.yaml /etc/arm/

Set up drives

    Create mount point for each dvd drive.
    If you don't know the device name try running 'dmesg | grep -i dvd'.  The mountpoint needs to be /mnt/dev/<device name>.
    So if your device name is sr0, set the mountpoint with this command:
    sudo mkdir -p /mnt/dev/sr0
    Repeat this for each device you plan on using with arm.

    Create entries in /etc/fstab to allow non-root to mount dvd-roms
    Example (create for each optical drive you plan on using for ARM:
    /dev/sr0  /mnt/dev/sr0  udf,iso9660  user,noauto,exec,utf8  0  0

- Edit your "config" file (located at /opt/arm/arm.yaml) to determine what options you'd like to use.  Pay special attention to the 'directory setup' section and make sure the 'arm' user has write access to wherever you define these directories.

- To rip Blu-Rays after the MakeMKV trial is up you will need to purchase a license key or while MakeMKV is in BETA you can get a free key (which you will need to update from time to time) here:  https://www.makemkv.com/forum2/viewtopic.php?f=5&t=1053 and create /root/.MakeMKV/settings.conf with the contents:

        app_Key = "insertlicensekeyhere"

- For ARM to identify movie/tv titles register for an API key at OMDb API: http://www.omdbapi.com/apikey.aspx and set the OMDB_API_KEY parameter in the config file.

Optionally if you want something more stable than master you can download the latest release from the releases page.

After setup is complete reboot...
    
    reboot

## Usage

- Insert disc
- Wait for disc to eject
- Repeat

## Troubleshooting

Check log files located /home/arm/logs/ (unless this is changed in your arm.yaml file) to see if you can find where the script failed.  If you need any help feel free to open an issue.

## Contributing

Pull requests are welcome.

## License

[MIT License](LICENSE)
