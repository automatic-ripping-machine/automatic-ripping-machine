"""Naming pattern engine for display titles and folder paths.

Supports per-type patterns with {variable} placeholders.
Variables are extracted from Job fields + MediaMetadata, preferring manual
over auto values. Per-job pattern overrides and per-track custom filenames
are supported.

Token vocabulary:
- "Core" tokens (title, show, year, season, episode, episode_name, video_type,
  imdb_id) are read directly from Job columns - the matcher writes these
  during disc identification.
- "Editorial" tokens (artist, album, director, genre, plot, tagline, etc.)
  are read from Job.media_metadata, which merges manual-over-auto from the
  two media_metadata_* JSON columns.
- "Engine-only" tokens (label, disc_number, disc_total) come from Job
  columns directly.
"""
import logging
import os
import re

from arm_contracts import PATTERN_TOKENS

_TITLE_YEAR_PATTERN = '{title} ({year})'

DEFAULTS = {
    'MOVIE_TITLE_PATTERN':  _TITLE_YEAR_PATTERN,
    'MOVIE_FOLDER_PATTERN': _TITLE_YEAR_PATTERN,
    'TV_TITLE_PATTERN':     '{show} S{season}E{episode}',
    'TV_FOLDER_PATTERN':    '{show}/Season {season}',
    'MUSIC_TITLE_PATTERN':  '{artist} - {album}',
    'MUSIC_FOLDER_PATTERN': '{artist}/{album} ({year})',
}

# Tokens the engine sources from Job columns (not from MediaMetadata), in
# addition to anything PATTERN_TOKENS covers. Kept here so the validator
# accepts them.
# - {show} mirrors {title} at job level; never gets overridden at track-level.
# - {episode} is the per-track concept (track-level), not part of MediaMetadata.
# - {episode_name} is the TVDB-matched per-track episode title.
# - label / disc_number / disc_total are physical-disc properties.
_ENGINE_ONLY_TOKENS = {
    'show':         'Series/show name (always the job-level title, never overridden by track)',
    'episode':      'TV episode number (zero-padded to 2 digits)',
    'episode_name': 'TV episode title from TVDB (track-level only)',
    'label':        'Original disc label from drive',
    'disc_number':  'Disc number in a multi-disc set',
    'disc_total':   'Total number of discs in the set',
}

# PATTERN_VARIABLES: source-of-truth for what tokens patterns can use.
# Contract-derived tokens come from PATTERN_TOKENS in arm_contracts;
# engine-only tokens are local to this module.
PATTERN_VARIABLES = {
    **{alias: desc for alias, (_, desc, _) in PATTERN_TOKENS.items()},
    **_ENGINE_ONLY_TOKENS,
}

# Frozen set for fast validation - derived from PATTERN_VARIABLES
VALID_VARS: frozenset = frozenset(PATTERN_VARIABLES.keys())

# Map video_type to pattern key prefixes
_TYPE_PREFIX = {
    'movie': 'MOVIE',
    'series': 'TV',
    'music': 'MUSIC',
}


class _SafeDict(dict):
    """Dict subclass that returns '' for missing keys in str.format_map()."""
    def __missing__(self, key):
        return ''


