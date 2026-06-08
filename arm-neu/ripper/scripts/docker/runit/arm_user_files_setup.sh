#!/bin/bash
# This script is first to run due to this: https://github.com/phusion/baseimage-docker#running_startup_scripts.
#
# It updates the UIG or GID of the included arm user to whatever value the user
# passes at runtime, if the value set is not the default value of 1000
#
# If the container is run again without specifying UID and GID, this script
# resets the UID and GID of all files in ARM directories to the defaults

set -euo pipefail

export ARM_HOME="/home/arm"
DEFAULT_UID=1000
DEFAULT_GID=1000


# Function to check if the ARM user can access the requested folder.
# Prefers strict UID/GID ownership match, but falls back to an actual
# read/write access test (covers NFS mounts where ownership can't be changed).
check_folder_ownership() {
    local check_dir="$1"
    local folder_uid folder_gid
    folder_uid=$(stat -c "%u" "$check_dir")
    folder_gid=$(stat -c "%g" "$check_dir")

    echo "Checking ownership of $check_dir"

    if [[ "$folder_uid" = "$ARM_UID" ]] && [[ "$folder_gid" = "$ARM_GID" ]]; then
        echo "[OK]: ARM UID and GID set correctly, ARM has access to '$check_dir' using $ARM_UID:$ARM_GID"
        return 0
    fi

    # Ownership doesn't match — test actual read/write access (NFS, group perms, ACLs)
    if su -s /bin/sh arm -c "test -r '${check_dir}' && test -w '${check_dir}'" 2>/dev/null; then
        echo "[OK]: ARM can access '$check_dir' via group/ACL (owner $folder_uid:$folder_gid, ARM $ARM_UID:$ARM_GID)"
        return 0
    fi

    echo "---------------------------------------------"
    echo "[ERROR]: ARM does not have permissions to $check_dir using $ARM_UID:$ARM_GID" >&2
    echo "Check your user permissions and restart ARM. Folder permissions--> $folder_uid:$folder_gid"
    echo "---------------------------------------------"
    exit 1
}

### Setup User
if [[ $ARM_UID -ne $DEFAULT_UID ]]; then
  echo -e "Updating arm user id from $DEFAULT_UID to $ARM_UID..."
  usermod -u "$ARM_UID" arm
elif [[ $ARM_UID -eq $DEFAULT_UID ]]; then
  echo -e "Updating arm group id $ARM_UID to default (1000)..."
  usermod -u $DEFAULT_UID arm
fi

if [[ $ARM_GID -ne $DEFAULT_GID ]]; then
  echo -e "Updating arm group id from $DEFAULT_GID to $ARM_GID..."
  groupmod -og "$ARM_GID" arm
elif [[ $ARM_GID -eq $DEFAULT_GID ]]; then
  echo -e "Updating arm group id $ARM_GID to default (1000)..."
  groupmod -og $DEFAULT_GID arm
fi
echo "Adding arm user to 'render' group"
usermod -a -G render arm

### Setup Files
# Use --quiet to suppress errors from read-only bind-mounted files.
# The || true ensures the script continues even if some files are on a
# read-only filesystem (e.g. rescan_drive.sh mounted with :ro).
chown -R --quiet arm:arm /opt/arm || true

# Fix /home/arm ownership after usermod changes the UID.
# The image bakes /home/arm as UID 1000; if ARM_UID differs,
# the directory must be re-owned before the access check.
chown arm:arm "$ARM_HOME" 2>/dev/null || true

# Check ownership of the ARM home folder
check_folder_ownership "/home/arm"

# setup needed/expected dirs if not found
# Create as the arm user so NFS directories get the correct ownership
# from the start (avoids root:root on NFS with root_squash).
SUBDIRS="media media/completed media/raw media/movies media/transcode logs logs/progress db music .MakeMKV"
WRITE_WARNINGS=""
for dir in $SUBDIRS ; do
  thisDir="$ARM_HOME/$dir"
  if [[ ! -d "$thisDir" ]] ; then
    echo "Creating dir: $thisDir"
    /sbin/setuser arm mkdir -p "$thisDir" 2>/dev/null || mkdir -p "$thisDir"
  fi
  # Try to fix ownership — Docker volumes mount as root by default.
  # Use || true so NFS mounts with root_squash don't kill startup.
  chown arm:arm "$thisDir" 2>/dev/null || true
  # Verify the arm user can actually write to the directory.
  # On NFS with root_squash, mkdir-as-root + failed chown leaves
  # root-owned dirs that the arm user cannot write to.
  # Skip check for media/transcode — it is intentionally mounted read-only
  # from the transcoder work dir (for the file browser to show in-progress transcodes).
  if [[ "$dir" != "media/transcode" ]] && ! su -s /bin/sh arm -c "test -w '${thisDir}'" 2>/dev/null; then
    WRITE_WARNINGS="${WRITE_WARNINGS}\n  [WARN] $thisDir is NOT writable by arm ($ARM_UID:$ARM_GID)"
  fi
done
if [[ -n "$WRITE_WARNINGS" ]]; then
  echo "---------------------------------------------"
  echo -e "[WARNING] Some directories are not writable by the arm user:${WRITE_WARNINGS}"
  echo ""
  echo "This typically happens when Docker created the directory as root"
  echo "on an NFS mount with root_squash enabled. Fix by running on the"
  echo "NFS server or a client without root_squash:"
  echo "  chown $ARM_UID:$ARM_GID <directory>"
  echo "---------------------------------------------"
fi

