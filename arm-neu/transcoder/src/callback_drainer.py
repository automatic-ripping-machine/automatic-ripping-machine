"""Durable queue drainer for ARM-callback POSTs.

Replaces the inline 3-retry pattern in transcoder._notify_arm_callback.
_notify_arm_callback enqueues a PendingCallbackDB row; this module's
TranscodeCallbackDrainer loops over the table, POSTs to arm-neu, and
updates row state based on the response.

See docs/superpowers/specs/2026-04-23-callback-retry-refactor-design.md
for the spec.
"""
import httpx


# HTTP codes where arm-neu's response tells us the callback will never
# succeed. Do NOT retry. The row stays in the table with
# permanent_failure_at set so an operator can audit.
_PERMANENT_HTTP_CODES = frozenset({400, 401, 403, 404, 410, 422})


def is_permanent_error(exc_or_response) -> bool:
    """Classify a send outcome as permanent (no retry) vs retriable.

    Permanent: explicit 4xx codes in _PERMANENT_HTTP_CODES.
    Retriable: everything else - 408, 429, 5xx, network errors, timeouts.
    Not-permanent for 2xx either; callers short-circuit on success
    before reaching this classifier.
    """
    if isinstance(exc_or_response, httpx.Response):
        return exc_or_response.status_code in _PERMANENT_HTTP_CODES
    # httpx exceptions (ConnectError, ReadTimeout, etc.) are all retriable.
    return False


_BASE_DELAY_SECONDS = 5
_MAX_DELAY_SECONDS = 1800  # 30 minutes


def backoff_seconds(attempt_count: int) -> int:
    """Return the delay before attempt #(attempt_count + 1).

    Schedule: 5, 10, 20, 40, 80, 160, 320, 640, 1280, 1800, 1800, ...
    First retry after 5s; doubles per attempt; capped at 30 minutes.
    attempt_count=0 returns 0 (send immediately).
    """
    if attempt_count <= 0:
        return 0
    return min(_BASE_DELAY_SECONDS * (2 ** (attempt_count - 1)), _MAX_DELAY_SECONDS)


import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx
from arm_contracts import JobStatus, TrackResult, TranscodeCallbackPayload
from sqlalchemy import select

from models import PendingCallbackDB
from version import API_VERSION

logger = logging.getLogger(__name__)


_POST_TIMEOUT_SECONDS = 10


