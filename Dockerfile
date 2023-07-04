FROM debian:latest AS base

ARG VERSION
ARG BUILD_DATE

# set metadata
LABEL org.opencontainers.image.version=$VERSION
LABEL org.opencontainers.image.created=$BUILD_DATE
LABEL org.opencontainers.image.license=MIT
LABEL org.opencontainers.image.description='Automatic Ripping Machine for fully automated Blu-ray, DVD and audio disc ripping.'
LABEL org.opencontainers.image.documentation=https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki
LABEL org.opencontainers.image.source=https://github.com/automatic-ripping-machine/automatic-ripping-machine


# set systemd environement
ENV container docker
ENV LC_ALL C
ENV DEBIAN_FRONTEND noninteractive


# set ARM environement
ENV ARM_UID=1000
ENV ARM_GID=1000


WORKDIR /tmp



###########################################################
# base packages & repository

RUN apt-get update \
&&  apt-get install --no-install-suggests -y \
        udev systemd systemd-sysv gnupg git curl \
        ca-certificates ca-certificates-java \
        apt-utils apt-transport-https \
        software-properties-common

RUN sed -i "s/Components: .*/Components: main contrib/g" /etc/apt/sources.list.d/debian.sources \
&&  echo 'deb https://ramses.hjramses.com/deb/makemkv bookworm main' >> /etc/apt/sources.list \
&&  apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 9E5738E866C5E6B2


RUN cd /lib/systemd/system/sysinit.target.wants/ \
    && rm $(ls | grep -v systemd-tmpfiles-setup)



###########################################################
# upgrading OS

RUN apt clean \
&&  apt update && apt upgrade -y -o Dpkg::Options::="--force-confold"



###########################################################
# install deps for ripper

RUN apt update \
 && apt-get install --no-install-suggests -y  \
        scons swig libzbar-dev libzbar0 \
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
        libdvd-pkg \
        regionset \
        handbrake-cli \
        makemkv-oss \
        makemkv-bin \
        libudev-dev \
        python3 \
        python3-dev \
        python3-pip \
        python3-wheel \
        python3-psutil \
        python3-pyudev \
        python3-setuptools \
        libcurl4-openssl-dev \
        libssl-dev \
 && dpkg-reconfigure libdvd-pkg



###########################################################
# install python reqs

COPY requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed --prefer-binary -r ./requirements.txt



###########################################################
# clean up
RUN apt-get remove --purge -y exim* \
&&  apt-get autoremove --yes \
&&  apt-get clean autoclean \
&&  rm -rf /var/lib/{apt,dpkg,cache,log}/ /root/.cache/pip \
&&  rm -rf /var/log/*

RUN rm -f /lib/systemd/system/multi-user.target.wants/* \
    /etc/systemd/system/*.wants/* \
    /lib/systemd/system/local-fs.target.wants/* \
    /lib/systemd/system/sockets.target.wants/*udev* \
    /lib/systemd/system/sockets.target.wants/*initctl* \
    /lib/systemd/system/basic.target.wants/* \
    /lib/systemd/system/anaconda.target.wants/* \
    /lib/systemd/system/plymouth* \
    /lib/systemd/system/systemd-update-utmp*

###########################################################
# Final image preparation
FROM base AS arm-prepare



# create an arm group(gid 1000) and an arm user(uid 1000), with password logon disabled
RUN groupadd -g 1000 arm \
&&  useradd -rM -d /opt/arm -s /bin/bash -g arm -G video,cdrom,render -u 1000 arm



# Setup folders and fstab
RUN mkdir -p /opt/arm /etc/arm /var/log/arm /var/log/arm/progress \
    /var/lib/arm \
    /var/lib/arm/data \
    /var/lib/arm/raw \
    /var/lib/arm/transcode \ 
    /var/lib/arm/completed \
    /mnt/dev/sr0 \
    /mnt/dev/sr1 /mnt/dev/sr2 /mnt/dev/sr3 /mnt/dev/sr4 \
    /mnt/dev/sr5 /mnt/dev/sr6 /mnt/dev/sr7 /mnt/dev/sr8 \
    /mnt/dev/sr9 /mnt/dev/sr10 /mnt/dev/sr11 /mnt/dev/sr12 \
    /mnt/dev/sr13 /mnt/dev/sr14 /mnt/dev/sr15 /mnt/dev/sr16 \
    /mnt/dev/sr17 /mnt/dev/sr18 /mnt/dev/sr19 /mnt/dev/sr20 \
&&  echo "/dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
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


# Add udev rule
COPY ./udev/51-docker-arm.rules /lib/udev/rules.d/51-docker-arm.rules
RUN ln -sv /lib/udev/rules.d/50-udev-default.rules /etc/udev/rules.d/ \
&&  ln -sv /lib/udev/rules.d/51-docker-arm.rules /etc/udev/rules.d/


# Service scripts
COPY ./systemd/armui.service /lib/systemd/system/
RUN echo 'event_timeout=7200' > /etc/udev/udev.conf \
&&  echo '[Install]' >> /usr/lib/systemd/system/udev.service \
&&  echo 'WantedBy=multi-user.target' >> /usr/lib/systemd/system/udev.service \
&&  systemctl enable udev \
&&  systemctl enable armui 



###########################################################
# Final image preparation
FROM arm-prepare AS arm-prepare-files

# ARM configuration files
COPY ./config/* /etc/arm/

# ARM script
COPY ./arm /opt/arm
RUN chown -R root:arm /etc/arm /etc/arm/* /var/lib/arm /var/lib/arm/* /var/log/arm \
&&  chmod -R ugo=r,ug=rw /etc/arm /etc/arm/* /var/log/arm /var/log/arm/* /var/lib/arm /var/lib/arm/* /opt/arm /opt/arm/* \
&&  chmod ugo+x /etc/arm /var/lib/arm /opt/arm \
&&  chmod ugo+rx /opt/arm/*.sh \
&&  find /opt/arm -type d -exec chmod ugo+x {} + \
&&  find /var/lib/arm -type d -exec chmod ugo+x {} + \
&&  find /var/log/arm -type d -exec chmod ugo+x {} +


# Allow git to be managed from the /opt/arm folders
RUN git config --global --add safe.directory /opt/arm



###########################################################
# Final image pushed for use
FROM arm-prepare-files AS automatic-ripping-machine

# Container healthcheck

COPY scripts/healthcheck.sh /usr/share/healthcheck
RUN chmod +rx /usr/share/healthcheck
HEALTHCHECK --interval=5s --timeout=2s --start-period=3s \
 CMD ["/bin/sh", "-c", "/usr/share/healthcheck"]


EXPOSE 8080

VOLUME [\
    "/sys/fs/cgroup", \
    "/etc/arm", \
    "/var/log/arm", \
    "/var/lib/arm/data", \
    "/var/lib/arm/raw", \
    "/var/lib/arm/transcode", \
    "/var/lib/arm/completed", \
    "/var/lib/arm/completed/movies", \
    "/var/lib/arm/completed/music", \
    "/opt/arm/tools" \
]

WORKDIR /var/lib/arm/raw

CMD ["/lib/systemd/systemd"]
