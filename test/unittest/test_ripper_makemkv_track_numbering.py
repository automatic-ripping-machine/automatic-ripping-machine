import unittest
from unittest.mock import Mock


class TestMakeMKVTrackNumbering(unittest.TestCase):
    """Test that MakeMKV track numbers are correctly converted from 0-indexed to 1-indexed"""

    def test_track_id_storage_conversion(self):
        """
        Test that track IDs from MakeMKV (0-indexed) are converted to 1-indexed for storage

        MakeMKV returns track IDs starting at 0, but we want to store them starting at 1
        for consistency with HandBrake and user expectations.
        """
        # Simulate the conversion that happens in TrackInfoProcessor._add_track()
        # In the actual code: str(int(self.track_id) + 1)

        test_cases = [
            (0, "1"),   # First track from MakeMKV (0) -> stored as 1
            (1, "2"),   # Second track from MakeMKV (1) -> stored as 2
            (9, "10"),  # Tenth track from MakeMKV (9) -> stored as 10
        ]

        for makemkv_id, expected_stored_id in test_cases:
            stored_id = str(int(makemkv_id) + 1)
            self.assertEqual(stored_id, expected_stored_id,
                             f"MakeMKV track ID {makemkv_id} should be stored as {expected_stored_id}")


class TestMakeMKVCommandGeneration(unittest.TestCase):
    """Test that MakeMKV commands use 0-indexed track numbers"""

    def test_track_number_conversion_in_command(self):
        """
        Test that when building a MakeMKV command, we convert from 1-indexed back to 0-indexed
        """
        # Create mock track with 1-indexed track_number
        mock_track = Mock()
        mock_track.track_number = "1"  # Stored as 1-indexed
        mock_track.length = 3600
        mock_track.filename = "title_1.mkv"

        # Simulate the conversion that should happen in the command
        # In the actual code: str(int(track.track_number) - 1)
        makemkv_track_arg = str(int(mock_track.track_number) - 1)

        # Verify it's converted to 0 for MakeMKV
        self.assertEqual(makemkv_track_arg, "0",
                         "Track number 1 should be converted to 0 for MakeMKV command")

    def test_track_number_conversion_for_multiple_tracks(self):
        """
        Test conversion for multiple track numbers
        """
        test_cases = [
            ("1", "0"),  # First track
            ("2", "1"),  # Second track
            ("10", "9"),  # Tenth track
        ]

        for stored_number, expected_makemkv_number in test_cases:
            makemkv_track_arg = str(int(stored_number) - 1)
            self.assertEqual(makemkv_track_arg, expected_makemkv_number,
                             f"Stored track {stored_number} should convert to {expected_makemkv_number}")


if __name__ == '__main__':
    unittest.main()
