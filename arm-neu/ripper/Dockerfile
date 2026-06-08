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
COPY ./scripts/docker/runit/cleanup_orphaned_jobs.sh /etc/my_init.d/cleanup_orphaned_jobs.sh
COPY ./scripts/docker/runit/start_udev.sh /etc/my_init.d/start_udev.sh

# Modified udev for container
COPY ./scripts/docker/custom_udev /etc/init.d/udev
# Bake udev.conf with increased event_timeout (default 180s SIGKILL kills rips)
COPY ./setup/udev.conf /etc/udev/udev.conf

# Override base image healthcheck with faster hostname -i resolution
COPY ./docker/base/scripts/healthcheck.sh /healthcheck.sh
RUN chmod +x /etc/service/armui/run /etc/my_init.d/*.sh /etc/init.d/udev /healthcheck.sh
HEALTHCHECK --interval=30s --timeout=30s --start-period=90s --retries=5 CMD /healthcheck.sh

###########################################################
# Final image
FROM base AS automatic-ripping-machine

COPY . /opt/arm/
COPY --from=contracts . /opt/arm/components/contracts

# Ensure Python deps are up-to-date, install rsync for NFS-safe file transfer,
# create udev symlink, allow git in container
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends rsync \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir -r /opt/arm/docker/base/requirements.txt \
    && pip3 install --no-cache-dir -e /opt/arm/components/contracts \
    && ln -sv /opt/arm/setup/61-docker-arm.rules /lib/udev/rules.d/ \
    && git config --global --add safe.directory /opt/arm

# Stamp VERSION with the actual build identity so the running image can
# distinguish release / RC / dev builds in the Settings -> Versions panel.
# - Release workflow passes IMAGE_TAG=<version>           -> e.g. 17.3.0
# - RC workflow passes      IMAGE_TAG=<version>-rc        -> e.g. 17.3.0-rc
# - Local docker compose build with no arg                -> e.g. 17.3.0-dev
# Last layer on purpose: this changes per build but costs ~nothing to rerun.
ARG IMAGE_TAG=
RUN if [ -n "$IMAGE_TAG" ]; then \
        echo "$IMAGE_TAG" > /opt/arm/VERSION; \
    else \
        echo "$(cat /opt/arm/VERSION)-dev" > /opt/arm/VERSION; \
    fi

CMD ["/sbin/my_init"]
WORKDIR /home/arm
