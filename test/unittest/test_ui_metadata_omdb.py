"""Tests for the OMDb exact title fallback in arm.ui.metadata.call_omdb_api"""
import sys
import json
import unittest
from unittest import mock

sys.path.insert(0, '/opt/arm')

from arm.ui import metadata  # noqa: E402

TOO_MANY = {"Response": "False", "Error": "Too many results."}
NOT_FOUND = {"Response": "False", "Error": "Movie not found!"}
SEARCH_OK = {
    "Search": [{"Title": "Goldfinger", "Year": "1964", "imdbID": "tt0058150", "Type": "movie", "Poster": "N/A"}],
    "totalResults": "1",
    "Response": "True",
}
EXACT_ER = {
    "Title": "ER", "Year": "1994–2009", "imdbID": "tt0108757", "Type": "series",
    "Poster": "https://example.com/er.jpg", "Plot": "Plot", "Response": "True",
}


def fake_urlopen(responses):
    """Return a urlopen replacement that answers in order and records the urls"""
    calls = []

    def _urlopen(url):
        calls.append(url)
        response = mock.Mock()
        response.read.return_value = json.dumps(responses[len(calls) - 1]).encode()
        return response
    return _urlopen, calls


class TestOmdbExactTitleFallback(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(metadata.cfg.arm_config, {"OMDB_API_KEY": "key"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_search(self, responses, title="ER", year=None, imdb_id=None):
        urlopen, calls = fake_urlopen(responses)
        with mock.patch("urllib.request.urlopen", side_effect=urlopen):
            result = metadata.call_omdb_api(title=title, year=year, imdb_id=imdb_id)
        return result, calls

    def test_search_results_are_returned_unchanged(self):
        result, calls = self.run_search([SEARCH_OK], title="Goldfinger")
        self.assertEqual(len(calls), 1)
        self.assertIn("?s=Goldfinger", calls[0])
        self.assertEqual(result["Search"][0]["imdbID"], "tt0058150")

    def test_too_many_results_falls_back_to_exact_title(self):
        result, calls = self.run_search([TOO_MANY, EXACT_ER])
        self.assertEqual(len(calls), 2)
        self.assertIn("?s=ER", calls[0])
        self.assertIn("?t=ER", calls[1])
        self.assertEqual(result["Search"][0]["imdbID"], "tt0108757")
        self.assertEqual(result["Search"][0]["Type"], "series")
        self.assertEqual(result["Search"][0]["Year"], "1994–2009")

    def test_fallback_keeps_the_year(self):
        _, calls = self.run_search([TOO_MANY, EXACT_ER], year="1994")
        self.assertIn("?t=ER&y=1994", calls[1])

    def test_fallback_ignores_none_year_string(self):
        _, calls = self.run_search([TOO_MANY, EXACT_ER], year="None")
        self.assertNotIn("&y=", calls[1])

    def test_fallback_without_match_returns_none(self):
        result, calls = self.run_search([TOO_MANY, NOT_FOUND])
        self.assertEqual(len(calls), 2)
        self.assertIsNone(result)

    def test_not_found_does_not_trigger_fallback(self):
        result, calls = self.run_search([NOT_FOUND], title="Nothing")
        self.assertEqual(len(calls), 1)
        self.assertIsNone(result)

    def test_imdb_id_lookup_is_unchanged(self):
        result, calls = self.run_search([EXACT_ER], title=None, imdb_id="tt0108757")
        self.assertEqual(len(calls), 1)
        self.assertIn("?i=tt0108757", calls[0])
        self.assertEqual(result["imdbID"], "tt0108757")


if __name__ == '__main__':
    unittest.main()
