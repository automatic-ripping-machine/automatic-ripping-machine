import errno
import unittest
from unittest.mock import MagicMock, mock_open, patch
import sys

sys.path.insert(0,'/opt/arm')
from arm.ripper.ARMInfo import ARMInfo

class TestArmInfo(unittest.TestCase):

    def setUp(self):
        self.arm_info = ARMInfo()
        self.arm_info.install_path = '/opt/arm'

    """
    ************************************************************
    Test - get_git_commit
    test_get_git_commit_fail - check for bad value check
    test_get_git_commit_pass - check for normal behaviour
    test_get_git_commit_bounds_low - check for low values
    test_get_git_commit_bounds_high - check for high values
    ************************************************************
    """
    def test_get_git_commit_fail(self):
        """
        CHECK "get_git_commit" handles returning no value
        data check:
            branch: return Unknown
            commit: return Unknown
        """
        arm_subprocess_mock = MagicMock()
        arm_subprocess_mock.return_value = b" master\ncommit "
        with unittest.mock.patch('arm.ripper.ProcessHandler.arm_subprocess',
                                arm_subprocess_mock):
           self.arm_info.get_git_commit()

        self.assertEqual(self.arm_info.git_branch, "unknown")
        self.assertEqual(self.arm_info.git_commit, "unknown")


    def test_get_git_commit_pass(self):
        """
        CHECK "get_git_commit" handles returning correct values
        data check:
            branch: master
            commit: abc12de
        """
        arm_subprocess_mock = MagicMock()
        arm_subprocess_mock.return_value = b"* master\ncommit abc12de"
        with unittest.mock.patch('arm.ripper.ProcessHandler.arm_subprocess',
                                arm_subprocess_mock):
           self.arm_info.get_git_commit()

        self.assertEqual(self.arm_info.git_branch, "master")
        self.assertEqual(self.arm_info.git_commit, "abc12de")


    def test_get_git_commit_bounds_low(self):
        """
        CHECK "get_git_commit" handles bounds low
        data check:
            branch: m
            commit: a
        """
        arm_subprocess_mock = MagicMock()
        arm_subprocess_mock.return_value = b"* m\ncommit a"
        with unittest.mock.patch('arm.ripper.ProcessHandler.arm_subprocess',
                                arm_subprocess_mock):
           self.arm_info.get_git_commit()

        self.assertEqual(self.arm_info.git_branch, "unknown")
        self.assertEqual(self.arm_info.git_commit, "unknown")

    def test_get_git_commit_bounds_high(self):
        """
        CHECK "get_git_commit" handles bounds high
        data check:
            branch: thequickbrownfoxjumpedoverthelazydog
            commit: a1b2c3d4e5f6g7h8i9j10
        """
        branch_len = 10
        commit_len = 7
        data_check_branch = "thequickbrownfoxjumpedoverthelazydog"
        data_check_commit = "a1b2c3d4e5f6g7h8i9j10"
        arm_subprocess_mock = MagicMock()
        arm_subprocess_mock.return_value = b"* thequickbrownfoxjumpedoverthelazydog\ncommit a1b2c3d4e5f6g7h8i9j10"
        with unittest.mock.patch('arm.ripper.ProcessHandler.arm_subprocess',
                                arm_subprocess_mock):
           self.arm_info.get_git_commit()

        self.assertEqual(self.arm_info.git_branch, data_check_branch[0:branch_len]+"...")
        self.assertEqual(self.arm_info.git_commit, data_check_commit[0:commit_len])

    """
    ************************************************************
    Test - get_arm_version
    test_get_arm_version_nofile - check for no file
    test_get_arm_version_pass - check for normal behaviour
    test_get_arm_version_bounds_low - check for low values
    test_get_arm_version_bounds_high - check for high values
    ************************************************************
    """
    def test_get_arm_version_nofile(self):
        """
        CHECK get_git_commit handles no file found
        data check:
            version: return unknown
        """
        with patch("builtins.open",
                   mock_open()) as mock_file:
            mock_file.side_effect = FileNotFoundError("File Not Found")
            self.arm_info.get_arm_version()

            self.assertEqual(self.arm_info.arm_version, "unknown")

    def test_get_arm_version_pass(self):
        """
        CHECK "get_arm_version" handles returning correct values
        data check:
            version: 1.2.3
        """
        data_check = "1.2.3"
        with unittest.mock.patch('builtins.open',
                                 unittest.mock.mock_open(read_data=data_check)):
            self.arm_info.get_arm_version()

        self.assertEqual(self.arm_info.arm_version, data_check)

    def test_get_arm_version_bounds_low(self):
        """
        CHECK "get_arm_version" handles bounds low
        data check:
            version: -1
        """
        data_check = "-1"
        with unittest.mock.patch('builtins.open',
                                 unittest.mock.mock_open(read_data=data_check)):
            self.arm_info.get_arm_version()

        self.assertEqual(self.arm_info.arm_version, data_check)

    def test_get_arm_version_bounds_high(self):
        """
        CHECK "get_arm_version" handles bounds high
        data check:
            version: 1000.1000
        """
        data_check = "1000.1000"
        with unittest.mock.patch('builtins.open',
                                 unittest.mock.mock_open(read_data=data_check)):
            self.arm_info.get_arm_version()

        self.assertEqual(self.arm_info.arm_version, data_check)

    """
    ************************************************************
    Test - get_python_version
    test_get_python_version_fail - check for bad value check
    test_get_python_version_pass - check for normal behaviour
    test_get_python_bounds_low - check for low values
    test_get_python_bounds_high - check for high values
    ************************************************************
    """
    def test_get_python_version_fail(self):
        """
        CHECK "get_python_version" handles none values
        data check:
            version: none
        """
        data_check = None
        with unittest.mock.patch('sys.version',
                                 data_check):
            self.arm_info.get_python_version()

        self.assertEqual(self.arm_info.python_version, "unknown")

    def test_get_python_version_pass(self):
        """
        CHECK "get_python_version" handles returning correct values
        data check:
            version: 1.2.3
        """
        data_check = "1.2.3"
        with unittest.mock.patch('sys.version',
                                 data_check):
            self.arm_info.get_python_version()

        self.assertEqual(self.arm_info.python_version,data_check)

    def test_get_python_version_bounds_low(self):
        """
        CHECK "get_python_version" handles bounds low
        data check:
            version: -1
        """
        data_check = "-1"
        with unittest.mock.patch('sys.version',
                                 data_check):
            self.arm_info.get_python_version()

        self.assertEqual(self.arm_info.python_version,data_check)

    def test_get_python_version_bounds_high(self):
        """
        CHECK "get_python_version" handles bounds high
        data check:
            version: 1000.1000
        """
        data_check = "1000.1000"
        with unittest.mock.patch('sys.version',
                                 data_check):
            self.arm_info.get_python_version()

        self.assertEqual(self.arm_info.python_version,data_check)

    """
    ************************************************************
    Test - get_user_details
    get_user_details_fail - check for bad value check
    get_user_details_pass - check for normal behaviour
    ************************************************************
    """
    def test_get_user_details_fail(self):
        """
        CHECK "get_user_details" handles none values
        data check:
            user:
        """
        data_check = None
        getuser_mock = MagicMock(return_value=data_check)
        with unittest.mock.patch('getpass.getuser', getuser_mock):
                self.arm_info.get_user_details()

        self.assertEqual(self.arm_info.user, 'unknown')


    def test_get_user_details_pass(self):
        """
        CHECK "get_user_details" handles returning correct values
        data check:
            user: user1
        """
        data_check = "user1"
        getuser_mock = MagicMock(return_value=data_check)
        with unittest.mock.patch('getpass.getuser', getuser_mock):
                self.arm_info.get_user_details()

        self.assertEqual(self.arm_info.user, data_check)

if __name__ == '__main__':
    unittest.main()
