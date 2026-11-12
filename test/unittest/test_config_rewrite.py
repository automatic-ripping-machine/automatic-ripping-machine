"""
arm.yaml is loaded by every ARM process. It must not be rewritten on every
start, emptied by a failed rewrite, or get null settings back as "None".
"""
import json
import os
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, '/opt/arm')
from arm.config import config as cfg  # noqa: E402

COMMENTS = {"ARM_CFG_GROUPS": {"BEGIN": "# ARM config", "DIR_SETUP": "", "WEB_SERVER": "", "FILE_PERMS": "",
                               "MAKE_MKV": "", "HANDBRAKE": "", "EMBY": "", "EMBY_ADDITIONAL": "",
                               "NOTIFY_PERMS": "", "APPRISE": ""}}
TEMPLATE = {"RAW_PATH": "/home/arm/media/raw/", "MINLENGTH": 600, "SKIP_TRANSCODE": False,
            "CHOWN_USER": None, "FFMPEG_PRE_FILE_ARGS": None}


class ConfigFileTest(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "arm.yaml")
        self.comments = os.path.join(self.dir, "comments.json")
        with open(self.comments, "w") as comments_file:
            json.dump(COMMENTS, comments_file)

    def write_user_config(self, values):
        with open(self.path, "w") as user_file:
            yaml.safe_dump(values, user_file)
        with open(self.path) as user_file:
            return user_file.read()

    def update(self, user, comments_path=None):
        config = dict(TEMPLATE)
        config.update(user)
        written = cfg._update_config_file(self.path, user, TEMPLATE, config, comments_path or self.comments)
        return written, config

    def read(self):
        with open(self.path) as config_file:
            return config_file.read()


class TestWhenToRewrite(ConfigFileTest):

    def test_complete_config_is_left_alone(self):
        """CHECK a config with every template key isn't rewritten"""
        user = dict(TEMPLATE, MINLENGTH=900)
        before = self.write_user_config(user)
        written, _config = self.update(user)
        self.assertFalse(written)
        self.assertEqual(self.read(), before)

    def test_missing_key_is_added(self):
        """CHECK a config missing a template key is rewritten with it"""
        user = {"RAW_PATH": "/media/raw/", "MINLENGTH": 900}
        self.write_user_config(user)
        written, _config = self.update(user)
        self.assertTrue(written)
        saved = yaml.safe_load(self.read())
        self.assertEqual(saved["MINLENGTH"], 900)
        self.assertIn("SKIP_TRANSCODE", saved)

    def test_broken_comments_file_keeps_old_config(self):
        """CHECK a failed rewrite leaves the existing arm.yaml intact (it used to be emptied)"""
        user = {"RAW_PATH": "/media/raw/"}
        before = self.write_user_config(user)
        broken = os.path.join(self.dir, "broken.json")
        with open(broken, "w") as comments_file:
            json.dump({}, comments_file)  # no ARM_CFG_GROUPS -> KeyError while rendering
        written, _config = self.update(user, comments_path=broken)
        self.assertFalse(written)
        self.assertEqual(self.read(), before)


class TestNullValues(ConfigFileTest):

    def test_null_is_written_as_null(self):
        """CHECK null settings are written as null, not the string "None" """
        text = cfg._render_config(dict(TEMPLATE), COMMENTS)
        self.assertIn("CHOWN_USER: null", text)
        self.assertEqual(yaml.safe_load(text), TEMPLATE)

    def test_none_strings_from_old_versions_are_repaired(self):
        """CHECK "None" strings written by earlier versions become null again"""
        user = dict(TEMPLATE, CHOWN_USER="None", FFMPEG_PRE_FILE_ARGS="None")
        self.write_user_config(user)
        written, config = self.update(user)
        self.assertTrue(written)
        self.assertIsNone(config["CHOWN_USER"])
        self.assertIsNone(yaml.safe_load(self.read())["FFMPEG_PRE_FILE_ARGS"])

    def test_none_string_kept_where_template_has_a_value(self):
        """CHECK "None" is only repaired where the template default is null"""
        user = dict(TEMPLATE, RAW_PATH="None")
        self.write_user_config(user)
        _written, config = self.update(user)
        self.assertEqual(config["RAW_PATH"], "None")


class TestWriteConfigFile(ConfigFileTest):

    def test_replaces_content_and_keeps_mode(self):
        """CHECK the file is replaced, keeps its permissions, and no temp file is left"""
        self.write_user_config({"A": 1})
        os.chmod(self.path, 0o640)
        cfg.write_config_file(self.path, "B: 2\n")
        self.assertEqual(self.read(), "B: 2\n")
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o640)
        self.assertFalse([name for name in os.listdir(self.dir) if ".tmp-" in name])


if __name__ == '__main__':
    unittest.main()
