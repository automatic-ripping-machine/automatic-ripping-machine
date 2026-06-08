import os
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

from sqlalchemy import create_engine, text

from arm.ripper.ARMInfo import ARMInfo

# Use the project root as install_path (same as test config INSTALLPATH)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestArmInfo(unittest.TestCase):

    def setUp(self):
        fd, self._db_file = tempfile.mkstemp(prefix='arm_test_legacy_', suffix='.db')
        os.close(fd)
        self.arm_info = ARMInfo(_PROJECT_ROOT, self._db_file)

    def tearDown(self):
        if os.path.exists(self._db_file):
            os.remove(self._db_file)

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
        arm_subprocess_mock.return_value = " master\ncommit "
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
        # Regex requires at least one intermediate line (with \n) between branch and commit
        arm_subprocess_mock.return_value = "* master\n \ncommit abc12de"
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
        arm_subprocess_mock.return_value = "* m\ncommit a"
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
        # Regex requires at least one intermediate line (with \n) between branch and commit
        arm_subprocess_mock.return_value = "* thequickbrownfoxjumpedoverthelazydog\n \ncommit a1b2c3d4e5f6g7h8i9j10"
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

        self.assertEqual(self.arm_info.python_version, data_check)

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

        self.assertEqual(self.arm_info.python_version, data_check)

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

        self.assertEqual(self.arm_info.python_version, data_check)

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

    """
    ************************************************************
    Test - get_db_head_version
    get_db_head_version_fail - check for bad value check
    get_db_head_version_pass - check for normal behaviour
    todo: fix these
    ************************************************************
    """
    def test_get_db_head_version_fail(self):
        """
        CHECK "get_db_head_version" handles none values
        data check:
            path: None
        """
        with unittest.mock.patch("os.path.join", return_value="/arm/opt"):
            self.arm_info.get_db_head_version()

            self.assertEqual(self.arm_info.head_version, "unknown")

    @patch('arm.ripper.ARMInfo.ScriptDirectory')
    def test_get_db_head_version_pass(self, mock_script_dir):
        """
        CHECK "get_db_head_version" handles returning correct values
        data check:
            db: mockhead123
        """
        mock_head_version = "mockhead123"
        with unittest.mock.patch("logging.info") as mock_logging:
            mock_script_dir.from_config.return_value.get_current_head.return_value = mock_head_version

            self.arm_info.get_db_head_version()

            self.assertEqual(self.arm_info.head_version, 'mockhead123')
            mock_logging.info.assert_not_called()

    """
    ************************************************************
    Test - get_db_version
    test_get_db_version_fail - check for bad value check
    test_get_db_version_pass - check for normal behaviour
    ************************************************************
    """
    def test_get_db_version_fail(self):
        """
        CHECK "get_db_version" handles a database that has no
        alembic_version table (e.g. a fresh/uninitialized DB).
        data check:
            db_version: "unknown"
        """
        # Empty in-memory engine: no alembic_version table, so the
        # SQLAlchemy code path should bail out and leave db_version
        # set to "unknown".
        empty_engine = create_engine("sqlite:///:memory:")
        with patch("arm.ripper.ARMInfo.cfg.get_db_uri", return_value="sqlite:///:memory:"), \
             patch("arm.ripper.ARMInfo.create_engine", return_value=empty_engine):
            self.arm_info.get_db_version()
            self.assertEqual(self.arm_info.db_version, "unknown")

    def test_get_db_version_pass(self):
        """
        CHECK "get_db_version" reads alembic_version via SQLAlchemy
        data check:
            db_version: "mock_version"
        """
        # Build a real in-memory sqlite engine pre-seeded with the
        # alembic_version row, then patch create_engine to hand it back.
        # Sharing the in-memory DB across connections is awkward, so we
        # short-circuit by returning the same engine instance.
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(36) PRIMARY KEY)"))
            conn.execute(text("INSERT INTO alembic_version VALUES ('mock_version')"))

        with patch("arm.ripper.ARMInfo.cfg.get_db_uri", return_value="sqlite:///:memory:"), \
             patch("arm.ripper.ARMInfo.create_engine", return_value=engine):
            self.arm_info.get_db_version()
            self.assertEqual(self.arm_info.db_version, "mock_version")

    """
    ************************************************************
    Test - get_values
    test_get_values_pass - check output is correct
    ************************************************************
    """
    def test_get_values_pass(self):
        """
        CHECK "get_values" handles printing output
        data check: (values as below)
        """
        # Set mock values for the variables
        self.arm_info.arm_version = 'mock_arm_version'
        self.arm_info.python_version = 'mock_python_version'
        self.arm_info.user = 'mock_user'
        self.arm_info.head_version = 'mock_head_version'
        self.arm_info.db_version = 'mock_db_version'

        with self.assertLogs(level='INFO') as cm:
            self.arm_info.get_values()

        # Assert that the log messages were written correctly
        self.assertIn(f"INFO:root:ARM version: {self.arm_info.arm_version}", cm.output)
        self.assertIn(f"INFO:root:Python version: {self.arm_info.python_version}", cm.output)
        self.assertIn(f"INFO:root:User is: {self.arm_info.user}", cm.output)
        self.assertIn(f"INFO:root:Alembic head is: {self.arm_info.head_version}", cm.output)
        self.assertIn(f"INFO:root:Database version is: {self.arm_info.db_version}", cm.output)


if __name__ == '__main__':
    unittest.main()
