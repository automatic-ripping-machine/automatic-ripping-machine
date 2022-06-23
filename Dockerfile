###########################################################
# setup default directories and configs
FROM 1337-server/arm-dependencies AS base

# Setup folders and fstab
RUN \
    mkdir -m 0777 -p /home/arm /home/arm/config /mnt/dev/sr0 /mnt/dev/sr1 /mnt/dev/sr2 /mnt/dev/sr3 && \
    echo "/dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr1  /mnt/dev/sr1  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr2  /mnt/dev/sr2  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr3  /mnt/dev/sr3  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab

# Copy over source code
COPY . /opt/arm/
RUN rm -rf /opt/arm/venv

# Remove SSH
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh

# Add ARMui service
RUN mkdir /etc/service/armui
COPY ./scripts/docker/runsv/armui.sh /etc/service/armui/run
RUN chmod +x /etc/service/armui/run

# Create our startup scripts
RUN mkdir -p /etc/my_init.d
COPY ./scripts/docker/runit/arm_user_files_setup.sh /etc/my_init.d/arm_user_files_setup.sh
COPY ./scripts/docker/runit/start_udev.sh /etc/my_init.d/start_udev.sh
RUN chmod +x /etc/my_init.d/*.sh

# We need to use a modified udev
COPY ./scripts/docker/custom_udev /etc/init.d/udev
RUN chmod +x /etc/my_init.d/*.sh

# Our docker udev rule
RUN ln -sv /opt/arm/setup/51-docker-arm.rules /lib/udev/rules.d/

EXPOSE 8080


###########################################################
# Final image pushed for use
FROM base as automatic-ripping-machine

CMD ["/sbin/my_init"]

LABEL org.opencontainers.image.source=https://github.com/1337-server/automatic-ripping-machine
LABEL org.opencontainers.image.license=MIT
