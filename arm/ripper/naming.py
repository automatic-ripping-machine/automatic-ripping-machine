"""Naming pattern engine for display titles and folder paths.

Supports per-type patterns with {variable} placeholders.
Variables are extracted from Job fields, preferring manual over auto values.
Per-job pattern overrides and per-track custom filenames are supported.
"""
import re

_TITLE_YEAR_PATTERN = '{title} ({year})'

DEFAULTS = {
    'MOVIE_TITLE_PATTERN':  _TITLE_YEAR_PATTERN,
    'MOVIE_FOLDER_PATTERN': _TITLE_YEAR_PATTERN,
    'TV_TITLE_PATTERN':     '{title} S{season}E{episode}',
    'TV_FOLDER_PATTERN':    '{title}/Season {season}',
    'MUSIC_TITLE_PATTERN':  '{artist} - {album}',
    'MUSIC_FOLDER_PATTERN': '{artist}/{album} ({year})',
}

# Canonical list of variables available in naming patterns.
# This is the single source of truth — UI, validation, and config docs derive from this.
PATTERN_VARIABLES = {
    'title':      'Disc title (prefers manual over auto-detected)',
    'year':       'Release year',
    'artist':     'Music artist name',
    'album':      'Music album name',
    'season':     'TV season number (zero-padded to 2 digits)',
    'episode':    'TV episode number (zero-padded to 2 digits)',
    'label':      'Original disc label from drive',
    'video_type': 'Media type: movie, series, or music',
}

# Frozen set for fast validation — derived from PATTERN_VARIABLES
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
    """Extract all pattern variables from a Job, preferring manual over auto."""
    title = job.title_manual or job.title or ''
    year = job.year_manual or job.year or ''
    if year == '0000':
        year = ''
    artist = getattr(job, 'artist_manual', None) or getattr(job, 'artist', None) or ''
    album = getattr(job, 'album_manual', None) or getattr(job, 'album', None) or ''
    season = getattr(job, 'season_manual', None) or getattr(job, 'season', None) or getattr(job, 'season_auto', None) or ''
    episode = getattr(job, 'episode_manual', None) or getattr(job, 'episode', None) or getattr(job, 'episode_auto', None) or ''

    # Zero-pad season/episode to 2 digits if numeric
    if season and season.isdigit():
        season = season.zfill(2)
    if episode and episode.isdigit():
        episode = episode.zfill(2)

    return _SafeDict({
        'title': title,
        'year': year,
        'artist': artist,
        'album': album,
        'season': season,
        'episode': episode,
        'label': getattr(job, 'label', '') or '',
        'video_type': getattr(job, 'video_type', '') or '',
    })


def _clean_empty_parens(s):
    """Remove empty parentheses like '()' left from missing variables."""
    return re.sub(r'\s*\(\s*\)', '', s).strip()


def _clean_for_filename(s):
    """Sanitize a single path segment for filesystem use."""
    s = re.sub(r'\s+', ' ', s)
    s = s.replace(' : ', ' - ')
    s = s.replace(':', '-')
    s = s.replace('&', 'and')
    s = s.replace('\\', ' - ')
    s = re.sub(r'[^\w .()-]', '', s)
    # Prevent path traversal — strip leading dots and collapse sequences
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
    segments = [_clean_for_filename(seg) for seg in segments if seg.strip()]
    return os.path.join(*segments) if segments else ''


def _build_track_variables(track, job):
    """Build variables for a track, starting from job defaults and overriding with track-level fields."""
    variables = _build_variables(job)
    if getattr(track, 'title', None):
        variables['title'] = track.title
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
        return _clean_for_filename(track.custom_filename)

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

    Uses the **job-level** title (show name) for the folder — NOT the
    per-track episode title.  Only video_type, year, and season/episode
    are taken from the track so that all episodes land under the same
    show folder (e.g. "The-Mrs-Bradley-Mysteries/Season 01").
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
    segments = [_clean_for_filename(seg) for seg in segments if seg.strip()]
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
    tokens = re.findall(r'\{(\w+)\}', pattern)
    invalid = [t for t in tokens if t not in VALID_VARS]
    suggestions = {}
    for inv in invalid:
        best = min(VALID_VARS, key=lambda v: _levenshtein(inv, v))
        if _levenshtein(inv, best) <= 2:
            suggestions[inv] = best
    return {"valid": len(invalid) == 0, "invalid_vars": invalid, "suggestions": suggestions}
