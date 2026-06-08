"""Transcoder demo route table. Paths mirror backend/services/transcoder_client.py."""
from __future__ import annotations

import re
from typing import Callable

import httpx

from backend.demo.http import json_response
from backend.demo.store import DemoStore

RouteHandler = Callable[..., httpx.Response]


def _health(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.transcoder_health)


def _jobs(request: httpx.Request, store: DemoStore) -> httpx.Response:
    jobs = store.transcode_jobs
    job_id = request.url.params.get("job_id")
    if job_id is not None:
        jobs = [j for j in jobs if str(j["id"]) == str(job_id)]
    status = request.url.params.get("status")
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    return json_response({"jobs": jobs, "total": len(jobs)})


def _stats(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.transcoder_stats)


def _system_info(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({"id": 1, "name": "Transcoder Demo",
                          "cpu": "AMD Ryzen 9", "mem_total": 64.0})


def _system_stats(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.system_stats)


def _config(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.transcoder_config)


def _presets(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({"presets": store.presets})


def _handbrake_presets(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.handbrake_presets)


def _logs_list(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.log_files)


def _log_content(request: httpx.Request, store: DemoStore,
                 filename: str) -> httpx.Response:
    content = "\n".join(e["raw"] for e in store.log_entries)
    return json_response({"filename": filename, "content": content,
                          "lines": len(store.log_entries)})


def _log_structured(request: httpx.Request, store: DemoStore,
                    filename: str) -> httpx.Response:
    level = request.url.params.get("level")
    entries = store.log_entries
    if level:
        entries = [e for e in entries if e["level"] == level]
    return json_response({"filename": filename, "entries": entries,
                          "lines": len(entries)})


def _workers(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({
        "max_concurrent": 4,
        "active_count": 1,
        "workers": [
            {"worker_id": 1, "status": "processing", "current_job": "1",
             "current_job_id": 1, "started_at": "2024-01-15T10:05:00Z"},
            {"worker_id": 2, "status": "idle", "current_job": None,
             "current_job_id": None, "started_at": None},
        ],
    })


def _scheme(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({
        "slug": "tiered-quality",
        "name": "Tiered Quality",
        "supported_encoders": [],
        "supported_audio_encoders": ["aac", "mp3", "opus"],
        "supported_subtitle_modes": ["auto", "forced", "all"],
        "advanced_fields": {},
    })


ROUTES: list[tuple[str, re.Pattern[str], RouteHandler]] = [
    ("GET", re.compile(r"^/health$"), _health),
    ("GET", re.compile(r"^/jobs$"), _jobs),
    ("GET", re.compile(r"^/stats$"), _stats),
    ("GET", re.compile(r"^/system/info$"), _system_info),
    ("GET", re.compile(r"^/system/stats$"), _system_stats),
    ("GET", re.compile(r"^/config$"), _config),
    ("GET", re.compile(r"^/workers$"), _workers),
    ("GET", re.compile(r"^/api/v1/presets$"), _presets),
    ("GET", re.compile(r"^/api/v1/handbrake-presets$"), _handbrake_presets),
    ("GET", re.compile(r"^/api/v1/scheme$"), _scheme),
    ("GET", re.compile(r"^/logs$"), _logs_list),
    ("GET", re.compile(r"^/logs/(?P<filename>[^/]+)/structured$"), _log_structured),
    ("GET", re.compile(r"^/logs/(?P<filename>[^/]+)$"), _log_content),
]
