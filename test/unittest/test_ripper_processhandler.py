import sys
import unittest
from unittest.mock import patch
import subprocess

sys.path.insert(0, '/opt/arm')
from arm.ripper.ProcessHandler import arm_subprocess    # noqa: E402


class TestProcessHandler(unittest.TestCase):
    @patch("subprocess.check_output")
    def test_arm_subprocess_success(self, mock_check_output):
        """
        CHECK "arm_subprocess" returns the correct output
        """
        # Mock the subprocess.check_output function to return a mock output
        mock_output = "Hello, World!"
        mock_check_output.return_value = mock_output

        cmd = ["echo", "Hello, World!"]
        in_shell = False

        result = arm_subprocess(cmd, in_shell)

        self.assertEqual(result, mock_output)
        mock_check_output.assert_called_once_with(cmd, shell=in_shell)

    @patch("subprocess.check_output")
    def test_arm_subprocess_error(self, mock_check_output):
        """
        CHECK "arm_subprocess" handles errors
        """
        # Mock the subprocess.run function to raise a CalledProcessError
        mock_check_output.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["invalid_command"],
            output=b"Mock error"
        )

        cmd = ["invalid_command"]
        in_shell = True

        result = arm_subprocess(cmd, in_shell)

        self.assertEqual(result, None)
        mock_check_output.assert_called_once_with(cmd, shell=in_shell)


if __name__ == '__main__':
    unittest.main()
