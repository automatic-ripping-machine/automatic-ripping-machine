import os
import unittest
import tempfile
import unittest.mock

from arm.ripper import apprise_bulk


class TestAppriseBulk(unittest.TestCase):
    def test_get_apprise_config_path_when_missing(self):
        with unittest.mock.patch.object(apprise_bulk, "cfg") as mock_config:
            # Notably absent is the "APPRISE" key
            mock_config.arm_config = {}
            self.assertIsNone(apprise_bulk.get_apprise_config_path())

    def test_get_apprise_config_path(self):
        expected = "/not/a/real/path"
        with unittest.mock.patch.object(apprise_bulk, "cfg") as mock_config:
            mock_config.arm_config = {
                "APPRISE": expected
            }
            self.assertEqual(apprise_bulk.get_apprise_config_path(), expected)

    def test_load_config_when_missing(self):
        with unittest.mock.patch.object(apprise_bulk, "get_apprise_config_path", return_value=None):
            self.assertIsNone(apprise_bulk.load_config())

    def test_config_malformed(self):
        self.assertFalse(apprise_bulk.test_config("not-a-real-configuration"))

    def test_config(self):
        self.assertTrue(apprise_bulk.test_config("hassio://host/my-awesome-token"))

    def test_save_config_no_path(self):
        with unittest.mock.patch.object(apprise_bulk, "get_apprise_config_path", return_value=None):
            self.assertFalse(apprise_bulk.save_config("hassio://host/my-awesome-token"))

    def test_save_config_malformed(self):
        self.assertFalse(apprise_bulk.save_config("not-a-real-configuration"))

    def test_save_config(self):
        expected = "hassio://host/my-awesome-token"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "apprise.yaml")
            with unittest.mock.patch.object(apprise_bulk, "get_apprise_config_path", return_value=path):
                apprise_bulk.save_config(expected)
                actual = apprise_bulk.load_config()
                self.assertEqual(actual, expected)

    def test_notify_no_config(self):
        with unittest.mock.patch.object(apprise_bulk, "get_apprise_config_path", return_value=None):
            self.assertFalse(apprise_bulk.notify("title", "body"))

    def test_notify_malformed_config(self):
        with unittest.mock.patch.object(apprise_bulk, "load_config", return_value="not-a-real-config"):
            self.assertFalse(apprise_bulk.notify("title", "body"))

    def test_notify(self):
        config = "hassio://host/my-awesome-token"
        with unittest.mock.patch.object(apprise_bulk, "load_config", return_value=config):
            self.assertTrue(apprise_bulk.notify("title", "body"))


if __name__ == '__main__':
    unittest.main()
