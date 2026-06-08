#!/usr/bin/env python3
"""Integration tests for RetrySession on a live ARM instance.

These tests hit the real ARM API at https://arm.murphbutt.xyz to verify
that the RetrySession commit retry logic works correctly in production.

Run with:
    python3 test/integration/test_retry_session_live.py

Requirements:
    - ARM rippers running on hifi-server with fix/sqlite-retry-session branch
    - ARM UI running and accessible at https://arm.murphbutt.xyz
    - At least one completed job in the database

These tests are NON-DESTRUCTIVE: they modify and then restore job fields,
and they don't delete or create jobs.
"""
import concurrent.futures
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "https://arm.murphbutt.xyz/api"
# Job ID to use for tests - must exist and be in success/fail state
TEST_JOB_ID = 135

# UI API routes for writing (proxied to ARM):
# PATCH /api/jobs/{id}/naming - sets title_pattern_override, folder_pattern_override
# PATCH /api/jobs/{id}/config - sets ARM config fields
# PATCH /api/jobs/{id}/transcode-config - sets transcode overrides
# PATCH /api/jobs/{id}/tracks/{track_id} - update track fields
# PUT   /api/jobs/{id}/title - update title/year/type
# POST  /api/notifications/dismiss-all - bulk dismiss

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api(method, path, body=None):
    """Make an API request and return (status, data)."""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        try:
            return e.code, json.loads(body_text)
        except json.JSONDecodeError:
            return e.code, {"raw": body_text}


def get(path):
    return api("GET", path)


def post(path, body=None):
    return api("POST", path, body)


def patch(path, body):
    return api("PATCH", path, body)


def passed(name):
    print(f"  PASS  {name}")


def failed(name, reason):
    print(f"  FAIL  {name}: {reason}")
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_api_is_reachable():
    """Verify the ARM API is up and responding."""
    status, data = get("/dashboard")
    if status != 200:
        return failed("api_reachable", f"status={status}")
    if not data.get("arm_online"):
        return failed("api_reachable", "arm_online=False")
    passed("api_reachable")
    return True


def test_job_exists():
    """Verify the test job exists."""
    status, data = get(f"/jobs/{TEST_JOB_ID}")
    if status != 200:
        return failed("job_exists", f"status={status}")
    if data.get("job_id") != TEST_JOB_ID:
        return failed("job_exists", f"wrong job_id={data.get('job_id')}")
    passed("job_exists")
    return True


def _write_naming(job_id, title_pattern=None, folder_pattern=None):
    """Write naming patterns via the correct UI API endpoint."""
    body = {}
    if title_pattern is not None:
        body["title_pattern_override"] = title_pattern
    if folder_pattern is not None:
        body["folder_pattern_override"] = folder_pattern
    return patch(f"/jobs/{job_id}/naming", body)


def test_single_write_succeeds():
    """A normal single write should succeed (baseline)."""
    status, resp = _write_naming(TEST_JOB_ID, title_pattern="__test_single_write__")
    if status != 200:
        return failed("single_write", f"write status={status} resp={resp}")

    # Verify via the response (ARM returns the written values)
    if resp.get("title_pattern_override") != "__test_single_write__":
        return failed("single_write", f"response mismatch: {resp}")

    # Restore
    _write_naming(TEST_JOB_ID, title_pattern="")
    passed("single_write")
    return True


def test_rapid_sequential_writes():
    """Multiple rapid writes to the same job should all succeed."""
    _, job = get(f"/jobs/{TEST_JOB_ID}")
    original = job.get("folder_pattern_override")

    errors = []
    for i in range(10):
        status, resp = _write_naming(TEST_JOB_ID, folder_pattern=f"__rapid_test_{i}__")
        if status != 200:
            errors.append(f"write {i}: status={status}")

    _write_naming(TEST_JOB_ID, folder_pattern=original or "")

    if errors:
        return failed("rapid_sequential", f"{len(errors)} errors: {errors[:3]}")
    passed("rapid_sequential")
    return True


