import asyncio

from fastapi import APIRouter

from backend.config import settings as app_settings
from backend.models.schemas import DashboardResponse, HardwareInfoSchema, JobSchema, SystemStatsSchema
from backend.models.transcoder import TranscoderJob, TranscoderStatsSummary
from backend.services import arm_client, transcoder_client, system_cache

router = APIRouter(prefix="/api", tags=["dashboard"])


async def _fetch_transcoder() -> tuple[bool, dict | None, list]:
    """Fetch transcoder health, stats, and active jobs concurrently.

    Returns a disabled payload without any HTTP call when the feature flag is off.
    """
    if not app_settings.transcoder_enabled:
        return False, None, []

    health = await transcoder_client.health()
    if not health:
        return False, None, []

    stats, jobs_data = await asyncio.gather(
        transcoder_client.get_stats(),
        transcoder_client.get_jobs(status="processing"),
    )
    active = jobs_data["jobs"] if jobs_data and "jobs" in jobs_data else []
    return True, stats, active


async def _fetch_arm_state() -> tuple[bool, list | None, int | None, dict[str, str] | None, int | None, bool | None]:
    """Fetch all ARM-derived dashboard state via the ripper REST API.

    Returns (db_available, active_jobs, drives_online, drive_names,
    notification_count, ripping_paused). All four endpoints are issued
    concurrently. db_available is True iff at least one call succeeded;
    each derived field is None when its specific endpoint failed, so the
    BFF response can carry None and the polling store keeps the prior
    value instead of overwriting with zero on a transient blip.
    """
    active_data, drives_data, notif_count_data, ripping_data = await asyncio.gather(
        arm_client.get_active_jobs(),
        arm_client.get_drives(),
        arm_client.get_notification_count(),
        arm_client.get_ripping_enabled(),
    )

    db_available = any(d is not None for d in (active_data, drives_data, notif_count_data, ripping_data))

    active_jobs = (active_data.get("jobs") or []) if active_data is not None else None

    drives_online: int | None = None
    drive_names: dict[str, str] | None = None
    if drives_data is not None:
        drives = drives_data.get("drives") or []
        drives_online = sum(1 for d in drives if not d.get("stale", False))
        # Normalize mount paths - drives store /mnt/dev/sr0, jobs store /dev/sr0
        drive_names = {}
        for d in drives:
            mount, name = d.get("mount"), d.get("name")
            if mount and name:
                drive_names[mount] = name
                basename = mount.rsplit("/", 1)[-1]
                drive_names[f"/dev/{basename}"] = name

    notification_count = notif_count_data.get("unseen", 0) if notif_count_data is not None else None
    ripping_paused = (not ripping_data.get("ripping_enabled", True)) if ripping_data is not None else None
    return db_available, active_jobs, drives_online, drive_names, notification_count, ripping_paused


async def _fetch_transcoder_system_stats() -> SystemStatsSchema | None:
    """Wrap transcoder_client.get_system_stats() with the feature-flag gate."""
    if not app_settings.transcoder_enabled:
        return None
    data = await transcoder_client.get_system_stats()
    return SystemStatsSchema(**data) if data else None


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    arm_state_task = asyncio.create_task(_fetch_arm_state())
    transcoder_task = asyncio.create_task(_fetch_transcoder())
    stats_task = asyncio.create_task(arm_client.get_system_stats())
    transcoder_stats_task = asyncio.create_task(_fetch_transcoder_system_stats())
    ripping_task = asyncio.create_task(system_cache.get_ripping_data())

    db_available, active_jobs, drives_online, drive_names, notification_count, ripping_paused = await arm_state_task
    transcoder_online, transcoder_stats, active_transcodes = await transcoder_task

    system_stats: SystemStatsSchema | None = None
    stats_data = await stats_task
    if stats_data:
        system_stats = SystemStatsSchema(**stats_data)

    transcoder_system_stats = await transcoder_stats_task

    ripping_data = await ripping_task
    makemkv_key_valid = None
    makemkv_key_checked_at = None
    if ripping_data and ripping_data.get("ripping_enabled") is not None:
        makemkv_key_valid = ripping_data.get("makemkv_key_valid")
        makemkv_key_checked_at = ripping_data.get("makemkv_key_checked_at")

    arm_hw = system_cache.get_arm_info()
    transcoder_hw = system_cache.get_transcoder_info() if app_settings.transcoder_enabled else None

    arm_online = stats_data is not None

    return DashboardResponse(
        db_available=db_available,
        arm_online=arm_online,
        active_jobs=[JobSchema(**j) for j in active_jobs] if active_jobs is not None else None,
        system_info=HardwareInfoSchema(**arm_hw) if arm_hw else None,
        drives_online=drives_online,
        drive_names=drive_names,
        notification_count=notification_count,
        ripping_enabled=(not ripping_paused) if ripping_paused is not None else None,
        makemkv_key_valid=makemkv_key_valid,
        makemkv_key_checked_at=makemkv_key_checked_at,
        transcoder_online=transcoder_online,
        transcoder_stats=(
            TranscoderStatsSummary(**transcoder_stats) if transcoder_stats else None
        ),
        transcoder_system_stats=transcoder_system_stats,
        active_transcodes=[TranscoderJob(**j) for j in active_transcodes],
        system_stats=system_stats,
        transcoder_info=HardwareInfoSchema(**transcoder_hw) if transcoder_hw else None,
    )


@router.post("/dashboard/makemkv-key-check")
async def check_makemkv_key():
    """Proxy MakeMKV key check to ARM backend."""
    result = await arm_client.check_makemkv_key()
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ARM is unreachable")
    if result.get("success") is False:
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail=result.get("error", "ARM request failed"))
    return result
