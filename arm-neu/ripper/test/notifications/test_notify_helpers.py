"""Unit tests for the shared ripper notification helpers.

These exercise the pure mapping/duration logic in isolation so every
branch is covered without spinning up the rip pipeline.
"""
import datetime
from types import SimpleNamespace

from arm_contracts.enums import Disctype

from arm.ripper._notify_helpers import job_disc_type, rip_duration_seconds


def test_rip_duration_zero_when_no_start_time():
    job = SimpleNamespace(start_time=None)
    assert rip_duration_seconds(job) == 0


def test_rip_duration_computes_elapsed_seconds():
    start = datetime.datetime.now(datetime.timezone.utc).replace(
        tzinfo=None) - datetime.timedelta(seconds=120)
    job = SimpleNamespace(start_time=start)
    secs = rip_duration_seconds(job)
    # Allow a small window for test execution time.
    assert 119 <= secs <= 125


def test_job_disc_type_maps_known_value():
    job = SimpleNamespace(disctype="bluray")
    assert job_disc_type(job) == Disctype.bluray


def test_job_disc_type_empty_is_unknown():
    job = SimpleNamespace(disctype="")
    assert job_disc_type(job) == Disctype.unknown


def test_job_disc_type_none_is_unknown():
    job = SimpleNamespace(disctype=None)
    assert job_disc_type(job) == Disctype.unknown


def test_job_disc_type_unrecognized_is_unknown():
    job = SimpleNamespace(disctype="laserdisc")
    assert job_disc_type(job) == Disctype.unknown
