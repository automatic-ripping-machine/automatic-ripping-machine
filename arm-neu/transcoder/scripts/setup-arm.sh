#!/usr/bin/env bash
# ARM Setup Script - Configure ARM for external transcoding via arm-transcoder
#
# Patches an existing ARM arm.yaml to configure the transcoder webhook
# so ARM notifies arm-transcoder when a rip completes.
#
# Usage:
#   ./setup-arm.sh --url URL --config DIR [--secret SECRET] [--local-raw PATH] [--shared-raw PATH] [--restart]
#
# Examples:
#   # Simple webhook (no auth)
#   ./setup-arm.sh --url http://TRANSCODER_IP:5000/webhook/arm --config /etc/arm/config
#
#   # Authenticated webhook
#   ./setup-arm.sh --url http://TRANSCODER_IP:5000/webhook/arm --config /etc/arm/config --secret myS3cret
#
#   # Local scratch storage (rip to local disk, move to shared storage before transcoding)
#   ./setup-arm.sh --url http://TRANSCODER_IP:5000/webhook/arm --config /etc/arm/config \
#     --secret myS3cret --local-raw /home/arm/media/raw --shared-raw /mnt/media/raw
#
#   # Docker ARM with container restart
#   ./setup-arm.sh --url http://TRANSCODER_IP:5000/webhook/arm --config /opt/arm/config --secret myS3cret --restart

set -euo pipefail

# --- Defaults ---
TRANSCODER_URL=""
ARM_CONFIG_DIR=""
WEBHOOK_SECRET=""
LOCAL_RAW_PATH=""
SHARED_RAW_PATH=""
RESTART=false

# --- Usage ---
usage() {
    cat <<EOF
Usage: $(basename "$0") --url URL --config DIR [--secret SECRET] [--local-raw PATH] [--shared-raw PATH] [--restart]

Configure an ARM installation for external transcoding via arm-transcoder.

Required:
  --url URL           Transcoder webhook URL (e.g. http://TRANSCODER_IP:5000/webhook/arm)
  --config DIR        Path to ARM config directory containing arm.yaml

Optional:
  --secret SECRET     Webhook secret (must match WEBHOOK_SECRET on the transcoder)
  --local-raw PATH    Local disk path where ARM rips to (e.g. /home/arm/media/raw)
  --shared-raw PATH   Shared storage path for handoff to transcoder (e.g. /mnt/media/raw)
  --restart           Restart ARM after setup (tries Docker first, then systemd)
  -h, --help          Show this help

When --local-raw and --shared-raw are both provided, ARM moves ripped files
from local disk to shared storage before notifying the transcoder.
EOF
    exit "${1:-0}"
}

# --- Parse arguments ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --url)
            TRANSCODER_URL="$2"
            shift 2
            ;;
        --config)
            ARM_CONFIG_DIR="$2"
            shift 2
            ;;
        --secret)
            WEBHOOK_SECRET="$2"
            shift 2
            ;;
        --local-raw)
            LOCAL_RAW_PATH="$2"
            shift 2
            ;;
        --shared-raw)
            SHARED_RAW_PATH="$2"
            shift 2
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        -h|--help)
            usage 0
            ;;
        *)
            echo "ERROR: Unknown argument: $1" >&2
            usage 1
            ;;
    esac
done

# --- Validate inputs ---
if [[ -z "$TRANSCODER_URL" ]]; then
    echo "ERROR: --url is required" >&2
    usage 1
fi

if [[ -z "$ARM_CONFIG_DIR" ]]; then
    echo "ERROR: --config is required" >&2
    usage 1
fi

ARM_YAML="$ARM_CONFIG_DIR/arm.yaml"
if [[ ! -f "$ARM_YAML" ]]; then
    echo "ERROR: arm.yaml not found at $ARM_YAML" >&2
    echo "       Make sure --config points to the ARM config directory." >&2
    exit 1
fi

# Validate local-raw / shared-raw pairing
if [[ -n "$LOCAL_RAW_PATH" && -z "$SHARED_RAW_PATH" ]] || [[ -z "$LOCAL_RAW_PATH" && -n "$SHARED_RAW_PATH" ]]; then
    echo "ERROR: --local-raw and --shared-raw must be used together" >&2
    usage 1
fi

