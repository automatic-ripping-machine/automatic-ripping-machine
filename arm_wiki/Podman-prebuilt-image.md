Everything described in [the docker instructions](docker) is relevant, but this page is dedicated to podman quirks.
# Podman
Your first instinct when using Podman should be to run containers as rootless.
A typical container designed to work with rootless podman would run as root or a user inside the container, and inherit any non-root permissions of the host user running the pod. In the BEST-case scenario, the user inside the container would also be rootless, with means the host user is rootless and the container is rootless.
**Unfortunately this is not how ARM works, since it has been designed with Docker in mind, which runs as insecure root by default**, but efforts have been made to not run the scripts as root inside the container.
### podman root mode
This is how you should think of ARM from a security standpoint with podman. The classic Podman matrix where the bottom-right side is the most secure, and the upper left side is the least. **This doesn't really matter if youre just running this locally without network access**, but it gives you an idea of the expectations of permissions needed in the container image.

|                                 | Rootful Host (insecure)         | Rootless Host (more secure)|
| ------------------------------- | -----------------------------   | -------------------------- |
| Root in Container (insecure)    | ARM during container setup      |            ✖️              |
| Rootless Container (more secure)| ARM when running as `arm` user  |            ✖️              |

- ARM expects the host to have a user called `arm` on the host machine (the name does not matter! as long as you pass in the correct PID and GID, which is typically 1000 for the first user on the system)
- It expects the the mounted volumes like `media`, `logs`, `music`, `config` to be owned by this `arm` user.
- It expects the Container to be run as root (which ensures that the mapping of all GIDs and PIDs on the host machine map 1:1 with the container)
- It expects the `arm` user on the host to belong to the groups `cdrom,video` and `arm`.
- It expects there to be a corresponding directory for each ´/dev/sr*´ in the ´/mnt/dev/sr*´ on the host, owned by the `arm` user

**These requirements are basically what the `setup-docker.sh` script does (except creating directories for volumes you need)**

### Minimum podman 
```
# This assumes your cdrom is sr0
sudo podman run \
    -p "8080:8080" \
    -e ARM_UID="1000" \
    -e ARM_GID="1000" \
    -v /home/arm/content:/home/arm:Z \
    -v /home/arm/.config:/etc/arm/config:Z \
    --device /dev/sr0 \
    --restart always \
    --name arm \
    --cpuset-cpus='5,6' \
    docker.io/automaticrippingmachine/automatic-ripping-machine:latest


```

This assumes a file structure like so:
```
- /home/
  - arm/
    - .config/
    - content/
      - music/
      - media/
      - logs/
```
This aligns with podman's tendency to prefer to keep config inside the calling user's directories, rather than polluting and chaning ownership in the hosts `/etc` directory.

[Other ARM documentation](docker) recommends that you need to run the `lsscsi -g` and grab the corresponding sg* device for your sr* device and pass that in as well, but I have had no trouble running with only ´sr0´ device passed in. Your mileage may vary.


### Gotchas
#### cdrom permissions
If you're using Podman, chances are you're also using Fedora.
- Fedora maps the GID of `cdrom` to 11, while the container image (based on ubuntu) maps it to 24. This discrepancy should be taken care of in [newer images of ARM](https://github.com/automatic-ripping-machine/arm-dependencies/pull/512), but if you have permission issues, you can go into the the running image like so:

```
podman exec -it arm bash
```
then run 
```
ls -al /dev/sr0
```
This assumes your cdrom is `sr0` and your running container is named `arm`

If the group ownership has an 11 in it like so:
`brw-rw----. 1 root 11 11, 0 Feb  7 13:12 /dev/sr0`
it means the group was not mapped correctly.
Your best bet is to use the most recent ARM image, or create a new group on the host mapped to GID 24 and change the ownership of /dev/sr0 to this new user group. 
#### log permissions
For some reason the log files like `empty.log` and `arm.log` have sometimes been created with the root user rather than the `arm` user. If this happens you can fix this on the host machine by `chown arm:arm empty.log` and it should stop giving you errors.
