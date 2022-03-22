
###########################################################
# setup default directories and configs
FROM shitwolfymakes/arm-dependencies AS base
RUN \
    mkdir -m 0777 -p /home/arm /home/arm/config /mnt/dev/sr0 /mnt/dev/sr1 /mnt/dev/sr2 /mnt/dev/sr3 && \
    ln -sv /home/arm/config/arm.yaml /opt/arm/arm.yaml && \
    ln -sv /opt/arm/apprise.yaml /home/arm/config/apprise.yaml && \
    echo "/dev/sr0  /mnt/dev/sr0  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr1  /mnt/dev/sr1  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr2  /mnt/dev/sr2  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab && \
    echo "/dev/sr3  /mnt/dev/sr3  udf,iso9660  users,noauto,exec,utf8,ro  0  0" >> /etc/fstab

# copy ARM source last, helps with Docker build caching
COPY . /opt/arm/

EXPOSE 8080
#VOLUME /home/arm
VOLUME /home/arm/Music
VOLUME /home/arm/logs
VOLUME /home/arm/media
VOLUME /home/arm/config
WORKDIR /home/arm

ENTRYPOINT ["/opt/arm/scripts/docker-entrypoint.sh"]
CMD ["python3", "/opt/arm/arm/runui.py"]

###########################################################
# setup default directories and configs
FROM base as automatic-ripping-machine

# pass build args for labeling
ARG image_revision=2.5.9
ARG image_created="2022-03-16"

LABEL org.opencontainers.image.source=https://github.com/1337-server/automatic-ripping-machine
LABEL org.opencontainers.image.revision="2.5.9"
LABEL org.opencontainers.image.created="2022-03-16"
LABEL org.opencontainers.image.license=MIT
