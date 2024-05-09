## Overview

Insert an optical disc (Blu-ray, DVD, CD) and checks to see if it's audio, video (Movie or TV), or data, then rips it.

See: https://b3n.org/automatic-ripping-machine for a more detailed breakdown of how the project started.


## Supported Operating Systems

This is a small project with few maintainers. As such we do not have the time to support a large number of distributions, and system's are chosen for support by most common use. We officially support the following operating systems:
| Operating System | Versions     |
|------------------|--------------|
| Ubuntu Desktop   | 20.04 |

The current main development effort is going into the Docker container, for minimal issues in deployment and setup use the provided docker image.

Please note that if you open an issue to ask for help, if the OS you are using is not on this list you will be asked to reimage and try again or your issue will be closed.

If you use an unsupported operating system and can't or don't want to reimage, that's okay! Please try our [Docker image](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker) instead.


## Get Started
[Getting Started](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Getting-Started on your journey with ARM

## Current Features

- Detects insertion of disc using udev
- Determines disc type...
  - If video (Blu-ray or DVD)
    - Retrieve title from disc or OMdb API to name the folder "movie title (year)" so that Plex or Emby can pick it up
    - Determine if video is Movie or TV using OMDb API
    - Rip using MakeMKV or HandBrake (can rip all features or main feature)
    - Eject disc and queue up Handbrake transcoding when done
    - Transcoding jobs are asynchronously batched from ripping
    - Send notifications on updates via IFTTT, Pushbullet, Pushover, Discord, Slack, Telegram and many more!
  - If audio (CD) - rip using abcde  (get discdata and album art from musicbrainz)
  - If data (Blu-Ray, DVD, or CD) - make an ISO backup
- Headless, designed to be run from a server
- Ripping from multiple-optical drives in parallel
- HTML UI to interact with ripping jobs, view logs, etc
- Intel QuickSync support
- NVIDIA NVENC support
- AMD VCE support