def _build_variables(job):
    """Extract all pattern variables from a Job + its MediaMetadata.

    Job columns drive `title`, `year`, `season`, `episode`, `imdb_id`,
    `video_type`, `label`, `disc_number`, `disc_total` (matcher writes
    these directly during identification). MediaMetadata fills in the
    editorial tokens (director, genre, plot, etc.) plus poster_url and
    artist/album/album_artist for music jobs.

    Manual-over-auto is layered:
    - Job-side: `_manual` columns override base columns (title_manual,
      year_manual, etc.).
    - MediaMetadata-side: the merged-read property in Job already does
      field-by-field manual-over-auto from the two JSON blobs.

    The job *must* expose a `media_metadata` attribute - either the
    property on a real Job, or a MediaMetadata attached to a test
    SimpleNamespace.
    """
    metadata = job.media_metadata

    # Core tokens from Job columns (matcher writes these in identify.py).
    title = job.title_manual or job.title or ''
    year = job.year_manual or job.year or ''
    if year == '0000':
        year = ''
    season = getattr(job, 'season_manual', None) or getattr(job, 'season', None) or getattr(job, 'season_auto', None) or ''
    episode = getattr(job, 'episode_manual', None) or getattr(job, 'episode', None) or getattr(job, 'episode_auto', None) or ''
    if season and season.isdigit():
        season = season.zfill(2)
    if episode and episode.isdigit():
        episode = episode.zfill(2)

    out = _SafeDict()

    # Contract-derived tokens from MediaMetadata, using each token's
    # accessor lambda. None / empty values render as empty strings.
    for alias, (field_name, _desc, accessor) in PATTERN_TOKENS.items():
        value = getattr(metadata, field_name, None)
        if value is None or value == [] or value == "":
            out[alias] = ''
        else:
            try:
                out[alias] = accessor(value)
            except Exception:  # noqa: BLE001 - never break naming on a bad token
                out[alias] = ''

    # Core tokens override the contract-derived defaults. Job columns are
    # authoritative for these because they participate in matching and UI
    # workflows beyond the naming engine.
    out.update({
        'title': title,
        'show': title,  # Always the job-level title (show name for TV).
        'year': year,
        'artist': metadata.artist or '',
        'album': metadata.album or '',
        'season': season,
        'episode': episode,
        'episode_name': '',  # Populated at track level from TVDB.
        'label': getattr(job, 'label', '') or '',
        'video_type': getattr(job, 'video_type', '') or '',
        'disc_number': str(getattr(job, 'disc_number', '') or ''),
        'disc_total': str(getattr(job, 'disc_total', '') or ''),
        'imdb_id': getattr(job, 'imdb_id', '') or '',
    })
    return out


def _clean_empty_parens(s):
    """Remove empty parentheses like '()' left from missing variables.

    The space-runs are bounded ({0,4}) rather than unbounded ` *`. An
    unbounded greedy run before a literal that can fail backtracks one
    space at a time at every offset, making re.sub polynomial (ReDoS) on a
    long run of spaces. Empty-paren artifacts only ever carry a handful of
    spaces, so a small bound preserves behaviour without the blow-up.
    """
    return re.sub(r' {0,4}\( {0,4}\)', '', s).strip()


def clean_for_filename(s):
    """Sanitize a single path segment for filesystem use."""
    s = s.replace(':', ' - ')
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('&', 'and')
    s = s.replace('\\', ' - ')
    # Keep Jellyfin/Plex folder tags like [imdbid-tt1234567] legible on disk.
    s = re.sub(r'[^\w .()\[\]-]', '', s)
    # Prevent path traversal - strip leading dots and collapse sequences
    s = re.sub(r'\.{2,}', '.', s)
    return s.strip('. ')


def _get_pattern(config_dict, video_type, kind, job=None):
    """Look up the pattern for a given video_type and kind (TITLE or FOLDER).

    When job has a pattern override for the given kind, it takes priority
    over the global config pattern regardless of video_type.
    """
    if job is not None:
        override = None
        if kind == 'TITLE':
            override = getattr(job, 'title_pattern_override', None)
        elif kind == 'FOLDER':
            override = getattr(job, 'folder_pattern_override', None)
        if override and isinstance(override, str):
            return override
    prefix = _TYPE_PREFIX.get(video_type)
    if not prefix:
        # Fall back to movie patterns for unknown types
        prefix = 'MOVIE'
    key = f'{prefix}_{kind}_PATTERN'
    pattern = config_dict.get(key) if config_dict else None
    if not pattern:
        pattern = DEFAULTS.get(key, _TITLE_YEAR_PATTERN)
    return pattern


def render_title(job, config_dict=None):
    """Render the display title for a job using the configured pattern.

    Returns the rendered title string with empty parentheses cleaned up.
    """
    variables = _build_variables(job)
    video_type = variables.get('video_type', '')
    pattern = _get_pattern(config_dict, video_type, 'TITLE', job=job)
    rendered = pattern.format_map(variables)
    return _clean_empty_parens(rendered)


