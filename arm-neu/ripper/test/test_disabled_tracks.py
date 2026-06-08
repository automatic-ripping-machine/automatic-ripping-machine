"""Disabled tracks (track.enabled == False) must not be sent to the transcoder."""
from arm.database import db
from arm.models.track import Track


def _add_track(job, number, enabled):
    t = Track(job.job_id, number, 3600, '16:9', 24.0, False, 'makemkv',
              f'title{number}', f'title{number}.mkv')
    t.enabled = enabled
    t.ripped = True
    db.session.add(t)
    return t


class TestWebhookManifestHonorsEnabled:
    def test_disabled_track_excluded_from_manifest(self, app_context, sample_job):
        from arm.ripper.utils import _build_webhook_payload
        sample_job.multi_title = True
        _add_track(sample_job, '1', enabled=True)
        _add_track(sample_job, '2', enabled=False)
        _add_track(sample_job, '3', enabled=None)  # legacy NULL -> include
        db.session.commit()

        payload = _build_webhook_payload("done", "body", sample_job, "raw_dir")
        numbers = {t["track_number"] for t in (payload.get("tracks") or [])}
        assert numbers == {"1", "3"}, f"disabled track 2 must be excluded, got {numbers}"

    def test_all_disabled_falls_back_to_all_tracks(self, app_context, sample_job):
        from arm.ripper.utils import _build_webhook_payload
        sample_job.multi_title = True
        _add_track(sample_job, '1', enabled=False)
        _add_track(sample_job, '2', enabled=False)
        db.session.commit()

        payload = _build_webhook_payload("done", "body", sample_job, "raw_dir")
        numbers = {t["track_number"] for t in (payload.get("tracks") or [])}
        assert numbers == {"1", "2"}, "all-disabled must fall back to sending all tracks"


import unittest.mock


class TestProcessSingleTracksHonorsEnabled:
    def test_disabled_track_not_ripped(self, app_context, sample_job, tmp_path):
        from arm.ripper import makemkv
        from arm_contracts.enums import SkipReason

        keep = _add_track(sample_job, '1', enabled=True)
        drop = _add_track(sample_job, '2', enabled=False)
        keep.process = True
        keep.length = 3600
        drop.length = 3600
        sample_job.config.MKV_ARGS = ''  # fixture omits this; real config always has it
        db.session.commit()

        ripped_numbers = []

        def fake_run(cmd, _out):
            # cmd is [..., source, track_number, rawpath]; capture the title arg
            ripped_numbers.append(cmd[-2])
            return iter(())

        with unittest.mock.patch('arm.ripper.makemkv.run', side_effect=fake_run), \
             unittest.mock.patch('arm.ripper.makemkv.progress_log', return_value=str(tmp_path / 'p.log')):
            makemkv.process_single_tracks(sample_job, str(tmp_path), 'manual')

        assert '1' in ripped_numbers, "enabled track must be ripped"
        assert '2' not in ripped_numbers, "disabled track must NOT be ripped"
        db.session.refresh(drop)
        assert drop.process is False
        assert drop.skip_reason == SkipReason.user_disabled.value
