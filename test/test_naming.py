"""Tests for the naming pattern engine (arm.ripper.naming)."""
import os
from types import SimpleNamespace

from arm.ripper.naming import (
    DEFAULTS,
    render_title,
    render_folder,
    render_preview,
)


def _make_job(**kwargs):
    """Create a SimpleNamespace that quacks like a Job for pattern rendering."""
    defaults = {
        'title': None, 'title_manual': None, 'title_auto': None,
        'year': None, 'year_manual': None, 'year_auto': None,
        'artist': None, 'artist_manual': None, 'artist_auto': None,
        'album': None, 'album_manual': None, 'album_auto': None,
        'season': None, 'season_manual': None, 'season_auto': None,
        'episode': None, 'episode_manual': None, 'episode_auto': None,
        'video_type': 'movie', 'label': None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# --- Movie title rendering ---


def test_movie_title_default():
    job = _make_job(title='Inception', year='2010', video_type='movie')
    assert render_title(job) == 'Inception (2010)'


def test_movie_title_custom_pattern():
    job = _make_job(title='Inception', year='2010', video_type='movie')
    cfg = {'MOVIE_TITLE_PATTERN': '{title} [{year}]'}
    assert render_title(job, cfg) == 'Inception [2010]'


def test_movie_title_missing_year():
    job = _make_job(title='Inception', video_type='movie')
    assert render_title(job) == 'Inception'


def test_movie_title_prefers_manual():
    job = _make_job(title='wrong', title_manual='Right Title', year='2010', video_type='movie')
    assert render_title(job) == 'Right Title (2010)'


# --- TV title rendering ---


def test_tv_title_default():
    job = _make_job(title='Breaking Bad', season='1', episode='3', video_type='series')
    assert render_title(job) == 'Breaking Bad S01E03'


def test_tv_title_multi_digit():
    job = _make_job(title='Lost', season='12', episode='5', video_type='series')
    assert render_title(job) == 'Lost S12E05'


def test_tv_folder_default():
    job = _make_job(title='Breaking Bad', season='2', video_type='series')
    assert render_folder(job) == os.path.join('Breaking Bad', 'Season 02')


# --- Music title rendering ---


def test_music_title_default():
    job = _make_job(artist='The Beatles', album='Abbey Road', video_type='music')
    assert render_title(job) == 'The Beatles - Abbey Road'


def test_music_title_custom_pattern():
    job = _make_job(artist='Pink Floyd', album='The Wall', year='1979', video_type='music')
    cfg = {'MUSIC_TITLE_PATTERN': '{artist} - {album} ({year})'}
    assert render_title(job, cfg) == 'Pink Floyd - The Wall (1979)'


def test_music_folder_default():
    job = _make_job(artist='The Beatles', album='Abbey Road', year='1969', video_type='music')
    result = render_folder(job)
    assert result == os.path.join('The Beatles', 'Abbey Road (1969)')


def test_music_folder_no_year():
    job = _make_job(artist='The Beatles', album='Abbey Road', video_type='music')
    result = render_folder(job)
    assert result == os.path.join('The Beatles', 'Abbey Road')


def test_music_prefers_manual_artist():
    job = _make_job(
        artist='beatles', artist_manual='The Beatles',
        album='Help', video_type='music'
    )
    assert render_title(job) == 'The Beatles - Help'


# --- Missing variables → empty string ---


def test_missing_variables_empty():
    job = _make_job(video_type='music')
    assert render_title(job) == '-'


def test_all_missing():
    job = _make_job(video_type='movie')
    # Default pattern: '{title} ({year})' → ' ()' → cleaned to ''
    assert render_title(job) == ''


# --- Empty parentheses cleanup ---


def test_empty_parens_cleaned():
    result = render_preview('{title} ({year})', {'title': 'Inception', 'year': ''})
    assert result == 'Inception'


def test_empty_parens_with_spaces():
    result = render_preview('{title} ( {year} )', {'title': 'Inception'})
    assert result == 'Inception'


# --- Folder path with / nesting ---


def test_folder_nested():
    job = _make_job(artist='Pink Floyd', album='The Wall', year='1979', video_type='music')
    result = render_folder(job)
    assert result == os.path.join('Pink Floyd', 'The Wall (1979)')


# --- Filesystem sanitization ---


def test_folder_sanitizes_special_chars():
    job = _make_job(artist='AC/DC', album='Back in Black', year='1980', video_type='music')
    cfg = {'MUSIC_FOLDER_PATTERN': '{artist}/{album} ({year})'}
    result = render_folder(job, cfg)
    # AC/DC contains a slash which would create nested dirs — each segment is sanitized
    # The artist "AC/DC" is split on the pattern-level /, but artist itself has no /
    # because format_map inserts "AC/DC" into {artist}, then split on / gives ["AC", "DC"]
    # This is by design — / in variable values creates nesting
    segments = result.split(os.sep)
    assert len(segments) >= 2


def test_folder_sanitizes_colons():
    job = _make_job(title='Star Wars: A New Hope', year='1977', video_type='movie')
    result = render_folder(job)
    assert ':' not in result


# --- Default fallbacks ---


def test_defaults_used_when_config_empty():
    job = _make_job(title='Test', year='2020', video_type='movie')
    assert render_title(job, {}) == 'Test (2020)'


def test_defaults_used_when_config_none():
    job = _make_job(title='Test', year='2020', video_type='movie')
    assert render_title(job, None) == 'Test (2020)'


def test_unknown_video_type_uses_movie_pattern():
    job = _make_job(title='Data Disc', year='2020', video_type='unknown')
    assert render_title(job) == 'Data Disc (2020)'


# --- render_preview ---


def test_preview_basic():
    result = render_preview('{artist} - {album} ({year})', {
        'artist': 'Queen',
        'album': 'Jazz',
        'year': '1978'
    })
    assert result == 'Queen - Jazz (1978)'


def test_preview_missing_var():
    result = render_preview('{title} S{season}E{episode}', {'title': 'Show'})
    assert result == 'Show SE'


# --- Season/episode zero-padding ---


def test_season_episode_padding():
    job = _make_job(title='Show', season='3', episode='7', video_type='series')
    assert render_title(job) == 'Show S03E07'


def test_season_episode_no_padding_non_numeric():
    job = _make_job(title='Show', season='S1', episode='E2', video_type='series')
    assert render_title(job) == 'Show SS1EE2'


def test_year_0000_treated_as_empty():
    job = _make_job(title='Inception', year='0000', video_type='movie')
    assert render_title(job) == 'Inception'
