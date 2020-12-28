# Automatic Ripping Machine (ARM)
[![Build Status](https://travis-ci.com/1337-server/automatic-ripping-machine.svg?branch=v2.3_dev)](https://travis-ci.com/1337-server/automatic-ripping-machine)
[![GitHub license](https://img.shields.io/github/license/1337-server/automatic-ripping-machine?style=plastic)](https://github.com/1337-server/automatic-ripping-machine/blob/v2.3_dev/LICENSE)
[![GitHub forks](https://img.shields.io/github/forks/1337-server/automatic-ripping-machine?style=plastic)](https://github.com/1337-server/automatic-ripping-machine/network)
[![GitHub stars](https://img.shields.io/github/stars/1337-server/automatic-ripping-machine?style=plastic)](https://github.com/1337-server/automatic-ripping-machine/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/1337-server/automatic-ripping-machine?style=plastic)](https://github.com/1337-server/automatic-ripping-machine/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/1337-server/automatic-ripping-machine?style=plastic)](https://github.com/1337-server/automatic-ripping-machine/issues)
[![Wiki](https://img.shields.io/badge/Wiki-Get%20Help-brightgreen?style=plastic)](https://github.com/1337-server/automatic-ripping-machine/wiki)
![GitHub contributors](https://img.shields.io/github/contributors/1337-server/automatic-ripping-machine?style=plastic)


![GitHub last commit](https://img.shields.io/github/last-commit/1337-server/automatic-ripping-machine)
![GitHub (Pre-)Release Date](https://img.shields.io/github/release-date-pre/1337-server/automatic-ripping-machine)


![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django?style=plastic)

## Overview

Insert an optical disc (Blu-Ray, DVD, CD) and checks to see if it's audio, video (Movie or TV), or data, then rips it.

See: https://b3n.org/automatic-ripping-machine


## Features

- Detects insertion of disc using udev
- Auto downloads keys_hashed.txt and KEYDB.cfg using robobrowser and tinydownloader
- Determines disc type...
  - If video (Blu-Ray or DVD)
    - Retrieve title from disc or OMdb API to name the folder "movie title (year)" so that Plex or Emby can pick it up
    - Determine if video is Movie or TV using OMDb API
    - Rip using MakeMKV or HandBrake (can rip all features or main feature)
    - Eject disc and queue up Handbrake transcoding when done
    - Transcoding jobs are asynchronusly batched from ripping
    - Send notification when done via IFTTT or Pushbullet
  - If audio (CD) - rip using abcde (get discdata and album art form musicbrainz)
  - If data (Blu-Ray, DVD, or CD) - make an ISO backup
- Headless, designed to be run from a server
- Can rip from multiple-optical drives in parallel
- HTML UI to interact with ripping jobs, view logs, etc



## Usage

- Insert disc
- Wait for disc to eject
- Repeat


## Requirements

- Ubuntu Server 18.04 (should work with other Linux distros) - Needs Multiverse and Universe repositories
- One or more optical drives to rip Blu-Rays, DVDs, and CDs
- Lots of drive space (I suggest using a NAS like FreeNAS) to store your movies


## Install
 Please see the [wiki](https://github.com/1337-server/automatic-ripping-machine/wiki/).

 
## Troubleshooting
 Please see the [wiki](https://github.com/1337-server/automatic-ripping-machine/wiki/).

[![Discord](https://img.shields.io/badge/discord-chat-7289DA.svg?maxAge=60)](https://discord.gg/rkEXY2Rbgn)
[![GitHub](https://img.shields.io/badge/github-issues-red.svg?maxAge=60)](https://github.com/Readarr/Readarr/issues)
[![Wiki](https://img.shields.io/badge/servarr-wiki-181717.svg?maxAge=60)](https://wiki.servarr.com/Readarr)

## Contributing

Pull requests are welcome.  Please see the [Contributing Guide](https://github.com/1337-server/automatic-ripping-machine/wiki/Contributing-Guide)

If you set ARM up in a different environment (harware/OS/virtual/etc), please consider submitting a howto to the [wiki](https://github.com/1337-server/automatic-ripping-machine/wiki/).

## License

[MIT License](LICENSE)