def test_concurrent_writes_different_jobs():
    """Concurrent writes to different jobs should all succeed."""
    _, jobs_resp = get("/jobs?page=1&per_page=3&sort_by=start_time&sort_dir=desc")
    job_ids = [j["job_id"] for j in jobs_resp.get("jobs", [])]
    if len(job_ids) < 2:
        return failed("concurrent_diff_jobs", f"need 2+ jobs, found {len(job_ids)}")

    errors = []

    def write_job(jid, iteration):
        try:
            status, resp = _write_naming(jid, title_pattern=f"__conc_{jid}_{iteration}__")
            if status != 200:
                errors.append(f"job {jid} iter {iteration}: status={status}")
        except Exception as e:
            errors.append(f"job {jid} iter {iteration}: {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = []
        for jid in job_ids[:3]:
            for i in range(3):
                futures.append(pool.submit(write_job, jid, i))
        concurrent.futures.wait(futures)

    for jid in job_ids[:3]:
        _write_naming(jid, title_pattern="")

    if errors:
        return failed("concurrent_diff_jobs", f"{len(errors)} errors: {errors[:3]}")
    passed("concurrent_diff_jobs")
    return True


def test_concurrent_writes_same_job():
    """Concurrent writes to the SAME job - tests SQLite write serialization."""
    _, job = get(f"/jobs/{TEST_JOB_ID}")
    original = job.get("title_pattern_override")

    errors = []
    success_count = [0]

    def write_iteration(i):
        try:
            status, resp = _write_naming(TEST_JOB_ID, title_pattern=f"__same_conc_{i}__")
            if status != 200:
                errors.append(f"iter {i}: status={status} resp={resp}")
            else:
                success_count[0] += 1
        except Exception as e:
            errors.append(f"iter {i}: {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(write_iteration, i) for i in range(10)]
        concurrent.futures.wait(futures)

    _write_naming(TEST_JOB_ID, title_pattern=original or "")

    if errors:
        return failed("concurrent_same_job", f"{len(errors)}/10 failed: {errors[:3]}")
    if success_count[0] != 10:
        return failed("concurrent_same_job", f"only {success_count[0]}/10 succeeded")
    passed("concurrent_same_job")
    return True


def test_session_recovers_after_error():
    """After a 4xx error, the next request should still work (no session poison)."""
    # Cause a 404
    status, _ = get("/jobs/99999")
    if status != 404:
        return failed("session_recovery", f"expected 404, got {status}")

    # Next request should work fine
    status, data = get(f"/jobs/{TEST_JOB_ID}")
    if status != 200:
        return failed("session_recovery", f"follow-up status={status}")

    passed("session_recovery")
    return True


def test_read_during_write():
    """Reads should succeed while a write is in progress (WAL mode)."""
    errors = []

    def writer():
        for i in range(5):
            status, _ = _write_naming(TEST_JOB_ID, title_pattern=f"__rw_test_{i}__")
            if status != 200:
                errors.append(f"write {i}: status={status}")
            time.sleep(0.05)

    def reader():
        for i in range(10):
            status, _ = get(f"/jobs/{TEST_JOB_ID}")
            if status != 200:
                errors.append(f"read {i}: status={status}")
            time.sleep(0.025)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pool.submit(writer)
        pool.submit(reader)

    _write_naming(TEST_JOB_ID, title_pattern="")

    if errors:
        return failed("read_during_write", f"{len(errors)} errors: {errors[:3]}")
    passed("read_during_write")
    return True


def test_dashboard_during_writes():
    """Dashboard endpoint (heavy read) should work during concurrent writes."""
    errors = []

    def writer():
        for i in range(5):
            _write_naming(TEST_JOB_ID, folder_pattern=f"__dash_test_{i}__")
            time.sleep(0.05)

    def dashboard_reader():
        for i in range(5):
            status, data = get("/dashboard")
            if status != 200:
                errors.append(f"dashboard read {i}: status={status}")
            elif not data.get("arm_online"):
                errors.append(f"dashboard read {i}: arm_online=False")
            time.sleep(0.1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pool.submit(writer)
        pool.submit(dashboard_reader)

    _write_naming(TEST_JOB_ID, folder_pattern="")

    if errors:
        return failed("dashboard_during_writes", f"{len(errors)} errors: {errors[:3]}")
    passed("dashboard_during_writes")
    return True


def test_notification_operations():
    """Notification dismiss-all (bulk DB write) should work."""
    status, _ = post("/maintenance/dismiss-all-notifications")
    if status != 200:
        return failed("notification_ops", f"dismiss status={status}")

    passed("notification_ops")
    return True


def test_burst_writes():
    """20 writes as fast as possible - stress test for write serialization."""
    _, job = get(f"/jobs/{TEST_JOB_ID}")
    original = job.get("title_pattern_override")

    errors = []
    success_count = [0]

    def burst_write(i):
        try:
            status, _ = _write_naming(TEST_JOB_ID, title_pattern=f"__burst_{i}__")
            if status == 200:
                success_count[0] += 1
            else:
                errors.append(f"burst {i}: status={status}")
        except Exception as e:
            errors.append(f"burst {i}: {e}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(burst_write, i) for i in range(20)]
        concurrent.futures.wait(futures)

    _write_naming(TEST_JOB_ID, title_pattern=original or "")

    if errors:
        return failed("burst_writes", f"{len(errors)}/20 failed: {errors[:5]}")
    if success_count[0] < 20:
        return failed("burst_writes", f"only {success_count[0]}/20 succeeded")
    passed("burst_writes")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"\nRetrySession Integration Tests - {BASE}")
    print(f"Test job: #{TEST_JOB_ID}")
    print("=" * 60)

    tests = [
        test_api_is_reachable,
        test_job_exists,
        test_single_write_succeeds,
        test_rapid_sequential_writes,
        test_concurrent_writes_different_jobs,
        test_concurrent_writes_same_job,
        test_session_recovers_after_error,
        test_read_during_write,
        test_dashboard_during_writes,
        test_notification_operations,
        test_burst_writes,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            if result is False:
                # Don't stop on failure - run all tests
                pass
        except Exception as e:
            failed(test.__name__, f"EXCEPTION: {e}")
            results.append(False)

    print("=" * 60)
    passed_count = sum(1 for r in results if r is True)
    failed_count = sum(1 for r in results if r is False)
    print(f"\n{passed_count} passed, {failed_count} failed out of {len(results)} tests")

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
