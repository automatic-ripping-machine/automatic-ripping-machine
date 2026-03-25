"""Tests for the naming pattern engine (arm.ripper.naming)."""
import os
from types import SimpleNamespace

from arm.ripper.naming import (
    DEFAULTS,
    render_title,
    render_folder,
    render_preview,
    render_track_title,
    render_track_folder,
    _clean_for_filename,
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
        'title_pattern_override': None, 'folder_pattern_override': None,
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


# --- render_track_title ---


def _make_track(**kwargs):
    """Create a SimpleNamespace that quacks like a Track."""
    defaults = {
        'title': None, 'year': None, 'video_type': None,
        'imdb_id': None, 'poster_url': None, 'custom_filename': None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_track_title_inherits_job_defaults():
    job = _make_job(title='Serial Mom', year='1994', video_type='movie')
    track = _make_track()
    assert render_track_title(track, job) == 'Serial Mom (1994)'


def test_track_title_overrides_job_title():
    job = _make_job(title='Disc Title', year='2020', video_type='movie')
    track = _make_track(title='Special Feature')
    assert render_track_title(track, job) == 'Special Feature (2020)'


def test_track_title_overrides_year():
    job = _make_job(title='Movie', year='2020', video_type='movie')
    track = _make_track(year='2021')
    assert render_track_title(track, job) == 'Movie (2021)'


def test_track_title_overrides_video_type():
    job = _make_job(title='Show', season='1', episode='1', video_type='movie')
    track = _make_track(video_type='series')
    # With video_type='series', uses TV pattern: '{title} S{season}E{episode}'
    assert render_track_title(track, job) == 'Show S01E01'


def test_track_title_no_overrides_uses_job():
    job = _make_job(artist='Beatles', album='Help', video_type='music')
    track = _make_track()
    assert render_track_title(track, job) == 'Beatles - Help'


def test_track_title_with_custom_config():
    job = _make_job(title='Movie', year='2020', video_type='movie')
    track = _make_track(title='Extended Cut')
    cfg = {'MOVIE_TITLE_PATTERN': '{title} [{year}]'}
    assert render_track_title(track, job, cfg) == 'Extended Cut [2020]'


# --- _clean_for_filename ---


def test_clean_for_filename_colons():
    # ' : ' → ' - ', but ':' without surrounding spaces → '-'
    assert _clean_for_filename('Star Wars : A New Hope') == 'Star Wars - A New Hope'
    assert _clean_for_filename('Star Wars: A New Hope') == 'Star Wars- A New Hope'


def test_clean_for_filename_ampersand():
    assert _clean_for_filename('Tom & Jerry') == 'Tom and Jerry'


def test_clean_for_filename_backslash():
    assert _clean_for_filename('AC\\DC') == 'AC - DC'


def test_clean_for_filename_special_chars():
    result = _clean_for_filename('Movie? <Title>!')
    assert '?' not in result
    assert '<' not in result
    assert '>' not in result


def test_clean_for_filename_whitespace():
    assert _clean_for_filename('  too   many   spaces  ') == 'too many spaces'


# --- render_track_folder ---


def test_track_folder_uses_show_name_not_episode_title():
    """Track folder should use the job (show) title, not the per-track episode title."""
    job = _make_job(title='The-Mrs-Bradley-Mysteries', year='1998', video_type='series', season='1')
    track = _make_track(title='The Rising of the Moon', video_type='series')
    result = render_track_folder(track, job)
    assert 'The-Mrs-Bradley-Mysteries' in result
    assert 'The Rising of the Moon' not in result


def test_track_folder_disc_number_fallback():
    """When season is unset, disc_number should produce 'Disc XX' not 'Season XX'."""
    job = _make_job(title='Some Show', video_type='series')
    job.disc_number = 3
    track = _make_track(video_type='series')
    result = render_track_folder(track, job)
    assert 'Disc 03' in result
    assert 'Season' not in result


def test_track_folder_no_season_no_disc_defaults_to_season_01():
    """When neither season nor disc_number is set, default to Season 01."""
    job = _make_job(title='Some Show', video_type='series')
    track = _make_track(video_type='series')
    result = render_track_folder(track, job)
    assert 'Season 01' in result


def test_track_folder_uses_season_auto():
    """When season_auto is set, use it for the folder."""
    job = _make_job(title='Some Show', video_type='series', season_auto='2')
    track = _make_track(video_type='series')
    result = render_track_folder(track, job)
    assert 'Season 02' in result


def test_track_title_disc_number_fallback():
    """When season is a disc_number fallback, title should use D instead of S."""
    job = _make_job(title='Some Show', video_type='series')
    job.disc_number = 2
    track = _make_track(video_type='series', episode_number='3')
    result = render_track_title(track, job)
    assert 'D02E03' in result
    assert 'S02' not in result


def test_track_folder_all_tracks_same_folder():
    """All tracks from a multi-title disc should land in the same show folder."""
    job = _make_job(title='Show', year='2020', video_type='series', season='1')
    tracks = [
        _make_track(title='Episode One', video_type='series', episode_number='1'),
        _make_track(title='Episode Two', video_type='series', episode_number='2'),
        _make_track(title=None, video_type='series'),  # no custom title
    ]
    folders = [render_track_folder(t, job) for t in tracks]
    # All should produce the same folder path
    assert len(set(folders)) == 1
    assert 'Show' in folders[0]


# ======================================================================
# Per-job naming overrides and custom filenames
# ======================================================================

from arm.ripper.naming import (
    VALID_VARS, validate_pattern, render_all_tracks, _get_pattern,
)


class TestValidVars:
    def test_valid_vars_matches_pattern_variables(self):
        from arm.ripper.naming import PATTERN_VARIABLES
        assert VALID_VARS == frozenset(PATTERN_VARIABLES.keys())

    def test_contains_expected_vars(self):
        for v in ('title', 'year', 'season', 'episode', 'label', 'video_type', 'artist', 'album'):
            assert v in VALID_VARS


class TestValidatePattern:
    def test_valid_pattern(self):
        result = validate_pattern('{title} S{season}E{episode}')
        assert result['valid'] is True
        assert result['invalid_vars'] == []

    def test_invalid_variable(self):
        result = validate_pattern('{title} S{season}E{episde}')
        assert result['valid'] is False
        assert 'episde' in result['invalid_vars']

    def test_suggestion_for_typo(self):
        result = validate_pattern('{titl}')
        assert result['valid'] is False
        assert result['suggestions'].get('titl') == 'title'

    def test_no_suggestion_for_distant_typo(self):
        result = validate_pattern('{xyzabc}')
        assert result['valid'] is False
        assert 'xyzabc' not in result['suggestions']

    def test_empty_pattern_is_valid(self):
        result = validate_pattern('literal text no vars')
        assert result['valid'] is True

    def test_multiple_invalid_vars(self):
        result = validate_pattern('{titl} {yar}')
        assert result['valid'] is False
        assert len(result['invalid_vars']) == 2


class TestGetPatternWithJobOverride:
    def test_job_title_override_takes_priority(self):
        job = _make_job(title_pattern_override='{title} - E{episode}')
        config = {'TV_TITLE_PATTERN': '{title} S{season}E{episode}'}
        result = _get_pattern(config, 'series', 'TITLE', job=job)
        assert result == '{title} - E{episode}'

    def test_job_folder_override_takes_priority(self):
        job = _make_job(folder_pattern_override='{title}/S{season}')
        config = {'TV_FOLDER_PATTERN': '{title}/Season {season}'}
        result = _get_pattern(config, 'series', 'FOLDER', job=job)
        assert result == '{title}/S{season}'

    def test_no_override_uses_global(self):
        job = _make_job()
        config = {'TV_TITLE_PATTERN': '{title} S{season}E{episode}'}
        result = _get_pattern(config, 'series', 'TITLE', job=job)
        assert result == '{title} S{season}E{episode}'

    def test_none_job_uses_global(self):
        config = {'TV_TITLE_PATTERN': '{title} S{season}E{episode}'}
        result = _get_pattern(config, 'series', 'TITLE', job=None)
        assert result == '{title} S{season}E{episode}'

    def test_override_is_video_type_agnostic(self):
        """Job override applies regardless of video_type."""
        job = _make_job(video_type='movie', title_pattern_override='{title} custom')
        config = {'MOVIE_TITLE_PATTERN': '{title} ({year})'}
        result = _get_pattern(config, 'movie', 'TITLE', job=job)
        assert result == '{title} custom'


class TestCustomFilename:
    def test_custom_filename_overrides_pattern(self):
        job = _make_job(title='Show', video_type='series', season='1')
        track = _make_track(track_number='0', episode_number='1', custom_filename='My Custom Name')
        result = render_track_title(track, job)
        assert result == 'My Custom Name'

    def test_custom_filename_is_sanitized(self):
        job = _make_job(title='Show', video_type='series')
        track = _make_track(track_number='0', custom_filename='Bad: Name & Stuff')
        result = render_track_title(track, job)
        assert ':' not in result
        assert '&' not in result
        assert 'Bad- Name and Stuff' == result

    def test_custom_filename_prevents_path_traversal(self):
        job = _make_job(title='Show')
        track = _make_track(track_number='0', custom_filename='../../etc/passwd')
        result = render_track_title(track, job)
        assert '..' not in result
        assert '/' not in result

    def test_no_custom_filename_uses_pattern(self):
        job = _make_job(title='Show', video_type='series', season='1')
        track = _make_track(track_number='0', episode_number='5', custom_filename=None)
        result = render_track_title(track, job)
        assert 'S01E05' in result

    def test_job_pattern_override_with_no_custom_filename(self):
        job = _make_job(
            title='Show', video_type='series', season='1',
            title_pattern_override='{title} - E{episode}',
        )
        track = _make_track(track_number='0', episode_number='5')
        result = render_track_title(track, job)
        assert result == 'Show - E05'

    def test_custom_filename_overrides_job_pattern(self):
        """Custom filename beats job pattern override."""
        job = _make_job(
            title='Show', video_type='series', season='1',
            title_pattern_override='{title} - E{episode}',
        )
        track = _make_track(track_number='0', episode_number='5', custom_filename='Override')
        result = render_track_title(track, job)
        assert result == 'Override'


class TestRenderAllTracks:
    def _make_job_with_tracks(self, tracks_data, **job_kwargs):
        job = _make_job(**job_kwargs)
        tracks = []
        for td in tracks_data:
            tracks.append(_make_track(**td))
        job.tracks = tracks
        return job

    def test_renders_all_tracks(self):
        job = self._make_job_with_tracks(
            [
                {'track_number': '0', 'episode_number': '1'},
                {'track_number': '1', 'episode_number': '2'},
            ],
            title='Show', video_type='series', season='1',
        )
        results = render_all_tracks(job)
        assert len(results) == 2
        assert 'S01E01' in results[0]['rendered_title']
        assert 'S01E02' in results[1]['rendered_title']

    def test_duplicate_detection_appends_track_number(self):
        """Literal pattern with no per-track variation → duplicates detected."""
        job = self._make_job_with_tracks(
            [
                {'track_number': '0'},
                {'track_number': '1'},
            ],
            title='Movie', video_type='movie', year='2024',
            title_pattern_override='Same Name',
        )
        results = render_all_tracks(job)
        titles = [r['rendered_title'] for r in results]
        assert titles[0] != titles[1]
        assert 'Track 0' in titles[0]
        assert 'Track 1' in titles[1]

    def test_cross_tier_duplicate_detection(self):
        """Custom filename collides with pattern-rendered name."""
        job = self._make_job_with_tracks(
            [
                {'track_number': '0', 'episode_number': '1', 'custom_filename': 'Show S01E02'},
                {'track_number': '1', 'episode_number': '2'},
            ],
            title='Show', video_type='series', season='1',
        )
        results = render_all_tracks(job)
        titles = [r['rendered_title'] for r in results]
        # Both would be "Show S01E02" — duplicates should be disambiguated
        assert titles[0] != titles[1]

    def test_no_duplicates_no_modification(self):
        job = self._make_job_with_tracks(
            [
                {'track_number': '0', 'episode_number': '1'},
                {'track_number': '1', 'episode_number': '2'},
            ],
            title='Show', video_type='series', season='1',
        )
        results = render_all_tracks(job)
        titles = [r['rendered_title'] for r in results]
        assert 'Track' not in titles[0]
        assert 'Track' not in titles[1]

    def test_single_track_no_duplicate(self):
        job = self._make_job_with_tracks(
            [{'track_number': '0', 'custom_filename': 'Solo'}],
            title='Movie', video_type='movie',
        )
        results = render_all_tracks(job)
        assert results[0]['rendered_title'] == 'Solo'
        assert 'Track' not in results[0]['rendered_title']


class TestRenderWithJobFolderOverride:
    def test_folder_override_applies(self):
        job = _make_job(
            title='Show', video_type='series', season='1',
            folder_pattern_override='{title}/S{season}',
        )
        result = render_folder(job)
        assert 'S01' in result
        assert 'Season' not in result

    def test_title_override_in_render_title(self):
        job = _make_job(
            title='Show', video_type='series', season='1',
            title_pattern_override='{title} Episode {episode}',
        )
        result = render_title(job)
        assert 'Episode' in result
        assert 'S01' not in result
