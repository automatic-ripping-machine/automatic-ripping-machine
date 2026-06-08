# ARM Transcoder Webhook Payload Spec

ARM sends a JSON webhook to the transcoder when a rip completes. The transcoder uses this payload to determine what to transcode and how to name output files.

The wire shape is defined in `arm_contracts.WebhookPayload` (and `WebhookTrackMeta` for track entries). Both arm-neu and the transcoder import these models, so a field rename or type change becomes a CI failure (via the lockstep workflow), not a 422 in production.

**ARM is the single source of truth for naming.** The transcoder uses `output_path` and `title_name` from the payload directly - it never invents its own names or partitions output by video type.

## Endpoint

```
POST /webhook/arm
Content-Type: application/json
X-Webhook-Secret: <optional secret>
X-Api-Version: 2
```

The `X-Api-Version: 2` header is required as of v17.4.0; missing-header requests are rejected with HTTP 400. See `docs/AUTHENTICATION.md`.

## Payload Schema

### Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string (<=500) | yes | Notification title (e.g. "Rip complete"); stripped of control chars |
| `body` | string (<=2000) | one of body/message | Direct-POST notification text |
| `message` | string (<=2000) | one of body/message | Apprise-shaped notification text. Use `effective_body` to read whichever is set |
| `job_id` | int | yes | ARM job ID (arm-neu sends as string; coerced) |
| `status` | string (<=50) | no | Job status at time of notification (e.g. `"waiting_transcode"`) |
| `type` | `WebhookEventType` enum | no | Notification kind. Currently always `"info"` |
| `video_type` | string (<=50) | no | `"movie"`, `"series"`, or `"music"` |
| `year` | string (<=10) | no | Release year |
| `disctype` | string (<=50) | no | `"bluray"`, `"bluray4k"`, `"dvd"`, etc. |
| `poster_url` | string (<=1000) | no | Poster image URL (from OMDb/TMDb) |
| `input_path` | string (<=1000) | no | Source directory **relative** to ARM's share root. The transcoder joins this to `settings.raw_path`. Rejected if absolute or contains `..` |
| `output_path` | string (<=1000) | no | Destination directory **relative** to ARM's completed share. The transcoder joins this to `settings.completed_path`. Same relative/`..` validation as `input_path` |
| `title_name` | string (<=500) | no | Pre-rendered filename stem from ARM's naming engine. Independent of `output_path` (which is the directory). |
| `multi_title` | bool | no | `true` when the job has multiple distinct titles (e.g. TV episodes) |
| `config_overrides` | `TranscodeJobConfig` \| null | no | Per-job preset + override envelope: `{"preset_slug": "<slug>", "overrides": {...}, "delete_source": bool, "output_extension": "mkv"}` |
| `tracks` | array of `WebhookTrackMeta` \| null | no | Per-track manifest. Always populated when the job has tracks |

### Track manifest (`tracks[]`)

Each entry is a `WebhookTrackMeta` describing one ripped track file. All string fields default to `""` rather than null - empty values arrive as empty strings.

| Field | Type | Description |
|-------|------|-------------|
| `track_number` | string | Track number on the disc (e.g. `"0"`, `"1"`) |
| `title` | string | Display title for this track. **Precedence**: `episode_name` > `track.title` > `job.title` |
| `year` | string | Track-level year override, or job year |
| `video_type` | string | Track-level type override, or job type |
| `filename` | string | Source MKV filename in the raw directory (e.g. `"Show Disc 1_t00.mkv"`) |
| `has_custom_title` | bool | `true` if the track has a per-track title or custom filename |
| `output_path` | string | Per-track relative output directory (joined to `settings.completed_path`). May differ per track for series (e.g. different seasons) |
| `title_name` | string | Pre-rendered output filename stem for this track (sanitized, no extension). The transcoder uses this as-is |
| `episode_number` | string | Episode number (e.g. `"6"`); empty string if unmatched |
| `episode_name` | string | Episode name from TVDB (e.g. `"Firefall"`); empty string if unmatched |

### Title field precedence

The `title` field on each track follows:

1. `episode_name` - track has been matched to a TVDB episode
2. `track.title` - set by auto-match or manual override
3. `job.title` - fallback to the show/movie name

Manual episode corrections in the UI propagate into the webhook even if an earlier auto-match set a different `track.title`.

### Naming contract

`title_name` is the **authoritative output filename** for each track. ARM pre-renders it using the configured patterns (`TV_TITLE_PATTERN`, `MOVIE_TITLE_PATTERN`, etc.) and sanitizes it for filesystem use.

The transcoder must:
- Use `title_name` as the output filename (adding the extension)
- Use `output_path` as the output subdirectory
- Never apply its own naming logic to matched tracks
- Only generate names for scratch/temp files during transcoding

### Path policy

`input_path` and `output_path` are **always relative** to ARM's share roots. The transcoder joins them to its mounted `settings.raw_path` and `settings.completed_path`. The contract validator rejects:

- Absolute paths (`/foo`, `\foo`)
- Any segment equal to `..` (after normalizing `\` to `/`)

ARM's `_build_webhook_payload` (`arm/ripper/utils.py`) sanitizes each segment via `render_folder`; the contract validator is belt-and-braces.

There is no per-type subdirectory routing on the transcoder side: all `MOVIES_SUBDIR`/`TV_SUBDIR`/`AUDIO_SUBDIR`/`UNIDENTIFIED_SUBDIR` partitioning happens in ARM and is folded into `output_path` before the webhook fires.

### Unmatched tracks

Tracks without episode assignments have:
- `episode_number`: `""`
- `episode_name`: `""`
- `has_custom_title`: `false`
- `title_name`: fallback format like `"Show Name - Track 5"` (not `S01E` format)

These are typically disc extras (menus, trailers, featurettes). The transcoder still transcodes them using the provided `title_name`.

## Example payload

```json
{
  "title": "Rip complete",
  "body": "Kolchak: The Night Stalker ripped successfully",
  "type": "info",
  "job_id": 73,
  "video_type": "series",
  "year": "1974",
  "disctype": "bluray4k",
  "status": "waiting_transcode",
  "poster_url": "https://example.com/poster.jpg",
  "input_path": "Kolchak The Night Stalker Disc 2",
  "output_path": "TV/Kolchak- The Night Stalker/Season 01",
  "title_name": "Kolchak- The Night Stalker S01E06",
  "multi_title": true,
  "tracks": [
    {
      "track_number": "0",
      "title": "Firefall",
      "year": "1974",
      "video_type": "series",
      "filename": "Kolchak The Night Stalker Disc 2_t00.mkv",
      "has_custom_title": true,
      "output_path": "TV/Kolchak- The Night Stalker/Season 01",
      "title_name": "Firefall S01E06",
      "episode_number": "6",
      "episode_name": "Firefall"
    },
    {
      "track_number": "3",
      "title": "Kolchak: The Night Stalker",
      "year": "1974",
      "video_type": "series",
      "filename": "Kolchak The Night Stalker Disc 2_t03.mkv",
      "has_custom_title": false,
      "output_path": "TV/Kolchak- The Night Stalker/Season 01",
      "title_name": "Kolchak- The Night Stalker - Track 3",
      "episode_number": "",
      "episode_name": ""
    }
  ]
}
```
