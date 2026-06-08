"""Tests for arm.ripper.arm_ripper._post_rip_handoff.

Covers the four post-rip outcomes:
  A. SKIP_TRANSCODE=true + transcoder configured -> SUCCESS + finalize_output
  B. SKIP_TRANSCODE=false + transcoder configured -> TRANSCODE_WAITING + webhook
  C. No transcoder configured -> SUCCESS + finalize_output
  D. transcoder_notify returns False -> FAILURE

Also covers NOTIFY_RIP gating: 'rip complete' notification fires only
on non-failure outcomes.

These tests exercise the helper directly without patching it in isolation,
catching the dual-writer bug in arm/ripper/main.py.
"""
from unittest.mock import MagicMock, patch

import pytest

from arm.ripper.arm_ripper import _post_rip_handoff
from arm.models.job import JobState


@pytest.fixture
def mock_job():
    """Return a minimal Job double."""
    job = MagicMock()
    job.job_id = 1
    job.title = "Test Movie"
    job.disctype = "bluray"
    job.imdb_id = None
    job.errors = None
    job.start_time = None
    job.path = ""
    job.config = MagicMock()
    job.config.SKIP_TRANSCODE = None  # caller sets per-test
    job.config.NOTIFY_RIP = False
    job.status = JobState.VIDEO_RIPPING.value
    job.tracks.count.return_value = 1
    return job


@patch("arm.ripper.arm_ripper.publish_event")
@patch("arm.ripper.arm_ripper.utils.transcoder_notify")
@patch("arm.ripper.naming.finalize_output")
@patch("arm.ripper.arm_ripper.db")
@patch("arm.config.config.arm_config", {"TRANSCODER_URL": "https://transcoder", "SKIP_TRANSCODE": False})
def test_skip_true_with_transcoder_configured_sets_success(
    mock_db, mock_finalize, mock_notify, mock_publish, mock_job,
):
    """Outcome A: SKIP_TRANSCODE=true wins over transcoder being configured."""
    mock_job.config.SKIP_TRANSCODE = True

    _post_rip_handoff(mock_job)

    mock_finalize.assert_called_once_with(mock_job)
    assert mock_job.status == JobState.SUCCESS.value
    mock_notify.assert_not_called()  # no webhook when skipping


@patch("arm.ripper.arm_ripper.publish_event")
@patch("arm.ripper.arm_ripper.utils.transcoder_notify")
@patch("arm.ripper.naming.finalize_output")
@patch("arm.ripper.arm_ripper.db")
@patch("arm.config.config.arm_config", {"TRANSCODER_URL": "https://transcoder", "SKIP_TRANSCODE": False})
def test_skip_false_with_transcoder_configured_sets_waiting(
    mock_db, mock_finalize, mock_notify, mock_publish, mock_job,
):
    """Outcome B: webhook fires AND status is TRANSCODE_WAITING.

    This is the test that fails today - the current implementation
    only fires the webhook but does not write TRANSCODE_WAITING.
    """
    mock_job.config.SKIP_TRANSCODE = False
    mock_notify.return_value = True

    _post_rip_handoff(mock_job)

    mock_finalize.assert_not_called()
    mock_notify.assert_called_once()  # webhook fired
    assert mock_job.status == JobState.TRANSCODE_WAITING.value


@patch("arm.ripper.arm_ripper.publish_event")
@patch("arm.ripper.arm_ripper.utils.transcoder_notify")
@patch("arm.ripper.naming.finalize_output")
@patch("arm.ripper.arm_ripper.db")
@patch("arm.config.config.arm_config", {"TRANSCODER_URL": "", "SKIP_TRANSCODE": False})
def test_no_transcoder_configured_sets_success(
    mock_db, mock_finalize, mock_notify, mock_publish, mock_job,
):
    """Outcome C: empty TRANSCODER_URL -> finalize locally, SUCCESS."""
    mock_job.config.SKIP_TRANSCODE = False

    _post_rip_handoff(mock_job)

    mock_finalize.assert_called_once_with(mock_job)
    assert mock_job.status == JobState.SUCCESS.value
    mock_notify.assert_not_called()


