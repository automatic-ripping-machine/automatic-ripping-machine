#!/bin/bash
# Smart Disc Identification Script
# Improves on ARM's flaky CRC lookup by using disc label parsing + runtime matching

set -euo pipefail

# Configuration
RADARR_API="YOUR_RADARR_API_KEY"
RADARR_URL="http://localhost:7878"
SONARR_API="YOUR_SONARR_API_KEY"
SONARR_URL="http://localhost:8989"
EMAIL_TO="your@email.com"
RUNTIME_TOLERANCE=300  # 5 minutes in seconds

LOG="/mnt/media/docker/arm/smart-identify.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG"
    echo "$1"
}

send_alert() {
    local subject="$1"
    local body="$2"
    echo -e "$body" | mail -s "$subject" "$EMAIL_TO"
    log "Email sent: $subject"
}

# Parse disc label into searchable title
# MARVEL_STUDIOS_GUARDIANS_3 -> "Guardians of the Galaxy Vol 3"
# JOHN_WICK_4 -> "John Wick Chapter 4"
parse_disc_label() {
    local label="$1"
    local parsed

    # Remove common studio prefixes
    parsed=$(echo "$label" | sed -E '
        s/^(MARVEL_STUDIOS_?|DISNEY_?|PIXAR_?|WARNER_?|WARNER_BROS_?|WB_?)//i
        s/^(UNIVERSAL_?|SONY_?|COLUMBIA_?|PARAMOUNT_?|20TH_CENTURY_?|FOX_?)//i
        s/^(LIONSGATE_?|MGM_?|DREAMWORKS_?|NEW_LINE_?|HBO_?|A24_?)//i
        s/^(BLU-?RAY_?|DVD_?|BD_?|UHD_?|4K_?)//i
        s/_?(DISC_?[0-9]*|D[0-9]+)$//i
    ')

    # Replace underscores with spaces
    parsed=$(echo "$parsed" | tr '_' ' ')

    # Handle franchise-specific patterns (order matters - check specific before generic)

    # Guardians of the Galaxy
    if [[ "$parsed" =~ ^GUARDIANS[[:space:]]*([0-9]+)$ ]]; then
        parsed="Guardians of the Galaxy Vol ${BASH_REMATCH[1]}"
    elif [[ "$parsed" =~ ^GUARDIANS[[:space:]]+OF[[:space:]]+THE[[:space:]]+GALAXY[[:space:]]*([0-9]+)?$ ]]; then
        if [[ -n "${BASH_REMATCH[1]}" ]]; then
            parsed="Guardians of the Galaxy Vol ${BASH_REMATCH[1]}"
        else
            parsed="Guardians of the Galaxy"
        fi
    fi

    # John Wick
    if [[ "$parsed" =~ ^JOHN[[:space:]]*WICK[[:space:]]*([0-9]+)$ ]]; then
        parsed="John Wick Chapter ${BASH_REMATCH[1]}"
    fi

    # Spider-Man (handle hyphen variations)
    if [[ "$parsed" =~ ^SPIDER[[:space:]]*MAN ]]; then
        parsed=$(echo "$parsed" | sed 's/SPIDER[[:space:]]*MAN/Spider-Man/i')
    fi

    # Mission Impossible
    if [[ "$parsed" =~ ^MISSION[[:space:]]*IMPOSSIBLE ]]; then
        parsed=$(echo "$parsed" | sed 's/MISSION[[:space:]]*IMPOSSIBLE/Mission Impossible/i')
    fi

    # Jurassic (Park/World)
    if [[ "$parsed" =~ ^JURASSIC[[:space:]]*WORLD ]]; then
        parsed=$(echo "$parsed" | sed 's/JURASSIC[[:space:]]*WORLD/Jurassic World/i')
    fi

    # Fast and Furious variants
    if [[ "$parsed" =~ ^(FAST|F)[[:space:]]*(AND|&|N)?[[:space:]]*(FURIOUS)?[[:space:]]*([0-9]+|X)$ ]]; then
        local num="${BASH_REMATCH[4]}"
        if [[ "$num" == "X" ]]; then
            parsed="Fast X"
        else
            parsed="Fast & Furious $num"
        fi
    fi

    # Transformers
    if [[ "$parsed" =~ ^TRANSFORMERS ]]; then
        parsed=$(echo "$parsed" | sed 's/TRANSFORMERS/Transformers/i')
    fi

    # Avatar
    if [[ "$parsed" =~ ^AVATAR[[:space:]]*(2|WAY|THE)?.*WATER ]]; then
        parsed="Avatar The Way of Water"
    fi

    # Clean up extra spaces and trim
    parsed=$(echo "$parsed" | sed 's/  */ /g' | xargs)

    # Title case (only if not already processed by specific handlers)
    if [[ ! "$parsed" =~ [a-z] ]]; then
        # Convert to title case for all-caps strings
        parsed=$(echo "$parsed" | awk '{for(i=1;i<=NF;i++){$i=toupper(substr($i,1,1))tolower(substr($i,2))}}1')
    fi

    echo "$parsed"
}

# Get video runtime in seconds using ffprobe
get_runtime() {
    local video_file="$1"
    local container_path

    # Convert host path to container path
    container_path=$(echo "$video_file" | sed 's|/mnt/media/rips/|/home/arm/media/|')

    # Get duration via ffprobe in container
    docker exec arm ffprobe -v error -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 "$container_path" 2>/dev/null | cut -d. -f1
}

# Search Radarr and return best match as JSON
search_radarr() {
    local title="$1"
    local runtime="$2"
    local encoded

    encoded=$(echo "$title" | sed 's/ /%20/g')

    curl -s "$RADARR_URL/api/v3/movie/lookup?term=$encoded" \
        -H "X-Api-Key: $RADARR_API" 2>/dev/null | \
    python3 -c "
import sys, json

try:
    data = json.load(sys.stdin)
    runtime = int('${runtime}') if '${runtime}'.isdigit() else 0
    tolerance = int('${RUNTIME_TOLERANCE}')

    if not data:
        sys.exit(0)

    best_match = None
    best_score = 0

    for movie in data[:10]:  # Check top 10 results
        score = 0
        movie_runtime = movie.get('runtime', 0) * 60  # Radarr returns minutes

        # Runtime match scoring
        if runtime > 0 and movie_runtime > 0:
            diff = abs(runtime - movie_runtime)
            if diff <= tolerance:
                score += 100 - (diff / tolerance * 50)  # Up to 100 points for exact match
            elif diff <= tolerance * 2:
                score += 25  # Partial credit for close match

        # Popularity bonus (more popular = more likely correct)
        popularity = movie.get('popularity', 0)
        score += min(popularity / 10, 20)  # Up to 20 points

        # Year recency bonus (newer movies more likely for new rips)
        year = movie.get('year', 2000)
        if year >= 2020:
            score += 10
        elif year >= 2015:
            score += 5

        if score > best_score:
            best_score = score
            best_match = movie

    if best_match and best_score >= 50:
        result = {
            'title': best_match.get('title'),
            'year': best_match.get('year'),
            'tmdbId': best_match.get('tmdbId'),
            'runtime': best_match.get('runtime'),
            'score': best_score,
            'confident': best_score >= 75
        }
        print(json.dumps(result))
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Main identification function
identify_rip() {
    local folder="$1"
    local folder_name
    local disc_label
    local video_file
    local runtime
    local parsed_title
    local match

    folder_name=$(basename "$folder")
    log "Processing: $folder_name"

    # Extract disc label (remove year and timestamp suffixes)
    disc_label=$(echo "$folder_name" | sed -E 's/ *\([0-9]{4}\)(_[0-9]+)?$//' | tr '-' '_' | tr '[:lower:]' '[:upper:]')
    log "  Disc label: $disc_label"

    # Find video file
    video_file=$(find "$folder" -maxdepth 1 -type f \( -name "*.mkv" -o -name "*.mp4" \) | head -1)

    if [[ -z "$video_file" ]]; then
        log "  No video file found yet, skipping"
        return 1
    fi

    # Get runtime
    runtime=$(get_runtime "$video_file")
    log "  Video runtime: ${runtime}s ($(( runtime / 60 )) min)"

    # Parse disc label into search term
    parsed_title=$(parse_disc_label "$disc_label")
    log "  Parsed search term: $parsed_title"

    # Search Radarr
    match=$(search_radarr "$parsed_title" "$runtime")

    if [[ -z "$match" ]]; then
        log "  No confident match found"
        send_alert "[ARM] Manual ID needed: $folder_name" \
            "ARM ripped a disc but smart identification couldn't find a confident match.\n\nFolder: $folder_name\nDisc label: $disc_label\nParsed as: $parsed_title\nRuntime: $(( runtime / 60 )) minutes\n\nPlease manually identify and rename:\n$folder"
        return 1
    fi

    # Parse match result
    local match_title match_year match_score confident
    match_title=$(echo "$match" | python3 -c "import sys,json; print(json.load(sys.stdin)['title'])")
    match_year=$(echo "$match" | python3 -c "import sys,json; print(json.load(sys.stdin)['year'])")
    match_score=$(echo "$match" | python3 -c "import sys,json; print(json.load(sys.stdin)['score'])")
    confident=$(echo "$match" | python3 -c "import sys,json; print(json.load(sys.stdin)['confident'])")

    log "  Match: $match_title ($match_year) - Score: $match_score, Confident: $confident"

    if [[ "$confident" == "True" ]]; then
        # High confidence - auto rename
        local new_name="${match_title} (${match_year})"
        new_name=$(echo "$new_name" | sed 's/[:]/-/g; s/[?]//g')  # Sanitize filename
        local new_path="$(dirname "$folder")/$new_name"

        if [[ "$folder" != "$new_path" ]]; then
            log "  Auto-renaming: $folder_name -> $new_name"
            mv "$folder" "$new_path"
            echo "$new_path"
        else
            log "  Name already correct"
            echo "$folder"
        fi
    else
        # Medium confidence - rename but alert
        local new_name="${match_title} (${match_year})"
        new_name=$(echo "$new_name" | sed 's/[:]/-/g; s/[?]//g')
        local new_path="$(dirname "$folder")/$new_name"

        log "  Medium confidence - renaming but sending alert"
        if [[ "$folder" != "$new_path" ]]; then
            mv "$folder" "$new_path"
        fi

        send_alert "[ARM] Please verify: $new_name" \
            "ARM ripped a disc and smart ID found a probable match, but confidence is medium.\n\nOriginal: $folder_name\nIdentified as: $new_name\nConfidence score: $match_score/100\n\nPlease verify this is correct.\nLocation: $new_path"

        echo "$new_path"
    fi
}

# Run identification on a folder
if [[ $# -ge 1 ]]; then
    identify_rip "$1"
else
    echo "Usage: $0 <folder_path>"
    echo "  Identifies a ripped disc folder and renames it based on TMDB match"
    exit 1
fi
