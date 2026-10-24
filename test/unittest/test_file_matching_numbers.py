"""Fuzzy file matching never substitutes another title."""


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