class TranscodeCallbackDrainer:
    """Background task that drains pending_callbacks rows to arm-neu.

    One instance per transcoder process. Owns no locking; SQLite's row-level
    write serialization is enough for the scale we handle (bounded concurrency
    of 5 in-flight sends). See spec for the full design.
    """

    def __init__(
        self,
        get_db,
        callback_url: str,
        http_client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ):
        self._get_db = get_db
        self._callback_url = callback_url.rstrip("/")
        self._http_client_factory = http_client_factory or (
            lambda: httpx.AsyncClient(timeout=_POST_TIMEOUT_SECONDS)
        )
        self._new_row_event = asyncio.Event()
        self._stop_flag = False

    async def send_one(self, row_id: int) -> None:
        """Send a single pending row and update its state.

        Reads the row, POSTs to arm-neu, writes the outcome back.
        All exceptions are caught and converted to retriable-state updates
        (so the drainer loop is robust to transient errors mid-send).
        """
        async with self._get_db() as session:
            result = await session.execute(
                select(PendingCallbackDB).where(PendingCallbackDB.id == row_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return  # Row was deleted between scan and send; nothing to do.
            if row.delivered_at is not None or row.permanent_failure_at is not None:
                return  # Already terminal; nothing to do.

            url = f"{self._callback_url}/api/v1/jobs/{row.job_id}/transcode-callback"
            track_results = None
            if row.track_results_json:
                track_results = [
                    TrackResult.model_validate(t)
                    for t in json.loads(row.track_results_json)
                ]
            payload = TranscodeCallbackPayload(
                status=JobStatus(row.status),
                error=row.error or None,
                track_results=track_results,
            )

            try:
                async with self._http_client_factory() as client:
                    response = await client.post(
                        url,
                        json=payload.model_dump(exclude_none=True),
                        headers={"X-Api-Version": API_VERSION},
                    )
                if response.status_code < 300:
                    row.delivered_at = datetime.now(timezone.utc)
                    await session.commit()
                    logger.info(
                        "ARM callback delivered: job_id=%s status=%s (row_id=%s)",
                        row.job_id, row.status, row.id,
                    )
                    return
                if is_permanent_error(response):
                    row.permanent_failure_at = datetime.now(timezone.utc)
                    row.last_error = f"HTTP {response.status_code}"
                    await session.commit()
                    logger.error(
                        "ARM callback permanent failure: job_id=%s status=%s "
                        "HTTP %s. Row %s tombstoned.",
                        row.job_id, row.status, response.status_code, row.id,
                    )
                    return
                # Retriable HTTP status
                row.attempt_count += 1
                row.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                    seconds=backoff_seconds(row.attempt_count)
                )
                row.last_error = f"HTTP {response.status_code}"
                await session.commit()
                logger.warning(
                    "ARM callback retriable HTTP %s for job_id=%s (attempt %d); "
                    "next in %ds",
                    response.status_code, row.job_id, row.attempt_count,
                    backoff_seconds(row.attempt_count),
                )
            except Exception as exc:
                # Network/timeout/etc. All retriable.
                row.attempt_count += 1
                row.next_attempt_at = datetime.now(timezone.utc) + timedelta(
                    seconds=backoff_seconds(row.attempt_count)
                )
                row.last_error = str(exc)[:500]
                await session.commit()
                logger.warning(
                    "ARM callback retriable error for job_id=%s (attempt %d): "
                    "%s; next in %ds",
                    row.job_id, row.attempt_count, exc,
                    backoff_seconds(row.attempt_count),
                )

    _SWEEP_LIMIT = 5
    _CLEANUP_DELIVERED_DAYS = 7

    async def sweep_once(self) -> None:
        """Run one pass: find due rows, send concurrently (capped), cleanup.

        - SELECT up to _SWEEP_LIMIT due rows (not delivered, not permanent
          failure, next_attempt_at <= now).
        - Spawn a send_one task per row; await them all.
        - Cleanup delivered rows older than _CLEANUP_DELIVERED_DAYS.
        """
        now = datetime.now(timezone.utc)
        async with self._get_db() as session:
            result = await session.execute(
                select(PendingCallbackDB.id)
                .where(PendingCallbackDB.delivered_at.is_(None))
                .where(PendingCallbackDB.permanent_failure_at.is_(None))
                .where(PendingCallbackDB.next_attempt_at <= now)
                .order_by(PendingCallbackDB.next_attempt_at)
                .limit(self._SWEEP_LIMIT)
            )
            due_ids = [r[0] for r in result.all()]

        if due_ids:
            await asyncio.gather(
                *(self.send_one(row_id) for row_id in due_ids),
                return_exceptions=False,
            )

        # Cleanup old delivered rows
        cutoff = now - timedelta(days=self._CLEANUP_DELIVERED_DAYS)
        async with self._get_db() as session:
            stale = await session.execute(
                select(PendingCallbackDB)
                .where(PendingCallbackDB.delivered_at.is_not(None))
                .where(PendingCallbackDB.delivered_at < cutoff)
            )
            for row in stale.scalars():
                await session.delete(row)
            await session.commit()

    _IDLE_SLEEP_SECONDS = 30
    _CRASH_RETRY_SLEEP_SECONDS = 5

    def notify_new_row(self) -> None:
        """Called by _notify_arm_callback after INSERT to wake the drainer."""
        self._new_row_event.set()

    def stop(self) -> None:
        """Signal the run loop to exit on its next iteration."""
        self._stop_flag = True
        self._new_row_event.set()

    async def run(self) -> None:
        """Main drainer loop. Runs until stop() is called.

        Each iteration: sweep_once (may raise, caught and logged),
        then wait for the event OR a 30s timeout.
        """
        while not self._stop_flag:
            try:
                await self.sweep_once()
            except Exception as exc:
                logger.error(
                    "Drainer sweep failed, will retry in %ds: %s",
                    self._CRASH_RETRY_SLEEP_SECONDS, exc,
                    exc_info=True,
                )
                try:
                    await asyncio.wait_for(
                        self._new_row_event.wait(),
                        timeout=self._CRASH_RETRY_SLEEP_SECONDS,
                    )
                except asyncio.TimeoutError:
                    pass
                self._new_row_event.clear()
                continue

            try:
                await asyncio.wait_for(
                    self._new_row_event.wait(),
                    timeout=self._IDLE_SLEEP_SECONDS,
                )
            except asyncio.TimeoutError:
                pass
            self._new_row_event.clear()
