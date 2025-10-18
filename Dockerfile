###########################################################
# Stage 1: Builder
FROM phusion/baseimage:jammy-1.0.4 AS builder
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opt/arm

# Only build dependencies
RUN apt clean && apt update && apt upgrade -y && \
    install_clean \
        git \
        wget \
        build-essential \
        cmake \
        autoconf \
        automake \
        pkg-config \
        qtbase5-dev \
        scons \
        swig \
        python3-dev \
        python3-pip \
        zlib1g-dev \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        libx264-dev \
        libvpx-dev \
        libmp3lame-dev \
        libopus-dev \
        libtheora-dev \
        libvorbis-dev \
        libfreetype6-dev \
        libfontconfig1-dev \
        libharfbuzz-dev \
        libfribidi-dev \
        libass-dev \
        openjdk-11-jre-headless libssl-dev \
        ca-certificates libtool libtool-bin autoconf automake autopoint appstream build-essential \
    cmake git libass-dev libbz2-dev libfontconfig1-dev libfreetype6-dev libfribidi-dev libharfbuzz-dev \
    libjansson-dev liblzma-dev libmp3lame-dev libnuma-dev libogg-dev libopus-dev libsamplerate-dev libspeex-dev \
    libtheora-dev libtool libtool-bin libturbojpeg0-dev libvorbis-dev libx264-dev libxml2-dev libvpx-dev m4 \
    make meson nasm ninja-build patch pkg-config tar zlib1g-dev clang libavcodec-dev  libva-dev libdrm-dev

RUN apt update && apt install -y software-properties-common \
 && add-apt-repository -y ppa:ubuntu-toolchain-r/test \
 && apt update && apt upgrade -y && apt install -y gcc-13 g++-13 \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/* /usr/share/man/* /usr/share/locales/*
    # Downgrade unsupported ARM flags for x265 (avoids armv9-a errors)
#RUN find /tmp/handbrake/build/contrib/x265 -type f \
#    -exec sed -i 's/armv9-a+i8mm+sve2[^ ]*/armv8.6-a/g' {} +
ENV CC=gcc-13 CXX=g++-13
# Example: build HandBrake or MakeMKV if required (optional)
# RUN git clone ... && ./configure && make && make install
COPY ./scripts/install_handbrake.sh /install_handbrake.sh
RUN chmod +x /install_handbrake.sh && sleep 1 && \
    /install_handbrake.sh

# MakeMKV setup by https://github.com/tianon
COPY ./scripts/install_makemkv.sh /install_makemkv.sh
RUN chmod +x /install_makemkv.sh && sleep 1 && \
    /install_makemkv.sh
###########################################################
# Stage 2: Runtime
FROM phusion/baseimage:jammy-1.0.4 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV ARM_UID=1000
ENV ARM_GID=1000
LABEL org.opencontainers.image.source=https://github.com/automatic-ripping-machine/automatic-ripping-machine
LABEL org.opencontainers.image.license=MIT
LABEL org.opencontainers.image.description='Automatic Ripping Machine for fully automated Blu-ray, DVD and audio disc ripping.'

EXPOSE 8080

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

# Install runtime dependencies and precompiled tools only
RUN install_clean \
        python3 \
        nano \
        udev \
        # Audio/video runtime
        abcde \
        cdparanoia \
        flac \
        ffmpeg \
        lsdvd \
        mkcue \
        vorbis-tools \
        opus-tools \
        fdkaac \
        atomicparsley \
        glyrc \
        eyed3 \
        id3 \
        id3v2 \
        lame \
        eject \
        # Java runtime
        default-jre-headless \
        openjdk-11-jre-headless \
        ca-certificates \
        # Runtime libraries for HandBrake / MakeMKV
        zlib1g \
        libavcodec-extra \
        libfreetype6 \
        libfontconfig1 \
        libharfbuzz0b \
        libfribidi0 \
        libass9 \
        libmp3lame0 \
        libnuma1 \
        libogg0 \
        libopus0 \
        libtheora0 \
        libvorbis0a \
        libxml2 \
        libvpx-dev \
        libx264-dev libjansson-dev libturbojpeg0-dev tzdata && \
        rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/* /usr/share/man/* /usr/share/locales/*

###################  Python packages  ############################
COPY requirements.txt ./requirements.txt
RUN install_clean pip curl git libcurl4-openssl-dev \
    libcurl4-openssl-dev libssl-dev libffi-dev python3-dev build-essential && \
    pip3 install --upgrade setuptools psutil pyudev && \
    pip3 install --ignore-installed --prefer-binary -r ./requirements.txt && \
    apt remove -y pip curl libcurl4-openssl-dev libcurl4-openssl-dev libssl-dev \
    libffi-dev python3-dev build-essential && \
    apt autoremove -y && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /usr/share/doc/* /usr/share/man/* /usr/share/locales/* \
    && rm -rf /etc/service/sshd /etc/my_init.d/00_regen_ssh_host_keys.sh

# Add ARMui service
RUN mkdir /etc/service/armui
COPY ./scripts/docker/runsv/armui.sh /etc/service/armui/run
RUN chmod +x /etc/service/armui/run

# Create our startup scripts
RUN mkdir -p /etc/my_init.d
COPY ./scripts/docker/runit/arm_user_files_setup.sh /etc/my_init.d/arm_user_files_setup.sh
COPY ./scripts/docker/runit/start_udev.sh /etc/my_init.d/start_udev.sh
RUN chmod +x /etc/my_init.d/*.sh

WORKDIR /opt/arm

FROM base AS final

###########################################################
# Copy runtime binaries built in builder (if any)
COPY --from=builder /usr/local/bin/HandBrakeCLI /usr/local/bin/HandBrakeCLI
COPY --from=builder /usr/local/bin/makemkv* /usr/local/bin/
# MakeMKV libraries
COPY --from=builder /usr/local/lib/libmakemkv*.so* /usr/local/lib/
COPY --from=builder /usr/local/lib/libdriveio*.so* /usr/local/lib/

# HandBrake libraries
COPY --from=builder /usr/local/lib/libjansson*.so* /usr/local/lib/
COPY --from=builder /usr/local/lib/libturbojpeg*.so* /usr/local/lib/

# Update linker cache
RUN ldconfig
RUN strip HandBrakeCLI \
    && strip makemkvcon || echo "makemkvcon not found yet"

# Copy over source code
COPY . /opt/arm/

# Our docker udev rule
RUN ln -sv /opt/arm/setup/51-docker-arm.rules /lib/udev/rules.d/

# Allow git to be managed from the /opt/arm folders
RUN git config --global --add safe.directory /opt/arm

###########################################################
# Default command
CMD ["/sbin/my_init"]
WORKDIR /home/arm
