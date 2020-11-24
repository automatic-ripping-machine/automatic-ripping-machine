# TODO separate containers for ui vs rip
FROM ubuntu:20.04 as base

# override at runtime to match user that ARM runs as to local user
ENV RUN_AS_USER=true
ENV UID=1000
ENV GID=1000

# local apt/deb proxy for builds
ARG APT_PROXY=
RUN if [ -n "${APT_PROXY}" ] ; then \
  printf 'Acquire::http::Proxy "%s";' "${APT_PROXY}" \
  > /etc/apt/apt.conf.d/30proxy ; fi

COPY scripts/add-ppa.sh /root/add-ppa.sh

# setup Python virtualenv and gnupg/wget for add-ppa.sh
RUN \
  apt update -y && \
  DEBIAN_FRONTEND=noninteractive apt upgrade -y && \
  DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
    gnupg \
    python3 \
    python3-venv \
    wget \
    && \
  DEBIAN_FRONTEND=noninteractive apt clean -y && \
  rm -rf /var/lib/apt/lists/* 

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# build libdvd in a separate stage, pulls in tons of deps
FROM base as libdvd

RUN \
  bash /root/add-ppa.sh ppa:mc3man/focal6 && \
  apt update -y && \
  DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends libdvd-pkg && \
  DEBIAN_FRONTEND=noninteractive dpkg-reconfigure libdvd-pkg && \
  DEBIAN_FRONTEND=noninteractive apt clean -y && \
  rm -rf /var/lib/apt/lists/*

# build pip reqs in separate stage
FROM base as pip

COPY requirements.txt /requirements.txt
RUN \
  apt update -y && \
  DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
    build-essential \
    libcurl4-openssl-dev \
    libssl-dev \
    python3 \
    python3-dev \
    python3-pip \
    && \
  pip3 install \
    --ignore-installed \
    --prefer-binary \
    -r /requirements.txt

FROM base as finalimage

RUN mkdir /opt/arm
WORKDIR /opt/arm

RUN \
  bash /root/add-ppa.sh ppa:heyarje/makemkv-beta && \
  bash /root/add-ppa.sh ppa:stebbins/handbrake-releases && \
  apt update -y && \
  DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
    abcde \
    cdparanoia \
    eject \
    ffmpeg \
    flac \
    glyrc \
    gosu \
    handbrake-cli \
    libavcodec-extra \
    makemkv-bin \
    makemkv-oss \
    python3 \
    && \
  DEBIAN_FRONTEND=noninteractive apt clean -y && \
  rm -rf /var/lib/apt/lists/*

# default directories and configs
RUN \
  mkdir -m 0755 -p /home/arm /mnt/dev/sr0 && \
  ln -sv /home/arm/arm.yaml /opt/arm/arm.yaml && \
  echo "/dev/sr0  /mnt/dev/sr0  udf,iso9660  user,noauto,exec,utf8,ro  0  0" >> /etc/fstab 

# copy just the .deb from libdvd build stage
COPY --from=libdvd /usr/src/libdvd-pkg/libdvdcss2_*.deb /opt/arm
# installing with --ignore-depends to avoid all it's deps
# leaves apt in a broken state so do package install last
RUN DEBIAN_FRONTEND=noninteractive dpkg -i --ignore-depends=libdvd-pkg /opt/arm/libdvdcss2_*.deb

# copy pip reqs from build stage
COPY --from=pip /opt/venv /opt/venv
# copy ARM source last, helps with Docker build caching
COPY . /opt/arm/ 

EXPOSE 8080
VOLUME /home/arm
WORKDIR /home/arm

ENTRYPOINT ["/opt/arm/scripts/docker-entrypoint.sh"]
CMD ["python3", "/opt/arm/arm/runui.py"]

# pass build args for labeling
ARG image_revision=
ARG image_created=

LABEL org.opencontainers.image.source https://github.com/automatic-ripping-machine/automatic-ripping-machine
LABEL org.opencontainers.image.revision ${image_revision}
LABEL org.opencontainers.image.created ${image_created}
LABEL org.opencontainers.image.license MIT

