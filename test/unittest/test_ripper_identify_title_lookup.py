"""
DVD title lookup: search with words instead of the raw disc label, keep an
exact disc-ID (CRC64) match, and URL-encode metadata queries.
"""
import io
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, '/opt/arm')
from arm.ripper import identify  # noqa: E402
from arm.ui import metadata  # noqa: E402


def make_job(**values):
    job = SimpleNamespace(label="SPIRITED_AWAY", mountpoint="/mnt/dev/sr0", devpath="/dev/sr0",
                          title=None, year=None, crc_id=None, hasnicetitle=False,
                          has_track_99=False, disctype="dvd", video_type="unknown")
    job.__dict__.update(values)
    job.pretty_table = lambda: ""
    return job


def fake_database_updater(args, job, *_args, **_kwargs):
    for key, value in args.items():
        setattr(job, key, value)
    return True


def crc_api_response(found):
    if not found:
        body = {"success": False, "results": {}}
    else:
        body = {"success": True, "results": {"0": {
            "title": "Spirited-Away", "year": "2001", "imdb_id": "tt0245429",
            "video_type": "movie", "poster_img": "poster.jpg"}}}
    return io.BytesIO(json.dumps(body).encode())


class TestIdentifyDvd(unittest.TestCase):

    def run_identify_dvd(self, job, crc_found):
        with patch.object(identify.pydvdid, "compute", return_value="abc123"), \
                patch.object(identify.urllib.request, "urlopen", return_value=crc_api_response(crc_found)), \
                patch.object(identify.utils, "database_updater", side_effect=fake_database_updater), \
                patch.object(identify, "metadata_selector", return_value=None) as selector, \
                patch.object(identify, "identify_loop") as loop, \
                patch.object(identify, "arm_subprocess", return_value=None):
            self.assertTrue(identify.identify_dvd(job))
        return selector, loop

    def test_label_is_searched_as_words(self):
        """CHECK the label search uses words, not THE_LABEL_WITH_UNDERSCORES"""
        selector, loop = self.run_identify_dvd(make_job(), crc_found=False)
        selector.assert_called_once()
        self.assertEqual(selector.call_args.args[1], "SPIRITED+AWAY")
        self.assertEqual(loop.call_args.args[2], "SPIRITED+AWAY")

    def test_unlabelled_disc_is_not_searched(self):
        """CHECK a disc without a label never searches for the 'not identified' placeholder"""
        job = make_job(label=None)
        with patch.object(identify.pydvdid, "compute", return_value="abc123"), \
                patch.object(identify.urllib.request, "urlopen", return_value=crc_api_response(False)), \
                patch.object(identify.utils, "database_updater", side_effect=fake_database_updater), \
                patch.object(identify.ui_utils, "tmdb_search") as tmdb, \
                patch.object(identify.ui_utils, "call_omdb_api") as omdb, \
                patch.object(identify, "arm_subprocess", return_value=None):
            identify.identify_dvd(job)
        tmdb.assert_not_called()
        omdb.assert_not_called()
        self.assertFalse(job.hasnicetitle)

    def test_placeholder_guard_matches_search_strings(self):
        """CHECK the placeholder guard also catches 'not+identified' and 'NOT_IDENTIFIED'"""
        with patch.object(identify.ui_utils, "tmdb_search") as tmdb:
            for title in ("not identified", "not+identified", "NOT_IDENTIFIED", " ", None):
                self.assertIsNone(identify.metadata_selector(make_job(), title))
        tmdb.assert_not_called()

    def test_crc_match_is_not_overwritten_by_label_search(self):
        """CHECK an exact disc-ID match skips the label search"""
        job = make_job()
        selector, loop = self.run_identify_dvd(job, crc_found=True)
        selector.assert_not_called()
        loop.assert_not_called()
        self.assertEqual(job.title, "Spirited-Away")
        self.assertEqual(job.year, "2001")
        self.assertTrue(job.hasnicetitle)


class TestIdentifySkipsSecondSearch(unittest.TestCase):

    def run_identify(self, job, identified):
        def fake_identify_dvd(dvd_job):
            dvd_job.hasnicetitle = identified
            return True

        with patch.object(identify, "check_mount", return_value=False), \
                patch.dict(identify.cfg.arm_config, {"GET_VIDEO_TITLE": True}), \
                patch.object(identify, "identify_dvd", side_effect=fake_identify_dvd), \
                patch.object(identify, "get_video_details") as details, \
                patch.object(identify, "arm_subprocess", return_value=None):
            identify.identify(job)
        return details

    def test_identified_dvd_is_not_searched_again(self):
        """CHECK get_video_details doesn't replace a title identify_dvd already found"""
        self.run_identify(make_job(), identified=True).assert_not_called()

    def test_unidentified_dvd_is_still_searched(self):
        """CHECK get_video_details still runs when identify_dvd found nothing"""
        self.run_identify(make_job(), identified=False).assert_called_once()


class TestSearchQueries(unittest.TestCase):

    def test_search_title(self):
        """CHECK labels and titles become '+'-separated search words"""
        self.assertEqual(identify.search_title(" THE_WIND_RISES "), "THE+WIND+RISES")
        self.assertEqual(identify.search_title("IT CHAPTER__TWO"), "IT+CHAPTER+TWO")

    def test_tmdb_query_is_encoded(self):
        """CHECK the TMDB search sends words as an encoded query parameter"""
        response = MagicMock(text='{"total_results": 0}')
        with patch.object(metadata.requests, "get", return_value=response) as get:
            metadata.tmdb_fetch_results("FAST+&+FURIOUS", "2009", "key")
        url, params = get.call_args.args[0], get.call_args.kwargs["params"]
        self.assertEqual(url, "https://api.themoviedb.org/3/search/movie")
        self.assertEqual(params, {"api_key": "key", "query": "FAST & FURIOUS", "year": "2009"})
        sent = requests.Request("GET", url, params=params).prepare().url
        self.assertIn("query=FAST+%26+FURIOUS", sent)

    def test_tmdb_tv_fallback_query_is_encoded(self):
        """CHECK the TV fallback search also encodes the query"""
        responses = [MagicMock(text='{"total_results": 0}'), MagicMock(text='{"total_results": 0}')]
        with patch.object(metadata.requests, "get", side_effect=responses) as get, \
                patch.dict(metadata.cfg.arm_config, {"TMDB_API_KEY": "key"}):
            self.assertIsNone(metadata.tmdb_search("DOCTOR+WHO"))
        self.assertEqual(get.call_args.args[0], "https://api.themoviedb.org/3/search/tv")
        self.assertEqual(get.call_args.kwargs["params"], {"api_key": "key", "query": "DOCTOR WHO"})

    def test_omdb_search_sends_spaces(self):
        """CHECK OMDb gets the words, not literal '+' characters"""
        urls = []

        def fake_urlopen(url, *_args, **_kwargs):
            urls.append(url)
            return io.BytesIO(b'{"Response": "False", "Error": "Movie not found!"}')

        with patch.object(metadata.urllib.request, "urlopen", side_effect=fake_urlopen):
            metadata.call_omdb_api("IT+CHAPTER+TWO", "2019")
        self.assertIn("s=IT%20CHAPTER%20TWO&y=2019", urls[0])


if __name__ == '__main__':
    unittest.main()
