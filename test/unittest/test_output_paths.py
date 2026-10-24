from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("title", ["..", ".", "", "[..]", "...", "/../"])
def test_dot_only_titles_never_become_folder_names(title):
    from arm.ripper import utils

    cleaned = utils.clean_for_filename(title)
    assert cleaned == utils.UNSAFE_TITLE_FALLBACK
    assert cleaned.strip(". ")


def test_ordinary_titles_keep_their_upstream_cleaning():
    from arm.ripper import utils

    assert utils.clean_for_filename("Mr. Smith: Goes [2000]") == "Mr.-Smith--Goes-"
    assert utils.clean_for_filename("A.I.") == "A.I."


def test_web_title_editor_cannot_produce_an_empty_folder_name():
    from arm.ui import utils as ui_utils

    assert ui_utils.clean_for_filename("..") == "Untitled-disc"
    assert ui_utils.clean_for_filename("Film: Cut") == "Film- Cut"


@pytest.mark.parametrize("parts", [("..",), (".",), ("",), ("movies", ".."), ("a/../..",), ("/etc",), ("a/..",)])
def test_output_folder_must_stay_strictly_under_its_root(tmp_path, parts):
    from arm.ripper import utils

    with pytest.raises(utils.RipperException):
        utils.contained_path(str(tmp_path), *parts)


def test_contained_path_matches_os_join_for_safe_names(tmp_path):
    import os
    from arm.ripper import utils

    expected = os.path.join(str(tmp_path), "movies", "Film (2000)")
    assert utils.contained_path(str(tmp_path), "movies", "Film (2000)") == expected


def test_makemkv_raw_folder_refuses_a_dot_dot_title(tmp_path, monkeypatch):
    from arm.ripper import makemkv, utils

    job = SimpleNamespace(title="..", stage="1", config=SimpleNamespace(RAW_PATH=str(tmp_path / "raw")))
    (tmp_path / "raw").mkdir()
    with pytest.raises(utils.RipperException):
        makemkv.setup_rawpath(job, utils.contained_path(job.config.RAW_PATH, job.title))
    # An existing safe folder falls back to the stage suffix, still under RAW_PATH.
    job.title = "Film"
    (tmp_path / "raw/Film").mkdir()
    raw_path = makemkv.setup_rawpath(job, utils.contained_path(job.config.RAW_PATH, job.title))
    assert raw_path == str(tmp_path / "raw/Film_1")
    assert (tmp_path / "raw/Film_1").is_dir()
