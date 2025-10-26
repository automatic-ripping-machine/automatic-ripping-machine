## Installing ARM using Docker on Linux

### **This is not compatible with the snap version of docker!**

A pre-built image has been added to docker hub [HERE](https://hub.docker.com/r/automaticrippingmachine/automatic-ripping-machine).

## Installing Linux
- Select the option to install all third-party drivers
- Make sure the username is `arm`

## Prepare Linux
If running in a VM, make sure all disks are available to your distro via hardware passthrough in the VM Hypervisor software and confirm all drives are showing up by running `lsscsi -g`

**This script only supports Linux distros using the `apt` package manager.**

```
sudo apt install wget lsscsi
lsscsi -g
wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/scripts/installers/docker-setup.sh
sudo chmod +x docker-setup.sh
```

## Setup ARM Docker
The script defaults to installing the `latest` tagged image from the `automaticrippingmachine` ARM from *DockerHub*.
- To specify a tag, add `-t <tag>`
- To specify a fork, add `-f <fork>`

To install default: `sudo ./docker-setup.sh`  
To install from a different repo, tag: `sudo ./docker-setup.sh -f automaticrippingmachine -t dev_build`

The script will now:
1. Create an `arm` user and group if they don't exist on the host
2. Install docker if it is not already found on the system
3. Pull the appropriate image from Dockerhub
4. Create host mountpoints for any DVD drives found on the system
5. Save a copy of the template run command for the user to fill in to `~arm/start_arm_container.sh`

## Post Install
1. **ARM User ID**: In a terminal session, type `id -u arm` and make a note of the returned value
2. **ARM Group ID**: In a terminal session, type `id -g arm` and make a note of the returned value
3. **Start Script**: Open up `start_arm_container.sh` in the text editor of your choice. 
    1. If the ARM user id is not 1000, enter that value for `ARM_UID`. If the returned value is 1000, delete that line from the script.
    
       Example: `-e ARM_UID="1001"` 
     
    2. If the ARM group id is not 1000, enter that value for `ARM_GID`. If the returned value is 1000, delete that line from the script.
    
       Example: `-e ARM_GID="1001"`

    3. To set the timezone, enter an acceptable value for `TZ`. If none is set, the default timezone is UTC.

       Example: -e `TZ=New_York`

    4. Fill in the appropriate paths for the volumes being mounted. Only change the path on the left hand side, docker volumes are configured with "[local path]:[arm path]". More information about volumes is found below under the heading: [Understanding Docker Volumes for A.R.M.](#understanding-docker-volumes-for-arm)

       Example: `-v "/home/arm:/home/arm"`

    5. Fill in your CD, DVD and Blu-Ray drives. Each `--device="/dev/sr0:/dev/sr0" \` line gives A.R.M. access to an optical drive.  To list all the drives (SSD, HD, Optical and others) found on your system, Run the command `lsscsi -g`.  For each Optical drive, the second column will have the "cd/dvd" entry, note the `/dev/sr#` (replace the pound sign # with the number) and add a device entry to your script.  By default, the script has `/dev/sr0` through `/dev/sr3` pre-entered.  Add or remove entries as necessary. You should have one entry for each "cd/dvd" that `lsscsi -g` finds.  

    6. Fill in the list of CPU core threads to give the container in `--cpuset-cpus`. It's highly recommended to leave at least one core for the hypervisor to use, so the host machine doesn't get choked out during transcoding! Also, CPUs with multiple threads per core will be numbered in pairs. In the below example, only core #4 would be passed to ARM.
   
       Example: `--cpuset-cpus='5,6'`

   7. Set the name of the docker image, the default is below, but can be user configured.
      
      Example: `--name "arm-rippers"`
   
   8. Save and close


4. **Permissions**: When starting the ARM docker container, if the ARM user ID and group ID from steps 1 and 2 are not set correctly ARM will not start. If the container does not start, check the docker logs.
   
   ```bash
   docker logs automatic-ripping-machine
   ```

    - If ARM has ownership, you'll see:
    ```
    Adding arm user to 'render' group
    Checking ownership of /home/arm
    [OK]: ARM UID and GID set correctly, ARM has access to '/home/arm' using 1001:1001
    Removing any link between music and Music
    Checking ownership of /etc/arm/config
    [OK]: ARM UID and GID set correctly, ARM has access to '/etc/arm/config' using 1001:1001
    Checking location of abcde configuration files
    ```
    - If ARM does not have ownership, you'll see:
    ```
    Removing any link between music and Music
    Checking ownership of /etc/arm
    ---------------------------------------------
    [ERROR]: ARM does not have permissions to /etc/arm using 1001:1001
    Check your user permissions and restart ARM
    Folder permissions--> 0:0
    ---------------------------------------------
    *** /etc/my_init.d/arm_user_files_setup.sh failed with status 1
    ```
   
   The script outputs the configuration it is expecting, the above error expects the UID and GID to both be '1001'. With the start script having set these values. However, ARM encountered the respective folder owned by root (0:0). To resolve this, ensure that the respective directories and sub-folders are owned by the correct user.

   This can be fixed by changing the ownership for the associated linked file. In the above example, the /etc/arm volume is linked to the /home/arm/config directory.

   ```bash
   sudo chown 1001:1001 -R /home/arm/config
   ```

   Additionally, any folders the container creates during startup will be owned by the user specified in `start_arm_container.sh`. If the folder paths passed to the container are on a remote share (SMB, NFS, etc.) and do not already exist, this may result in the folders on the share not being owned by the same user.

5. **Start ARM**: Run the container with `sudo ./start_arm_container.sh`

You will then need to visit http://WEBSERVER_IP:PORT
An admin account is required to view rips and settings. A default one has been created for you.

**Username**: admin

**Password**: password


## Updating docker image
Refer to [Docker Upgrading](Docker-Upgrading)

## Understanding Docker Volumes for A.R.M.

In the `start_arm_container.sh` script you will find these lines:
```
    -v "<path_to_arm_user_home_folder>:/home/arm" \
    -v "<path_to_music_folder>:/home/arm/music" \
    -v "<path_to_logs_folder>:/home/arm/logs" \
    -v "<path_to_media_folder>:/home/arm/media" \
    -v "<path_to_config_folder>:/etc/arm/config" \
```
These create volumes. What are volumes? They are easily accessible locations on your computer where you can access, delete, and change files that are accessible by the A.R.M. docker container.  They are also persistent, meaning that you can delete the docker image as many times as you want (probably to update your version of arm described in the [Updating docker image](#updating-docker-image) section above) without losing the contents of the volumes, as long as you rebuild the docker container (by re-running the `start_arm_container.sh` script) with these same volumes your previous settings, logs, database entries and completed rips will be there.  

### Explaining the different parts of the volume options

The script runs a single command, `docker run`  Each line corresponds to an option passed to the `docker run` command.  
* `-v` means you are telling `docker run` you wish to specify a volume.
* `"<path_to_arm_user_home_folder>:/home/arm"` is the volume description.  It takes the following form: "{Path_Outside_Of_Docker_Container}:{Path_Inside_Of_Docker_Container}" The script is pre-populated with the volumes needed by A.R.M.  If you fail to specify these volumes, the Docker will start but it will create temporary volumes that will be erased when the image is re-created.  So you are highly encouraged to specify them.
* `\` simply tells the computer that there are more lines to the `docker run` command

Before you run the `start_arm_container.sh` script, you must create the directories you specify on your computer, and these directories should be owned by the arm user and the arm group.

### The purpose of each A.R.M. volumes

Each volume specified in the default script is needed by A.R.M. The following is a short explanation of the purpose for each of the volumes.  Each explanation refers to the "{Path_Inside_Of_Docker_Container}" portion of each volume

* `/home/arm`
    * Is the home directory for the arm user.  This is where the different apps used by A.R.M. (HandBrake and MakeMKV) will store their settings files, It is also where A.R.M. will store its database files.
    * The default recommended is to use `/home/arm` for the "{Path_Outside_Of_Docker_Container}" of the volume definition.
* `/home/arm/music`
    * This is where A.R.M. will store completed rips from Music CDs.  You can specify any location on your computer.
    * The default recommended is: `/home/arm/music/` for the "{Path_Outside_Of_Docker_Container}" of the volume definition.
* `/home/arm/logs`
    * This is where A.R.M. will store the logs it creates.  It creates one new log file for each "job" it has (each disk it rips).
    * The default recommended is: `/home/arm/logs` for the "{Path_Outside_Of_Docker_Container}" of the volume definition.
* `/home/arm/media`
    * This is where A.R.M. will save your completed rips from DVDs and Blu-rays as well as Data Disk ISOs. A.R.M. will create subfolders in this directory, these are;
        * `raw` - Where A.R.M. temporarily saves the files created by MakeMKV
        * `transcode` - Where A.R.M. temporarily saves the files created by HandBrake
        * `completed` - Where A.R.M. moves the files when it completes the rip
    * It is strongly recommended that this volume has access to a large amount of fast (SSD) disk space.
    * The default suggested location is `/home/arm/media` for the "{Path_Outside_Of_Docker_Container}" of the volume definition.
* `/etc/arm/config`
    * This is where A.R.M. will look for the configuration files `arm.yaml`, `apprise.yaml` and `abcde.conf`. If the files are present it will use them, if they are not present A.R.M. will copy fresh copies with all the defaults and use those.  You can edit these files manually here or you can edit them in the A.R.M. web interface by clicking on the "Arm Settings" button on the toolbar.
    * The default suggested location is `/home/arm/config` for the "{Path_Outside_Of_Docker_Container}" of the volume definition.
 
### An Important note about permissions.

You can choose whichever location you want for each of these volumes. They can even be mounted in locations referring to network share. However, every one of these volumes _**MUST**_ be readable and writable by the arm user and group.  For simplicity, we strongly recommend that these folders be created as the `arm` user. (Log in to your machine, as the arm user, and create the folders, using the `mkdir` command.) If you are using all the suggested defaults, run these commands as the arm user:
```
mkdir /home/arm/logs
mkdir /home/arm/music
mkdir /home/arm/media
mkdir /home/arm/config
```
Then add these volumes to your `start_arm_container.sh` script like so.  
```
-v "/home/arm:/home/arm" \
-v "/home/arm/music:/home/arm/music" \
-v "/home/arm/logs:/home/arm/logs" \
-v "/home/arm/media:/home/arm/media" \
-v "/home/arm/config:/etc/arm/config" \
```

After that start the A.R.M. container as described above.

### Using Network Shares as volumes
If using network shares, be aware that the performance of your A.R.M. installation will be greatly affected by how fast it can read and write to the network share.  If you want to use a network share for the _completed_ rips, a suggestion could be to create a mount point _inside_ the volume...
*    `{media_volume_local_path}` is a location on the local machine running on Fast SSD and plenty of space (20+ gigabytes for each concurrent Dual Layer DVDs or 100 gigabytes for each concurrent 4k blu-rays)
*    `{media_volume_local_path}/completed` is a mounted network share (for example, pointing to a Plex, Emby or Jellyfin media library folder)

If using a network share for the `/home/arm` volume, read this [section](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Docker-Troubleshooting#my-volume-paths-point-to-a-cifs-mount---but-now-the-database-is-locked) from [Docker Troubleshooting](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Docker-Troubleshooting) 
