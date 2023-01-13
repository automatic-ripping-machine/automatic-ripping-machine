# Automatic Ripping Machine (ARM)
[![CI](https://github.com/1337-server/automatic-ripping-machine/actions/workflows/main.yml/badge.svg)](https://github.com/1337-server/automatic-ripping-machine/actions/workflows/main.yml) [![Publish Docker Image](https://github.com/1337-server/automatic-ripping-machine/actions/workflows/publish-image.yml/badge.svg)](https://github.com/1337-server/automatic-ripping-machine/actions/workflows/publish-image.yml)
[![Docker](https://img.shields.io/docker/pulls/1337server/automatic-ripping-machine.svg)](https://hub.docker.com/r/1337server/automatic-ripping-machine)

[![GitHub forks](https://img.shields.io/github/forks/1337-server/automatic-ripping-machine)](https://github.com/1337-server/automatic-ripping-machine/network)
[![GitHub stars](https://img.shields.io/github/stars/1337-server/automatic-ripping-machine)](https://github.com/1337-server/automatic-ripping-machine/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/1337-server/automatic-ripping-machine)](https://github.com/1337-server/automatic-ripping-machine/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/1337-server/automatic-ripping-machine)](https://github.com/1337-server/automatic-ripping-machine/pulls)
[![GitHub contributors](https://img.shields.io/github/contributors/1337-server/automatic-ripping-machine)](https://github.com/1337-server/automatic-ripping-machine/graphs/contributors)
[![GitHub last commit](https://img.shields.io/github/last-commit/1337-server/automatic-ripping-machine?)](https://github.com/1337-server/automatic-ripping-machine/commits/v2_devel)

[![GitHub license](https://img.shields.io/github/license/1337-server/automatic-ripping-machine)](https://github.com/1337-server/automatic-ripping-machine/blob/v2_devel/LICENSE)

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/1337-server/automatic-ripping-machine?label=Latest%20Stable%20Version)](https://github.com/1337-server/automatic-ripping-machine/releases)
[![GitHub release Date](https://img.shields.io/github/release-date/1337-server/automatic-ripping-machine?label=Latest%20Stable%20Released)](https://github.com/1337-server/automatic-ripping-machine/releases)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django)](https://github.com/automatic-ripping-machine/automatic-ripping-machine)


[![Wiki](https://img.shields.io/badge/Wiki-Get%20Help-brightgreen)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki)
[![Discord](https://img.shields.io/discord/576479573886107699)](https://discord.gg/FUSrn8jUcR)

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django)

## Overview

Insert an optical disc (Blu-ray, DVD, CD) and checks to see if it's audio, video (Movie or TV), or data, then rips it.

See: https://b3n.org/automatic-ripping-machine


## Features

- Detects insertion of disc using udev
- Determines disc type...
  - If video (Blu-ray or DVD)
    - Retrieve title from disc or [OMDb API](http://www.omdbapi.com/) to name the folder "Movie Title (Year)" so that Plex or Emby can pick it up
    - Determine if video is Movie or TV using [OMDb API](http://www.omdbapi.com/)
    - Rip using MakeMKV or HandBrake (can rip all features or main feature)
    - Eject disc and queue up Handbrake transcoding when done
    - Transcoding jobs are asynchronously batched from ripping
    - Send notifications via IFTTT, Pushbullet, Slack, Discord, and many more!
  - If audio (CD) - rip using abcde (get disc-data and album art from [musicbrainz](https://musicbrainz.org/))
  - If data (Blu-ray, DVD, or CD) - make an ISO backup
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

For normal installation please see the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/).

For docker installation please see [here](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).

## Troubleshooting
 Please see the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/).

## Contributing

Pull requests are welcome.  Please see the [Contributing Guide](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Contributing-Guide)

If you set ARM up in a different environment (hardware/OS/virtual/etc.), please consider submitting a howto to the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki).

## License

[MIT License](LICENSE)
