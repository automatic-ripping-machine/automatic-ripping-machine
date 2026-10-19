"""
Tests for the MakeMKV duplicate-title filter in arm.ripper.makemkv.

Importing ``arm.ripper.makemkv`` pulls in the whole of ARM (config, Flask app, database), so a
throwaway arm.yaml is written first and pointed at with ARM_CONFIG_FILE. Needs the Linux
dependencies ARM itself needs (libdiscid, pyudev); skipped when they are missing.
"""
import importlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]

_TMP = tempfile.mkdtemp(prefix="arm_makemkv_test_")
_CONFIG = os.path.join(_TMP, "arm.yaml")
with open(_CONFIG, "w") as _handle:
    _handle.write(f"INSTALLPATH: \"{REPO_ROOT}\"\n"
                  f"DBFILE: \"{_TMP}/arm.db\"\n"
                  f"LOGPATH: \"{_TMP}/logs/\"\n"
                  f"ABCDE_CONFIG_FILE: \"{REPO_ROOT}/setup/.abcde.conf\"\n"
                  f"RAW_PATH: \"{_TMP}/raw/\"\nTRANSCODE_PATH: \"{_TMP}/transcode/\"\n"
                  f"COMPLETED_PATH: \"{_TMP}/completed/\"\n"
                  f"DISC_PHOTO_PATH: \"{_TMP}/photos/\"\n"
                  "DISABLE_LOGIN: true\n")
os.environ["ARM_CONFIG_FILE"] = _CONFIG

try:
    makemkv = importlib.import_module("arm.ripper.makemkv")
    IMPORT_ERROR = None
except Exception as error:  # pragma: no cover - depends on the host
    makemkv = None
    IMPORT_ERROR = error


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


def _track(number, length, filesize, chapters, segment_map="", source_file=""):
    """A stand-in for arm.models.track.Track with the fields the filter looks at."""
    return SimpleNamespace(track_number=str(number), length=length, filesize=filesize, chapters=chapters,
                           segment_map=segment_map, source_file=source_file, filename=f"title_t{number:02d}.mkv",
                           process=False, duplicate_of=None)


class _Tracks(list):
    """Stands in for the job.tracks relationship: iterable and has .all()."""

    def all(self):
        return list(self)


def _job(tracks, **config):
    settings = dict(MAINFEATURE=False, MAXLENGTH="99999", MINLENGTH="600", MKV_ARGS="",
                    SKIP_DUPLICATE_TITLES=True, LOGPATH=_TMP)
    settings.update(config)
    return SimpleNamespace(job_id=1, devpath="/dev/sr0", no_of_titles=len(tracks), status="",
                           drive=SimpleNamespace(mdisc=0), config=SimpleNamespace(**settings),
                           tracks=_Tracks(tracks))


@unittest.skipIf(IMPORT_ERROR is not None, f"ARM could not be imported here: {IMPORT_ERROR}")
class TestTinfoParsing(unittest.TestCase):
    """The new TINFO ids reach put_track."""

    def test_track_ids_match_apdefs(self):
        # AP_ItemAttributeId in MakeMKV's apdefs.h
        self.assertEqual(makemkv.TrackID.SOURCE_FILENAME, 16)
        self.assertEqual(makemkv.TrackID.SEGMENTS_MAP, 26)

    def test_parse_line_segment_map_keeps_commas(self):
        msg_type, info = makemkv.parse_line('TINFO:1,26,0,"155,156,157"')
        self.assertEqual(msg_type, makemkv.OutputType.TINFO)
        self.assertEqual((info.tid, info.id, info.value), (1, 26, "155,156,157"))

    def test_processor_passes_source_file_and_segment_map_to_put_track(self):
        lines = [
            'TINFO:0,8,0,"20"', 'TINFO:0,9,0,"1:55:03"', 'TINFO:0,11,0,"75000000000"',
            'TINFO:0,16,0,"00800.mpls"', 'TINFO:0,26,0,"1,2,3"', 'TINFO:0,27,0,"Film_t00.mkv"',
            'TINFO:1,8,0,"1"', 'TINFO:1,9,0,"1:55:03"', 'TINFO:1,11,0,"75000000000"',
            'TINFO:1,16,0,"00801.mpls"', 'TINFO:1,26,0,"1,2,3"', 'TINFO:1,27,0,"Film_t01.mkv"',
        ]
        messages = [makemkv.parse_line(line)[1] for line in lines]
        job = SimpleNamespace(job_id=1)
        processor = makemkv.TrackInfoProcessor(job, 0)
        with mock.patch.object(makemkv.utils, "put_track") as put_track:
            for message in messages:
                processor._process_message(message)
            processor._add_track()
        self.assertEqual(put_track.call_count, 2)
        first, second = [call.args for call in put_track.call_args_list]
        # (job, track_id, seconds, aspect, fps, mainfeature, source, filename, chapters, filesize, source, segments)
        self.assertEqual(first[1:3], (0, 6903))
        self.assertEqual(first[7:], ("Film_t00.mkv", 20, 75000000000, "00800.mpls", "1,2,3"))
        self.assertEqual(second[1], 1)
        self.assertEqual(second[7:], ("Film_t01.mkv", 1, 75000000000, "00801.mpls", "1,2,3"))
        # state is reset between titles
        self.assertEqual((processor.source_file, processor.segment_map), ("", ""))


