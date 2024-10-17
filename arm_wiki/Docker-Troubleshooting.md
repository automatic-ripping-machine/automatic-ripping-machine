
# Troubleshooting

## Nothing happens when i insert a disc

For me personally i had to add the `--privileged` flag to my container for it to fully work, However i'm very new to docker there may be a better work around to get it to work. But this is how i got it working.

You can check if your udev rules are working on the host machine via linux logs 

`tail -f /var/log/syslog | grep ARM`

This should show when you insert a disc
```
xxx ARM: container 'arm-rippers' status: "Up 24 seconds"
xxx ARM: Starting rip
```
If it doesnt you udev isnt setup on the host machine.

## MakeMKV cant find drives
MakeMKV requires both drive identifiers to be passed into the container for example if `lsscsi -g` outputs

`cd/dvd  TEAC     DVD-ROM DV28SV   R.0C  /dev/sr0   /dev/sg5 `

You will need to add 
```
--device /dev/sr0
--device /dev/sg5
```
to the docker run command

Failing to do so may mean that the rest of ARM can find the drive but MakeMKV fails as it uses  SCSI commands to interact with the drive

## Docker is adding jobs but no files are created
Check the docker to make sure both the UID and GID match to a user outside the container, and the user has write permissions to the media directory.
You may need to chmod your media/music directories outside the container. 

## Changing where the docker puts files
**DO NOT try to change these paths in the arm.yaml** 

Instead change the containers volume paths. 
These can be changed to suit your needs
```
    -v "/my-music-path:/home/arm/Music" \
    -v "/my-config-path:/home/arm/config" \
    -v "/my-logs-path:/home/arm/logs" \
    -v "/my-media-path:/home/arm/media" \
```

## My volume paths point to a CIFS mount - but now the database is locked
This is caused by a byte-range lock on the mount by default.
To fix this, the CIFS mount of your host needs the `nobrl` flag. 

## NVENC doesn't work

Be sure that both variables for `NVIDIA_DRIVER_CAPABILITIES=all`
and `--gpus all` are set as NVENC won't work without them