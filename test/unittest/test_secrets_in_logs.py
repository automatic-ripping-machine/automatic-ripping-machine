"""
Secrets must not reach logs: the ntfy password (printed to stdout, which the
Docker wrapper sends to syslog/the container log) and the MakeMKV key or
JSON_URL (printed in DEBUG job logs via Config.pretty_table()).
"""
import io
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, '/opt/arm')
from arm.models.config import Config  # noqa: E402
from arm.ripper import apprise_bulk  # noqa: E402

NTFY = {"NTFY_TOPIC": "arm", "NTFY_URL": "https://ntfy.example.org", "NTFY_USER": "chris",
        "NTFY_PASS": "s3cret-pass", "NTFY_PORT": ""}


class TestNtfyPassword(unittest.TestCase):

    def test_password_not_printed_or_logged(self):
        """CHECK the ntfy URL with the password isn't printed or logged, but is still used"""
        out = io.StringIO()
        with patch.object(apprise_bulk.apprise, "Apprise") as apprise_cls, redirect_stdout(out), \
                self.assertLogs(level="DEBUG") as logs:
            apprise_bulk.ntfy_notify(NTFY, "title", "body")
        self.assertNotIn("s3cret-pass", out.getvalue())
        self.assertFalse([line for line in logs.output if "s3cret-pass" in line])
        apprise_cls.return_value.add.assert_called_once_with("ntfys://chris:s3cret-pass@ntfy.example.org/arm")


class TestConfigHidesKeys(unittest.TestCase):

    def setUp(self):
        self.config = Config({"MAKEMKV_PERMA_KEY": "M-perma-secret", "JSON_URL": "https://hooks.example/abc-token",
                              "MINLENGTH": "600"}, job_id=1)

    def test_pretty_table_hides_makemkv_key_and_json_url(self):
        """CHECK the DEBUG job-log dump hides the MakeMKV key and JSON_URL"""
        table = self.config.pretty_table()
        self.assertNotIn("M-perma-secret", table)
        self.assertNotIn("abc-token", table)
        self.assertIn("600", table)

    def test_str_and_get_d_hide_them(self):
        """CHECK str() and get_d() don't expose them either"""
        self.assertNotIn("M-perma-secret", str(self.config))
        self.assertNotIn("MAKEMKV_PERMA_KEY", self.config.get_d())
        self.assertNotIn("JSON_URL", self.config.get_d())


if __name__ == '__main__':
    unittest.main()
