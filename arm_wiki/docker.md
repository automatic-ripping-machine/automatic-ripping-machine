## Installing ARM using Docker on Linux

### **This is not compatible with the snap version of docker!**

A pre-built image has been added to docker hub [HERE](https://hub.docker.com/repository/docker/automaticrippingmachine/automatic-ripping-machine).

## Installing Linux
- Select the option to install all third-party drivers
- Make sure the username is `arm`

## Prepare Linux
If running in a VM, make sure all disks are available to your distro via hardware passthrough in the VM Hypervisor software and confirm all drives are showing up by running `lsscsi -g`

**This script only supports Linux distros using the `apt` package manager.**

```
sudo apt install wget lsscsi
lsscsi -g
wget https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/scripts/docker-setup.sh
sudo chmod +x docker-setup.sh
```

## Setup ARM Docker
The script defaults to installing the `latest` tagged image from the `automaticrippingmachine` ARM from *DockerHub*.
- To specify a tag, add `-t <tag>`
- To specify a fork, add `-f <fork>`

To install default: `sudo ./docker-setup.sh`  
To install from a different repo, tag: `sudo ./docker-setup.sh -f automaticrippingmachine -t dev_build`

The script will now:
1. Create an `arm` user and group if they don't exist
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
     
    4. If the ARM group id is not 1000, enter that value for `ARM_GID`. If the returned value is 1000, delete that line from the script.
    
       Example: `-e ARM_GID="1001"`

    3. Fill in the appropriate paths for the volumes being mounted. Only change the path on the left hand side, docker volumes are configured with "[local path]:[arm path]".

       Example: `-v "/home/arm:/home/arm"`

    4. Fill in the list of CPU core threads to give the container in `--cpuset-cpus`. It's highly recommended to leave at least one core for the hypervisor to use, so the host machine doesn't get choked out during transcoding! Also, CPUs with multiple threads per core will be numbered in pairs. In the below example, only core #4 would be passed to ARM.
   
       Example: `--cpuset-cpus='5,6'`

   5. Set the name of the docker image, the default is below, but can be user configured.
      
      Example: `--name "automatic-ripping-machine"`
   
   5. Save and close


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

5. **Start ARM**: Run the container with `sudo ./start_arm_container.sh`

You will then need to visit http://WEBSERVER_IP:PORT
An admin account is required to view rips and settings. A default one has been created for you.

**Username**: admin

**Password**: password
