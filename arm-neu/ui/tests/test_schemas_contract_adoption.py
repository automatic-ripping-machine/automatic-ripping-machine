"""Coverage for the Job-family contract adoption (Phase C of the rollout).

The arm-ui Pydantic mirrors (`JobSchema`, `TrackSchema`, `TrackCountsSchema`,
`JobSummary`) now derive from `arm_contracts.*`. These tests pin the audit
gaps the adoption was meant to close, plus the legacy-stripping field
validator behavior on `JobSchema.transcode_overrides`.
"""
import json

from arm_contracts import Job as JobContract, JobSummary as JobSummaryContract, Track as TrackContract, TrackCounts
from backend.models.schemas import (
    JobDetailSchema,
    JobSchema,
    JobSummary,
    TrackCountsSchema,
    TrackSchema,
)


# --- Re-export sanity ---


def test_track_schema_is_contract():
    """TrackSchema is the shared contract, not a hand-rolled mirror."""
    assert TrackSchema is TrackContract


def test_track_counts_is_contract():
    assert TrackCountsSchema is TrackCounts


def test_job_summary_is_contract():
    assert JobSummary is JobSummaryContract


def test_job_schema_subclasses_contract():
    """JobSchema layers the legacy-stripping validator on top of the
    contract; it MUST inherit from the shared Job model so adding a
    field to the contract automatically flows to the BFF."""
    assert issubclass(JobSchema, JobContract)


# --- Audit-gap closures (fields previously stripped by the old JobSchema) ---


def test_job_schema_carries_audit_gap_fields():
    """These fields exist on the producer (arm-neu) and the contract, but
    the pre-Phase-C JobSchema silently dropped them. Lock them in."""
    j = JobSchema(
        job_id=1,
        guid="abc-123",
        is_iso=False,
        manual_start=True,
        manual_mode=False,
        pid_hash=42,
        updated=True,
        title_pattern_override="{title} ({year})",
        folder_pattern_override="{video_type}/{title}",
    )
    assert j.guid == "abc-123"
    assert j.is_iso is False
    assert j.manual_start is True
    assert j.manual_mode is False
    assert j.pid_hash == 42
    assert j.updated is True
    assert j.title_pattern_override == "{title} ({year})"
    assert j.folder_pattern_override == "{video_type}/{title}"


def test_track_schema_carries_custom_filename():
    """custom_filename was previously stripped by arm-ui's TrackSchema; it
    now flows through the contract."""
    t = TrackSchema(track_id=1, job_id=1, custom_filename="S01E01_pilot.mkv")
    assert t.custom_filename == "S01E01_pilot.mkv"


# --- transcode_overrides validator (arm-ui-only behavior on the contract) ---


def test_transcode_overrides_validator_strips_legacy_keys():
    """Pre-v15 ARM rows can carry legacy top-level keys; the validator
    drops them and keeps the valid subset."""
    j = JobSchema.model_validate({
        "job_id": 1,
        "transcode_overrides": {
            "preset_slug": "nvidia_balanced",
            "video_encoder": "x264",      # legacy
            "handbrake_preset": "Fast",   # legacy
        },
    })
    assert j.transcode_overrides == {"preset_slug": "nvidia_balanced"}


def test_transcode_overrides_validator_accepts_json_string():
    """arm-neu's DB column is a JSON string; the validator parses it."""
    j = JobSchema.model_validate({
        "job_id": 1,
        "transcode_overrides": json.dumps({"preset_slug": "software-balanced"}),
    })
    assert j.transcode_overrides == {"preset_slug": "software-balanced"}


def test_transcode_overrides_validator_returns_none_on_garbage_json():
    """Corrupt JSON drops to None instead of raising or propagating
    garbage to the frontend."""
    j = JobSchema.model_validate({
        "job_id": 1,
        "transcode_overrides": "{this is not json",
    })
    assert j.transcode_overrides is None


def test_transcode_overrides_validator_returns_none_on_failed_contract_validation():
    """Shape that doesn't match TranscodeJobConfig drops to None."""
    j = JobSchema.model_validate({
        "job_id": 1,
        "transcode_overrides": {"preset_slug": 12345},  # wrong type
    })
    assert j.transcode_overrides is None


def test_transcode_overrides_validator_passes_through_none():
    j = JobSchema.model_validate({"job_id": 1, "transcode_overrides": None})
    assert j.transcode_overrides is None


def test_transcode_overrides_validator_rejects_non_dict_non_string():
    """A list (or anything that isn't dict/str/None) drops to None."""
    j = JobSchema.model_validate({"job_id": 1, "transcode_overrides": [1, 2, 3]})
    assert j.transcode_overrides is None


# --- JobDetailSchema layering ---


def test_job_detail_schema_extends_job_with_tracks_and_config():
    # config is now typed (JobConfigSnapshot); the model accepts the
    # DOS-cased keys defined by JobConfigUpdateRequest. Unknown keys are
    # silently dropped (extra='ignore' on the model).
    d = JobDetailSchema(
        job_id=1,
        tracks=[TrackSchema(track_id=1, job_id=1)],
        config={"RIPMETHOD": "mkv", "MAINFEATURE": True},
    )
    assert d.job_id == 1
    assert len(d.tracks) == 1
    assert d.tracks[0].track_id == 1
    assert d.config is not None
    assert d.config.RIPMETHOD == "mkv"
    assert d.config.MAINFEATURE is True
