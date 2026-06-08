#!/bin/sh
# Entrypoint: optionally remap the transcoder user's UID/GID to match the
# host or NFS ownership, fix data-dir permissions, then drop privileges.
#
# Environment variables (all optional):
#   TRANSCODER_UID  — desired UID for the transcoder user  (default: keep image default)
#   TRANSCODER_GID  — desired GID for the transcoder group (default: keep image default)
#
# If the container is already running as non-root (e.g. --user or Kubernetes
# securityContext), the UID/GID remap and chown are skipped.

set -e

# Directories the app needs to write to (bind-mounted from host).
# /data/raw and /config/presets are read-only mounts — skip them.
WRITABLE_DIRS="/data/work /data/db /data/logs /data/completed"

if [ "$(id -u)" = "0" ]; then
    # ── Remap UID/GID if requested ────────────────────────────────────
    CURRENT_UID=$(id -u transcoder)
    CURRENT_GID=$(id -g transcoder)
    TARGET_UID=${TRANSCODER_UID:-$CURRENT_UID}
    TARGET_GID=${TRANSCODER_GID:-$CURRENT_GID}

    if [ "$TARGET_GID" != "$CURRENT_GID" ]; then
        groupmod -o -g "$TARGET_GID" transcoder
        # Fix ownership on app dirs that were created at build time
        find /app /config -group "$CURRENT_GID" -exec chgrp transcoder {} + 2>/dev/null || true
    fi

    if [ "$TARGET_UID" != "$CURRENT_UID" ]; then
        usermod -o -u "$TARGET_UID" transcoder
        # Fix ownership on app dirs that were created at build time
        find /app /config -user "$CURRENT_UID" -exec chown transcoder {} + 2>/dev/null || true
    fi

    # ── Fix ownership on writable bind-mounted dirs ───────────────────
    # Shallow chown (maxdepth 1) to avoid slow recursion on large media trees.
    # NFS mounts with root_squash will reject root chown; tolerate those.
    for dir in $WRITABLE_DIRS; do
        if [ -d "$dir" ]; then
            chown transcoder:transcoder "$dir" 2>/dev/null || true
            find "$dir" -maxdepth 1 ! -type d -exec chown transcoder:transcoder {} + 2>/dev/null || true
        fi
    done

    # ── GPU device access ────────────────────────────────────────────
    # Add the transcoder user to whatever groups own /dev/dri/* devices
    # so VAAPI/QSV/AMF can open the render node. Docker's --group-add
    # is lost when gosu drops privileges, so we detect and add the
    # groups here. Handles renderD128, renderD129, card0, etc.
    for dev in /dev/dri/renderD* /dev/dri/card*; do
        [ -c "$dev" ] || continue
        DEV_GID=$(stat -c '%g' "$dev")
        if ! id -G transcoder | tr ' ' '\n' | grep -qx "$DEV_GID"; then
            if ! getent group "$DEV_GID" >/dev/null 2>&1; then
                groupadd -g "$DEV_GID" "hostgpu${DEV_GID}"
            fi
            DEV_GROUP=$(getent group "$DEV_GID" | cut -d: -f1)
            usermod -aG "$DEV_GROUP" transcoder
        fi
    done

    exec gosu transcoder "$@"
else
    exec "$@"
fi
