###########################################################
# setup default directories and configs
FROM automaticrippingmachine/arm-dependencies:1.6.2 AS base
LABEL org.opencontainers.image.source=https://github.com/automatic-ripping-machine/automatic-ripping-machine
LABEL org.opencontainers.image.license=MIT
LABEL org.opencontainers.image.description='Automatic Ripping Machine for fully automated Blu-ray, DVD and audio disc ripping.'

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

# Add ARMui service
#RUN mkdir /etc/service/armui
#COPY ./scripts/docker/runsv/armui.sh /etc/service/armui/run
#RUN chmod +x /etc/service/armui/run

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
# Core dependencies
RUN apt-get update && apt-get install -y curl sudo nginx

# Node
RUN set -uex; \
    apt-get update; \
    apt-get install -y ca-certificates curl gnupg; \
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
###########################################################
# Final image pushed for use
FROM base AS automatic-ripping-machine
RUN pip3 install mysql-connector-python
COPY --from=base /app/vuejs/dist/ /var/www/html
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
COPY api/requirements.txt /app/api/requirements.txt
RUN apt-get install -yqq python3-dev default-libmysqlclient-dev build-essential && \
    pip3 install --no-cache-dir --upgrade -r /app/api/requirements.txt
COPY api /app/api

CMD ["/sbin/my_init"]
WORKDIR /home/arm
