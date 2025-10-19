#!/usr/bin/env python3
"""
Unit tests for GROUP_TV_DISCS_UNDER_SERIES feature

Tests the parent series folder grouping functionality for TV series discs.
"""

import unittest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add ARM to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from arm.ripper import utils


class TestGetTVSeriesParentFolder(unittest.TestCase):
    """Test get_tv_series_parent_folder() function"""

    def setUp(self):
        """Set up test fixtures"""
        self.job = Mock()
        self.job.title = "Breaking Bad"
        self.job.title_manual = None
        self.job.year = "2008"
        self.job.video_type = "series"

    def test_parent_folder_with_year(self):
        """Test parent folder includes year"""
        result = utils.get_tv_series_parent_folder(self.job)
        self.assertEqual(result, "Breaking Bad (2008)")

    def test_parent_folder_without_year(self):
        """Test parent folder without year"""
        self.job.year = None
        result = utils.get_tv_series_parent_folder(self.job)
        self.assertEqual(result, "Breaking Bad")

    def test_parent_folder_with_manual_title(self):
        """Test parent folder uses manual title when set"""
        self.job.title_manual = "Breaking Bad (US)"
        result = utils.get_tv_series_parent_folder(self.job)
        self.assertEqual(result, "Breaking Bad (US) (2008)")

    def test_parent_folder_with_special_chars(self):
        """Test parent folder with special characters in title"""
        self.job.title = "Marvel's Agents of S.H.I.E.L.D."
        result = utils.get_tv_series_parent_folder(self.job)
        self.assertEqual(result, "Marvel's Agents of S.H.I.E.L.D. (2008)")

    def test_parent_folder_empty_year(self):
        """Test parent folder with empty string year"""
        self.job.year = ""
        result = utils.get_tv_series_parent_folder(self.job)
        self.assertEqual(result, "Breaking Bad")

    def test_parent_folder_zero_year(self):
        """Test parent folder with '0000' year (invalid)"""
        self.job.year = "0000"
        result = utils.get_tv_series_parent_folder(self.job)
        self.assertEqual(result, "Breaking Bad")


class TestGroupTVDiscsIntegration(unittest.TestCase):
    """Integration tests for GROUP_TV_DISCS_UNDER_SERIES with USE_DISC_LABEL_FOR_TV"""

    def setUp(self):
        """Set up test fixtures"""
        self.job = Mock()
        self.job.title = "Breaking Bad"
        self.job.title_manual = None
        self.job.year = "2008"
        self.job.video_type = "series"
        self.job.label = "BB_S01_D01"
        
        # Mock config object
        self.job.config = Mock()
        self.job.config.USE_DISC_LABEL_FOR_TV = True
        self.job.config.GROUP_TV_DISCS_UNDER_SERIES = True

    def test_both_features_enabled(self):
        """Test folder structure with both features enabled"""
        parent = utils.get_tv_series_parent_folder(self.job)
        disc_folder = utils.get_tv_folder_name(self.job)
        
        self.assertEqual(parent, "Breaking Bad (2008)")
        self.assertEqual(disc_folder, "Breaking_Bad_S1D1")
        
        # Simulated full path structure
        full_path = f"tv/{parent}/{disc_folder}"
        self.assertEqual(full_path, "tv/Breaking Bad (2008)/Breaking_Bad_S1D1")

    def test_disc_label_only(self):
        """Test with USE_DISC_LABEL_FOR_TV enabled, GROUP disabled"""
        self.job.config.GROUP_TV_DISCS_UNDER_SERIES = False
        
        disc_folder = utils.get_tv_folder_name(self.job)
        self.assertEqual(disc_folder, "Breaking_Bad_S1D1")
        
        # Path without parent folder
        full_path = f"tv/{disc_folder}"
        self.assertEqual(full_path, "tv/Breaking_Bad_S1D1")

    def test_grouping_only(self):
        """Test with GROUP_TV_DISCS_UNDER_SERIES enabled, disc label disabled"""
        self.job.config.USE_DISC_LABEL_FOR_TV = False
        
        parent = utils.get_tv_series_parent_folder(self.job)
        disc_folder = utils.get_tv_folder_name(self.job)
        
        self.assertEqual(parent, "Breaking Bad (2008)")
        # Falls back to standard naming when disc label is disabled
        self.assertEqual(disc_folder, "Breaking Bad (2008)")

    def test_neither_feature_enabled(self):
        """Test with both features disabled (standard behavior)"""
        self.job.config.USE_DISC_LABEL_FOR_TV = False
        self.job.config.GROUP_TV_DISCS_UNDER_SERIES = False
        
        disc_folder = utils.get_tv_folder_name(self.job)
        self.assertEqual(disc_folder, "Breaking Bad (2008)")
        
        # Path is just standard naming
        full_path = f"tv/{disc_folder}"
        self.assertEqual(full_path, "tv/Breaking Bad (2008)")

    def test_multiple_discs_same_series(self):
        """Test multiple discs from same series generate correct folder names"""
        discs = [
            ("BB_S01_D01", "Breaking_Bad_S1D1"),
            ("BB_S01_D02", "Breaking_Bad_S1D2"),
            ("BB_S02_D01", "Breaking_Bad_S2D1"),
            ("BB_S03_D01", "Breaking_Bad_S3D1"),
        ]
        
        parent = utils.get_tv_series_parent_folder(self.job)
        
        for label, expected_folder in discs:
            self.job.label = label
            disc_folder = utils.get_tv_folder_name(self.job)
            self.assertEqual(disc_folder, expected_folder)
            
            # All should be under same parent
            full_path = f"tv/{parent}/{disc_folder}"
            self.assertTrue(full_path.startswith("tv/Breaking Bad (2008)/"))

    def test_different_series_different_parents(self):
        """Test different series get different parent folders"""
        series_data = [
            ("Breaking Bad", "2008", "BB_S01_D01", "Breaking Bad (2008)", "Breaking_Bad_S1D1"),
            ("Game of Thrones", "2011", "GOT_S01_D01", "Game of Thrones (2011)", "Game_of_Thrones_S1D1"),
            ("The Wire", "2002", "WIRE_S01_D01", "The Wire (2002)", "The_Wire_S1D1"),
        ]
        
        for title, year, label, expected_parent, expected_disc in series_data:
            self.job.title = title
            self.job.year = year
            self.job.label = label
            
            parent = utils.get_tv_series_parent_folder(self.job)
            disc_folder = utils.get_tv_folder_name(self.job)
            
            self.assertEqual(parent, expected_parent)
            self.assertEqual(disc_folder, expected_disc)

    def test_manual_title_affects_both_folders(self):
        """Test manual title updates both parent and disc folder names"""
        self.job.title_manual = "Breaking Bad (US)"
        
        parent = utils.get_tv_series_parent_folder(self.job)
        disc_folder = utils.get_tv_folder_name(self.job)
        
        self.assertEqual(parent, "Breaking Bad (US) (2008)")
        self.assertTrue(disc_folder.startswith("Breaking_Bad_(US)_S1D1"))

    def test_grouping_with_failed_disc_parsing(self):
        """Test grouping when disc label parsing fails"""
        self.job.label = "INVALID_LABEL"
        
        parent = utils.get_tv_series_parent_folder(self.job)
        disc_folder = utils.get_tv_folder_name(self.job)
        
        # Parent is still valid
        self.assertEqual(parent, "Breaking Bad (2008)")
        # Disc folder falls back to standard naming
        self.assertEqual(disc_folder, "Breaking Bad (2008)")

    def test_config_attributes_missing(self):
        """Test behavior when config attributes are missing (backward compatibility)"""
        # Remove attributes to simulate old config
        del self.job.config.USE_DISC_LABEL_FOR_TV
        del self.job.config.GROUP_TV_DISCS_UNDER_SERIES
        
        # Should still work with fallback behavior
        parent = utils.get_tv_series_parent_folder(self.job)
        disc_folder = utils.get_tv_folder_name(self.job)
        
        self.assertEqual(parent, "Breaking Bad (2008)")
        self.assertEqual(disc_folder, "Breaking Bad (2008)")


