#!/usr/bin/env python3
"""
Unit tests for disc label-based TV series folder naming feature.

Tests the parsing, normalization, and folder name generation functions
for the USE_DISC_LABEL_FOR_TV configuration option.
"""
import unittest
from unittest.mock import MagicMock, patch
import sys

sys.path.insert(0, '/opt/arm')

from arm.ripper import utils  # noqa: E402


class TestParseDiscLabelForIdentifiers(unittest.TestCase):
    """Test the parse_disc_label_for_identifiers function with various label formats."""

    def test_s_d_no_separator(self):
        """Test S##D## format without separators (e.g., S1D1, S01D02)."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("BB_S1D1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("S01D02"), "S1D2")
        self.assertEqual(utils.parse_disc_label_for_identifiers("BreakingBad_S10D5"), "S10D5")

    def test_s_d_with_underscore(self):
        """Test S##_D## format with underscore separator."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("S1_D1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("S01_D02"), "S1D2")
        self.assertEqual(utils.parse_disc_label_for_identifiers("BB_S01_D1"), "S1D1")

    def test_s_d_with_hyphen(self):
        """Test S##-D## format with hyphen separator."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("S1-D1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("S01-D02"), "S1D2")
        self.assertEqual(utils.parse_disc_label_for_identifiers("Series_S2-D3"), "S2D3")

    def test_s_d_with_space(self):
        """Test S## D## format with space separator."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("S1 D1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("Breaking Bad S01 D2"), "S1D2")

    def test_s_e_d_format(self):
        """Test S##E##D## format with episode number."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("S1E1D1"), "S1E1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("S01E01D1"), "S1E1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("S1E1_D1"), "S1E1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("S01_E05_D2"), "S1E5D2")

    def test_season_disc_word_format(self):
        """Test Season##Disc## word format."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("Season1Disc1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("SEASON01DISC02"), "S1D2")
        self.assertEqual(utils.parse_disc_label_for_identifiers("Season 1 Disc 1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("Season_01_Disc_02"), "S1D2")

    def test_leading_zeros_stripped(self):
        """Test that leading zeros are stripped from season/disc numbers."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("S01D01"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("S001D001"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("Season01Disc01"), "S1D1")

    def test_separate_s_and_d_tokens(self):
        """Test finding S## and D## separately anywhere in label."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("Breaking Bad S01 Disc 1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("Disc1_S2"), "S2D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("GOT S5 D3"), "S5D3")

    def test_case_insensitivity(self):
        """Test that parsing is case-insensitive."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("s1d1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("season1disc1"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("BREAKING_BAD_S01_D02"), "S1D2")

    def test_no_match_returns_none(self):
        """Test that invalid labels return None."""
        self.assertIsNone(utils.parse_disc_label_for_identifiers("BREAKING_BAD_2008"))
        self.assertIsNone(utils.parse_disc_label_for_identifiers("Episode 1"))
        self.assertIsNone(utils.parse_disc_label_for_identifiers("No identifiers here"))
        self.assertIsNone(utils.parse_disc_label_for_identifiers("Disc1"))  # Missing season
        self.assertIsNone(utils.parse_disc_label_for_identifiers("S1"))  # Missing disc

    def test_empty_or_none_input(self):
        """Test that empty or None input returns None."""
        self.assertIsNone(utils.parse_disc_label_for_identifiers(""))
        self.assertIsNone(utils.parse_disc_label_for_identifiers(None))

    def test_complex_labels(self):
        """Test complex real-world label examples."""
        self.assertEqual(utils.parse_disc_label_for_identifiers("TheWire_S01_D01_BluRay"), "S1D1")
        self.assertEqual(utils.parse_disc_label_for_identifiers("GOT_Season_05_Disc_03"), "S5D3")
        self.assertEqual(utils.parse_disc_label_for_identifiers("Breaking.Bad.S02.D02"), "S2D2")


class TestNormalizeSeriesName(unittest.TestCase):
    """Test the normalize_series_name function."""

    def test_basic_normalization(self):
        """Test basic space-to-underscore replacement."""
        self.assertEqual(utils.normalize_series_name("Breaking Bad"), "Breaking_Bad")
        self.assertEqual(utils.normalize_series_name("Game of Thrones"), "Game_of_Thrones")

    def test_special_characters(self):
        """Test removal/replacement of special characters."""
        self.assertEqual(utils.normalize_series_name("Series!Name"), "Series_Name")
        self.assertEqual(utils.normalize_series_name("Series@#$Name"), "Series_Name")
        self.assertEqual(utils.normalize_series_name("Series: The Show"), "Series__The_Show")

    def test_preserve_hyphens_and_parens(self):
        """Test that hyphens and parentheses are preserved."""
        self.assertEqual(utils.normalize_series_name("The Walking-Dead"), "The_Walking-Dead")
        self.assertEqual(utils.normalize_series_name("Series (US)"), "Series_(US)")
        self.assertEqual(utils.normalize_series_name("Show-Name (2020)"), "Show-Name_(2020)")

    def test_multiple_spaces(self):
        """Test that multiple consecutive spaces become single underscore."""
        self.assertEqual(utils.normalize_series_name("Series   Name"), "Series_Name")
        self.assertEqual(utils.normalize_series_name("The  Office"), "The_Office")

    def test_leading_trailing_underscores(self):
        """Test stripping of leading/trailing underscores."""
        self.assertEqual(utils.normalize_series_name("__Series__"), "Series")
        self.assertEqual(utils.normalize_series_name("_Name_"), "Name")

    def test_unicode_characters(self):
        """Test handling of unicode/accented characters."""
        # Should convert to ASCII equivalents or strip
        self.assertEqual(utils.normalize_series_name("Café"), "Caf")
        self.assertEqual(utils.normalize_series_name("Niño"), "Nio")

    def test_empty_or_none_input(self):
        """Test that empty or None input returns empty string."""
        self.assertEqual(utils.normalize_series_name(""), "")
        self.assertEqual(utils.normalize_series_name(None), "")

    def test_already_normalized(self):
        """Test that already normalized names pass through unchanged."""
        self.assertEqual(utils.normalize_series_name("Breaking_Bad"), "Breaking_Bad")
        self.assertEqual(utils.normalize_series_name("The_Office"), "The_Office")


class TestGetTVFolderName(unittest.TestCase):
    """Test the get_tv_folder_name function with various configurations."""

    def setUp(self):
        """Set up mock job object for testing."""
        self.job = MagicMock()
        self.job.video_type = "series"
        self.job.title = "Breaking Bad"
        self.job.title_manual = None
        self.job.year = "2008"
        self.job.label = "BB_S1D1"

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_feature_enabled_with_valid_label(self):
        """Test folder name generation when feature is enabled and label is valid."""
        result = utils.get_tv_folder_name(self.job)
        self.assertEqual(result, "Breaking_Bad_S1D1")

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_feature_enabled_prefer_manual_title(self):
        """Test that manual title is preferred over auto title."""
        self.job.title_manual = "Breaking Bad (US)"
        result = utils.get_tv_folder_name(self.job)
        self.assertEqual(result, "Breaking_Bad_(US)_S1D1")

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_feature_enabled_invalid_label_fallback(self):
        """Test fallback to standard naming when label parsing fails."""
        self.job.label = "INVALID_LABEL"
        result = utils.get_tv_folder_name(self.job)
        # Should fall back to standard format: "Breaking Bad (2008)"
        self.assertEqual(result, "Breaking Bad (2008)")

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': False})
    def test_feature_disabled_standard_naming(self):
        """Test standard naming when feature is disabled."""
        result = utils.get_tv_folder_name(self.job)
        self.assertEqual(result, "Breaking Bad (2008)")

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_non_series_uses_standard_naming(self):
        """Test that movies use standard naming even if feature is enabled."""
        self.job.video_type = "movie"
        result = utils.get_tv_folder_name(self.job)
        self.assertEqual(result, "Breaking Bad (2008)")

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_no_title_fallback(self):
        """Test fallback when no title is available."""
        self.job.title = None
        self.job.title_manual = None
        result = utils.get_tv_folder_name(self.job)
        # Should fall back to fix_job_title which handles empty titles
        self.assertEqual(result, "")

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_various_label_formats(self):
        """Test various disc label formats."""
        test_cases = [
            ("S01D01", "Breaking_Bad_S1D1"),
            ("Season1Disc1", "Breaking_Bad_S1D1"),
            ("Breaking Bad S02 D03", "Breaking_Bad_S2D3"),
            ("S1E1D1", "Breaking_Bad_S1E1D1"),
        ]

        for label, expected in test_cases:
            self.job.label = label
            result = utils.get_tv_folder_name(self.job)
            self.assertEqual(result, expected, f"Failed for label: {label}")

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_series_without_year(self):
        """Test series without year in metadata."""
        self.job.year = None
        self.job.label = "BB_S1D1"
        result = utils.get_tv_folder_name(self.job)
        self.assertEqual(result, "Breaking_Bad_S1D1")

    @patch('arm.config.config.arm_config', {})
    def test_config_key_missing_defaults_to_false(self):
        """Test that missing config key defaults to standard naming."""
        result = utils.get_tv_folder_name(self.job)
        # Should use standard naming as if feature is disabled
        self.assertEqual(result, "Breaking Bad (2008)")


class TestIntegration(unittest.TestCase):
    """Integration tests combining all functions."""

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_full_workflow_success(self):
        """Test complete workflow from label to folder name."""
        job = MagicMock()
        job.video_type = "series"
        job.title = "Game of Thrones"
        job.title_manual = None
        job.year = "2011"
        job.label = "GOT_Season_01_Disc_02"

        # Parse label
        identifier = utils.parse_disc_label_for_identifiers(job.label)
        self.assertEqual(identifier, "S1D2")

        # Normalize series name
        normalized = utils.normalize_series_name(job.title)
        self.assertEqual(normalized, "Game_of_Thrones")

        # Generate folder name
        folder_name = utils.get_tv_folder_name(job)
        self.assertEqual(folder_name, "Game_of_Thrones_S1D2")

    @patch('arm.config.config.arm_config', {'USE_DISC_LABEL_FOR_TV': True})
    def test_full_workflow_fallback(self):
        """Test complete workflow when parsing fails."""
        job = MagicMock()
        job.video_type = "series"
        job.title = "The Office"
        job.title_manual = None
        job.year = "2005"
        job.label = "NO_IDENTIFIER"

        # Parse label (should fail)
        identifier = utils.parse_disc_label_for_identifiers(job.label)
        self.assertIsNone(identifier)

        # Get folder name (should fall back)
        folder_name = utils.get_tv_folder_name(job)
        self.assertEqual(folder_name, "The Office (2005)")


if __name__ == '__main__':
    unittest.main()
