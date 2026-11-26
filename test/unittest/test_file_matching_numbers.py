"""Fuzzy file matching never substitutes another title."""

import pytest


def test_missing_title_is_not_replaced_by_a_differently_numbered_title(tmp_path):
    from arm.ripper.utils import find_matching_file

    (tmp_path / "title_t00.mkv").write_bytes(b"main feature")
    expected = str(tmp_path / "title_t01.mkv")
    assert find_matching_file(expected) == expected


def test_minor_name_discrepancy_still_matches(tmp_path):
    from arm.ripper.utils import find_matching_file

    actual = tmp_path / "Ocean's Eleven (2001).mkv"
    actual.write_bytes(b"x")
    assert find_matching_file(str(tmp_path / "Oceans Eleven (2001).mkv")) == str(actual)


@pytest.mark.parametrize("expected,actual", [
    ("title_t1.mkv", "title_t10.mkv"),
    ("title_t01.mkv", "title_t101.mkv"),
    ("title_t01.mkv", "title-t02.mkv"),
    ("Movie123.mkv", "Movie12.mkv"),
    ("Movie (2001).mkv", "Movie (2002).mkv"),
    ("title_t01.mkv", "title.mkv"),
])
def test_changed_or_missing_numeric_tokens_are_not_fuzzy_matches(tmp_path, expected, actual):
    from arm.ripper.utils import find_matching_file

    (tmp_path / actual).write_bytes(b"different title")
    wanted = str(tmp_path / expected)
    assert find_matching_file(wanted) == wanted


def test_title_padding_can_change_without_changing_its_number(tmp_path):
    from arm.ripper.utils import find_matching_file

    actual = tmp_path / "title_t1.mkv"
    actual.write_bytes(b"same title")
    assert find_matching_file(str(tmp_path / "title_t01.mkv")) == str(actual)
