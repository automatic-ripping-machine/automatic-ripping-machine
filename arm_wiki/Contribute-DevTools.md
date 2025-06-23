## Overview
To support development of ARM, some of the more tedious and repetitious development tasks have been wrapped up into the ARM Development Tools. The developer tools (devtools) are designed to help out anyone contributing to ARM and save time when testing out any changes being made.

To run devtools, navigate to the arm devtools folder and run the python file, armdevtools.py.

_Note: if the file is not executable, run `chown u+x armdevtools.py`_

`cd devtools`

## Running devtools

There are various commands available to the developer, as detailed below. The general output from the devtools follows:

```
INFO: <detail of the command being run>
INFO: Going to stop ARMUI - requesting sudo <requested to stop any ARM UI currently running>
INFO: ARM UI stopped    [Ok]
INFO: -------------------------------------
INFO: <command(s) the script runs>
INFO: <Script status on running the command_     [Ok]
INFO: -------------------------------------
INFO: <command(s) the script runs>
INFO: <Script status on running the command>     [Ok]
INFO: Going to restart ARMUI - requesting sudo _requested to restart the ARM UI_
INFO: ARM UI started    [Ok]
```

### [-h] Help
The below shows the list of available commands devtools provides.

```
./armdevtools.py -h
usage: armdevtools.py [-h] [-b B] [-dr DR] [-db_rem] [-qa] [-pr] [-v]

Automatic Ripping Machine Development Tool Scripts

options:
  -h, --help  show this help message and exit
  -b B        Name of the branch to move to, example -b bugfix_removecode
  -dr DR      Docker rebuild post ARM code update. Requires docker run script path to run.
  -db_rem     Database tool - remove current arm.db file
  -qa         QA Checks - run Flake8 against ARM
  -pr         Actions to run prior to committing a PR against ARM on github
  -v          ARM Dev Tools Version
```

### [-b B] Git branch change
Running this command provides a simple way to stop the ARM UI (if running on bare metal) and checkout a new branch. Whilst checking out a new git branch is a simple task, if the current ARM UI is not stopped prior to changing branches, strange things can occur. This script automates the change and aims to prevent spooky action at a distance.

```
./armdevtools.py -b bugfix_removecode
INFO: Change the current git branch to - bugfix_removecode
INFO: Going to stop ARMUI - requesting sudo
INFO: ARM UI stopped    [Ok]
M       arm-dependencies
Branch 'bugfix_removecode' set up to track remote branch 'bugfix_removecode' from 'origin'.
Switched to a new branch 'bugfix_removecode'
INFO: ARM branch: bugfix_removecode checked out
INFO: Going to restart ARMUI - requesting sudo
INFO: ARM UI started    [Ok]
```

### [-dr DR] Docker Rebuild
Following any code changes to ARM, testing the changes in the docker image can be a tedious process.
This command automates some of the process to make that change easier.
The script will stop the current container, remove the images (if specified), then restart the container.
The script requires passing in the ARM docker container start script, in the below example `~/start_arm_container.sh`

For more details on the docker run configuration, refer to [Building ARM docker image from source](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Building-ARM-docker-image-from-source)

_Note: executing this script requires the user to have docker permissions, otherwise it will fail._

Running this command executes the following docker commands.
1. Stops the ARM container
2. Removes the ARM container
3. Rebuilds the ARM container
4. Starts the ARM container, using the provided bash file/script

```
./armdevtools.py -dr ~/start_arm_container.sh
INFO: Going to stop ARMUI - requesting sudo
INFO: ARM UI stopped    [Ok]
INFO: Rebuilding docker image post ARM update
INFO: -------------------------------------
INFO: Executing: docker stop automatic-ripping-machine
Error response from daemon: No such container: automatic-ripping-machine
INFO: ARM container stopped     [Ok]
INFO: -------------------------------------
INFO: Executing: docker container rm automatic-ripping-machine
Error: No such container: automatic-ripping-machine
INFO: ARM Docker container deleted      [Ok]
INFO: -------------------------------------
INFO: Executing: docker build -t automatic-ripping-machine /opt/arm
Sending build context to Docker daemon   34.2MB
Step 1/21 : FROM automaticrippingmachine/arm-dependencies:1.1.1 AS base
 ---> 601d89529745
...
steps removed to reduce wiki size
...
Step 21/21 : WORKDIR /home/arm
 ---> Running in 6ed2590d5d46
Removing intermediate container 6ed2590d5d46
 ---> 58b643c79d04
Successfully built 58b643c79d04
Successfully tagged automatic-ripping-machine:latest
INFO: ARM Docker container rebuilt      [Ok]
INFO: -------------------------------------
INFO: Executing: ~/start_arm_container.sh
ec1f1c857f498c16f5149efaf305ed78828247577dd2c637c4c2bfd81525a449
INFO: ARM Docker container running      [Ok]
INFO: Going to restart ARMUI - requesting sudo
INFO: ARM UI started    [Ok]
```

