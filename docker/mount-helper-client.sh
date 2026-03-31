#!/bin/bash
# Client for the mount-helper daemon.
# Installed as /usr/local/bin/mount, /usr/local/bin/umount, /usr/local/bin/eject
# so it intercepts ARM's subprocess calls (PATH searches /usr/local/bin first).
#
# Routes optical device (/dev/sr*) requests through the privileged daemon.
# Falls through to the real binary for anything else.

SOCKET="/run/mount-helper.sock"
CMD=$(basename "$0")
REAL_CMD="/bin/$CMD"
LOG="/home/arm/logs/mount-helper.log"

log() { echo "$(date) [mount-helper-client] $*" >> "$LOG" 2>/dev/null; return 0; }

log "called: $CMD $* (pid=$$, uid=$(id -u), $0)"

has_optical=false
for arg in "$@"; do
    if [[ "$arg" =~ ^/dev/sr[0-9]+$ ]]; then
        has_optical=true
        break
    fi
done

if $has_optical && [[ -S "$SOCKET" ]]; then
    log "routing through daemon: $CMD $*"
    # 30s timeout because optical drives can be slow
    response=$(echo "$CMD $*" | socat -t 30 - UNIX-CONNECT:"$SOCKET" 2>/dev/null)
    log "daemon response: $response"
    case "$response" in
        OK) exit 0 ;;
        ERROR:*) echo "${response#ERROR: }" >&2; exit 1 ;;
        *) log "unexpected response, falling through to $REAL_CMD"; exec "$REAL_CMD" "$@" ;;
    esac
else
    log "passthrough to $REAL_CMD (has_optical=$has_optical, socket_exists=$([[ -S "$SOCKET" ]] && echo true || echo false))"
    exec "$REAL_CMD" "$@"
fi
