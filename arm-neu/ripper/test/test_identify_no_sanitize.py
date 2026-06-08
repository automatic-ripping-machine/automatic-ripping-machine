"""Tests that identification stores clean, unsanitized titles."""
import unittest.mock

from arm.ripper import identify


class TestUpdateJobNoSanitize:
    """update_job should store API titles without aggressive sanitization."""

    def test_title_preserves_spaces(self, app_context, sample_job):
        """Metadata title 'Serial Mom' should not become 'Serial-Mom'."""
        match = unittest.mock.MagicMock()
        match.title = "Serial Mom"
        match.year = "1994"
        match.type = "movie"
        match.imdb_id = "tt0111127"
        match.poster_url = ""
        match.raw_result = None
        match.score = 0.95
        match.title_score = 0.95
        match.year_score = 1.0
        match.type_score = 1.0

        selection = unittest.mock.MagicMock()
        selection.hasnicetitle = True
        selection.confident = True
        selection.best = match
        selection.all_scored = [match]
        selection.label_info = None

        sample_job.label = "SERIAL_MOM"

        with unittest.mock.patch('arm.ripper.arm_matcher.match_disc', return_value=selection), \
             unittest.mock.patch('arm.ripper.utils.database_updater') as mock_db:
            identify.update_job(sample_job, {"Search": [{"Title": "Serial Mom", "Year": "1994"}]})

        # Verify the title stored in the database_updater call has spaces
        args_dict = mock_db.call_args[0][0]
        assert args_dict['title'] == "Serial Mom"
        assert " " in args_dict['title']

    def test_title_preserves_colons(self, app_context, sample_job):
        """Colons in metadata titles are preserved for display/search."""
        match = unittest.mock.MagicMock()
        match.title = "Star Wars: A New Hope"
        match.year = "1977"
        match.type = "movie"
        match.imdb_id = "tt0076759"
        match.poster_url = ""
        match.raw_result = None
        match.score = 0.95
        match.title_score = 0.95
        match.year_score = 1.0
        match.type_score = 1.0

        selection = unittest.mock.MagicMock()
        selection.hasnicetitle = True
        selection.confident = True
        selection.best = match
        selection.all_scored = [match]
        selection.label_info = None

        sample_job.label = "STAR_WARS"

        with unittest.mock.patch('arm.ripper.arm_matcher.match_disc', return_value=selection), \
             unittest.mock.patch('arm.ripper.utils.database_updater') as mock_db:
            identify.update_job(sample_job, {"Search": [{"Title": "Star Wars: A New Hope", "Year": "1977"}]})

        args_dict = mock_db.call_args[0][0]
        assert args_dict['title'] == "Star Wars: A New Hope"

    def test_trailing_year_stripped_from_title(self, app_context, sample_job):
        """API titles like 'The Cabin In The Woods (2012)' should have the
        trailing year stripped since year is stored separately."""
        match = unittest.mock.MagicMock()
        match.title = "The Cabin In The Woods (2012)"
        match.year = "2012"
        match.type = "movie"
        match.imdb_id = "tt1259521"
        match.poster_url = ""
        match.raw_result = None
        match.score = 0.95
        match.title_score = 0.95
        match.year_score = 1.0
        match.type_score = 1.0

        selection = unittest.mock.MagicMock()
        selection.hasnicetitle = True
        selection.confident = True
        selection.best = match
        selection.all_scored = [match]
        selection.label_info = None

        sample_job.label = "CABIN_IN_THE_WOODS"

        with unittest.mock.patch('arm.ripper.arm_matcher.match_disc', return_value=selection), \
             unittest.mock.patch('arm.ripper.utils.database_updater') as mock_db:
            identify.update_job(sample_job, {"Search": [{"Title": "The Cabin In The Woods (2012)", "Year": "2012"}]})

        args_dict = mock_db.call_args[0][0]
        assert args_dict['title'] == "The Cabin In The Woods"
        assert "(2012)" not in args_dict['title']

    def test_year_not_stripped_when_mismatch(self, app_context, sample_job):
        """Don't strip (YEAR) if it doesn't match the year field."""
        match = unittest.mock.MagicMock()
        match.title = "Apollo 13 (1995)"
        match.year = "1995"
        match.type = "movie"
        match.imdb_id = "tt0112384"
        match.poster_url = ""
        match.raw_result = None
        match.score = 0.95
        match.title_score = 0.95
        match.year_score = 1.0
        match.type_score = 1.0

        selection = unittest.mock.MagicMock()
        selection.hasnicetitle = True
        selection.confident = True
        selection.best = match
        selection.all_scored = [match]
        selection.label_info = None

        sample_job.label = "APOLLO_13"

        with unittest.mock.patch('arm.ripper.arm_matcher.match_disc', return_value=selection), \
             unittest.mock.patch('arm.ripper.utils.database_updater') as mock_db:
            identify.update_job(sample_job, {"Search": [{"Title": "Apollo 13 (1995)", "Year": "1995"}]})

        args_dict = mock_db.call_args[0][0]
        # Year stripped since it matches
        assert args_dict['title'] == "Apollo 13"

    def test_year_in_middle_not_stripped(self, app_context, sample_job):
        """Only strip trailing (YEAR), not mid-title numbers."""
        match = unittest.mock.MagicMock()
        match.title = "2001: A Space Odyssey"
        match.year = "1968"
        match.type = "movie"
        match.imdb_id = "tt0062622"
        match.poster_url = ""
        match.raw_result = None
        match.score = 0.95
        match.title_score = 0.95
        match.year_score = 1.0
        match.type_score = 1.0

        selection = unittest.mock.MagicMock()
        selection.hasnicetitle = True
        selection.confident = True
        selection.best = match
        selection.all_scored = [match]
        selection.label_info = None

        sample_job.label = "2001_A_SPACE_ODYSSEY"

        with unittest.mock.patch('arm.ripper.arm_matcher.match_disc', return_value=selection), \
             unittest.mock.patch('arm.ripper.utils.database_updater') as mock_db:
            identify.update_job(sample_job, {"Search": [{"Title": "2001: A Space Odyssey", "Year": "1968"}]})

        args_dict = mock_db.call_args[0][0]
        assert args_dict['title'] == "2001: A Space Odyssey"
