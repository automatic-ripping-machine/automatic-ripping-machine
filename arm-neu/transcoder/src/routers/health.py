"""Health and system endpoints."""

import logging
import os
import platform

import psutil
from fastapi import APIRouter, BackgroundTasks, Request

from config import settings
from version import API_VERSION

logger = logging.getLogger(__name__)

router = APIRouter()


def _detect_cpu() -> str:
    """Detect CPU model name from /proc/cpuinfo (Linux) or platform fallback."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Unknown"


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint with GPU support and active configuration."""
    worker = request.app.state.worker
    gpu_support = worker.gpu_support if worker else {}
    return {
        "status": "healthy",
        "version": request.app.version,
        "api_version": API_VERSION,
        "worker_running": worker is not None and worker.is_running,
        "queue_size": worker.queue_size if worker else 0,
        "active_count": worker.active_count if worker else 0,
        "max_concurrent": settings.max_concurrent,
        "gpu_support": gpu_support,
        "config": {
            "selected_preset_slug": settings.selected_preset_slug,
            "delete_source": settings.delete_source,
            "output_extension": settings.output_extension,
            "max_concurrent": settings.max_concurrent,
            "stabilize_seconds": settings.stabilize_seconds,
        },
        "require_api_auth": settings.require_api_auth,
        "webhook_secret_configured": bool(settings.webhook_secret),
    }


@router.get("/system/info")
async def get_system_info(request: Request):
    """Return static hardware identity (CPU, RAM, GPU). No auth required."""
    worker = request.app.state.worker
    mem = psutil.virtual_memory()
    return {
        "cpu": _detect_cpu(),
        "memory_total_gb": round(mem.total / 1073741824, 1),
        "gpu_support": worker.gpu_support if worker else {},
    }


@router.get("/system/stats")
async def get_system_stats(request: Request):
    """Return live system metrics: CPU, memory, temperature. No auth required."""
    cpu_percent = psutil.cpu_percent()
    cpu_temp = 0.0
    try:
        temps = psutil.sensors_temperatures()
        for key in ('coretemp', 'cpu_thermal', 'k10temp', 'zenpower'):
            if temps.get(key):
                cpu_temp = temps[key][0].current
                break
    except (AttributeError, OSError):
        pass

    mem = psutil.virtual_memory()

    storage = []
    media_paths = [
        ("Raw", settings.raw_path),
        ("Work", settings.work_path),
        ("Completed", settings.completed_path),
    ]
    for name, path in media_paths:
        try:
            usage = psutil.disk_usage(path)
            storage.append({
                "name": name,
                "path": path,
                "total_gb": round(usage.total / 1073741824, 1),
                "used_gb": round(usage.used / 1073741824, 1),
                "free_gb": round(usage.free / 1073741824, 1),
                "percent": usage.percent,
            })
        except OSError:
            continue

    gpu_data = None
    gpu_monitor = getattr(request.app.state, 'gpu_monitor', None)
    if os.environ.get("FAKE_GPU_STATS"):
        import random
        gpu_data = {
            "vendor": "nvidia",
            "utilization_percent": round(random.uniform(20, 95), 1),
            "memory_used_mb": round(random.uniform(1000, 7000), 1),
            "memory_total_mb": 8192.0,
            "temperature_c": round(random.uniform(45, 82), 1),
            "encoder_percent": round(random.uniform(30, 100), 1),
            "power_draw_w": round(random.uniform(50, 280), 1),
            "power_limit_w": 300.0,
            "clock_core_mhz": round(random.uniform(800, 2100), 0),
            "clock_memory_mhz": round(random.uniform(5000, 8000), 0),
        }
    elif gpu_monitor is not None:
        try:
            gpu_data = gpu_monitor.snapshot().to_dict()
        except Exception:
            pass

    return {
        "cpu_percent": cpu_percent,
        "cpu_temp": cpu_temp,
        "memory": {
            "total_gb": round(mem.total / 1073741824, 1),
            "used_gb": round(mem.used / 1073741824, 1),
            "free_gb": round(mem.available / 1073741824, 1),
            "percent": mem.percent,
        },
        "storage": storage,
        "gpu": gpu_data,
    }


@router.post("/system/restart")
async def restart_service(background_tasks: BackgroundTasks, request: Request):
    """Restart the transcoder service.

    In reload mode (dev): kills the server child; the WatchFiles reloader
    automatically spawns a new one.
    In non-reload mode (prod): os._exit terminates PID 1 and Docker's
    restart policy brings the container back.
    """
    import os

    worker = request.app.state.worker

    def _shutdown():
        import signal
        import time
        logger.info("Restart requested via API — shutting down for Docker restart")
        if worker:
            worker.shutdown()
        time.sleep(0.5)
        try:
            # Kill process group — in Docker, this triggers restart policy.
            # PGID 0 = our own group, so this reaches uvicorn/reloader.
            os.killpg(0, signal.SIGTERM)
        except OSError as e:
            logger.warning("killpg failed, falling back to self-signal: %s", e)
            os.kill(os.getpid(), signal.SIGTERM)

    background_tasks.add_task(_shutdown)
    return {"success": True, "message": "Transcoder is restarting"}