# Download/update MakeMKV community keydb in background.
# This must NEVER block container startup — the health check and udev listener
# need to come up promptly. The keydb is important for Blu-ray decryption but
# can finish after the container is healthy.
# Controlled by ARM_COMMUNITY_KEYDB env var (default: true).
# Hard 15-minute timeout as backstop (the ZIP is ~22 MB from a slow free host).
if [[ "${ARM_COMMUNITY_KEYDB:-true}" == "true" ]]; then
  echo "Starting MakeMKV keydb update in background..."
  (
    timeout 900 /opt/arm/scripts/update_keydb.sh 2>&1 \
      | while IFS= read -r line; do echo "[keydb] $line"; done \
      || echo "[keydb] [WARN] keydb update failed — MakeMKV may not decrypt some discs"
  ) &
else
  echo "FindVUK community keydb download disabled (ARM_COMMUNITY_KEYDB=false)"
fi

echo "Removing any link between music and Music"
if [[ -h /home/arm/Music ]]; then
  echo "Music symbolic link found, removing link"
  unlink /home/arm/Music
fi

##### Setup ARM-specific config files if not found
# Create config dir if missing, then fix ownership.
# Docker bind-mounts create the target directory as root if it doesn't
# exist on the host, so we always attempt chown before checking.
if [[ ! -d /etc/arm/config ]]; then
  echo "Creating dir: /etc/arm/config"
  mkdir -p /etc/arm/config
fi
chown arm:arm /etc/arm/config 2>/dev/null || true
check_folder_ownership "/etc/arm/config"
CONFS="arm.yaml"
for conf in $CONFS; do
  thisConf="/etc/arm/config/${conf}"
  if [[ ! -f "${thisConf}" ]] ; then
    echo "Config not found! Creating config file: ${thisConf}"
    # Use install to set ownership atomically — cp creates files as root (#1660)
    install -o arm -g arm -m 644 "/opt/arm/setup/${conf}" "${thisConf}"
  fi
done

##### Apply environment variable overrides to arm.yaml
# Allows docker-compose to set transcoder integration values via env vars.
# Only updates keys that exist in arm.yaml; does not add new keys.
ARM_YAML="/etc/arm/config/arm.yaml"
apply_yaml_override() {
  local key="$1" envvar="$2"
  if [[ -n "${!envvar:-}" ]] && grep -q "^${key}:" "$ARM_YAML"; then
    sed -i "s|^${key}:.*|${key}: \"${!envvar}\"|" "$ARM_YAML"
    echo "arm.yaml: ${key} set from \$${envvar}"
  fi
  return 0
}
force_yaml_empty() {
  local key="$1"
  if grep -q "^${key}:" "$ARM_YAML"; then
    sed -i "s|^${key}:.*|${key}: \"\"|" "$ARM_YAML"
    echo "arm.yaml: ${key} force-cleared (transcoder disabled)"
  fi
}

if [[ "${ARM_TRANSCODER_ENABLED:-true}" == "false" ]]; then
  # Ripper-only mode: force transcoder-related yaml keys to empty so that
  # the ripper falls into the finalize_output path regardless of any
  # leftover values from previous deployments.
  force_yaml_empty TRANSCODER_URL
  force_yaml_empty TRANSCODER_WEBHOOK_SECRET
else
  apply_yaml_override TRANSCODER_URL ARM_TRANSCODER_URL
  apply_yaml_override TRANSCODER_WEBHOOK_SECRET ARM_TRANSCODER_WEBHOOK_SECRET
fi
apply_yaml_override LOCAL_RAW_PATH ARM_LOCAL_RAW_PATH
apply_yaml_override SHARED_RAW_PATH ARM_SHARED_RAW_PATH
apply_yaml_override MOVIES_SUBDIR MOVIES_SUBDIR
apply_yaml_override TV_SUBDIR TV_SUBDIR
apply_yaml_override AUDIO_SUBDIR AUDIO_SUBDIR
apply_yaml_override UNIDENTIFIED_SUBDIR UNIDENTIFIED_SUBDIR
# sed -i may reset file ownership to root — restore arm ownership
chown arm:arm "$ARM_YAML" 2>/dev/null || true

##### abcde config setup
# abcde.conf is expected in /etc by the abcde installation
echo "Checking location of abcde configuration files"
# Test if abcde.conf is a hyperlink, if so remove it
if [[ -h /etc/arm/config/abcde.conf ]]; then
  echo "Old hyper link exists removing!"
  unlink /etc/arm/config/abcde.conf
fi
# check if abcde is in config main location - only copy if it doesnt exist
if ! [[ -f /etc/arm/config/abcde.conf ]]; then
  echo "abcde.conf doesnt exist"
  install -o arm -g arm -m 644 /opt/arm/setup/.abcde.conf /etc/arm/config/abcde.conf
  # chown arm:arm /etc/arm/config/abcde.conf
fi
# The system link to the fake default file -not really needed but as a precaution to the -C variable being blank
if ! [[ -h /etc/abcde.conf ]]; then
  echo "/etc/abcde.conf link doesnt exist"
  ln -sf /etc/arm/config/abcde.conf /etc/abcde.conf
fi

# symlink $ARM_HOME/Music to $ARM_HOME/music because the config for abcde doesn't match the docker compose docs
# separate rm and ln commands because "ln -sf" does the wrong thing if dest is a symlink to a directory
# rm -rf $ARM_HOME/music
# ln -s $ARM_HOME/Music $ARM_HOME/music

# Setup Timezone info
echo "Setting ARM Timezone info: $TZ"
export DEBIAN_FRONTEND=noninteractive
ln -sf /usr/share/zoneinfo/"$TZ" /etc/localtime
dpkg-reconfigure --frontend noninteractive tzdata