echo "=== ARM Setup for arm-transcoder ==="
echo "Transcoder URL: $TRANSCODER_URL"
echo "ARM config:     $ARM_CONFIG_DIR"
echo "Webhook auth:   $(if [[ -n "$WEBHOOK_SECRET" ]]; then echo "yes (secret configured)"; else echo "none"; fi)"
if [[ -n "$LOCAL_RAW_PATH" ]]; then
    echo "Local scratch:  $LOCAL_RAW_PATH → $SHARED_RAW_PATH"
fi
echo ""

# --- Helper: patch a YAML key ---
# Sets KEY: VALUE in arm.yaml. If the key exists (uncommented), replaces it.
# If the key only exists commented out, uncomments the first occurrence.
# If the key doesn't exist at all, appends it.
patch_yaml() {
    local key="$1"
    local value="$2"
    local file="$ARM_YAML"

    if grep -qE "^${key}:" "$file"; then
        # Key exists uncommented — replace it
        sed -i "s|^${key}:.*|${key}: ${value}|" "$file"
    elif grep -qE "^#\s*${key}:" "$file"; then
        # Key exists only as comment — uncomment and set value (first occurrence)
        sed -i "0,/^#\s*${key}:.*/s||${key}: ${value}|" "$file"
    else
        # Key doesn't exist — append it
        echo "${key}: ${value}" >> "$file"
    fi
}

# --- Patch transcoding settings ---
echo "Patching arm.yaml..."

patch_yaml "SKIP_TRANSCODE" "false"
patch_yaml "RIPMETHOD" '"mkv"'
patch_yaml "DELRAWFILES" "false"

echo "  SKIP_TRANSCODE: false"
echo "  RIPMETHOD: \"mkv\""
echo "  DELRAWFILES: false"

# --- Configure transcoder webhook ---
echo ""
echo "Configuring transcoder webhook..."

patch_yaml "TRANSCODER_URL" "\"${TRANSCODER_URL}\""
echo "  TRANSCODER_URL: \"$TRANSCODER_URL\""

if [[ -n "$WEBHOOK_SECRET" ]]; then
    patch_yaml "TRANSCODER_WEBHOOK_SECRET" "\"${WEBHOOK_SECRET}\""
    echo "  TRANSCODER_WEBHOOK_SECRET: ****${WEBHOOK_SECRET: -4}"
else
    patch_yaml "TRANSCODER_WEBHOOK_SECRET" '""'
    echo "  TRANSCODER_WEBHOOK_SECRET: \"\""
fi

# --- Configure shared storage paths ---
if [[ -n "$LOCAL_RAW_PATH" ]]; then
    patch_yaml "LOCAL_RAW_PATH" "\"${LOCAL_RAW_PATH}\""
    patch_yaml "SHARED_RAW_PATH" "\"${SHARED_RAW_PATH}\""
    echo "  LOCAL_RAW_PATH: \"$LOCAL_RAW_PATH\""
    echo "  SHARED_RAW_PATH: \"$SHARED_RAW_PATH\""
fi

# --- Restart ARM if requested ---
if [[ "$RESTART" == true ]]; then
    echo ""
    echo "Restarting ARM..."
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^arm"; then
        CONTAINER=$(docker ps --format '{{.Names}}' | grep "^arm" | head -1)
        docker restart "$CONTAINER"
        echo "  Restarted Docker container: $CONTAINER"
    elif systemctl is-active --quiet armui 2>/dev/null; then
        systemctl restart armui
        echo "  Restarted systemd service: armui"
    else
        echo "  WARNING: Could not find ARM Docker container or systemd service to restart."
        echo "           Please restart ARM manually."
    fi
fi

# --- Summary ---
echo ""
echo "=== Setup complete ==="
echo ""
echo "Test with:"
if [[ -n "$WEBHOOK_SECRET" ]]; then
    cat <<EOF
  curl -s -X POST ${TRANSCODER_URL} \\
    -H "Content-Type: application/json" \\
    -H "X-Webhook-Secret: ${WEBHOOK_SECRET}" \\
    -d '{"title": "ARM notification", "body": "Test Movie (2024) rip complete. Starting transcode.", "type": "info"}'
EOF
else
    cat <<EOF
  curl -s -X POST ${TRANSCODER_URL} \\
    -H "Content-Type: application/json" \\
    -d '{"title": "ARM notification", "body": "Test Movie (2024) rip complete. Starting transcode.", "type": "info"}'
EOF
fi
echo ""
