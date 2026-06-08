"""Frozen-fixture regression test for transcoder response shapes.

These tests catch upstream transcoder API drift before deploy. When
the transcoder's actual API changes, the fixture under
tests/fixtures/transcoder/ is updated by hand - that update is the
deliberate signal that a contract change happened.

Pattern matches tests/services/test_arm_client_contract_roundtrip.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.models.transcoder import (
    TranscoderJobListResponse,
    TranscoderStatsResponse,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "transcoder"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_job_list_shape_matches_contract():
    payload = _load("job_list.json")
    parsed = TranscoderJobListResponse(**payload)
    assert parsed.total == 1
    assert len(parsed.jobs) == 1
    job = parsed.jobs[0]
    assert job.id == 1
    assert job.status == "processing"
    assert job.progress == pytest.approx(42.5)


def test_stats_shape_matches_contract():
    payload = _load("stats.json")
    parsed = TranscoderStatsResponse(**payload)
    assert parsed.online is True
    assert parsed.stats is not None
    assert parsed.stats.processing == 1
    assert parsed.stats.worker_running is True
