# Automatic bare metal installation on Debian Bookworm (12)



> [!CAUTION]
> This installation method is not supported or maintained by the ARM Developers.
> For full support and continued maintenance,
> we recommend installing ARM via the supported [Docker Container](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).
> This installation method was developed for those that wish to use ARM without Docker.
>
> **Use at your own risk** 

## Intended Linux Distributions
This method for installing A.R.M. has been tested using;
* Debian 12 (Bookworm) - *Fully Tested*
* Debian 11 (Bullseye) - *Should work*

While this method may work with other Linux distributions, your mileage may vary. 

## Intended Use
This installation guide, is created for a bare metal installation, while the script can be used on a 
virtual or containerized environment, the additional steps needed are not explained in this guide. For such environments
one must first make full and unrestricted access to the optical drives and optionally the graphics processor
(if Hardware Encoding is desired) to the environment before running this installation script.

> [!NOTE]
> The Script builds a MakeMKV and HandBrake on your system.  
> Building these applications is a processor intensive endeavour and may take a while complete, depending on your system.

## Installing A.R.M.
### Pre-Installation steps
1. Confirm the presence of the contrib repository to your `/etc/apt/sources.list` file
   * Please read the official [Debian Wiki](https://wiki.debian.org/SourcesList) for help on adding the contrib repository if needed.
2. Run `apt update && apt upgrade -y` to ensure your computer is up to date.  (if not root user, prefix the command with sudo `sudo update && sudo upgrade -y`
3. Install any third-party drivers (for example; NVidia, AMD or Intel graphics drivers)
4. Make sure that sudo is installed.  (Even if running this script as root, sudo is required, so that the script may run commands as the arm user.)
### Installation steps
If running as a root user remove the sudo calls.
1. Download the script.
   * `wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/scripts/installers/DebianInstaller.sh`
2. Make the script executable
   * `sudo chmod +x DebianInstaller.sh`
3. Execute the script
   * `sudo ./DebianInstaller.sh`
4. Accept the disclaimer.
5. Choose to enter a password for the arm user or accept the default. If you choose to enter a password, 
enter the password twice as prompted.
6. Navigate to your A.R.M. installation by navigating to the machine’s IP address, port 8080. `http://{MachineIP}:8080/` 
The default User is “`admin`”, and the default password is “`password`”

### Script Options
The script may be called with these options;

`./DebianInstaller.sh [-f <Fork_Name>] [-t <Tag_or_Branch_Name>] [-p <Port_Number>] [-h] [-H]`
* `[-f <Fork_Name>]`
  * Replace `<Fork Name>` with the name of the fork you wish to use for this installation. The default value is: automatic-ripping-machine
* `[-t <Tag_or_Branch_Name>]`
  * Replace `<Tag_or_Branch_Name>` with the name of the tag or branch you wish to use for this installation. The default value is: "latest" (Note that calling this script with a default value of fork and a tag value lower than 2.10.2 will result in an error that the script currently does not test for.)
* `[-p <Port_Number>]`
  * Replace `<Port_Number>` with any port number between 1 and 65535. The default value is: 8080
* `[-h]` or `[-H]`
  * Display the script’s usage instructions message.

### Script Exit Codes
If the script encounters an error, or exits without completing the installation of ARM it will generate an 
Exit Error Code of 0 or in the 200s. Values outside of that are likely the result of one of the numerous commands 
being called in the script exiting with its own Exit Code. To find which exit code the script produced, run `echo $?` 
after the script exists.

* 0– Either the script completed the installation successfully or the script was called with the `-h` or `-H` option 
which presented the user with the script’s usage instructions.
* 201 – The script was executed with insufficient privileges. Please run the script as root or using `sudo`...
* 202 – The user chose to enter a custom password for the arm user but failed to provide a valid password. 
(The script will ask the user to enter a password twice and will confirm that both times the password is identical. 
It allows the user 3 attempts. If after three attempts the passwords still do not match, the script exits with this 
error code)
* 203 – The script detected that the Linux distribution was not Debian 11 or 12, and the user chose to not continue 
with the installation.
* 204 – The script detected that this is a Debian Linux distribution but could not confirm the presence of the 
contribs repository. Please edit /etc/apt/sources.list and include the contrib repository. Instructions can be found 
[here](https://wiki.debian.org/SourcesList).
* 205 – The user did not accept the script disclaimer and the script exited.
* 206 – The script was called as root but could not find the presence of the “sudo” command. This command is required to 
complete the installation of A.R.M. Please run apt install sudo -y as root.
* 207 – The script was called with the `[-p {PortNumber}]` option, but the supplied port was not between 1024 and 65535
* 208 – The script was called with an unknown option and exited.
* 209 – The script found that /opt/arm directory existed, but the user declined to allow the script to delete it and 
proceed with a fresh installation of A.R.M. The script exited without installing A.R.M., but having installed MakeMKV 
and all of the Debian packages that are prerequisites.
* 211 – The script was called with the `[-f {ForkName}]` option, but the script could not confirm the existence of the 
fork. It looked for it on GitHub at: https://github.com/{ForkName}/automatic-ripping-machine
* 212 – The script was called with the `[-t {TagName}]` option, but the script could not confirm the existence of the 
tag or branch. It looked for it in the (named or default) fork on GitHub using the `git ls-remote` command.
* 213 – The script found that SystemD is currently running the armui service and that it is currently active.  To prevent errors, please turn off the service with `systemctl stop armui` The script cannot continue if the service is running.
* 214 – The installation script found that SystemD has a service loaded called armui but it is not currently running. However, the user chose to not proceed with the installation. 

## What the Automatic Installation Script does
The Automatic Installation Script completes the following tasks.
1. If the script was called with the `-p` option, verify that the provided port is valid.
2. Provides a disclaimer that the user must accept to run the script.
3. Checks that the script is run with necessary privileges (sudo or as root)
4. Checks that the “sudo” package is installed.
5. Install the following packages
    1. `curl` (necessary to download MakeMKV)
    2. `git` (necessary to download A.R.M.)
    3. `wget` (necessary to download A.R.M.)
    4. `lsb-release` (necessary to confirm which Linux distribution the script is running on)
6. Checks that the Linux Distribution is supported (If the distribution is not supported the script informs the user 
it is not and asks permission to proceed)
7. If it is a Debian (11 or 12) distribution, confirm the presence of the contrib repository.
8. Checks for the updates/contrib and security/contrib repositories, if they are missing inform the user and ask if they 
wish to proceed. These repositories are recommended but not necessary.
9. If the script was called using the `-f` and/or `-t` options it verifies that the fork and tag (or branch) exist 
and are accessible.
10. Checks for the presence of the arm user. If the arm user is present, give the user the option to change its password. 
If it is not present and the user declines to set a password the default password of ‘1234’ is set. 
It is recommended that this password be changed.
11. Installs the latest version of MakeMKV
    1. Installs the Debian packages necessary to build MakeMKV;
       1. `build-essential`
       2. `pkg-config`
       3. `libc6-dev`
       4. `libssl-dev`
       5. `libexpat1-dev`
       6. `libavcodec-dev`
       7. `libgl1-mesa-dev`
       8. `qtbase5-dev`
       9. `zlib1g-dev`
    2. Downloads the latest version of MakeMKV to `~arm/MakeMKVBuildFiles/{MakeMKVVersionNumber}/`
    Where ~arm is the home directory of the arm user.
    3. Extracts and builds MakeMKV, accepts the MakeMKV Eula
12. Install the A.R.M. Prerequisite Debian packages.
    1. `abcde`
    2. `at`
    3. `cdparanoia`
    4. `default-jre-headless`
    5. `eject`
    6. `ffmpeg`
    7. `flac`
    8. `glyrc`
    9. `handbrake-cli`
    10. `imagemagick`
    11. `libavcodec-extra`
    12. `libcurl4-openssl-dev`
    13. `libdvd-pkg`
    14. `libdvdcss2`
    15. `libssl-dev`
    16. `lsdvd`
    17. `python3`
    18. `python3-venv`
    19. `python3-libdiscid`
    20. `python3-pip`
13. Downloads A.R.M. If a fork or tag (branch) were specified, download the chosen version. 
If either fork or tag was not provided, use the default values (Default Fork: `automatic-ripping-machine`; 
Default Tag; `latest`) (“latest” will search Git Hub for the latest tagged release of A.R.M. and download that one.)
    1. If the `/opt/arm` folder exists, the script assumes that a pre-existing installation of A.R.M. is present. 
    It will ask the user permission to delete the folder (warning that this is a permanent change) before proceeding, 
    if permission is denied the script exits.
    2. The script will backup any config files found in `/etc/arm/config` to `/etc/arm/config/{filename}.bck` 
    **_WARNING_**, it will overwrite any `*.bck` files present)
    3. The script will make two copies of the config files, the regular ones and the `*.default` ones. 
    The default ones are there to allow the user to have a reference version if needed.
14. Creates a Python Virtual Environment in `/opt/arm/venv` and installs the necessary Python dependencies in the 
Virtual Environment.
15. Create the udev rule in `/lib/udev/rules.d/51-automatic-ripping-machine-venv.rules`
16. Create the necessary `/etc/fstab` entries to mount the optical drives to `/mnt/dev/sr#` 
(where # is replaced with the drive’s number)
17. Create the necessary folders in the `~arm` directory (where ~arm is the home directory of the arm user);
    1. `~arm/logs/`
    2. `~arm/logs/progress/`
    3. `~arm/media/transcode/`
    4. `~arm/media/completed/`
    5. `~arm/media/raw/`
18. Create the ArmUI service in `/lib/systemd/system/armui.service`
19. Start the service and enable it.
20. Run the setup by calling `http://{machineIP}:{ARMPort}/setup`
21. Provide a link for the user to access A.R.M. `http://{machineIP}:{ARMPort}/`
