# components/contracts/tests/test_media_metadata.py
"""Tests for the MediaMetadata contract."""
from datetime import date

import pytest
from pydantic import ValidationError

from arm_contracts.enums import VideoType
from arm_contracts.media_metadata import MediaMetadata


def test_minimal_construction_accepts_all_optional():
    """Empty MediaMetadata should construct cleanly - every field is optional."""
    m = MediaMetadata()
    assert m.title is None
    assert m.year is None
    assert m.video_type is None
    assert m.imdb_id is None
    assert m.genres == []
    assert m.directors == []
    assert m.actors == []


def test_full_movie_payload_round_trips():
    """A typical movie payload from OMDb survives serialization."""
    m = MediaMetadata(
        title="Annihilation",
        year="2018",
        video_type=VideoType.movie,
        imdb_id="tt2798920",
        runtime_seconds=6900,
        plot="A biologist signs up for a mission...",
        genres=["Sci-Fi", "Drama", "Adventure"],
        directors=["Alex Garland"],
        mpaa_rating="R",
        released_date=date(2018, 2, 23),
        language="en",
        country="USA",
        imdb_rating=6.8,
    )
    blob = m.model_dump_json()
    restored = MediaMetadata.model_validate_json(blob)
    assert restored.title == "Annihilation"
    assert restored.runtime_seconds == 6900
    assert restored.released_date == date(2018, 2, 23)
    assert restored.imdb_rating == pytest.approx(6.8)


def test_imdb_id_pattern_rejects_garbage():
    """imdb_id must match tt\\d+ or be empty/None."""
    with pytest.raises(ValidationError):
        MediaMetadata(imdb_id="not-an-imdb-id")


def test_year_pattern_rejects_two_digit():
    """year must be a 4-digit string or empty."""
    with pytest.raises(ValidationError):
        MediaMetadata(year="18")


def test_imdb_rating_bounds():
    """imdb_rating is bounded 0.0..10.0."""
    with pytest.raises(ValidationError):
        MediaMetadata(imdb_rating=11.0)
    with pytest.raises(ValidationError):
        MediaMetadata(imdb_rating=-0.1)
    # Boundary values pass
    MediaMetadata(imdb_rating=0.0)
    MediaMetadata(imdb_rating=10.0)


def test_runtime_seconds_non_negative():
    """runtime_seconds cannot be negative."""
    with pytest.raises(ValidationError):
        MediaMetadata(runtime_seconds=-1)


def test_audio_payload_round_trips():
    """Music CD payload from MusicBrainz uses artist/album/album_artist."""
    m = MediaMetadata(
        video_type=VideoType.music,
        artist="Pink Floyd",
        album="The Dark Side of the Moon",
        album_artist="Pink Floyd",
        released_date=date(1973, 3, 1),
        genres=["Progressive Rock"],
    )
    restored = MediaMetadata.model_validate_json(m.model_dump_json())
    assert restored.album == "The Dark Side of the Moon"
    assert restored.album_artist == "Pink Floyd"


def test_extra_fields_ignored():
    """Provider quirks that smuggle extra keys must not break validation."""
    payload = {
        "title": "Annihilation",
        "year": "2018",
        "some_provider_specific_key": "ignored",
    }
    m = MediaMetadata.model_validate(payload)
    assert m.title == "Annihilation"
    assert not hasattr(m, "some_provider_specific_key")


def test_re_exported_from_package_root():
    """Consumers should be able to `from arm_contracts import MediaMetadata`."""
    from arm_contracts import MediaMetadata as M  # noqa: F401
    from arm_contracts import PATTERN_TOKENS as T  # noqa: F401
    assert isinstance(T, dict)
    assert "title" in T
    assert "director" in T


def test_pattern_tokens_field_names_exist_on_model():
    """Every PATTERN_TOKENS entry must reference a real MediaMetadata field
    (or one of the aliases that point at the same field)."""
    from arm_contracts import PATTERN_TOKENS, MediaMetadata
    valid_fields = set(MediaMetadata.model_fields.keys())
    for alias, (field_name, _desc, _accessor) in PATTERN_TOKENS.items():
        assert field_name in valid_fields, (
            f"PATTERN_TOKENS['{alias}'] references unknown field '{field_name}'"
        )


def test_pattern_tokens_descriptions_are_non_empty():
    """Every token needs a description (shown in UI autocomplete)."""
    from arm_contracts import PATTERN_TOKENS
    for alias, (_field, desc, _accessor) in PATTERN_TOKENS.items():
        assert desc and isinstance(desc, str), f"token '{alias}' has empty description"


def test_pattern_tokens_accessors_handle_typed_values():
    """Each accessor renders a string from a sample value of its field's type.

    Smoke-tests the rendering path so a wrong lambda surfaces as a test
    failure rather than as a runtime error in the naming engine.
    """
    from datetime import date
    from arm_contracts import PATTERN_TOKENS, MediaMetadata
    from arm_contracts.enums import VideoType

    sample_meta = MediaMetadata(
        title="Sample",
        year="2024",
        video_type=VideoType.movie,
        imdb_id="tt1234567",
        runtime_seconds=7200,  # 120 min
        genres=["Drama"],
        directors=["Director Name"],
        writers=["Writer Name"],
        mpaa_rating="PG-13",
        released_date=date(2024, 1, 15),
        language="en",
        network="HBO",
        season="03",
        artist="Artist Name",
        album="Album Name",
        album_artist="Album Artist",
    )

    for alias, (field_name, _desc, accessor) in PATTERN_TOKENS.items():
        value = getattr(sample_meta, field_name)
        if value is None or value == [] or value == "":
            continue  # accessors only run on populated values
        rendered = accessor(value)
        assert isinstance(rendered, str), (
            f"accessor for '{alias}' returned {type(rendered).__name__}, expected str"
        )

    # Spot-check the non-trivial accessors
    assert PATTERN_TOKENS["runtime_minutes"][2](sample_meta.runtime_seconds) == "120"
    assert PATTERN_TOKENS["genre"][2](sample_meta.genres) == "Drama"
    assert PATTERN_TOKENS["genre"][2]([]) == ""  # empty list -> empty string
    assert PATTERN_TOKENS["released"][2](sample_meta.released_date) == "2024-01-15"
    assert PATTERN_TOKENS["season"][2]("3") == "03"
    assert PATTERN_TOKENS["video_type"][2](VideoType.movie) == "movie"
