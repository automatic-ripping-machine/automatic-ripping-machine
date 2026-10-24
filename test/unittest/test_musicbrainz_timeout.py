"""MusicBrainz / Cover Art Archive lookups must not be able to hang a job forever"""
import socket
import types

import musicbrainzngs as mb
import pytest

from arm.ripper import music_brainz

PREVIOUS_TIMEOUT = 7.0
DISC_INFO = {
    'disc': {
        'release-list': [
            {'id': 'release-id', 'cover-art-archive': {'artwork': 'true'}},
        ],
    },
}


@pytest.fixture
def job(monkeypatch):
    """A minimal job, with database updates recorded instead of written"""
    updates = []
    monkeypatch.setattr(music_brainz.u, "database_updater", lambda args, job: updates.append(args))
    original = socket.getdefaulttimeout()
    socket.setdefaulttimeout(PREVIOUS_TIMEOUT)
    yield types.SimpleNamespace(arm_version="test", job_id=1, updates=updates)
    socket.setdefaulttimeout(original)


def test_disc_lookup_uses_timeout_and_restores_it(job, monkeypatch):
    seen = []

    def fake_lookup(discid, includes):
        seen.append(socket.getdefaulttimeout())
        return {'disc': {}}

    monkeypatch.setattr(music_brainz.mb, "get_releases_by_discid", fake_lookup)

    assert music_brainz.get_disc_info(job, "discid") == {'disc': {}}
    assert seen == [music_brainz.MUSICBRAINZ_TIMEOUT]
    assert socket.getdefaulttimeout() == PREVIOUS_TIMEOUT


def test_title_lookup_network_error_restores_timeout(job, monkeypatch):
    seen = []

    def fake_lookup(discid, includes):
        seen.append(socket.getdefaulttimeout())
        raise mb.NetworkError(cause=socket.timeout("timed out"))

    monkeypatch.setattr(music_brainz.mb, "get_releases_by_discid", fake_lookup)

    assert music_brainz.get_title("discid", job) == "not identified"
    assert seen == [music_brainz.MUSICBRAINZ_TIMEOUT]
    assert socket.getdefaulttimeout() == PREVIOUS_TIMEOUT


def test_cover_art_timeout_is_handled(job, monkeypatch):
    seen = []

    def fake_image_list(release_id):
        seen.append(socket.getdefaulttimeout())
        raise mb.NetworkError(cause=socket.timeout("timed out"))

    monkeypatch.setattr(music_brainz.mb, "get_image_list", fake_image_list)

    assert music_brainz.get_cd_art(job, DISC_INFO) is False
    assert seen == [music_brainz.MUSICBRAINZ_TIMEOUT]
    assert socket.getdefaulttimeout() == PREVIOUS_TIMEOUT
    assert job.updates == [False]
