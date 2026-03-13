"""Naming pattern engine for display titles and folder paths.

Supports per-type patterns with {variable} placeholders.
Variables are extracted from Job fields, preferring manual over auto values.
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
# This is the single source of truth — UI and config docs derive from this.
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
    season = getattr(job, 'season_manual', None) or getattr(job, 'season', None) or ''
    episode = getattr(job, 'episode_manual', None) or getattr(job, 'episode', None) or ''

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
    return s.strip()


def _get_pattern(config_dict, video_type, kind):
    """Look up the pattern for a given video_type and kind (TITLE or FOLDER)."""
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
    pattern = _get_pattern(config_dict, video_type, 'TITLE')
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
    pattern = _get_pattern(config_dict, video_type, 'FOLDER')
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
    # Auto-fill episode from track_number (1-indexed) when not set,
    # so TV pattern "{title} S{season}E{episode}" produces useful defaults
    if not variables.get('episode'):
        track_num = getattr(track, 'track_number', None)
        if track_num is not None:
            try:
                variables['episode'] = str(int(track_num) + 1).zfill(2)
            except (ValueError, TypeError):
                pass
    # Use disc_number as season fallback when season isn't set
    if not variables.get('season'):
        disc_num = getattr(job, 'disc_number', None)
        if disc_num is not None:
            variables['season'] = str(disc_num).zfill(2)
    return variables


def render_track_title(track, job, config_dict=None):
    """Render a display title for a single track on a multi-title disc.

    Starts with job-level defaults from _build_variables(), then overrides
    with any track-level fields (title, year, video_type).
    Returns the rendered string without extension — caller adds it.
    """
    variables = _build_track_variables(track, job)
    video_type = variables.get('video_type', '')
    pattern = _get_pattern(config_dict, video_type, 'TITLE')
    rendered = pattern.format_map(variables)
    return _clean_empty_parens(rendered)


def render_track_folder(track, job, config_dict=None):
    """Render the folder path for a single track on a multi-title disc.

    Like render_folder() but with track-level overrides applied.
    Supports '/' for nested directories.
    """
    import os
    variables = _build_track_variables(track, job)
    video_type = variables.get('video_type', '')
    pattern = _get_pattern(config_dict, video_type, 'FOLDER')
    rendered = pattern.format_map(variables)
    rendered = _clean_empty_parens(rendered)
    segments = rendered.split('/')
    segments = [_clean_for_filename(seg) for seg in segments if seg.strip()]
    return os.path.join(*segments) if segments else ''


def render_preview(pattern, variables):
    """Render a pattern with explicit variables dict (for API preview).

    No filesystem sanitization — purely for display.
    """
    safe_vars = _SafeDict(variables)
    rendered = pattern.format_map(safe_vars)
    return _clean_empty_parens(rendered)