def render_folder(job, config_dict=None):
    """Render the folder path segment for a job using the configured pattern.

    Supports '/' in patterns for nested directories (e.g. '{artist}/{album}').
    Each segment is individually sanitized for filesystem use.
    """
    import os
    variables = _build_variables(job)
    video_type = variables.get('video_type', '')
    pattern = _get_pattern(config_dict, video_type, 'FOLDER', job=job)
    rendered = pattern.format_map(variables)
    rendered = _clean_empty_parens(rendered)
    # Sanitize each path segment individually
    segments = rendered.split('/')
    segments = [clean_for_filename(seg) for seg in segments if seg.strip()]
    return os.path.join(*segments) if segments else ''


def _build_track_variables(track, job):
    """Build variables for a track, starting from job defaults and overriding with track-level fields.

    {show} always stays as the job-level title (series name for TV).
    {title} is overridden by per-track title when available.
    {episode_name} is populated from TVDB-matched episode name.
    """
    variables = _build_variables(job)
    if getattr(track, 'title', None):
        variables['title'] = track.title
    # {show} is never overridden — always the job-level show/series name
    ep_name = getattr(track, 'episode_name', None)
    if ep_name:
        variables['episode_name'] = ep_name
    if getattr(track, 'year', None):
        variables['year'] = track.year
    track_video_type = getattr(track, 'video_type', None)
    if track_video_type:
        variables['video_type'] = track_video_type
    # Episode number: prefer TVDB-matched episode_number, then fall back
    # to track_number + 1 as a rough default
    ep_num = getattr(track, 'episode_number', None)
    if ep_num:
        variables['episode'] = str(ep_num).zfill(2)
    elif not variables.get('episode'):
        track_num = getattr(track, 'track_number', None)
        if track_num is not None:
            try:
                variables['episode'] = str(int(track_num) + 1).zfill(2)
            except (ValueError, TypeError):
                pass
    # Season fallback: prefer season_auto (e.g. from TVDB), then fall back
    # to disc_number — but label it "Disc" so the folder reflects reality.
    if not variables.get('season'):
        season_auto = getattr(job, 'season_auto', None)
        if season_auto:
            variables['season'] = str(season_auto).zfill(2)
        else:
            disc_num = getattr(job, 'disc_number', None)
            if disc_num is not None:
                variables['_disc_fallback'] = True
                variables['season'] = str(disc_num).zfill(2)
            else:
                variables['season'] = '01'
    return variables


def render_track_title(track, job, config_dict=None):
    """Render a display title for a single track on a multi-title disc.

    Precedence:
    1. track.custom_filename (sanitized, used as-is)
    2. job pattern override → rendered with variables
    3. global pattern → rendered with variables
    """
    # Custom filename takes highest priority
    if getattr(track, 'custom_filename', None):
        return clean_for_filename(track.custom_filename)

    variables = _build_track_variables(track, job)
    video_type = variables.get('video_type', '')

    # For series tracks without an episode match and no job-level episode,
    # use a simple track-based name instead of the TV pattern. This avoids
    # fake S01E04 names derived from track_number on menu/intro tracks.
    ep_num = getattr(track, 'episode_number', None)
    job_episode = getattr(job, 'episode_manual', None) or getattr(job, 'episode', None) or getattr(job, 'episode_auto', None)
    if video_type == 'series' and not ep_num and not job_episode:
        title = variables.get('title', '')
        track_num = getattr(track, 'track_number', None) or '0'
        return f'{title} - Track {track_num}' if title else f'Track {track_num}'

    pattern = _get_pattern(config_dict, video_type, 'TITLE', job=job)
    rendered = pattern.format_map(variables)
    rendered = _clean_empty_parens(rendered)
    # When season is actually a disc number, replace S02 with D02
    if variables.get('_disc_fallback'):
        season = variables.get('season', '')
        rendered = rendered.replace(f'S{season}', f'D{season}')
    return rendered


