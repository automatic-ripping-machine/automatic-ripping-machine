###########################################################
# setup default directories and configs
FROM phusion/baseimage:jammy-1.0.4 AS base
LABEL org.opencontainers.image.source=https://github.com/automatic-ripping-machine/automatic-ripping-machine
LABEL org.opencontainers.image.license=MIT
LABEL org.opencontainers.image.description='Automatic Ripping Machine for fully automated Blu-ray, DVD and audio disc ripping.'

# start by updating and upgrading the OS
RUN \
    apt clean && \
    apt update && \
    apt upgrade -y -o Dpkg::Options::="--force-confold"
# create an arm group(gid 1000) and an arm user(uid 1000), with password logon disabled
RUN groupadd -g 1000 arm \
    && useradd -rm -d /home/arm -s /bin/bash -g arm -G video,cdrom -u 1000 arm

# enable support for Arch Linux and derivatives, who use a different user group for optical drive permissions
RUN groupadd -g 990 optical \
    && usermod -aG optical arm

# set the default environment variables
# UID and GID are not settable as of https://github.com/phusion/baseimage-docker/pull/86, as doing so would
# break multi-account containers
ENV ARM_UID=1000
ENV ARM_GID=1000


EXPOSE 81
EXPOSE 80
ENV MYSQL_USER=root
ENV MYSQL_PASSWORD=example
ENV MYSQL_IP=127.0.0.1

# Setup folders and fstab
RUN \
    mkdir -m 0777 -p /home/arm \
    /home/arm/config /mnt/dev/sr0 \
    /mnt/dev/sr1 /mnt/dev/sr2 /mnt/dev/sr3 /mnt/dev/sr4 \
    /mnt/dev/sr5 /mnt/dev/sr6 /mnt/dev/sr7 /mnt/dev/sr8 \
    /mnt/dev/sr9 /mnt/dev/sr10 /mnt/dev/sr11 /mnt/dev/sr12 \
    /mnt/dev/sr13 /mnt/dev/sr14 /mnt/dev/sr15 /mnt/dev/sr16 \
    /mnt/dev/sr17 /mnt/dev/sr18 /mnt/dev/sr19 /mnt/dev/sr20 \
    && \
    echo "/dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr1  /mnt/dev/sr1  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr2  /mnt/dev/sr2  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr3  /mnt/dev/sr3  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr4  /mnt/dev/sr4  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr5  /mnt/dev/sr5  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr6  /mnt/dev/sr6  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr7  /mnt/dev/sr7  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr8  /mnt/dev/sr8  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr9  /mnt/dev/sr9  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr10  /mnt/dev/sr10  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr11  /mnt/dev/sr11  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr12  /mnt/dev/sr12  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr13  /mnt/dev/sr13  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr14  /mnt/dev/sr14  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr15  /mnt/dev/sr15  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr16  /mnt/dev/sr16  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr17  /mnt/dev/sr17  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr18  /mnt/dev/sr18  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr19  /mnt/dev/sr19  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr20  /mnt/dev/sr20  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab


# Remove SSH
RUN rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh

# setup gnupg/wget for add-ppa.sh
RUN apt update && apt install -y \
        ca-certificates \
        git \
        wget \
        curl \
        build-essential \
        libcurl4-openssl-dev \
        libssl-dev \
        gnupg \
        libudev-dev \
        udev \
        python3 \
        python3-dev \
        python3-pip \
        nano \
        # arm extra requirements
        scons swig libzbar-dev libzbar0 \
        curl sudo nginx \
        default-libmysqlclient-dev && apt clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY api/requirements.txt /app/api/requirements.txt
RUN pip3 install --upgrade pip wheel setuptools psutil pyudev \
    && pip3 install --no-cache-dir --upgrade -r /app/api/requirements.txt