### [-db_rem] Remove ARM Database
During development, there may come a time when testing requires removing the ARM database to confirm functionality and graceful exit states when no database exists. Whilst a simple command to remove the database, removing whilst ARM is running is not a good idea, again the whole spooky action at a distance. This command handles stopping the UI, removing the database and starting the UI again.

_Note: This command won't stop a docker container, and removing the ARM.db file whilst running is not a good idea._

_Note 2: Removing the arm.db file requires the user running the script to have ownership of the file, otherwise the script will fail._

```
./armdevtools.py -db_rem
INFO: Removing the ARM DB file
INFO: Going to stop ARMUI - requesting sudo
INFO: ARM UI stopped    [Ok]
INFO: ARM DB /home/arm/db/arm.db removed        [Ok]
INFO: Going to restart ARMUI - requesting sudo
INFO: ARM UI started    [Ok]
```


### [-qa] Run Flake8 Check
When a new commit is made against ARM, the [github workflows](https://github.com/automatic-ripping-machine/automatic-ripping-machine/tree/main/.github/workflows) are automatically run against the commit, to ensure the new codes quality and functionality. Running the QA check devtool command runs the same Flake8 check against the '/opt/arm' folder and files prior to commencing any commits and potentially failing the QA checks.
For more details of how Flake8 works can be found at [https://flake8.pycqa.org/en/latest/](https://flake8.pycqa.org/en/latest/).
Running the qa check executes the below command, and if all is good will return no results, as shown below.

`flake8 /opt/arm/arm --max-complexity=15 --max-line-length=120 --show-source --statistics`

```
./armdevtools.py -qa
INFO: Going to stop ARMUI - requesting sudo
INFO: ARM UI stopped    [Ok]
INFO: Running quality checks against ARM - /opt/arm
INFO: -------------------------------------
INFO: Executing: flake8 /opt/arm/arm --max-complexity=15 --max-line-length=120 --show-source --statistics
INFO: ARM QA check completed    [Ok]
INFO: Going to restart ARMUI - requesting sudo
INFO: ARM UI started    [Ok]
```

### [-pr] Pre-PR Actions
Executes a list of actions required to bring any ARM code up to scratch prior to raising a new PR.
Currently this runs:
- Update Git submodule (ARM dependencies)

```
./armdevtools.py -pr
INFO: Going to stop ARMUI - requesting sudo
INFO: ARM UI stopped    [Ok]
INFO: Running scripts to bring ARM up to date
INFO: -------------------------------------
INFO: Executing: cd .. & git submodule update --remote
remote: Enumerating objects: 7, done.
remote: Counting objects: 100% (7/7), done.
remote: Compressing objects: 100% (7/7), done.
remote: Total 7 (delta 2), reused 0 (delta 0), pack-reused 0
Unpacking objects: 100% (7/7), 3.01 KiB | 770.00 KiB/s, done.
From https://github.com/automatic-ripping-machine/arm-dependencies
 * [new branch]      dependabot/pip/sqlalchemy-2.0.6 -> origin/dependabot/pip/sqlalchemy-2.0.6
   6caa6fb..8029c3e  main                            -> origin/main
Successfully rebased and updated detached HEAD.
Submodule path '../arm-dependencies': rebased into '8029c3ebbe0406d07cf09e277eb17f6978986ee1'
INFO: ARM submodule updated     [Ok]
INFO: Going to restart ARMUI - requesting sudo
INFO: ARM UI started    [Ok]
```

### [-v] Devtools version
Reports the current version of devtools
```
./armdevtools.py -v
armdevtools.py 0.2
```