@unittest.skipIf(IMPORT_ERROR is not None, f"ARM could not be imported here: {IMPORT_ERROR}")
class TestFindDuplicateTitles(unittest.TestCase):

    def test_same_segment_map_keeps_most_chapters(self):
        main = _track(0, 6903, 75_000_000_000, 20, "1,2,3", "00800.mpls")
        copy = _track(1, 6903, 75_000_000_000, 1, "1,2,3", "00801.mpls")
        extra = _track(2, 1500, 3_000_000_000, 4, "7", "00810.mpls")
        groups = makemkv.find_duplicate_titles([copy, main, extra])
        self.assertEqual([(kept.track_number, [t.track_number for t in dupes]) for kept, dupes in groups],
                         [("0", ["1"])])

    def test_zero_chapter_copy_listed_first_is_still_the_one_dropped(self):
        copy = _track(0, 6903, 75_000_000_000, 0, "1,2,3")
        main = _track(1, 6903, 74_500_000_000, 20, "1,2,3")
        groups = makemkv.find_duplicate_titles([copy, main])
        self.assertEqual(groups[0][0], main)
        self.assertEqual(groups[0][1], [copy])

    def test_different_segment_maps_are_not_duplicates_even_if_size_and_length_match(self):
        episode_1 = _track(0, 1420, 4_000_000_000, 5, "10,11")
        episode_2 = _track(1, 1420, 4_000_000_000, 5, "12,13")
        self.assertEqual(makemkv.find_duplicate_titles([episode_1, episode_2]), [])

    def test_fallback_on_duration_and_size_without_segment_maps(self):
        main = _track(0, 6903, 75_000_000_000, 20)
        copy = _track(1, 6905, 76_000_000_000, 0)     # +2 s, +1.3 %
        too_long = _track(2, 6906, 75_000_000_000, 0)  # +3 s
        too_big = _track(3, 6903, 77_000_000_000, 0)   # +2.7 %
        groups = makemkv.find_duplicate_titles([main, copy, too_long, too_big])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0][0], main)
        self.assertEqual(groups[0][1], [copy])

    def test_fallback_without_size_information_is_not_a_duplicate(self):
        # same duration, no size and no segment map: not enough to tell copies from episodes
        main = _track(0, 6903, 0, 20)
        copy = _track(1, 6903, 0, 0)
        self.assertEqual(makemkv.find_duplicate_titles([main, copy]), [])
        # an identical segment map is enough on its own
        main = _track(0, 6903, 0, 20, "1,2,3")
        copy = _track(1, 6903, 0, 0, "1,2,3")
        self.assertEqual(makemkv.find_duplicate_titles([main, copy]), [(main, [copy])])

    def test_segment_map_on_one_side_only_falls_back_to_duration_and_size(self):
        main = _track(0, 6903, 75_000_000_000, 20, "1,2,3")
        copy = _track(1, 6903, 75_000_000_000, 0, "")
        self.assertEqual(makemkv.find_duplicate_titles([main, copy])[0][1], [copy])

    def test_tie_breaks_larger_filesize_then_lower_track_number(self):
        small = _track(0, 6903, 75_000_000_000, 20, "1,2,3")
        big = _track(1, 6903, 75_900_000_000, 20, "1,2,3")
        groups = makemkv.find_duplicate_titles([small, big])
        self.assertEqual(groups[0][0], big)
        same_a = _track(5, 6903, 75_000_000_000, 20, "1,2,3")
        same_b = _track(12, 6903, 75_000_000_000, 20, "1,2,3")
        groups = makemkv.find_duplicate_titles([same_b, same_a])
        self.assertEqual(groups[0][0], same_a)
        self.assertEqual(groups[0][1], [same_b])

    def test_three_copies_collapse_to_one(self):
        main = _track(0, 6903, 75_000_000_000, 20, "1,2,3")
        copies = [_track(n, 6903, 75_000_000_000, 0, "1,2,3") for n in (1, 2)]
        groups = makemkv.find_duplicate_titles([main] + copies)
        self.assertEqual(groups, [(main, copies)])

    def test_nothing_to_do(self):
        self.assertEqual(makemkv.find_duplicate_titles([]), [])
        self.assertEqual(makemkv.find_duplicate_titles([_track(0, 6903, 1, 20, "1")]), [])


