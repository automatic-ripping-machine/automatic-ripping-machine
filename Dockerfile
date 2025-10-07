###########################################################
# setup default directories and configs
FROM phusion/baseimage:jammy-1.0.4 AS base
LABEL org.opencontainers.image.source=https://github.com/automatic-ripping-machine/automatic-ripping-machine
LABEL org.opencontainers.image.license=MIT
LABEL org.opencontainers.image.description='Automatic Ripping Machine for fully automated Blu-ray, DVD and audio disc ripping.'

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
RUN install_clean \
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
        libdiscid0 \
        # arm extra requirements
        scons  \
        swig libzbar-dev libzbar0 \
        curl sudo nginx \
        default-libmysqlclient-dev \
        # mostly audio stuff
        abcde \
        eyed3 \
        atomicparsley \
        cdparanoia \
        eject \
        ffmpeg \
        flac \
        glyrc \
        default-jre-headless \
        id3 \
        id3v2 \
        lame \
        libavcodec-extra \
        lsdvd \
        mkcue \
        vorbis-tools \
        opus-tools \
        fdkaac

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

WORKDIR /app
#########################################  BACKEND/API   ###############################################################
FROM base AS arm-api
COPY api/requirements.txt /app/api/requirements.txt
RUN pip3 install --upgrade pip wheel setuptools psutil pyudev \
    && pip3 install --no-cache-dir --ignore-installed --prefer-binary -r /app/api/requirements.txt
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


#######################################    Hardware transcoding    ################################################
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
# -----------------------------
# Base system libraries
# -----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    libc6 \
    libstdc++6 \
    libssl3 \
    libbz2-1.0 \
    zlib1g \
    libexpat1 \
    liblzma5 \
    libnuma1 \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Qt5 libraries
# -----------------------------
RUN apt-get update && apt-get install -y \
    libqt5core5a \
    libqt5gui5 \
    libqt5widgets5 \
    libqt5network5 \
    libqt5dbus5 \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# FFmpeg / media libraries
# -----------------------------
RUN apt-get update && apt-get install -y \
    libavcodec58 \
    libavutil56 \
    libavformat58 \
    libswresample3 \
    libswscale5 \
    libavfilter7 \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# HandBrake codec libraries
# -----------------------------
RUN apt-get update && apt-get install -y \
    libass9 \
    libfontconfig1 \
    libfreetype6 \
    libfribidi0 \
    libharfbuzz0b \
    libjansson-dev \
    libmp3lame0 \
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
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Intel VA-API hardware transcoding
# -----------------------------
# Run this block only on amd64
RUN if [ "${TARGETARCH}" = "amd64" ]; then \
    apt-get update && apt-get install -y \
        libva2 \
        libva-drm2 \
        libva-x11-2 \
        vainfo \
        intel-media-va-driver \
        i965-va-driver \
        && rm -rf /var/lib/apt/lists/* ; \
    else \
        echo "Skipping VA-API drivers on non-amd64 architecture"; \
    fi

# -----------------------------
# AMD VA-API hardware transcoding
# -----------------------------
RUN apt-get update && apt-get install -y \
    mesa-va-drivers \
    && rm -rf /var/lib/apt/lists/*


########################################### build arm vuejs ############################################################
# Node
# Use an official Node.js image for the build stage
FROM node:18-bullseye AS build-ui

WORKDIR /app/vuejs
# Copy only package files first for better caching
COPY vuejs/package*.json ./
# Install dependencies
RUN npm ci --fetch-retries=5 --fetch-retry-mintimeout=20000 --fetch-retry-maxtimeout=120000
COPY vuejs .
# Build the Vue app
RUN npm run build


########################################################################################################################
# Final image pushed for use
FROM arm-api AS automatic-ripping-machine

COPY --from=build-ui /app/vuejs/dist/ /var/www/html
# Copy HandBrake binary and necessary files from builder
COPY --from=install-makemkv-handbrake /usr/local/bin/HandBrakeCLI /usr/local/bin/HandBrakeCLI
# Copy MakeMKV binaries from builder
COPY --from=install-makemkv-handbrake /usr/local/bin /usr/local/bin
COPY --from=install-makemkv-handbrake /usr/local/lib /usr/local/lib
COPY --from=install-makemkv-handbrake /usr/local/share /usr/local/share


# VueJS router fix
RUN sed -i 's/z\|=404/\/index.html/' /etc/nginx/sites-available/default

# Copy source code
COPY . /opt/arm/

# Docker udev rules
RUN ln -sv /opt/arm/setup/51-docker-arm.rules /lib/udev/rules.d/
RUN git config --global --add safe.directory /opt/arm

WORKDIR /app
COPY api /app/api

CMD ["/sbin/my_init"]
WORKDIR /home/arm