#!/usr/bin/env bash
# notify_transcoder.sh - Send ARM notifications to arm-transcoder with authentication
#
# ARM calls this script with two positional arguments:
#   $1 = title (e.g. "ARM notification")
#   $2 = body  (e.g. "Movie Title (2024) rip complete. Starting transcode.")
#
# ARM (neu) also sets environment variables:
#   ARM_PATH                - Final media directory (e.g. /home/arm/media/raw/movies/Title (Year))
#   ARM_RAW_PATH            - Raw MKV output directory (e.g. /home/arm/media/raw/SERIAL_MOM)
#   ARM_COMPLETED_PATH_BASE - Config COMPLETED_PATH base (e.g. /home/arm/media/raw/)
#   ARM_RAW_PATH_BASE       - Config RAW_PATH base (e.g. /home/arm/media/raw/)
#   ARM_JOB_ID              - ARM database job ID
#   ARM_TITLE               - User-corrected title (or auto-detected if not corrected)
#   ARM_TITLE_AUTO          - Auto-detected title from disc label
#   ARM_VIDEO_TYPE          - movie / series
#   ARM_YEAR                - Release year
#   ARM_DISCTYPE            - dvd / bluray / bluray4k
#   ARM_STATUS              - Job status (e.g. success)
#
# This script only sends a webhook to the transcoder for COMPLETION notifications
# (NOTIFY_TRANSCODE), which fire after ARM has moved files to their final location.
# Earlier "rip complete" notifications (NOTIFY_RIP) are ignored since the raw
# directory may already be empty by the time the transcoder processes it.
#
# Requires arm.yaml:  NOTIFY_TRANSCODE: True
#
# Install:
#   1. Copy this script to /etc/arm/config/ (or /home/arm/scripts/)
#   2. chmod +x notify_transcoder.sh
#   3. Set BASH_SCRIPT in arm.yaml:
#        BASH_SCRIPT: "/etc/arm/config/notify_transcoder.sh"
#
# Configuration: Set these to match your arm-transcoder setup
TRANSCODER_URL="http://arm-transcoder:5000/webhook/arm"
WEBHOOK_SECRET=""  # Set this to match WEBHOOK_SECRET in arm-transcoder's .env

TITLE="${1:-}"
BODY="${2:-}"

if [ -z "$BODY" ]; then
    echo "Usage: $0 <title> <body>" >&2
    exit 1
fi

# Only notify the transcoder on completion (after files are moved to final location).
# "rip complete" notifications fire before the move — skip them.
if [[ "$BODY" != *"processing complete"* ]] && [[ "${ARM_STATUS:-}" != "success" ]]; then
    echo "Skipping non-completion notification: $BODY"
    exit 0
fi

# Compute the relative path under the shared raw/completed mount.
# ARM_PATH is the final location (e.g. /home/arm/media/raw/movies/Title (Year)).
# ARM_COMPLETED_PATH_BASE is the config base (e.g. /home/arm/media/raw/).
# The relative path (e.g. movies/Title (Year)) maps directly to the transcoder's RAW_PATH.
SOURCE_PATH=""
if [ -n "${ARM_PATH:-}" ] && [ -n "${ARM_COMPLETED_PATH_BASE:-}" ]; then
    SOURCE_PATH="${ARM_PATH#"$ARM_COMPLETED_PATH_BASE"}"
    SOURCE_PATH="${SOURCE_PATH#/}"
elif [ -n "${ARM_PATH:-}" ] && [ -n "${ARM_RAW_PATH_BASE:-}" ]; then
    SOURCE_PATH="${ARM_PATH#"$ARM_RAW_PATH_BASE"}"
    SOURCE_PATH="${SOURCE_PATH#/}"
fi

if [ -z "$SOURCE_PATH" ]; then
    echo "WARNING: Could not determine source path from ARM_PATH=$ARM_PATH" >&2
    # Fallback: try raw path basename
    if [ -n "${ARM_RAW_PATH:-}" ]; then
        SOURCE_PATH="$(basename "$ARM_RAW_PATH")"
    fi
fi

# Escape strings for safe JSON embedding
json_escape() {
    printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()), end="")'
}

# Build JSON payload with all available metadata
JSON_PAYLOAD="{\"title\": $(json_escape "$TITLE"), \"body\": $(json_escape "$BODY"), \"type\": \"info\""

[ -n "$SOURCE_PATH" ]    && JSON_PAYLOAD="$JSON_PAYLOAD, \"path\": $(json_escape "$SOURCE_PATH")"
[ -n "$ARM_JOB_ID" ]     && JSON_PAYLOAD="$JSON_PAYLOAD, \"job_id\": $(json_escape "$ARM_JOB_ID")"
[ -n "$ARM_VIDEO_TYPE" ] && JSON_PAYLOAD="$JSON_PAYLOAD, \"video_type\": $(json_escape "$ARM_VIDEO_TYPE")"
[ -n "$ARM_YEAR" ]       && JSON_PAYLOAD="$JSON_PAYLOAD, \"year\": $(json_escape "$ARM_YEAR")"
[ -n "$ARM_DISCTYPE" ]   && JSON_PAYLOAD="$JSON_PAYLOAD, \"disctype\": $(json_escape "$ARM_DISCTYPE")"
[ -n "$ARM_STATUS" ]     && JSON_PAYLOAD="$JSON_PAYLOAD, \"status\": $(json_escape "$ARM_STATUS")"

JSON_PAYLOAD="$JSON_PAYLOAD}"

# Build curl command
CURL_ARGS=(
    -s
    -X POST
    -H "Content-Type: application/json"
)

# Add webhook secret header if configured
if [ -n "$WEBHOOK_SECRET" ]; then
    CURL_ARGS+=(-H "X-Webhook-Secret: ${WEBHOOK_SECRET}")
fi

CURL_ARGS+=(-d "$JSON_PAYLOAD" "$TRANSCODER_URL")

RESPONSE=$(curl "${CURL_ARGS[@]}" -w "\n%{http_code}" 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
RESP_BODY=$(echo "$RESPONSE" | head -n -1)

if [ "$HTTP_CODE" -ge 200 ] 2>/dev/null && [ "$HTTP_CODE" -lt 300 ] 2>/dev/null; then
    echo "Notification sent to arm-transcoder (HTTP ${HTTP_CODE}): path=$SOURCE_PATH"
else
    echo "Failed to notify arm-transcoder (HTTP ${HTTP_CODE}): ${RESP_BODY}" >&2
    exit 1
fi
