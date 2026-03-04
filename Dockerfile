###########################################################
# ARM (neu) — Automatic Ripping Machine
#
# Base image:   docker build -t arm-base:latest docker/base/
# This image:   docker build -t arm:latest .
#
# The base image compiles MakeMKV from source
# and only needs rebuilding when that version changes.
###########################################################

ARG BASE_IMAGE=uprightbass360/arm-dependencies:latest
FROM ${BASE_IMAGE} AS base

LABEL org.opencontainers.image.source=https://github.com/uprightbass360/automatic-ripping-machine-neu
LABEL org.opencontainers.image.license=MIT
LABEL org.opencontainers.image.description='ARM (neu) — fully automated Blu-ray, DVD and audio disc ripping.'

EXPOSE 8080

# Setup mount points and fstab entries for optical drives
RUN \
    mkdir -m 0777 -p /home/arm \
    /home/arm/config /mnt/dev/sr0 \
    /mnt/dev/sr1 /mnt/dev/sr2 /mnt/dev/sr3 /mnt/dev/sr4 \
    /mnt/dev/sr5 /mnt/dev/sr6 /mnt/dev/sr7 /mnt/dev/sr8 \
    /mnt/dev/sr9 /mnt/dev/sr10 /mnt/dev/sr11 /mnt/dev/sr12 \
    /mnt/dev/sr13 /mnt/dev/sr14 /mnt/dev/sr15 /mnt/dev/sr16 \
    /mnt/dev/sr17 /mnt/dev/sr18 /mnt/dev/sr19 /mnt/dev/sr20 \
    && \
    for i in $(seq 0 20); do \
        echo "/dev/sr$i  /mnt/dev/sr$i  udf,iso9660  defaults,users,utf8,ro  0  0" >> /etc/fstab; \
    done

# Remove SSH (not needed in container) and create service dirs
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh \
    && mkdir /etc/service/armui \
    && mkdir -p /etc/my_init.d

# ARMui runit service
COPY ./scripts/docker/runsv/armui.sh /etc/service/armui/run

# Startup scripts
COPY ./scripts/docker/runit/arm_user_files_setup.sh /etc/my_init.d/arm_user_files_setup.sh
COPY ./scripts/docker/runit/start_udev.sh /etc/my_init.d/start_udev.sh

# Modified udev for container
COPY ./scripts/docker/custom_udev /etc/init.d/udev

RUN chmod +x /etc/service/armui/run /etc/my_init.d/*.sh /etc/init.d/udev

###########################################################
# Final image
FROM base AS automatic-ripping-machine

COPY . /opt/arm/

# Ensure Python deps are up-to-date, create udev symlink, allow git in container
RUN pip3 install --no-cache-dir -r /opt/arm/docker/base/requirements.txt \
    && ln -sv /opt/arm/setup/61-docker-arm.rules /lib/udev/rules.d/ \
    && git config --global --add safe.directory /opt/arm

CMD ["/sbin/my_init"]
WORKDIR /home/arm
