import sys
import unittest
import os
import tempfile
import shutil

sys.path.insert(0, '/opt/arm')

from arm.ripper.utils import find_matching_file  # noqa: E402


class TestFileMatching(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory for testing"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up the temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_find_matching_file_exact_match(self):
        """Test that exact filename match is returned"""
        # Create a test file
        test_file = os.path.join(self.test_dir, "TestMovie.mp4")
        with open(test_file, 'w') as f:
            f.write("test")

        result = find_matching_file(test_file)
        self.assertEqual(result, test_file)

    def test_find_matching_file_off_by_one(self):
        """Test finding file when name is off by one character (FiveArmies case)"""
        # Expected file has one extra character
        expected_file = os.path.join(self.test_dir, "FiveArmiess.mp4")
        # Actual file is missing one 's'
        actual_file = os.path.join(self.test_dir, "FiveArmies.mp4")

        with open(actual_file, 'w') as f:
            f.write("test")

        result = find_matching_file(expected_file)
        self.assertEqual(result, actual_file)

    def test_find_matching_file_off_by_two(self):
        """Test finding file when name is off by two characters (SpiritedAway case)"""
        # Expected file has two extra characters
        expected_file = os.path.join(self.test_dir, "SpiritedAwayy.mp4")
        # Actual file is missing two 'y's
        actual_file = os.path.join(self.test_dir, "SpiritedAway.mp4")

        with open(actual_file, 'w') as f:
            f.write("test")

        result = find_matching_file(expected_file)
        self.assertEqual(result, actual_file)

    def test_find_matching_file_no_match(self):
        """Test that original file is returned when no similar file exists"""
        expected_file = os.path.join(self.test_dir, "NonExistent.mp4")

        result = find_matching_file(expected_file)
        self.assertEqual(result, expected_file)

    def test_find_matching_file_multiple_candidates(self):
        """Test that the best match is selected when multiple similar files exist"""
        expected_file = os.path.join(self.test_dir, "Movie123.mp4")

        # Create multiple files
        close_match = os.path.join(self.test_dir, "Movie12.mp4")
        far_match = os.path.join(self.test_dir, "Movie1.mp4")

        with open(close_match, 'w') as f:
            f.write("test")
        with open(far_match, 'w') as f:
            f.write("test")

        result = find_matching_file(expected_file)
        # Should return the closer match
        self.assertEqual(result, close_match)

    def test_find_matching_file_different_extension(self):
        """Test that files with different extensions are not matched"""
        expected_file = os.path.join(self.test_dir, "TestMovie.mp4")
        wrong_ext_file = os.path.join(self.test_dir, "TestMovie.mkv")

        with open(wrong_ext_file, 'w') as f:
            f.write("test")

        result = find_matching_file(expected_file)
        # Should not match files with different extensions
        self.assertEqual(result, expected_file)

    def test_find_matching_file_nonexistent_directory(self):
        """Test handling of non-existent directory"""
        expected_file = os.path.join(self.test_dir, "nonexistent_dir", "TestMovie.mp4")

        result = find_matching_file(expected_file)
        self.assertEqual(result, expected_file)

    def test_fuzzy_match_with_file_move(self):
        """Test fuzzy matching in a simulated file move scenario"""
        # Create source file with slightly different name
        actual_source = os.path.join(self.test_dir, "SourceMovie.mp4")
        expected_source = os.path.join(self.test_dir, "SourceMoviee.mp4")
        destination = os.path.join(self.test_dir, "dest", "FinalMovie.mp4")

        # Create the source file
        with open(actual_source, 'w') as f:
            f.write("test content")

        # Create destination directory
        os.makedirs(os.path.dirname(destination), exist_ok=True)

        # Find the file with fuzzy matching
        found_file = find_matching_file(expected_source)

        # Verify it found the right file
        self.assertEqual(found_file, actual_source)

        # Simulate the move
        shutil.move(found_file, destination)

        # Verify the file was moved
        self.assertTrue(os.path.isfile(destination))
        self.assertFalse(os.path.isfile(actual_source))


if __name__ == '__main__':
    unittest.main()
