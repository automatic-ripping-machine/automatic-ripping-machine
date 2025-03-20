## Building an ARM Docker Image  

### :bangbang:This is not compatible with the snap version of docker!:bangbang:

This requires you to build an image from source. 

### Pre-requisites
1. Instructions tested based on a new Ubuntu 20.04 LTS minimal install 
2. Create the arm user and set a password
3. Install Docker, an editor such as Atom or VS Codium, lsscsi, and any other needed utilities as desired  
4. Setup all of your optical drives so that the arm (non-root) user can mount them. Run `lsscsi -g` to verify their mountpoints if you're unsure.  
  -run `sudo mkdir -p /mnt/dev/sr0` and repeat for each device, e.g., sr1, sr2, etc  
  -edit fstab and add an entry for each drive, incrementing the sr* number for each  
  `sudo nano /etc/fstab`     
  `/dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8  0  0`

### Add the arm user and group (Recommended)
This help with permission issues, and isolates A.R.M to its own user.
```
# Create the arm group
groupadd arm
# Create the arm user
useradd -m arm -g arm
# Set the new arm users password
passwd arm
# Add the user to the cdrom,video groups
usermod -aG cdrom,video arm
```

### Build the image:
`git clone https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm`  

`cd arm`

`docker build -t automatic-ripping-machine .`

### Create the container:
Remember to modify this for YOUR unique configuration!
 ```
docker run -d \
    -p "8080:8080" \
    -e ARM_UID="<id -u arm>" \
    -e ARM_GID="<id -g arm>" \
    -v "<path_to_arm_user_home_folder>:/home/arm" \
    -v "<path_to_music_folder>:/home/arm/Music" \
    -v "<path_to_logs_folder>:/home/arm/logs" \
    -v "<path_to_media_folder>:/home/arm/media" \
    -v "<path_to_config_folder>:/etc/arm/config" \
    --device="/dev/sr0:/dev/sr0" \
    --device="/dev/sr1:/dev/sr1" \
    --device="/dev/sr2:/dev/sr2" \
    --device="/dev/sr3:/dev/sr3" \
    --privileged \
    --restart "always" \
    --name "automatic-ripping-machine"
```
### Finally -  Open localhost:8080/setup, then login to the account

The default username and password:
username: admin
password: password

** It is strongly recommended you change this using the change password page **
A.R.M should now be fully setup, and ripping should start when a disc is inserted.

----

#### Notes
The ARM_UID(1000) and ARM_GID(1000) should exist outside the container. This helps against any permission issues.

It is recommended when passing in a device to pass in both labels you get from `lsscsi -g`
For example, if `lsscsi -g` outputs 

```
[2:0:0:0]    cd/dvd  NECVMWar VMware SATA CD00 1.00  /dev/sr0   /dev/sg1 
[32:0:0:0]   disk    VMware,  VMware Virtual S 1.0   /dev/sda   /dev/sg0 
```
You should pass in 
```
    --device="/dev/sr0:/dev/sr0" \
    --device="/dev/sg1:/dev/sg1" \
```
This isn't required, arm will still work, but it will not perform as well as it can.

### Troubleshooting
Please see the [docker troubleshooting page](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Docker-Troubleshooting)