@patch("arm.ripper.arm_ripper.publish_event")
@patch("arm.ripper.arm_ripper.utils.transcoder_notify")
@patch("arm.ripper.naming.finalize_output")
@patch("arm.ripper.arm_ripper.db")
@patch("arm.config.config.arm_config", {"TRANSCODER_URL": "https://transcoder", "SKIP_TRANSCODE": False})
def test_transcoder_notify_returns_false_sets_failure(
    mock_db, mock_finalize, mock_notify, mock_publish, mock_job,
):
    """Outcome D: transcoder_notify returns False -> job marked FAILURE.

    transcoder_notify swallows its own transport exceptions and returns
    False on failure; the caller branches on the return value.
    """
    mock_job.config.SKIP_TRANSCODE = False
    mock_notify.return_value = False

    _post_rip_handoff(mock_job)

    assert mock_job.status == JobState.FAILURE.value
    assert "Transcoder handoff failed" in (mock_job.errors or "")
    mock_finalize.assert_not_called()


@patch("arm.ripper.arm_ripper.publish_event")
@patch("arm.ripper.arm_ripper.utils.transcoder_notify")
@patch("arm.ripper.naming.finalize_output")
@patch("arm.ripper.arm_ripper.db")
@patch("arm.config.config.arm_config", {"TRANSCODER_URL": "https://transcoder", "SKIP_TRANSCODE": False})
def test_rip_complete_not_published_on_handoff_failure(
    mock_db, mock_finalize, mock_transcoder_notify, mock_publish, mock_job,
):
    """job.rip_complete must not publish when the handoff failed —
    a job.failed event is what subscribers should see for that path."""
    from arm_contracts import JobRipCompleteEvent, JobFailedEvent
    mock_job.config.SKIP_TRANSCODE = False
    mock_job.config.NOTIFY_RIP = True
    mock_transcoder_notify.return_value = False

    _post_rip_handoff(mock_job)

    assert mock_job.status == JobState.FAILURE.value
    published_types = [type(c[0][0]) for c in mock_publish.call_args_list]
    assert JobRipCompleteEvent not in published_types
    assert JobFailedEvent in published_types


@patch("arm.ripper.arm_ripper.publish_event")
@patch("arm.ripper.arm_ripper.utils.transcoder_notify")
@patch("arm.ripper.naming.finalize_output")
@patch("arm.ripper.arm_ripper.db")
@patch("arm.config.config.arm_config", {"TRANSCODER_URL": "https://transcoder", "SKIP_TRANSCODE": False})
def test_rip_complete_published_on_successful_handoff(
    mock_db, mock_finalize, mock_transcoder_notify, mock_publish, mock_job,
):
    """job.rip_complete fires on a successful handoff
    (TRANSCODE_WAITING) — channels filter on subscribed_events; the
    legacy NOTIFY_RIP per-job guard is gone."""
    from arm_contracts import JobRipCompleteEvent
    mock_job.config.SKIP_TRANSCODE = False
    mock_job.config.NOTIFY_RIP = True
    mock_transcoder_notify.return_value = True

    _post_rip_handoff(mock_job)

    assert mock_job.status == JobState.TRANSCODE_WAITING.value
    published_types = [type(c[0][0]) for c in mock_publish.call_args_list]
    assert JobRipCompleteEvent in published_types


@patch("arm.ripper.arm_ripper.publish_event")
@patch("arm.ripper.arm_ripper.utils.transcoder_notify")
@patch("arm.ripper.naming.finalize_output")
@patch("arm.ripper.arm_ripper.db")
@patch("arm.config.config.arm_config", {"TRANSCODER_URL": "https://transcoder", "SKIP_TRANSCODE": True})
def test_global_skip_used_when_per_job_is_none(
    mock_db, mock_finalize, mock_notify, mock_publish, mock_job,
):
    """Fallback: per-job config.SKIP_TRANSCODE=None -> global wins."""
    mock_job.config.SKIP_TRANSCODE = None

    _post_rip_handoff(mock_job)

    mock_finalize.assert_called_once_with(mock_job)
    assert mock_job.status == JobState.SUCCESS.value
