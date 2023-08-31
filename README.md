# Automatic Ripping Machine (ARM)
[![CI](https://github.com/automatic-ripping-machine/automatic-ripping-machine/actions/workflows/main.yml/badge.svg)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/actions/workflows/main.yml)[![GitHub license](https://img.shields.io/github/license/automatic-ripping-machine/automatic-ripping-machine?style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/v2_devel/LICENSE)
[![GitHub forks](https://img.shields.io/github/forks/automatic-ripping-machine/automatic-ripping-machine?style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/network)
[![GitHub stars](https://img.shields.io/github/stars/automatic-ripping-machine/automatic-ripping-machine?style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/automatic-ripping-machine/automatic-ripping-machine?style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/automatic-ripping-machine/automatic-ripping-machine?style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/pulls)
[![Wiki](https://img.shields.io/badge/Wiki-Get%20Help-brightgreen?style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki)
[![GitHub contributors](https://img.shields.io/github/contributors/automatic-ripping-machine/automatic-ripping-machine?style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/graphs/contributors)
[![GitHub last commit](https://img.shields.io/github/last-commit/automatic-ripping-machine/automatic-ripping-machine?&style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/commits/v2_devel)

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/automatic-ripping-machine/automatic-ripping-machine?label=Latest%20Stable%20Version&style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/releases)
[![GitHub release Date](https://img.shields.io/github/release-date/automatic-ripping-machine/automatic-ripping-machine?label=Latest%20Stable%20Released&style=plastic)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/releases)

[![Docker](https://img.shields.io/docker/pulls/1337server/automatic-ripping-machine.svg)](https://hub.docker.com/r/1337server/automatic-ripping-machine)

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django?style=plastic)



## Overview

Insert an optical disc (Blu-Ray, DVD, CD) and checks to see if it's audio, video (Movie or TV), or data, then rips it.

See: https://b3n.org/automatic-ripping-machine


## Features

- Detects insertion of disc using udev
- Auto downloads keys_hashed.txt and KEYDB.cfg using robobrowser and tinydownloader
- Determines disc type...
  - If video (Blu-Ray or DVD)
    - Retrieve title from disc or [OMDb API](http://www.omdbapi.com/) to name the folder "Movie Title (Year)" so that Plex or Emby can pick it up
    - Determine if video is Movie or TV using [OMDb API](http://www.omdbapi.com/)
    - Rip using MakeMKV or HandBrake (can rip all features or main feature)
    - Eject disc and queue up Handbrake transcoding when done
    - Transcoding jobs are asynchronusly batched from ripping
    - Send notifications via IFTTT, Pushbullet, Slack, Discord, and many more!
  - If audio (CD) - rip using abcde (get discdata and album art from [musicbrainz](https://musicbrainz.org/))
  - If data (Blu-Ray, DVD, or CD) - make an ISO backup
- Headless, designed to be run from a server
- Can rip from multiple-optical drives in parallel
- Python Flask UI to interact with ripping jobs, view logs, update jobs, etc



## Usage

- Insert disc
- Wait for disc to eject
- Repeat


## Requirements

- Ubuntu Server 18.04 (should work with other Linux distros) - Needs Multiverse and Universe repositories
- One or more optical drives to rip Blu-rays, DVDs, and CDs
- Lots of drive space (I suggest using a NAS like FreeNAS) to store your movies


## Install

For normal install please see the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/).

For docker install please see [here](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).

## Troubleshooting
 Please see the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/).

## Contributing

Pull requests are welcome.  Please see the [Contributing Guide](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Contributing-Guide)

If you set ARM up in a different environment (harware/OS/virtual/etc), please consider submitting a howto to the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki).

### Icons:
This Project uses [ForkAwesome](https://forkaweso.me/Fork-Awesome/)!


## License

[MIT License](LICENSE)
