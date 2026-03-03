#!/usr/bin/env bash

# Downloads and filters the FindVUK community keydb.cfg for MakeMKV.
#
# MakeMKV's HK server (hkdata.crabdance.com) is dead, so it can no longer
# derive AACS volume keys on its own. This script fetches the community
# keydb.cfg from the FindVUK Online Database and strips out | DK | and | PK |
# entries that conflict with MakeMKV's internal AACS engine.
#
# - Runs at container startup in background (called from arm_user_files_setup.sh)
# - Can be run manually: docker exec -u arm arm-rippers /opt/arm/scripts/update_keydb.sh
# - Skips download if existing keydb is fresh (default: 7 days)
# - Use --force to bypass age check
#
# The FindVUK ZIP is ~22 MB served from a free host (bplaced.net) that can be
# very slow (10-50 KB/s) or return 503 errors. This script handles that by:
#   - Running in background (never blocks container startup)
#   - Retrying with generous timeouts (the server is slow, not dead)
#   - Aborting stalled connections (--speed-limit/--speed-time)
#   - Preserving the existing keydb on any failure

set -euo pipefail

ARM_CONFIG="${ARM_CONFIG_FILE:-/etc/arm/config/arm.yaml}"
KEYDB_URL="http://fvonline-db.bplaced.net/fv_download.php?lang=eng"
MAKEMKV_DIR="/home/arm/.MakeMKV"
KEYDB_FILE="$MAKEMKV_DIR/keydb.cfg"
MAX_AGE_DAYS=7
FORCE=false
MAX_RETRIES=3
CURL_CONNECT_TIMEOUT=15
CURL_MAX_TIME=600
# Abort if transfer drops below 1 KB/s for 30 seconds (stall detection)
CURL_SPEED_LIMIT=1024
CURL_SPEED_TIME=30

if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

# Check if disabled via environment variable (takes precedence) or arm.yaml.
# ARM_COMMUNITY_KEYDB env var > MAKEMKV_COMMUNITY_KEYDB in arm.yaml > default (true)
if [[ "$FORCE" == false ]]; then
    if [[ -n "${ARM_COMMUNITY_KEYDB:-}" ]]; then
        # Env var is set — use it directly
        enabled="${ARM_COMMUNITY_KEYDB,,}"  # lowercase
    else
        # Fall back to arm.yaml setting
        enabled=$(python3 -c "
import yaml, sys
try:
    cfg = yaml.safe_load(open('$ARM_CONFIG'))
    print(str(cfg.get('MAKEMKV_COMMUNITY_KEYDB', True)).lower())
except Exception:
    print('true')
" 2>/dev/null || echo "true")
    fi
    if [[ "$enabled" != "true" ]]; then
        echo "FindVUK community keydb is disabled — skipping"
        exit 0
    fi
fi

# Check if existing keydb is fresh enough
if [[ "$FORCE" == false && -f "$KEYDB_FILE" ]]; then
    file_age=$(( ( $(date +%s) - $(stat -c %Y "$KEYDB_FILE") ) / 86400 ))
    if (( file_age < MAX_AGE_DAYS )); then
        echo "keydb.cfg is ${file_age}d old (< ${MAX_AGE_DAYS}d) — skipping update"
        exit 0
    fi
    echo "keydb.cfg is ${file_age}d old (>= ${MAX_AGE_DAYS}d) — updating"
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

ZIP_FILE="$TMPDIR/keydb.zip"
RAW_KEYDB="$TMPDIR/keydb_raw.cfg"
FILTERED_KEYDB="$TMPDIR/keydb.cfg"

# Download the ZIP with retry logic, generous timeouts, and stall detection.
# The bplaced.net server is a free host that can be very slow — allow up to
# 10 minutes per attempt but abort if the connection stalls completely.
echo "Downloading keydb from FindVUK..."
download_ok=false
for attempt in $(seq 1 "$MAX_RETRIES"); do
    if curl -fsSL \
        --connect-timeout "$CURL_CONNECT_TIMEOUT" \
        --max-time "$CURL_MAX_TIME" \
        --speed-limit "$CURL_SPEED_LIMIT" \
        --speed-time "$CURL_SPEED_TIME" \
        -o "$ZIP_FILE" "$KEYDB_URL"; then
        download_ok=true
        break
    fi
    if [[ "$attempt" -lt "$MAX_RETRIES" ]]; then
        backoff=$(( attempt * 5 ))
        echo "[WARN] Download attempt $attempt/$MAX_RETRIES failed — retrying in ${backoff}s..."
        sleep "$backoff"
    fi
done
if [[ "$download_ok" = false ]]; then
    echo "[WARN] Failed to download keydb after $MAX_RETRIES attempts — network error or site unavailable" >&2
    exit 0
fi

# Verify we got a ZIP (not an HTML error page)
if ! file "$ZIP_FILE" | grep -q 'Zip archive'; then
    echo "[WARN] Downloaded file is not a ZIP archive — site may have changed"
    exit 0
fi

# Extract keydb.cfg from ZIP using python3 (unzip not available in container)
if ! python3 -c "
import zipfile, sys
with zipfile.ZipFile('$ZIP_FILE') as z:
    names = z.namelist()
    cfg = [n for n in names if n.endswith('keydb.cfg')]
    if not cfg:
        print('No keydb.cfg found in ZIP. Contents: ' + str(names), file=sys.stderr)
        sys.exit(1)
    with open('$RAW_KEYDB', 'wb') as f:
        f.write(z.read(cfg[0]))
"; then
    echo "[WARN] Failed to extract keydb.cfg from ZIP"
    exit 0
fi

# Filter out | DK | and | PK | lines (conflict with MakeMKV's AACS engine on MKBv82+)
grep -v '| DK |' "$RAW_KEYDB" | grep -v '| PK |' > "$FILTERED_KEYDB"

# Sanity check: filtered file should contain VUK entries
if ! grep -q '| V |' "$FILTERED_KEYDB"; then
    echo "[WARN] Filtered keydb.cfg contains no VUK entries — aborting"
    exit 0
fi

vuk_count=$(grep -c '| V |' "$FILTERED_KEYDB")
echo "Filtered keydb.cfg: ${vuk_count} VUK entries (DK/PK lines removed)"

# Atomic replace: write to .tmp then mv
cp "$FILTERED_KEYDB" "${KEYDB_FILE}.tmp"
mv "${KEYDB_FILE}.tmp" "$KEYDB_FILE"
chown arm:arm "$KEYDB_FILE"

echo "keydb.cfg updated successfully at $KEYDB_FILE"
