"""ARM-neu demo route table. Paths mirror backend/services/arm_client.py."""
from __future__ import annotations

import json
import re
from typing import Callable

import httpx

from backend.demo.http import json_response
from backend.demo.store import DemoStore

RouteHandler = Callable[..., httpx.Response]


def _jobs_paginated(request: httpx.Request, store: DemoStore) -> httpx.Response:
    jobs = store.jobs
    return json_response({"jobs": jobs, "total": len(jobs), "page": 1,
                          "per_page": max(len(jobs), 25), "pages": 1})


def _jobs_active(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(
        {"jobs": [j for j in store.jobs if j["status"] == "active"]})


def _jobs_stats(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.job_stats)


def _job_detail(request: httpx.Request, store: DemoStore,
                job_id: str) -> httpx.Response:
    job = store.job(int(job_id))
    if job is None:
        return json_response({"error": "job not found"}, status=404)
    return json_response({"job": job, "tracks": store.tracks_for(int(job_id)),
                          "config": store.job_config})


def _job_track_counts(request: httpx.Request, store: DemoStore,
                      job_id: str) -> httpx.Response:
    job = store.job(int(job_id))
    counts = (job or {}).get("track_counts", {"total": 0, "ripped": 0})
    return json_response(counts)


def _drives(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({"drives": store.drives})


def _drives_with_jobs(request: httpx.Request, store: DemoStore) -> httpx.Response:
    # Demo drive dicts already embed `current_job`, so the with-jobs view is
    # the same payload as /drives (no separate join needed in demo mode).
    return json_response({"drives": store.drives})


def _notifications(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({"notifications": store.notifications})


def _notification_count(request: httpx.Request, store: DemoStore) -> httpx.Response:
    unseen = sum(1 for n in store.notifications if not n["seen"])
    total = len(store.notifications)
    return json_response({"total": total, "unseen": unseen,
                          "seen": total - unseen, "cleared": 0})


def _channels(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.channels)


def _channel(request: httpx.Request, store: DemoStore,
             channel_id: str) -> httpx.Response:
    ch = store.channel(int(channel_id))
    return json_response(ch or {}, status=200 if ch else 404)


def _dispatches(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.dispatches)


def _services(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({"services": []})


def _config(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({"config": store.config})


def _system_info(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.system_info)


def _system_stats(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.system_stats)


def _system_stats_jobs(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.job_stats)


def _setup_status(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.setup_status)


def _ripping_enabled(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.ripping_enabled)


def _version(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({"version": "2.8.0-demo"})


def _dismiss_all(request: httpx.Request, store: DemoStore) -> httpx.Response:
    for n in store.notifications:
        n["seen"] = True
    return json_response({"success": True})


def _pause_job(request: httpx.Request, store: DemoStore,
               job_id: str) -> httpx.Response:
    job = store.job(int(job_id))
    if job is not None:
        job["status"] = "waiting"
    return json_response({"success": True})


def _start_job(request: httpx.Request, store: DemoStore,
               job_id: str) -> httpx.Response:
    job = store.job(int(job_id))
    if job is not None:
        job["status"] = "active"
    return json_response({"success": True})


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


def _naming_preview(request: httpx.Request, store: DemoStore,
                    job_id: str) -> httpx.Response:
    job = store.job(int(job_id))
    if job is None:
        return json_response({"error": "job not found"}, status=404)
    title = job.get("title", "Unknown")
    year = job.get("year", "")
    folder = f"{title} ({year})" if year else title
    tracks = [
        {"track_number": t.get("track_number", str(i + 1)),
         "filename": t.get("filename", f"title_t0{i}.mkv"),
         "rendered_filename": f"{title} - Track {t.get('track_number', i + 1)}.mkv"}
        for i, t in enumerate(store.tracks_for(int(job_id)))
    ]
    return json_response({"success": True, "job_title": title,
                          "job_folder": folder, "tracks": tracks})


def _files_roots(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.file_roots)


def _files_list(request: httpx.Request, store: DemoStore) -> httpx.Response:
    path = request.url.params.get("path") or "/mnt/raw"
    entries = store.file_tree.get(path, [])
    parent = None if path in ("/", "") else path.rsplit("/", 1)[0] or "/"
    return json_response({"path": path, "parent": parent,
                          "entries": entries, "readonly": False})


def _metadata_search(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response(store.movie_search)


def _metadata_detail(request: httpx.Request, store: DemoStore,
                     imdb_id: str) -> httpx.Response:
    return json_response(store.media_detail)


def _job_metadata(request: httpx.Request, store: DemoStore,
                  job_id: str) -> httpx.Response:
    job = store.job(int(job_id)) or {}
    return json_response({
        "title": job.get("title_auto"),
        "year": job.get("year"),
        "imdb_id": job.get("imdb_id"),
        "poster_url": job.get("poster_url"),
    })


def _music_search(request: httpx.Request, store: DemoStore) -> httpx.Response:
    return json_response({
        "results": store.music_search,
        "total": len(store.music_search),
        "offset": 0,
    })


def _music_detail(request: httpx.Request, store: DemoStore,
                  release_id: str) -> httpx.Response:
    return json_response(store.music_detail)


def _set_ripping_enabled(request: httpx.Request, store: DemoStore) -> httpx.Response:
    try:
        body = json.loads(request.content or b"{}")
    except (ValueError, TypeError):
        body = {}
    if isinstance(body, dict) and "enabled" in body:
        store.ripping_enabled["enabled"] = bool(body["enabled"])
    else:
        store.ripping_enabled["enabled"] = not store.ripping_enabled.get("enabled", True)
    return json_response({"success": True,
                          "enabled": store.ripping_enabled["enabled"]})


ROUTES: list[tuple[str, re.Pattern[str], RouteHandler]] = [
    ("GET", re.compile(r"^/api/v1/jobs/paginated$"), _jobs_paginated),
    ("GET", re.compile(r"^/api/v1/jobs/active$"), _jobs_active),
    ("GET", re.compile(r"^/api/v1/jobs/stats$"), _jobs_stats),
    ("GET", re.compile(r"^/api/v1/jobs/(?P<job_id>\d+)/detail$"), _job_detail),
    ("GET", re.compile(r"^/api/v1/jobs/(?P<job_id>\d+)/track-counts$"),
     _job_track_counts),
    ("GET", re.compile(r"^/api/v1/drives$"), _drives),
    ("GET", re.compile(r"^/api/v1/drives/with-jobs$"), _drives_with_jobs),
    ("GET", re.compile(r"^/api/v1/notifications$"), _notifications),
    ("GET", re.compile(r"^/api/v1/notifications/count$"), _notification_count),
    ("GET", re.compile(r"^/api/v1/notifications/channels$"), _channels),
    ("GET", re.compile(r"^/api/v1/notifications/channels/(?P<channel_id>\d+)$"),
     _channel),
    ("GET", re.compile(r"^/api/v1/notifications/dispatches$"), _dispatches),
    ("GET", re.compile(r"^/api/v1/notifications/services$"), _services),
    ("GET", re.compile(r"^/api/v1/settings/config$"), _config),
    ("GET", re.compile(r"^/api/v1/system/info$"), _system_info),
    ("GET", re.compile(r"^/api/v1/system/stats$"), _system_stats),
    ("GET", re.compile(r"^/api/v1/system/stats/jobs$"), _system_stats_jobs),
    ("GET", re.compile(r"^/api/v1/system/version$"), _version),
    ("GET", re.compile(r"^/api/v1/setup/status$"), _setup_status),
    ("GET", re.compile(r"^/api/v1/system/ripping-enabled$"), _ripping_enabled),
    ("GET", re.compile(r"^/api/v1/logs$"), _logs_list),
    ("GET", re.compile(r"^/api/v1/logs/(?P<filename>[^/]+)/structured$"), _log_structured),
    ("GET", re.compile(r"^/api/v1/logs/(?P<filename>[^/]+)$"), _log_content),
    ("GET", re.compile(r"^/api/v1/jobs/(?P<job_id>\d+)/naming-preview$"), _naming_preview),
    ("GET", re.compile(r"^/api/v1/jobs/(?P<job_id>\d+)/metadata$"), _job_metadata),
    ("GET", re.compile(r"^/api/v1/files/roots$"), _files_roots),
    ("GET", re.compile(r"^/api/v1/files/list$"), _files_list),
    # Metadata search/detail — specific paths before generic /{imdb_id} catch-all
    ("GET", re.compile(r"^/api/v1/metadata/search$"), _metadata_search),
    ("GET", re.compile(r"^/api/v1/metadata/music/search$"), _music_search),
    ("GET", re.compile(r"^/api/v1/metadata/music/(?P<release_id>[^/]+)$"), _music_detail),
    ("GET", re.compile(r"^/api/v1/metadata/(?P<imdb_id>[^/]+)$"), _metadata_detail),
]

ROUTES += [
    ("POST", re.compile(r"^/api/v1/notifications/dismiss-all$"), _dismiss_all),
    ("POST", re.compile(r"^/api/v1/jobs/(?P<job_id>\d+)/pause$"), _pause_job),
    ("POST", re.compile(r"^/api/v1/jobs/(?P<job_id>\d+)/start$"), _start_job),
    ("POST", re.compile(r"^/api/v1/system/ripping-enabled$"), _set_ripping_enabled),
]
