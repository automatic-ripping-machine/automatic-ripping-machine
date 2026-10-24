"""Tests for picking the job poster from the Cover Art Archive (#1197)"""
from unittest import mock

import arm.ripper.music_brainz as music_brainz

CAA = "https://coverartarchive.org/release/c2ee7139-1d26-4d94-861d-bc2f3231da00/"
DISC_INFO = {"disc": {"release-list": [{"id": "c2ee7139-1d26-4d94-861d-bc2f3231da00",
                                        "cover-art-archive": {"artwork": "true"}}]}}


def _get_cd_art(images):
    """Run get_cd_art with a mocked CAA response and return (result, database_updater mock)"""
    with mock.patch.object(music_brainz.mb, "get_image_list", return_value={"images": images}), \
            mock.patch.object(music_brainz.u, "database_updater") as updater:
        result = music_brainz.get_cd_art(mock.Mock(), DISC_INFO)
    return result, updater


def test_front_cover_preferred_over_first_image():
    images = [
        {"image": CAA + "back.jpg", "front": False, "back": True, "types": ["Back"]},
        {"image": CAA + "front.jpg", "front": True, "back": False, "types": ["Front"]},
    ]
    result, updater = _get_cd_art(images)
    assert result is True
    updater.assert_called_once()
    assert updater.call_args[0][0]["poster_url"] == CAA + "front.jpg"


def test_front_type_without_flag_is_preferred():
    images = [
        {"image": CAA + "booklet.jpg", "types": ["Booklet"]},
        {"image": CAA + "front.jpg", "types": ["Front", "Booklet"]},
    ]
    _, updater = _get_cd_art(images)
    assert updater.call_args[0][0]["poster_url"] == CAA + "front.jpg"


def test_first_image_used_when_no_front():
    images = [
        {"image": CAA + "first.jpg"},
        {"image": CAA + "second.jpg", "front": False, "types": ["Back"]},
    ]
    result, updater = _get_cd_art(images)
    assert result is True
    assert updater.call_args[0][0]["poster_url"] == CAA + "first.jpg"


def test_no_images():
    result, updater = _get_cd_art([])
    assert result is False
    updater.assert_not_called()