class TestFolderPathConstruction(unittest.TestCase):
    """Test complete folder path construction scenarios"""

    def test_full_path_both_features(self):
        """Test complete path construction with both features enabled"""
        job = Mock()
        job.title = "The Office"
        job.year = "2005"
        job.label = "OFFICE_S01_D01"
        job.video_type = "series"
        job.title_manual = None
        job.config = Mock()
        job.config.USE_DISC_LABEL_FOR_TV = True
        job.config.GROUP_TV_DISCS_UNDER_SERIES = True
        job.config.COMPLETED_PATH = "/media/completed"
        
        type_sub_folder = "tv"
        parent_folder = utils.get_tv_series_parent_folder(job)
        disc_folder = utils.get_tv_folder_name(job)
        
        # Construct paths as arm_ripper.py would
        expected_path = os.path.join(
            job.config.COMPLETED_PATH,
            type_sub_folder,
            parent_folder,
            disc_folder
        )
        
        self.assertEqual(expected_path, "/media/completed/tv/The Office (2005)/The_Office_S1D1")

    def test_full_path_disc_label_only(self):
        """Test path construction with only disc label feature"""
        job = Mock()
        job.title = "The Office"
        job.year = "2005"
        job.label = "OFFICE_S01_D01"
        job.video_type = "series"
        job.title_manual = None
        job.config = Mock()
        job.config.USE_DISC_LABEL_FOR_TV = True
        job.config.GROUP_TV_DISCS_UNDER_SERIES = False
        job.config.COMPLETED_PATH = "/media/completed"
        
        type_sub_folder = "tv"
        disc_folder = utils.get_tv_folder_name(job)
        
        expected_path = os.path.join(
            job.config.COMPLETED_PATH,
            type_sub_folder,
            disc_folder
        )
        
        self.assertEqual(expected_path, "/media/completed/tv/The_Office_S1D1")

    def test_full_path_standard_naming(self):
        """Test path construction with standard naming (no features)"""
        job = Mock()
        job.title = "The Office"
        job.year = "2005"
        job.label = "OFFICE_S01_D01"
        job.video_type = "series"
        job.title_manual = None
        job.config = Mock()
        job.config.USE_DISC_LABEL_FOR_TV = False
        job.config.GROUP_TV_DISCS_UNDER_SERIES = False
        job.config.COMPLETED_PATH = "/media/completed"
        
        type_sub_folder = "tv"
        disc_folder = utils.get_tv_folder_name(job)
        
        expected_path = os.path.join(
            job.config.COMPLETED_PATH,
            type_sub_folder,
            disc_folder
        )
        
        self.assertEqual(expected_path, "/media/completed/tv/The Office (2005)")


if __name__ == '__main__':
    unittest.main()