def render_track_folder(track, job, config_dict=None):
    """Render the folder path for a single track on a multi-title disc.

    For **series**: uses the job-level title (show name) so all episodes
    land under the same show folder (e.g. "Breaking Bad/Season 01").

    For **movies**: uses the per-track title when available, since each
    track is a separate movie that needs its own folder in Plex/Jellyfin
    (e.g. "The Sender (2024)" and "The Invader (2024)" instead of
    both landing in "The Sender And The Invader (None)").
    """
    import os
    # Start from job-level variables (keeps job title for {title})
    variables = _build_variables(job)
    # Override only type/year/season/episode from track
    track_video_type = getattr(track, 'video_type', None)
    if track_video_type:
        variables['video_type'] = track_video_type
    if getattr(track, 'year', None):
        variables['year'] = track.year
    # For movie tracks with per-track metadata, use the track's own title
    # for the folder so each movie gets its own directory in media libraries.
    effective_type = variables.get('video_type', '') or 'movie'
    if effective_type == 'movie' and getattr(track, 'title', None):
        variables['title'] = track.title
    ep_num = getattr(track, 'episode_number', None)
    if ep_num:
        variables['episode'] = str(ep_num).zfill(2)
    # Season: prefer job season, then season_auto, then disc_number
    if not variables.get('season'):
        season_auto = getattr(job, 'season_auto', None)
        if season_auto:
            variables['season'] = str(season_auto).zfill(2)
        else:
            disc_num = getattr(job, 'disc_number', None)
            if disc_num is not None:
                variables['_disc_fallback'] = True
                variables['season'] = str(disc_num).zfill(2)
            else:
                variables['season'] = '01'
    video_type = variables.get('video_type', '')
    pattern = _get_pattern(config_dict, video_type, 'FOLDER', job=job)
    rendered = pattern.format_map(variables)
    rendered = _clean_empty_parens(rendered)
    # Replace "Season XX" with "Disc XX" when using disc_number fallback
    if variables.get('_disc_fallback'):
        rendered = rendered.replace('Season ', 'Disc ')
    segments = rendered.split('/')
    segments = [clean_for_filename(seg) for seg in segments if seg.strip()]
    return os.path.join(*segments) if segments else ''


def render_all_tracks(job, config_dict=None):
    """Render filenames for all tracks with duplicate collision detection.

    Returns a list of dicts with track_number, rendered_title, rendered_folder.
    When duplicate rendered_titles are detected, appends ' - Track {N}' to
    disambiguate (covers both pattern collisions and cross-tier collisions
    between custom_filename and pattern-rendered names).
    """
    results = []
    for track in sorted(job.tracks, key=lambda t: int(t.track_number or 0)):
        results.append({
            "track_number": track.track_number,
            "rendered_title": render_track_title(track, job, config_dict),
            "rendered_folder": render_track_folder(track, job, config_dict),
        })
    # Detect duplicates and append track number
    seen = {}
    for r in results:
        name = r["rendered_title"]
        if name in seen:
            # Mark both the first occurrence and this one
            if seen[name] is not None:
                seen[name]["rendered_title"] += f" - Track {seen[name]['track_number']}"
                seen[name] = None  # already fixed
            r["rendered_title"] += f" - Track {r['track_number']}"
        else:
            seen[name] = r
    return results


def render_preview(pattern, variables):
    """Render a pattern with explicit variables dict (for API preview).

    No filesystem sanitization — purely for display.
    """
    safe_vars = _SafeDict(variables)
    rendered = pattern.format_map(safe_vars)
    return _clean_empty_parens(rendered)


# ======================================================================
# Pattern validation
# ======================================================================


