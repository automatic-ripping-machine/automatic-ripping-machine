"""
MusicBrainz lists one release per pressing of a CD. ARM must use the first CD
release only, and tolerate recordings without a length.
"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, '/opt/arm')
from arm.ripper import music_brainz  # noqa: E402


def release(title, release_id):
    tracks = [{"number": str(n), "recording": {"title": f"Song {n}", "length": "200000"}} for n in (1, 2, 3)]
    return {"id": release_id, "title": title, "date": "1999-05-01",
            "artist-credit": [{"artist": {"name": "Band"}}],
            "cover-art-archive": {"artwork": "false"},
            "medium-list": [{"format": "CD", "track-list": tracks}]}


DISC_INFO = {"disc": {"offset-count": 3, "release-list": [
    release("Album", "first-pressing"), release("Album (Remaster)", "second-pressing")]}}


class TestFirstCdReleaseOnly(unittest.TestCase):

    def test_only_the_first_cd_release_is_used(self):
        """CHECK tracks and title come from the first CD release only"""
        job = SimpleNamespace(job_id=3)
        with patch.object(music_brainz.u, "put_track") as put_track, \
                patch.object(music_brainz.u, "database_updater") as updater, \
                patch.object(music_brainz, "get_cd_art", return_value=False):
            result = music_brainz.check_musicbrainz_data(job, DISC_INFO)
        self.assertEqual(result, "Band Album")
        self.assertEqual(put_track.call_count, 3)
        updater.assert_called_once()
        self.assertEqual(updater.call_args.args[0]["crc_id"], "first-pressing")


class TestTrackWithoutLength(unittest.TestCase):

    def test_missing_length_is_recorded_as_zero(self):
        """CHECK a recording without a length doesn't crash process_tracks"""
        job = SimpleNamespace(job_id=3)
        tracks = [{"number": "1", "recording": {"title": "Intro"}},
                  {"number": "2", "recording": {"title": "Song", "length": None}}]
        with patch.object(music_brainz.u, "put_track") as put_track:
            music_brainz.process_tracks(job, tracks)
        self.assertEqual([call.args[2] for call in put_track.call_args_list], [0, 0])


if __name__ == '__main__':
    unittest.main()
