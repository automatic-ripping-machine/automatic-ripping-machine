#!/bin/bash
# ARM Post-Processing Script v3
# Uses smart identification before moving to Radarr/Sonarr

set -euo pipefail

RAW="/mnt/media/rips/raw"
COMPLETED="/mnt/media/rips/completed"
MOVIES_DIR="/mnt/media/movies"
TV_DIR="/mnt/media/tv"
MUSIC_DIR="/mnt/media/music"
LOG="/mnt/media/docker/arm/move-completed.log"
SMART_ID="/mnt/media/docker/arm/smart-identify.sh"

# API Keys
RADARR_API="YOUR_RADARR_API_KEY"
SONARR_API="YOUR_SONARR_API_KEY"
RADARR_URL="http://localhost:7878"
SONARR_URL="http://localhost:8989"

# Email settings
EMAIL_TO="your@email.com"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG"
}

send_alert() {
    local subject="$1"
    local body="$2"
    echo -e "$body" | mail -s "$subject" "$EMAIL_TO"
    log "Email alert sent: $subject"
}

# Check if folder has finished ripping (no active makemkv process for this path)
is_rip_complete() {
    local folder="$1"
    local folder_name
    folder_name=$(basename "$folder")

    # Check if MakeMKV is still writing to this folder
    if docker exec arm pgrep -f "makemkv.*$folder_name" > /dev/null 2>&1; then
        return 1
    fi

    # Check for video files
    if ! find "$folder" -maxdepth 2 -type f \( -name "*.mkv" -o -name "*.mp4" \) 2>/dev/null | grep -q .; then
        return 1
    fi

    return 0
}

# Check if it's TV content
is_tv_content() {
    local name="$1"
    [[ "$name" =~ [Ss][0-9]+[Ee][0-9]+ ]] || \
    [[ "$name" =~ \{tvdb- ]] || \
    [[ "$name" =~ [Ss]eason ]]
}

# Add movie to Radarr if not already present
ensure_in_radarr() {
    local title="$1"
    local year="$2"
    local search_term="$title $year"
    local encoded

    encoded=$(echo "$search_term" | sed 's/ /%20/g')

    # Check if already in library
    local existing
    existing=$(curl -s "$RADARR_URL/api/v3/movie" -H "X-Api-Key: $RADARR_API" | \
        python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data:
    if m.get('title','').lower() == '${title}'.lower() and m.get('year') == int('${year}'):
        print(m.get('id'))
        break
" 2>/dev/null)

    if [[ -n "$existing" ]]; then
        log "  Already in Radarr library (ID: $existing)"
        return 0
    fi

    # Lookup and add
    local lookup
    lookup=$(curl -s "$RADARR_URL/api/v3/movie/lookup?term=$encoded" -H "X-Api-Key: $RADARR_API" 2>/dev/null)

    local tmdb_id
    tmdb_id=$(echo "$lookup" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data:
    print(data[0].get('tmdbId', ''))
" 2>/dev/null)

    if [[ -n "$tmdb_id" ]]; then
        curl -s -X POST "$RADARR_URL/api/v3/movie" \
            -H "X-Api-Key: $RADARR_API" \
            -H "Content-Type: application/json" \
            -d "{
                \"tmdbId\": $tmdb_id,
                \"title\": \"$title\",
                \"rootFolderPath\": \"/movies\",
                \"qualityProfileId\": 1,
                \"monitored\": true,
                \"addOptions\": {\"searchForMovie\": false}
            }" > /dev/null 2>&1
        log "  Added to Radarr (tmdbId: $tmdb_id)"
    fi
}

# Trigger Radarr library scan
trigger_radarr_scan() {
    curl -s -X POST "$RADARR_URL/api/v3/command" \
        -H "X-Api-Key: $RADARR_API" \
        -H "Content-Type: application/json" \
        -d '{"name": "RescanMovie"}' > /dev/null 2>&1
    log "  Triggered Radarr scan"
}

# Process raw directory (rips that skipped transcode)
process_raw() {
    for dir in "$RAW"/*; do
        [[ -d "$dir" ]] || continue
        local name
        name=$(basename "$dir")

        # Skip if still ripping
        if ! is_rip_complete "$dir"; then
            log "Skipping $name (still ripping or no video files)"
            continue
        fi

        log "Processing raw: $name"

        # Run smart identification
        local identified_path
        if identified_path=$("$SMART_ID" "$dir" 2>/dev/null); then
            if [[ -n "$identified_path" && -d "$identified_path" ]]; then
                dir="$identified_path"
                name=$(basename "$dir")
            fi
        fi

        # Extract title and year from folder name
        local title year
        title=$(echo "$name" | sed -E 's/ *\([0-9]{4}\)$//')
        year=$(echo "$name" | grep -oP '\((\d{4})\)' | tr -d '()' || echo "")

        if is_tv_content "$name"; then
            log "  TV content - moving to $TV_DIR"
            mv "$dir" "$TV_DIR/" 2>/dev/null || true
        else
            log "  Movie content - moving to $MOVIES_DIR"
            [[ -n "$year" ]] && ensure_in_radarr "$title" "$year"
            mv "$dir" "$MOVIES_DIR/" 2>/dev/null || true
            trigger_radarr_scan
        fi
    done
}

# Process completed directory (transcoded rips)
process_completed() {
    for subdir in "$COMPLETED" "$COMPLETED/movies" "$COMPLETED/tv"; do
        [[ -d "$subdir" ]] || continue

        for dir in "$subdir"/*; do
            [[ -d "$dir" ]] || continue
            local name
            name=$(basename "$dir")

            # Skip parent folders
            [[ "$name" == "movies" || "$name" == "tv" ]] && continue

            # Skip empty dirs
            [[ -z "$(ls -A "$dir" 2>/dev/null)" ]] && continue

            # Skip if no video files
            if ! find "$dir" -maxdepth 2 -type f \( -name "*.mkv" -o -name "*.mp4" \) 2>/dev/null | grep -q .; then
                continue
            fi

            log "Processing completed: $name"

            # Run smart identification
            local identified_path
            if identified_path=$("$SMART_ID" "$dir" 2>/dev/null); then
                if [[ -n "$identified_path" && -d "$identified_path" ]]; then
                    dir="$identified_path"
                    name=$(basename "$dir")
                fi
            fi

            # Extract title and year
            local title year
            title=$(echo "$name" | sed -E 's/ *\([0-9]{4}\)$//')
            year=$(echo "$name" | grep -oP '\((\d{4})\)' | tr -d '()' || echo "")

            if is_tv_content "$name"; then
                log "  TV content - moving to $TV_DIR"
                mv "$dir" "$TV_DIR/" 2>/dev/null || true
            else
                log "  Movie content - moving to $MOVIES_DIR"
                [[ -n "$year" ]] && ensure_in_radarr "$title" "$year"
                mv "$dir" "$MOVIES_DIR/" 2>/dev/null || true
                trigger_radarr_scan
            fi
        done
    done
}

# Main
log "=== Starting post-processing ==="
process_raw
process_completed
log "=== Post-processing complete ==="