def _levenshtein(s1, s2):
    """Simple Levenshtein distance for fuzzy matching suggestions."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,
                prev_row[j + 1] + 1,
                prev_row[j] + cost,
            ))
        prev_row = curr_row
    return prev_row[-1]


def validate_pattern(pattern):
    """Validate a naming pattern against VALID_VARS.

    Returns {"valid": bool, "invalid_vars": [...], "suggestions": {...}}.
    """
    # Match {name} or {name:format_spec}. The token name (\w+) and an
    # optional ":"-introduced format spec are disjoint: the format spec is
    # gated behind a literal ":" (not a word char), so the two quantifiers
    # can't overlap and backtrack against each other. The previous
    # r'\{(\w+)[^}]*\}' let \w+ and [^}]* both consume word chars, which is
    # polynomial (ReDoS) on input like "{a" followed by many word chars and
    # no closing brace.
    tokens = re.findall(r'\{(\w+)(?::[^}]*)?\}', pattern)
    invalid = [t for t in tokens if t not in VALID_VARS]
    suggestions = {}
    for inv in invalid:
        best = min(VALID_VARS, key=lambda v: _levenshtein(inv, v))
        if _levenshtein(inv, best) <= 2:
            suggestions[inv] = best
    return {"valid": len(invalid) == 0, "invalid_vars": invalid, "suggestions": suggestions}


# ======================================================================
# File finalization (transcoder-disabled deployments)
# ======================================================================


def _move_track(track, raw_path, final_dir, rendered_map):
    """Move a single track file to its final rendered destination.

    Returns True if the file was moved, False if skipped.
    """
    import shutil

    if not track.filename:
        return False
    src = os.path.join(raw_path, track.filename)
    if not os.path.isfile(src):
        return False

    r = rendered_map.get(str(track.track_number or ''), {})
    rendered_title = r.get("rendered_title", '')

    if rendered_title:
        ext = os.path.splitext(track.filename)[1]
        dest_name = clean_for_filename(rendered_title) + ext
    else:
        dest_name = track.filename

    rendered_folder = r.get("rendered_folder", '')
    dest_dir = os.path.join(final_dir, rendered_folder) if rendered_folder else final_dir

    os.makedirs(dest_dir, exist_ok=True)
    shutil.move(src, os.path.join(dest_dir, dest_name))
    return True


def _move_untracked_mkvs(raw_path, final_dir, job, config_dict):
    """Fallback: move all MKV files using the job-level rendered title.

    Used when no track records matched (e.g. single-title disc).
    Returns the number of files moved.
    """
    import shutil

    moved = 0
    rendered_title = render_title(job, config_dict)
    mkv_files = sorted(f for f in os.listdir(raw_path) if f.lower().endswith('.mkv'))
    for i, fname in enumerate(mkv_files):
        if rendered_title:
            base = clean_for_filename(rendered_title)
            # Append track index for multi-file fallback to avoid overwriting
            dest_name = f"{base}.mkv" if len(mkv_files) == 1 else f"{base} - {i + 1}.mkv"
        else:
            dest_name = fname
        shutil.move(os.path.join(raw_path, fname), os.path.join(final_dir, dest_name))
        moved += 1
    return moved


def _cleanup_empty_dir(path):
    """Remove a directory if it exists and is empty."""
    try:
        if os.path.isdir(path) and not os.listdir(path):
            os.rmdir(path)
    except OSError:
        pass


def finalize_output(job):
    """Move ripped files from GUID work directory to final named location.

    Used when the transcoder is disabled - ARM handles final naming directly.
    Renders folder/file names via the naming engine, moves files, updates
    job.path, and cleans up the empty work directory.
    """
    from arm.database import db
    import arm.config.config as cfg

    raw_path = getattr(job, 'raw_path', None)
    if not raw_path or not os.path.isdir(raw_path):
        logging.debug("finalize_output: no raw_path for job %s, skipping",
                       getattr(job, 'job_id', '?'))
        return

    config_dict = cfg.arm_config if hasattr(cfg, 'arm_config') else None
    final_dir = job.build_final_path()
    os.makedirs(final_dir, exist_ok=True)

    rendered = render_all_tracks(job, config_dict)
    rendered_map = {r["track_number"]: r for r in rendered}

    moved_count = sum(1 for t in job.tracks if _move_track(t, raw_path, final_dir, rendered_map))

    if moved_count == 0:
        moved_count = _move_untracked_mkvs(raw_path, final_dir, job, config_dict)

    if moved_count > 0:
        job.path = final_dir
        db.session.commit()
        _cleanup_empty_dir(raw_path)
        logging.info("finalize_output: moved %d files to %s", moved_count, final_dir)
    else:
        logging.warning("finalize_output: no files moved for job %s from %s",
                        getattr(job, 'job_id', '?'), raw_path)
