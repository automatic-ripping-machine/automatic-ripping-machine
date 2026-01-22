# Smart Post-Processing for Disc Identification

A post-processing solution that fixes ARM's unreliable disc identification by re-identifying completed rips using disc label parsing and runtime matching.

## Problem

ARM's CRC64 online lookup frequently returns incorrect titles, especially for newer releases. The database may not have accurate entries, leading to misidentified discs.

**Examples of bad identifications:**
- `MARVEL_STUDIOS_GUARDIANS_3` → identified as "Guardians of the Galaxy (2014)" instead of Vol. 3 (2023)
- Blu-rays without readable `bdmt_eng.xml` often get completely wrong matches

**Related issues:**
- [#1636 - DVDs not ripping after Title Search](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1636)
- [#714 - If DVD has a title use it instead of title name from identification](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/714)

## Solution

Post-processing scripts that re-identify completed rips using:

1. **Disc label parsing** - Extracts meaningful titles from labels like `MARVEL_STUDIOS_GUARDIANS_3`
2. **Runtime matching** - Uses ffprobe to get actual video duration, matches against TMDB via Radarr's API
3. **Confidence scoring** - Only auto-renames when confident, otherwise sends email alert for manual review

This works *after* ARM completes the rip - no ARM code changes needed.

## How It Works

```
Disc Label: MARVEL_STUDIOS_GUARDIANS_3
     ↓
Parse: "Guardians of the Galaxy Vol 3"
     ↓
ffprobe: Runtime = 8976s (149 min)
     ↓
Radarr/TMDB Search → Filter by runtime (±5 min)
     ↓
Match: "Guardians of the Galaxy Vol. 3" (2023) = 150 min ✓
     ↓
Confidence: HIGH → Auto-rename folder
```

## Requirements

- **Radarr** running with API access (used for TMDB lookups)
- **ffprobe** available (included in ARM container)
- **Email** configured via `mail` command (for alerts on uncertain matches)

## Installation

### 1. Copy scripts to your ARM config directory

```bash
cp smart-identify.sh /etc/arm/config/
cp move-completed.sh /etc/arm/config/
chmod +x /etc/arm/config/smart-identify.sh /etc/arm/config/move-completed.sh
```

### 2. Configure the scripts

Edit both scripts and update:

```bash
# API Keys - get from Radarr Settings → General
RADARR_API="your-radarr-api-key"
RADARR_URL="http://localhost:7878"

# Email for alerts
EMAIL_TO="your@email.com"
```

### 3. Set up cron job

```bash
crontab -e
# Add this line:
*/5 * * * * /etc/arm/config/move-completed.sh
```

## Scripts

| Script | Purpose |
|--------|---------|
| `smart-identify.sh` | Core identification logic - parses disc labels, gets runtime, matches via Radarr/TMDB |
| `move-completed.sh` | Integration script - finds completed rips, runs identification, moves to library |

## Confidence Scoring

| Score | Action |
|-------|--------|
| ≥75 | Auto-rename, no alert |
| 50-74 | Auto-rename + email alert to verify |
| <50 | No rename, email alert for manual identification |

**Scoring factors:**
- **Runtime match** (up to 100 pts) - Primary signal, within ±5 min tolerance
- **Popularity** (up to 20 pts) - More popular movies score higher
- **Year** (up to 10 pts) - Recent releases prioritized for new rips

## Supported Disc Label Patterns

The parser handles common patterns:

| Disc Label | Parsed As |
|------------|-----------|
| `MARVEL_STUDIOS_GUARDIANS_3` | Guardians of the Galaxy Vol 3 |
| `JOHN_WICK_4` | John Wick Chapter 4 |
| `SPIDER_MAN_NO_WAY_HOME` | Spider-Man No Way Home |
| `FAST_X` | Fast X |
| `AVATAR_WAY_OF_WATER` | Avatar The Way of Water |

**Studio prefixes automatically removed:**
- MARVEL_STUDIOS_, DISNEY_, PIXAR_, WARNER_, UNIVERSAL_
- SONY_, PARAMOUNT_, LIONSGATE_, MGM_, A24_, etc.

## Adding Custom Patterns

Edit `smart-identify.sh` and add patterns to the `parse_disc_label()` function:

```bash
# Example: Handle "MISSION_IMPOSSIBLE_7"
if [[ "$parsed" =~ ^MISSION[[:space:]]*IMPOSSIBLE[[:space:]]*([0-9]+)$ ]]; then
    parsed="Mission: Impossible ${BASH_REMATCH[1]}"
fi
```

## Limitations

- Requires Radarr for TMDB lookups (Sonarr support for TV could be added)
- Runtime matching assumes main feature only (won't work well with bonus features included)
- Very new releases may not be in TMDB yet

## Troubleshooting

**Check logs:**
```bash
tail -50 /path/to/smart-identify.log
tail -50 /path/to/move-completed.log
```

**Test manually:**
```bash
/etc/arm/config/smart-identify.sh /path/to/ripped/folder
```

## License

MIT - Same as ARM project.
