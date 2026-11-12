"""
Values set in the UI while a disc is being identified must survive the
automatic identification (only title_manual did before).
"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, '/opt/arm')
from arm.ripper import main as ripper_main  # noqa: E402
from arm.ripper import utils  # noqa: E402


def overwritten_job():
    """The user picked "It Chapter Two (2019)"; identification then overwrote year and type"""
    return SimpleNamespace(job_id=19, title="It Chapter Two", year="None", video_type="unknown",
                           imdb_id=None, poster_url=None, title_manual="It Chapter Two", updated=False,
                           hasnicetitle=True, config=SimpleNamespace(MANUAL_WAIT=True, MANUAL_WAIT_TIME=10))


def manual_row(title="It Chapter Two", year="2019", video_type="movie", imdb_id="tt7349950", poster_url="p.jpg"):
    return (title, year, video_type, imdb_id, poster_url)


def fake_database_updater(args, job, *_args, **_kwargs):
    for key, value in args.items():
        setattr(job, key, value)
    return True


class TestApplyManualOverrides(unittest.TestCase):

    def apply(self, job, row):
        query = MagicMock()
        query.return_value.filter.return_value.one_or_none.return_value = row
        with patch.object(utils.db.session, "query", query), \
                patch.object(utils, "database_updater", side_effect=fake_database_updater) as updater:
            changed = utils.apply_manual_overrides(job)
        return changed, updater

    def test_manual_year_and_type_are_restored(self):
        """CHECK year, type, IMDb id and poster set in the UI are re-applied"""
        job = overwritten_job()
        changed, _updater = self.apply(job, manual_row())
        self.assertTrue(changed)
        self.assertEqual((job.year, job.video_type, job.imdb_id, job.poster_url),
                         ("2019", "movie", "tt7349950", "p.jpg"))
        self.assertEqual(utils.fix_job_title(job), "It Chapter Two (2019)")
        self.assertEqual(utils.convert_job_type(job.video_type), "movies")

    def test_nothing_set_in_the_ui_changes_nothing(self):
        """CHECK automatic values stay when nothing was set manually"""
        job = overwritten_job()
        changed, updater = self.apply(job, (None, None, "", None, None))
        self.assertFalse(changed)
        updater.assert_not_called()
        self.assertEqual(job.year, "None")

    def test_none_string_is_not_applied(self):
        """CHECK a stringified None in a *_manual column is ignored"""
        job = overwritten_job()
        changed, _updater = self.apply(job, manual_row(year="None", video_type=None, imdb_id=None, poster_url=None))
        self.assertFalse(changed)

    def test_check_for_wait_reapplies_manual_values(self):
        """CHECK the manual-wait override also restores the manual year and type"""
        job = overwritten_job()
        query = MagicMock()
        query.return_value.filter.return_value.one_or_none.return_value = manual_row()
        with patch.object(utils.db.session, "query", query), \
                patch.object(utils.db.session, "refresh"), \
                patch.object(utils.time, "sleep"), \
                patch.object(utils, "database_updater", side_effect=fake_database_updater):
            utils.check_for_wait(job)
        self.assertEqual((job.year, job.video_type), ("2019", "movie"))


class TestMainAppliesOverrides(unittest.TestCase):

    def test_main_reapplies_after_identification(self):
        """CHECK main() re-applies UI values right after identification and the dupe check"""
        order = MagicMock()
        job = overwritten_job()
        job.disctype = "data"
        job.label = "IT_CHAPTER_TWO"
        with patch.object(ripper_main, "job", job), \
                patch.object(ripper_main.identify, "identify", order.identify), \
                patch.object(ripper_main.utils, "job_dupe_check", order.job_dupe_check), \
                patch.object(ripper_main.utils, "apply_manual_overrides", order.apply_manual_overrides), \
                patch.object(ripper_main.utils, "notify_entry"), \
                patch.object(ripper_main.utils, "check_for_wait"), \
                patch.object(ripper_main, "log_arm_params"), \
                patch.object(ripper_main, "check_fstab"), \
                patch.object(ripper_main.utils, "rip_data", return_value=True), \
                patch.object(ripper_main.utils, "notify"):
            ripper_main.main()
        # top-level calls only (main() also logs str() of the dupe check result)
        names = [call[0] for call in order.mock_calls if "." not in call[0]]
        self.assertEqual(names, ["identify", "job_dupe_check", "apply_manual_overrides"])
        order.apply_manual_overrides.assert_called_once_with(job)


if __name__ == '__main__':
    unittest.main()