@unittest.skipIf(IMPORT_ERROR is not None, f"ARM could not be imported here: {IMPORT_ERROR}")
class TestSkipDuplicateTitles(unittest.TestCase):

    def test_marks_duplicates_and_commits(self):
        main = _track(0, 6903, 75_000_000_000, 20, "1,2,3", "00800.mpls")
        copy = _track(1, 6903, 75_000_000_000, 0, "1,2,3", "00801.mpls")
        extra = _track(2, 1500, 3_000_000_000, 4, "7")
        main.process = copy.process = True
        job = _job([main, copy, extra])
        with mock.patch.object(makemkv.db.session, "commit") as commit, \
                self.assertLogs(level="INFO") as logs:
            skipped = makemkv.skip_duplicate_titles(job)
        self.assertEqual(skipped, [copy])
        self.assertEqual(copy.duplicate_of, "0")
        self.assertFalse(copy.process)
        self.assertTrue(main.process)
        self.assertIsNone(main.duplicate_of)
        self.assertIsNone(extra.duplicate_of)
        commit.assert_called_once()
        self.assertTrue(any("Title 1" in line and "copy of title 0" in line and "same segment map" in line
                            for line in logs.output), logs.output)

    def test_no_duplicates_no_commit(self):
        job = _job([_track(0, 6903, 1, 20, "1"), _track(1, 1500, 1, 2, "2")])
        with mock.patch.object(makemkv.db.session, "commit") as commit:
            self.assertEqual(makemkv.skip_duplicate_titles(job), [])
        commit.assert_not_called()


@unittest.skipIf(IMPORT_ERROR is not None, f"ARM could not be imported here: {IMPORT_ERROR}")
class TestMakemkvMkvRouting(unittest.TestCase):
    """The single "all" command is only used when no title was dropped."""

    def setUp(self):
        self.main = _track(0, 6903, 75_000_000_000, 20, "1,2,3")
        self.copy = _track(1, 6903, 75_000_000_000, 0, "1,2,3")
        self.extra = _track(2, 1500, 3_000_000_000, 4, "7")
        patches = [
            mock.patch.object(makemkv.utils, "get_drive_mode", return_value="auto"),
            mock.patch.object(makemkv, "get_track_info"),
            mock.patch.object(makemkv, "run", return_value=iter(())),
            mock.patch.object(makemkv, "progress_log", return_value="/tmp/progress.log"),
            mock.patch.object(makemkv.db.session, "commit"),
        ]
        self.mocks = [patch.start() for patch in patches]
        for patch in patches:
            self.addCleanup(patch.stop)
        self.run_mock = self.mocks[2]

    def _ripped_title_args(self):
        """The title argument of every makemkvcon mkv command that was run."""
        return [call.args[0][call.args[0].index("mkv") + 1:] for call in self.run_mock.call_args_list]

    def test_duplicate_dropped_rips_remaining_titles_one_by_one(self):
        job = _job([self.main, self.copy, self.extra])
        with mock.patch("builtins.open", mock.mock_open()):
            makemkv.makemkv_mkv(job, "/raw")
        commands = [call.args[0] for call in self.run_mock.call_args_list]
        self.assertEqual(len(commands), 2, commands)
        self.assertNotIn("all", [arg for cmd in commands for arg in cmd])
        self.assertEqual([cmd[cmd.index("dev:/dev/sr0") + 1] for cmd in commands], ["0", "2"])
        self.assertEqual(self.copy.duplicate_of, "0")
        self.assertFalse(self.copy.process)
        self.assertTrue(self.main.process)
        self.assertTrue(self.extra.process)

    def test_no_duplicates_uses_all(self):
        job = _job([self.main, self.extra])
        makemkv.makemkv_mkv(job, "/raw")
        commands = [call.args[0] for call in self.run_mock.call_args_list]
        self.assertEqual(len(commands), 1)
        self.assertIn("all", commands[0])

    def test_disabled_uses_all_and_rips_both_copies(self):
        job = _job([self.main, self.copy], SKIP_DUPLICATE_TITLES=False)
        makemkv.makemkv_mkv(job, "/raw")
        commands = [call.args[0] for call in self.run_mock.call_args_list]
        self.assertEqual(len(commands), 1)
        self.assertIn("all", commands[0])
        self.assertIsNone(self.copy.duplicate_of)

    def test_maxlength_path_still_skips_duplicates(self):
        job = _job([self.main, self.copy, self.extra], MAXLENGTH="7000")
        with mock.patch("builtins.open", mock.mock_open()):
            makemkv.makemkv_mkv(job, "/raw")
        commands = [call.args[0] for call in self.run_mock.call_args_list]
        self.assertEqual([cmd[cmd.index("dev:/dev/sr0") + 1] for cmd in commands], ["0", "2"])


if __name__ == '__main__':
    unittest.main()
