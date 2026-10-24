"""MusicBrainz track labels such as "A1" are not track numbers (#1846)."""

from types import SimpleNamespace


def test_vinyl_style_track_labels_use_the_medium_position(monkeypatch):
    from arm.ripper import music_brainz, utils

    stored = []
    monkeypatch.setattr(utils, "database_adder", stored.append)
    job = SimpleNamespace(job_id=1, title="Legend", config=SimpleNamespace(MINLENGTH="0"))
    tracks = [
        {"number": "A1", "position": "1", "recording": {"title": "Is This Love", "length": "230000"}},
        {"number": "A2", "position": "2", "recording": {"title": "No Woman, No Cry", "length": "425000"}},
        {"number": "B1", "position": "3", "recording": {"title": "Could You Be Loved", "length": "236000"}},
    ]
    music_brainz.process_tracks(job, tracks)
    assert [(t.track_number, t.filename) for t in stored] == [
        ("1", "Is This Love"), ("2", "No Woman, No Cry"), ("3", "Could You Be Loved")]


def test_stub_tracks_without_a_position_fall_back_to_their_order(monkeypatch):
    from arm.ripper import music_brainz, utils

    stored = []
    monkeypatch.setattr(utils, "database_adder", stored.append)
    job = SimpleNamespace(job_id=1, title="Stub", config=SimpleNamespace(MINLENGTH="0"))
    music_brainz.process_tracks(job, [{"length": "1000"}, {"number": "A2", "length": "1000"}], is_stub=True)
    assert [(t.track_number, t.filename) for t in stored] == [("1", "Untitled track 1"), ("2", "Untitled track A2")]
