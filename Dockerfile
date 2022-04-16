###########################################################
# setup default directories and configs
FROM shitwolfymakes/arm-dependencies AS base

# override at runtime to match user that ARM runs as local user
ENV RUN_AS_USER=true
ENV UID=1000
ENV GID=1000

RUN \
    mkdir -m 0777 -p /home/arm /home/arm/config /mnt/dev/sr0 /mnt/dev/sr1 /mnt/dev/sr2 /mnt/dev/sr3 && \
    echo "/dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr1  /mnt/dev/sr1  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr2  /mnt/dev/sr2  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr3  /mnt/dev/sr3  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab

COPY . /opt/arm/
RUN rm -rf /opt/arm/venv

# Create our startup scripts
WORKDIR /opt/arm/scripts/docker
RUN mkdir -p /etc/my_init.d
COPY ./runit/start_aaudev.sh /etc/my_init.d/start_udev.sh
COPY ./runit/start_armui.sh /etc/my_init.d/start_armui.sh
COPY ./runit/docker-entrypoint.sh /etc/my_init.d/docker-entrypoint.sh

# We need to use a modified udev
COPY ./custom_udev /etc/init.d/udev
RUN chmod +x /etc/my_init.d/*.sh
WORKDIR /opt/arm

# Our docker udev rule
RUN ln -sv /opt/arm/setup/51-automedia-docker.rules /lib/udev/rules.d/

EXPOSE 8080

WORKDIR /opt/arm
VOLUME /home/arm/music
VOLUME /home/arm/logs
VOLUME /home/arm/media
VOLUME /etc/arm/config

###########################################################
# Final image pushed for use
FROM base as automatic-ripping-machine

CMD ["/sbin/my_init"]

LABEL org.opencontainers.image.source=https://github.com/1337-server/automatic-ripping-machine
LABEL org.opencontainers.image.license=MIT
