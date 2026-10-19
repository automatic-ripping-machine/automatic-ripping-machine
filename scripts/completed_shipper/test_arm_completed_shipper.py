#!/usr/bin/env python3
"""
End-to-end test for arm_completed_shipper.py.

Builds a fake COMPLETED_PATH and a temporary ARM sqlite database, points the
shipper at local destination folders and runs it through a small rsync wrapper
that records every call (and can be told to fail for a given folder).

Run with:  python3 -m unittest scripts/completed_shipper/test_arm_completed_shipper.py
Needs a real rsync on PATH.
"""

import os
import shutil
import sqlite3
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arm_completed_shipper as shipper  # noqa: E402

FAKE_RSYNC = """#!/bin/sh
# Test double: log the call, optionally fail, otherwise run the real rsync.
printf '%s\\n' "$*" >> "$SHIPPER_TEST_LOG"
if [ -n "$SHIPPER_TEST_FAIL_FOR" ]; then
    case "$*" in
        *"$SHIPPER_TEST_FAIL_FOR"*) echo "fake rsync: forced failure" >&2; exit 23 ;;
    esac
fi
exec "$SHIPPER_TEST_REAL_RSYNC" "$@"
"""


class ShipperEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="arm-shipper-test-")
        self.completed = os.path.join(self.tmp, "completed")
        self.dest = os.path.join(self.tmp, "media-box")
        for sub in ("movies", "tv", "unidentified"):
            os.makedirs(os.path.join(self.completed, sub))
        for sub in ("Movies", "TV", "staging"):
            os.makedirs(os.path.join(self.dest, sub))

        self.db = os.path.join(self.tmp, "arm.db")
        self._create_db()
        self.log = os.path.join(self.tmp, "rsync.log")
        self.fake_rsync = os.path.join(self.tmp, "rsync")
        with open(self.fake_rsync, "w") as handle:
            handle.write(FAKE_RSYNC)
        os.chmod(self.fake_rsync, os.stat(self.fake_rsync).st_mode | stat.S_IXUSR)
        real = shutil.which("rsync")
        self.assertIsNotNone(real, "rsync must be installed to run this test")
        os.environ["SHIPPER_TEST_LOG"] = self.log
        os.environ["SHIPPER_TEST_REAL_RSYNC"] = real
        os.environ.pop("SHIPPER_TEST_FAIL_FOR", None)

        self.conf = os.path.join(self.tmp, "shipper.conf")
        with open(self.conf, "w") as handle:
            handle.write(f"""[shipper]
db_path = {self.db}
completed_path = {self.completed}
remote_host =
remote_movies_path = {self.dest}/Movies
remote_tv_path = {self.dest}/TV
remote_unidentified_path = {self.dest}/staging
bwlimit_recognized = 0
bwlimit_unidentified = 500
rsync_path = {self.fake_rsync}
rsync_timeout = 30
lock_file = {self.tmp}/shipper.lock
post_ship_command = echo "$SHIPPER_TYPE $SHIPPER_FOLDER" >> {self.tmp}/hook.log
""")

        # Job folders and matching DB rows.
        self._job("movies", "Movie A (2001)", "success", files=["Movie A (2001).mkv", "extras/trailer.mkv"])
        self._job("movies", "Movie B (2002)", "active")           # still ripping: must stay
        self._job("movies", "Movie D (2004)", "fail")             # failed: must stay
        self._folder("movies", "Movie C (2003)")                  # no DB row at all: must stay
        self._job("movies", "Movie E (2005)", "success")
        self._job("movies", "Movie E (2005)", "ripping", make_folder=False)  # second job re-using the path
        self._job("tv", "Show A (2010)", "success", files=["S01E01.mkv", "S01E02.mkv"], trailing_slash=True)
        self._job("unidentified", "UNKNOWN_DISC", "success", files=["title_t00.mkv"])
        self._job("unidentified", "UNKNOWN_2", "success", files=["title_t00.mkv"])
        # A job living outside COMPLETED_PATH (e.g. music) must be ignored even though it is a success.
        self._row("success", os.path.join(self.tmp, "music", "Album"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------------ helpers
    def _create_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute("""CREATE TABLE job (
            job_id INTEGER PRIMARY KEY, status VARCHAR(32), path VARCHAR(256),
            video_type VARCHAR(20), title VARCHAR(256), stop_time DATETIME)""")
        conn.commit()
        conn.close()

    def _row(self, status, path):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO job (status, path, video_type, title) VALUES (?, ?, ?, ?)",
                     (status, path, "movie", os.path.basename(path)))
        conn.commit()
        conn.close()

    def _folder(self, sub, name, files=("main.mkv",)):
        folder = os.path.join(self.completed, sub, name)
        for rel in files:
            full = os.path.join(folder, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as handle:
                handle.write(f"content of {rel}\n")
        return folder

    def _job(self, sub, name, status, files=("main.mkv",), make_folder=True, trailing_slash=False):
        folder = os.path.join(self.completed, sub, name)
        if make_folder:
            self._folder(sub, name, files)
        self._row(status, folder + ("/" if trailing_slash else ""))
        return folder

    def _calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as handle:
            return [line.rstrip("\n") for line in handle if line.strip()]

    def _local(self, sub, name):
        return os.path.join(self.completed, sub, name)

    def _shipped(self, dest_sub, name):
        return os.path.join(self.dest, dest_sub, name)

    def _run(self, *extra):
        return shipper.main(["-c", self.conf, *extra])

    # ------------------------------------------------------------------ tests
    def test_ships_recognized_first_then_unidentified(self):
        rc = self._run()
        self.assertEqual(rc, 0)

        # Finished recognized rips arrived intact and the local copies are gone.
        movie_a = self._shipped("Movies", "Movie A (2001)")
        self.assertTrue(os.path.isfile(os.path.join(movie_a, "Movie A (2001).mkv")))
        self.assertTrue(os.path.isfile(os.path.join(movie_a, "extras", "trailer.mkv")))
        self.assertTrue(os.path.isfile(os.path.join(self._shipped("TV", "Show A (2010)"), "S01E02.mkv")))
        self.assertFalse(os.path.exists(self._local("movies", "Movie A (2001)")))
        self.assertFalse(os.path.exists(self._local("tv", "Show A (2010)")))

        # Unidentified rips went to staging, throttled.
        for name in ("UNKNOWN_DISC", "UNKNOWN_2"):
            self.assertTrue(os.path.isfile(os.path.join(self._shipped("staging", name), "title_t00.mkv")))
            self.assertFalse(os.path.exists(self._local("unidentified", name)))

        # Unfinished, failed, unknown and re-used-path folders stay put.
        for name in ("Movie B (2002)", "Movie C (2003)", "Movie D (2004)", "Movie E (2005)"):
            self.assertTrue(os.path.isdir(self._local("movies", name)), name)
            self.assertFalse(os.path.exists(self._shipped("Movies", name)), name)

        # The movies/ and tv/ root folders themselves survive.
        for sub in ("movies", "tv", "unidentified"):
            self.assertTrue(os.path.isdir(os.path.join(self.completed, sub)))

        calls = self._calls()
        self.assertEqual(len(calls), 4)
        kinds = ["/completed/movies/" in c and "movies" or "/completed/tv/" in c and "tv" or "unidentified"
                 for c in calls]
        self.assertEqual(kinds, ["movies", "tv", "unidentified", "unidentified"])
        for call in calls[:2]:
            self.assertNotIn("--bwlimit", call)
            self.assertIn("--remove-source-files", call)
        for call in calls[2:]:
            self.assertIn("--bwlimit=500", call)

        with open(os.path.join(self.tmp, "hook.log")) as handle:
            hooks = handle.read().splitlines()
        self.assertEqual(hooks[:2], ["movies Movie A (2001)", "tv Show A (2010)"])
        self.assertCountEqual(hooks[2:], ["unidentified UNKNOWN_DISC", "unidentified UNKNOWN_2"])

    def test_second_run_is_a_noop(self):
        self.assertEqual(self._run(), 0)
        os.remove(self.log)
        self.assertEqual(self._run(), 0)
        self.assertEqual(self._calls(), [])

    def test_recognized_failure_blocks_unidentified(self):
        os.environ["SHIPPER_TEST_FAIL_FOR"] = "Movie A (2001)"
        rc = self._run()
        self.assertEqual(rc, 1)
        # Failed folder is untouched locally, tv still shipped, unidentified never started.
        self.assertTrue(os.path.isfile(os.path.join(self._local("movies", "Movie A (2001)"), "Movie A (2001).mkv")))
        self.assertTrue(os.path.isfile(os.path.join(self._shipped("TV", "Show A (2010)"), "S01E01.mkv")))
        self.assertTrue(os.path.isdir(self._local("unidentified", "UNKNOWN_DISC")))
        self.assertFalse(any("unidentified" in c for c in self._calls()))

        # Once the problem clears, the next run finishes the job.
        os.environ.pop("SHIPPER_TEST_FAIL_FOR")
        self.assertEqual(self._run(), 0)
        self.assertFalse(os.path.exists(self._local("movies", "Movie A (2001)")))
        self.assertFalse(os.path.exists(self._local("unidentified", "UNKNOWN_DISC")))

    def test_unidentified_failure_does_not_block_the_rest(self):
        os.environ["SHIPPER_TEST_FAIL_FOR"] = "UNKNOWN_DISC"
        rc = self._run()
        self.assertEqual(rc, 1)
        self.assertTrue(os.path.isdir(self._local("unidentified", "UNKNOWN_DISC")))
        self.assertFalse(os.path.exists(self._local("unidentified", "UNKNOWN_2")))
        self.assertTrue(os.path.isfile(os.path.join(self._shipped("staging", "UNKNOWN_2"), "title_t00.mkv")))

    def test_interrupted_transfer_resumes_on_rerun(self):
        # Pretend an earlier run copied one episode and was killed before removing the source.
        partial = self._shipped("TV", "Show A (2010)")
        os.makedirs(partial)
        shutil.copy(os.path.join(self._local("tv", "Show A (2010)"), "S01E01.mkv"), partial)
        self.assertEqual(self._run(), 0)
        self.assertTrue(os.path.isfile(os.path.join(partial, "S01E01.mkv")))
        self.assertTrue(os.path.isfile(os.path.join(partial, "S01E02.mkv")))
        self.assertFalse(os.path.exists(self._local("tv", "Show A (2010)")))

    def test_dry_run_moves_nothing(self):
        rc = self._run("--dry-run")
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isdir(self._local("movies", "Movie A (2001)")))
        self.assertFalse(os.path.exists(self._shipped("Movies", "Movie A (2001)")))
        calls = self._calls()
        self.assertEqual(len(calls), 4)
        self.assertTrue(all("--dry-run" in c for c in calls))

    def test_lock_prevents_overlapping_runs(self):
        cfg = shipper.load_config(self.conf)
        held = shipper.acquire_lock(cfg["lock_file"])
        try:
            self.assertEqual(self._run(), 2)
            self.assertEqual(self._calls(), [])
        finally:
            held.close()

    def test_job_newly_finished_between_passes_is_picked_up(self):
        # Movie B finishes while the shipper is working: a later pass must ship it.
        self.assertEqual(self._run(), 0)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE job SET status = 'success' WHERE path LIKE '%Movie B%'")
        conn.commit()
        conn.close()
        self.assertEqual(self._run(), 0)
        self.assertTrue(os.path.isfile(os.path.join(self._shipped("Movies", "Movie B (2002)"), "main.mkv")))


class RsyncCommandShape(unittest.TestCase):
    def test_remote_destination_uses_ssh_and_quotes_path(self):
        cfg = dict(shipper.DEFAULTS, remote_host="arm@t620", remote_movies_path="/srv/plex/Movies",
                   remote_tv_path="/srv/plex/TV", remote_unidentified_path="/srv/staging",
                   bwlimit_unidentified="8000", ssh_options="-o BatchMode=yes -i /home/arm/.ssh/shipper",
                   rsync_extra_args="--chown=plex:plex")
        cmd = shipper.build_rsync_command(cfg, "unidentified", "/home/arm/media/completed/unidentified/DISC X")
        self.assertEqual(cmd[0], "rsync")
        self.assertIn("--bwlimit=8000", cmd)
        self.assertIn("--remove-source-files", cmd)
        self.assertIn("--partial", cmd)
        self.assertIn("--chown=plex:plex", cmd)
        self.assertEqual(cmd[cmd.index("-e") + 1], "ssh -o BatchMode=yes -i /home/arm/.ssh/shipper")
        self.assertEqual(cmd[-2], "/home/arm/media/completed/unidentified/DISC X/")
        self.assertEqual(cmd[-1], "arm@t620:'/srv/staging/DISC X'/")

    def test_recognized_without_bwlimit(self):
        cfg = dict(shipper.DEFAULTS, remote_movies_path="/m", remote_tv_path="/t", remote_unidentified_path="/u",
                   bwlimit_unidentified="8000")
        cmd = shipper.build_rsync_command(cfg, "movies", "/c/movies/Film (1999)")
        self.assertFalse(any(part.startswith("--bwlimit") for part in cmd))
        self.assertNotIn("-e", cmd)
        self.assertEqual(cmd[-1], "/m/Film (1999)/")

    def test_missing_destination_is_a_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            conf = os.path.join(tmp, "c.conf")
            with open(conf, "w") as handle:
                handle.write("[shipper]\nremote_movies_path = /m\n")
            with self.assertRaises(shipper.ShipperError):
                shipper.load_config(conf)


if __name__ == "__main__":
    unittest.main()