# Create our startup scripts
RUN mkdir -p /etc/my_init.d
COPY ./scripts/docker/runit/arm_user_files_setup.sh /etc/my_init.d/arm_user_files_setup.sh
COPY ./scripts/docker/runit/arm_start_udev.sh /etc/my_init.d/arm_start_udev.sh
COPY ./scripts/docker/runit/arma_vuejs.sh /etc/my_init.d/armvueui.sh
COPY ./scripts/docker/runit/fast_api.sh /etc/my_init.d/fast_api.sh
RUN chmod +x /etc/my_init.d/*.sh

# We need to use a modified udev
COPY ./scripts/docker/custom_udev /etc/init.d/udev
RUN chmod +x /etc/my_init.d/*.sh

########################################### build arm vuejs ############################################################
# Node
FROM base AS build-ui

RUN set -uex; \
    apt-get update; \
    mkdir -p /etc/apt/keyrings; \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
     | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg; \
    NODE_MAJOR=18; \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" \
     > /etc/apt/sources.list.d/nodesource.list; \
    apt-get update; \
    apt-get install nodejs -y;

WORKDIR /app
COPY vuejs /app/vuejs
WORKDIR /app/vuejs
RUN npm install
RUN ls -la ./
RUN npm run build

###########################   BUILD HANDBRAKE AND MAKEMKV   ############################################################
FROM base AS install-makemkv-handbrake
###########################################################
# install makemkv and handbrake
COPY ./scripts/install_mkv_hb_deps.sh /install_mkv_hb_deps.sh
RUN chmod +x /install_mkv_hb_deps.sh && sleep 1 && \
    /install_mkv_hb_deps.sh

COPY ./scripts/install_handbrake.sh /install_handbrake.sh
RUN chmod +x /install_handbrake.sh && sleep 1 && \
    /install_handbrake.sh

# MakeMKV setup by https://github.com/tianon
COPY ./scripts/install_makemkv.sh /install_makemkv.sh
RUN chmod +x /install_makemkv.sh && sleep 1 && \
    /install_makemkv.sh

# clean up apt
RUN apt clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

###########################################################
# Final image pushed for use
FROM base AS automatic-ripping-machine

COPY --from=build-ui /app/vuejs/dist/ /var/www/html
# Copy HandBrake binary and necessary files from builder
COPY --from=install-makemkv-handbrake /usr/local/bin/HandBrakeCLI /usr/local/bin/HandBrakeCLI
# Copy MakeMKV binaries from builder
COPY --from=install-makemkv-handbrake /usr/local/bin /usr/local/bin
COPY --from=install-makemkv-handbrake /usr/local/lib /usr/local/lib
COPY --from=install-makemkv-handbrake /usr/local/share /usr/local/share

# Set library path
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Install runtime dependencies for MakeMKV
RUN apt-get update && apt-get install -y \
    libssl3  \
    libbz2-1.0  \
    zlib1g  \
    libexpat1  \
    libc6  \
    libstdc++6 \
    liblzma5  \
    libnuma1  \
    libqt5core5a  \
    libqt5gui5  \
    libqt5widgets5 \
    libqt5network5 \
    libqt5dbus5 \
    libavcodec58 \
    libavutil56 \
    libswresample3 \
    libswscale5 \
    libavformat58 \
    libavfilter7 \
    && rm -rf /var/lib/apt/lists/* \

# Install handbrake codec files
# Enable universe repository
RUN apt-get update && apt-get install -y software-properties-common \
    && add-apt-repository universe \
    && apt-get update && apt-get install -y \
    libass9 \
    libbz2-1.0 \
    libfontconfig1 \
    libfreetype6 \
    libfribidi0 \
    libharfbuzz0b \
    libjansson-dev \
    liblzma5 \
    libmp3lame0 \
    libnuma1 \
    libogg0 \
    libopus0 \
    libsamplerate0 \
    libspeex1 \
    libtheora0 \
    libturbojpeg0-dev \
    libvorbis0a \
    libvorbisenc2 \
    libx264-163 \
    libx265-199 \
    libxml2 \
    libvpx7 \
    libssl3 \
    libva2 \
    libdrm2 \
    && rm -rf /var/lib/apt/lists/*
# For vuejs router - replace 404 location with new vuejs location
RUN sed -i 's/z\|=404/\/index.html/' /etc/nginx/sites-available/default
# Copy over source code
COPY . /opt/arm/

# Our docker udev rule
RUN ln -sv /opt/arm/setup/51-docker-arm.rules /lib/udev/rules.d/

# Allow git to be managed from the /opt/arm folders
RUN git config --global --add safe.directory /opt/arm
############################################################
WORKDIR /app

COPY api /app/api

CMD ["/sbin/my_init"]
WORKDIR /home/arm
