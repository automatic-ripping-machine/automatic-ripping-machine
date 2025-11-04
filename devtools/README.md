# Automatic Ripping Machine (ARM) - Development Tools

## Overview

Development tools to help automate testing and fault-finding when making changes the ARM main code.
Aim of this code is to be independent of the main ARM Repo, such that no libraries are pulled into support the test code. With the intent that it is possible to run the ARM Devtools as a standalone python script. This is to avoid introducing errors into the main code from the test tool.
Currently, a work in progress.

## Features

- Manage branch changes and the ARMUI
- Docker
    - Rebuild the docker image with updated ARM code
- Database management
    - Remove the database file, test running of ARM on a new system
- Quality Checks (runs Flake8 against all arm code)
- PR Checks
    - Run actions prior to commiting a PR
- Notification check, generate notifications to the UI


## Usage
```
$ ./armdevtools.py -h
usage: armdevtools.py [-h] [-b B] [-dr DR] [-db_rem] [-qa] [-pr] [-n] [-v]

Automatic Ripping Machine Development Tool Scripts. Note: scripts assume running on a bare
metal server when running, unless running the specific docker rebuild scripts.

options:
  -h, --help  show this help message and exit
  -b B        Name of the branch to move to, example -b bugfix_removecode
  -dr DR      Docker rebuild post ARM code update. Requires docker run script path to run.
  -db_rem     Database tool - remove current arm.db file
  -qa         QA Checks - run Flake8 against ARM
  -pr         Actions to run prior to committing a PR against ARM on github
  -n          Notification tool - show a test notification
  -v          ARM Dev Tools Version
``````

## Requirements

No unique requirements for devtools

## Install

No install required, once ARM installed

## Troubleshooting
 Please see the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/).

## Contributing

Pull requests are welcome.  Please see the [Contributing Guide](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Contributing-Guide)

If you set ARM up in a different environment (hardware/OS/virtual/etc.), please consider submitting a howto to the [wiki](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki).

## License

[MIT License](../LICENSE)
