"""Single source of truth for demo/test entity builders.

These builders return plain dicts matching the JSON shapes ARM-neu and the
Transcoder return, so the data flows through the real router Pydantic
validation unchanged. Deterministic: fixed ids/titles/timestamps, no
datetime.now()/random.
"""
from __future__ import annotations

from datetime import datetime, timezone

from backend.demo.store import DemoStore


_JOB_DEFAULTS: dict = {
    "job_id": 1,
    "arm_version": "2.8.0",
    "crc_id": "abc123",
    "logfile": "job_1.log",
    "start_time": datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    "stop_time": None,
    "job_length": "01:30:00",
    "status": "active",
    "stage": "rip",
    "no_of_titles": 5,
    "title": "Test Movie",
    "title_auto": "Test Movie",
    "title_manual": None,
    "year": "2024",
    "year_auto": "2024",
    "year_manual": None,
    "video_type": "movie",
    "video_type_auto": "movie",
    "video_type_manual": None,
    "imdb_id": "tt1234567",
    "poster_url": None,
    "devpath": "/dev/sr0",
    "mountpoint": "/mnt/dev/sr0",
    "hasnicetitle": True,
    "errors": None,
    "disctype": "dvd",
    "label": "TEST_MOVIE",
    "path": "/home/arm/media/Test Movie (2024)",
    "raw_path": "/home/arm/raw/Test Movie (2024)",
    "transcode_path": "/home/arm/transcode",
    "source_type": None,
    "source_path": None,
    "ejected": False,
    "disc_number": None,
    "disc_total": None,
    "pid": 12345,
    "artist": None,
    "artist_auto": None,
    "artist_manual": None,
    "album": None,
    "album_auto": None,
    "album_manual": None,
    "season": None,
    "season_auto": None,
    "season_manual": None,
    "episode": None,
    "episode_auto": None,
    "episode_manual": None,
}


def make_job_dict(**overrides) -> dict:
    """Return a plain dict matching the Job-columns dict the ripper API returns.

    Used by router tests that mock ``arm_client.get_jobs_paginated`` /
    ``get_active_jobs`` / ``get_job_detail``. Includes a default
    ``track_counts`` so JobSchema's nested-counts field is populated.
    """
    defaults = {
        **_JOB_DEFAULTS,
        "track_counts": {"total": 5, "ripped": 0},
    }
    defaults.update(overrides)
    return defaults


def make_track_dict(**overrides) -> dict:
    d = {
        "track_id": 1,
        "job_id": 1,
        "track_number": "1",
        "length": 3600,
        "filename": "title_t00.mkv",
        "orig_filename": "title_t00.mkv",
        "basename": "title_t00.mkv",
        "ripped": False,
        "main_feature": False,
        "source": "makemkv",
    }
    d.update(overrides)
    return d


def make_drive_dict(**overrides) -> dict:
    d = {
        "drive_id": 1,
        "name": "DVD-RW",
        "mount": "/dev/sr0",
        "job_id_current": None,
        "job_id_previous": None,
        "description": "Primary drive",
        "drive_mode": "auto",
        "maker": "Plextor",
        "model": "PX-891SA",
        "serial": "ABC123",
        "connection": "SATA",
        "capabilities": ["dvd-r", "dvd-rw", "bd-r"],
        "firmware": "1.04",
        "location": "/dev/sr0",
        "stale": False,
        "mdisc": 0,
        "serial_id": "PLEXTOR_ABC123",
        "uhd_capable": False,
        "current_job": None,
    }
    d.update(overrides)
    return d


def make_notification_dict(**overrides) -> dict:
    d = {
        "id": 1,
        "title": "Job Complete",
        "message": "Test Movie finished ripping",
        "trigger_time": "2024-01-15T10:30:00Z",
        "seen": False,
        "cleared": False,
    }
    d.update(overrides)
    return d


def make_channel_dict(**overrides) -> dict:
    d = {
        "id": 1,
        "type": "apprise",
        "name": "Family Discord",
        "enabled": True,
        "config": {"type": "apprise", "url": "discord://x/y"},
        "subscribed_events": ["job.started", "job.completed"],
        "templates": {},
    }
    d.update(overrides)
    return d


def make_dispatch_dict(**overrides) -> dict:
    d = {
        "id": 1,
        "channel_id": 1,
        "event_key": "job.completed",
        "status": "success",
        "attempts": 1,
        "error": None,
        "created_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:30:01Z",
    }
    d.update(overrides)
    return d


def make_transcode_job_dict(**overrides) -> dict:
    d = {
        "id": 1,
        "title": "Test Movie",
        "source_path": "/mnt/raw/job_1/title_t00.mkv",
        "status": "processing",
        "progress": 42.0,
        "current_fps": 120.5,
        "error": None,
        "logfile": "transcode_1.log",
        "video_type": "movie",
        "year": "2024",
        "disctype": "dvd",
        "output_path": "/mnt/library/Test Movie (2024)/title_t00.mkv",
        "total_tracks": 5,
        "poster_url": None,
        "config_overrides": {"preset_slug": "h264-fast", "delete_source": True},
        "created_at": "2024-01-15T10:00:00Z",
        "started_at": "2024-01-15T10:05:00Z",
        "completed_at": None,
    }
    d.update(overrides)
    return d


def make_preset_dict(**overrides) -> dict:
    d = {
        "slug": "h264-fast",
        "name": "H.264 Fast",
        "scheme": "tiered-quality",
        "description": "Fast hardware-accelerated H.264",
        "builtin": True,
        "shared": {"container": "mkv"},
        "tiers": {"sd": {"crf": 28}, "hd": {"crf": 23}, "uhd": {"crf": 20}},
        "parent_slug": None,
        "unavailable": False,
        "reason": None,
    }
    d.update(overrides)
    return d


def make_log_entry_dict(**overrides) -> dict:
    d = {
        "timestamp": "2024-01-15T10:30:00Z",
        "level": "INFO",
        "logger": "arm.ripper",
        "event": "Ripping track 1",
        "job_id": 1,
        "label": "TEST_MOVIE",
        "raw": "2024-01-15 10:30:00 INFO arm.ripper Ripping track 1",
    }
    d.update(overrides)
    return d


def make_file_entry_dict(**overrides) -> dict:
    """Return a plain dict matching the FileEntry JSON shape."""
    d: dict = {
        "name": "unknown",
        "type": "file",
        "size": 0,
        "modified": "2024-01-15T11:00:00Z",
        "extension": "",
        "category": "",
        "permissions": None,
        "owner": None,
        "group": None,
    }
    d.update(overrides)
    return d


def build_demo_store() -> DemoStore:
    """Assemble one deterministic dataset covering every UI state."""
    jobs = [
        make_job_dict(job_id=1, title="Blade Runner 2049", year="2017",
                      title_auto="Blade Runner 2049",
                      imdb_id="tt1856101",
                      path="/home/arm/media/Blade Runner 2049 (2017)",
                      raw_path="/home/arm/raw/Blade Runner 2049 (2017)",
                      status="active", stage="rip", disctype="bluray",
                      track_counts={"total": 3, "ripped": 1},
                      poster_url="https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg"),
        make_job_dict(job_id=2, title="Dune: Part Two", year="2024",
                      title_auto="Dune: Part Two",
                      imdb_id="tt15239678",
                      path="/home/arm/media/Dune Part Two (2024)",
                      raw_path="/home/arm/raw/Dune Part Two (2024)",
                      status="active", stage="transcode", disctype="bluray",
                      track_counts={"total": 1, "ripped": 1},
                      poster_url="https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg"),
        make_job_dict(job_id=3, title="The Office S03", year="2006",
                      title_auto="The Office S03",
                      imdb_id="tt0386676",
                      path="/home/arm/media/The Office S03 (2006)",
                      raw_path="/home/arm/raw/The Office S03 (2006)",
                      status="waiting", stage="rip", disctype="dvd",
                      video_type="tv", season="3",
                      no_of_titles=8, track_counts={"total": 8, "ripped": 0},
                      poster_url="https://image.tmdb.org/t/p/w500/7DJKHzAi83BmQrWLrYYOqcoKfhR.jpg"),
        make_job_dict(job_id=4, title="Abbey Road", year="1969",
                      title_auto="Abbey Road",
                      imdb_id=None,
                      path="/home/arm/media/Abbey Road (1969)",
                      raw_path="/home/arm/raw/Abbey Road (1969)",
                      status="success", stage="rip", disctype="music",
                      video_type="music", artist="The Beatles",
                      album="Abbey Road", stop_time="2024-01-15T11:00:00Z",
                      track_counts={"total": 17, "ripped": 17},
                      poster_url="https://coverartarchive.org/release-group/9162580e-5df4-32de-80cc-f45a8d8a9b1d/front-500"),
        make_job_dict(job_id=5, title="Corrupt Disc", year=None,
                      title_auto="Corrupt Disc",
                      imdb_id=None,
                      path="/home/arm/media/Corrupt Disc",
                      raw_path="/home/arm/raw/Corrupt Disc",
                      status="fail", stage="rip", disctype="dvd",
                      errors="MakeMKV read error on title 2",
                      track_counts={"total": 0, "ripped": 0},
                      poster_url=None),
        make_job_dict(job_id=6, title="Planet Earth II", year="2016",
                      title_auto="Planet Earth II",
                      imdb_id="tt5491994",
                      path="/home/arm/media/Planet Earth II (2016)",
                      raw_path="/home/arm/raw/Planet Earth II (2016)",
                      status="success", stage="transcode", disctype="bluray",
                      video_type="tv", season="1", disc_number=1, disc_total=2,
                      track_counts={"total": 6, "ripped": 6},
                      poster_url="https://image.tmdb.org/t/p/w500/5maYKYzWpE68ycxGh1luu4P2LOS.jpg"),
    ]
    tracks = {
        1: [make_track_dict(track_id=10 + i, job_id=1, track_number=str(i + 1),
                            filename=f"title_t0{i}.mkv", ripped=(i == 0),
                            main_feature=(i == 0), length=8400 - i * 60)
            for i in range(3)],
        5: [],
    }
    drives = [
        make_drive_dict(drive_id=1, name="Blu-ray", mount="/dev/sr0",
                        job_id_current=1, uhd_capable=True,
                        current_job={"job_id": 1, "title": "Blade Runner 2049",
                                     "status": "active", "disctype": "bluray"}),
        make_drive_dict(drive_id=2, name="DVD-RW", mount="/dev/sr1",
                        serial="DEF456", serial_id="HLDS_DEF456"),
        make_drive_dict(drive_id=3, name="Stale Drive", mount="/dev/sr2",
                        stale=True, description="Unplugged"),
    ]
    notifications = [
        make_notification_dict(id=1, title="Rip complete",
                               message="Abbey Road finished", seen=False),
        make_notification_dict(id=2, title="Transcode started",
                               message="Dune: Part Two", seen=False),
        make_notification_dict(id=3, title="Job failed",
                               message="Corrupt Disc", seen=True),
    ]
    channels = [
        make_channel_dict(id=1, type="apprise", name="Family Discord"),
        make_channel_dict(id=2, type="webhook", name="Home Assistant",
                          config={"type": "webhook",
                                  "url": "https://hass.local/hook"}),
        make_channel_dict(id=3, type="bash", name="Notify Script",
                          config={"type": "bash",
                                  "script_path": "/opt/arm/scripts/notify.sh"}),
    ]
    dispatches = [
        make_dispatch_dict(id=1, channel_id=1, status="success"),
        make_dispatch_dict(id=2, channel_id=2, status="failed",
                           error="connection refused", attempts=3),
    ]
    transcode_jobs = [
        make_transcode_job_dict(id=1, title="Dune: Part Two", status="processing",
                                progress=63.0,
                                poster_url="https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg"),
        make_transcode_job_dict(id=2, title="Planet Earth II", status="pending",
                                progress=0.0, started_at=None,
                                poster_url="https://image.tmdb.org/t/p/w500/5maYKYzWpE68ycxGh1luu4P2LOS.jpg"),
        make_transcode_job_dict(id=3, title="Blade Runner 2049",
                                status="completed", progress=100.0,
                                completed_at="2024-01-15T10:45:00Z",
                                poster_url="https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg"),
    ]
    presets = [
        make_preset_dict(slug="h264-fast", name="H.264 Fast"),
        make_preset_dict(slug="h265-quality", name="H.265 Quality",
                         scheme="tiered-quality", builtin=False),
    ]
    log_files = [
        {"filename": "job_1.log", "size": 20480, "modified": "2024-01-15T11:00:00Z"},
        {"filename": "job_4.log", "size": 8192, "modified": "2024-01-15T11:05:00Z"},
    ]
    file_roots = [
        {"label": "Raw", "path": "/mnt/raw", "key": "raw"},
        {"label": "Library", "path": "/mnt/library", "key": "library",
         "readonly": True},
    ]
    file_tree: dict = {
        "/mnt/raw": [
            make_file_entry_dict(name="Blade Runner 2049 (2017)", type="directory",
                                 modified="2024-01-15T10:00:00Z"),
            make_file_entry_dict(name="The Office S03 (2006)", type="directory",
                                 modified="2024-01-15T10:30:00Z"),
        ],
        "/mnt/raw/Blade Runner 2049 (2017)": [
            make_file_entry_dict(name="title_t00.mkv", type="file",
                                 size=42000000000, extension="mkv",
                                 category="video",
                                 modified="2024-01-15T10:15:00Z"),
        ],
        "/mnt/raw/The Office S03 (2006)": [
            make_file_entry_dict(name="title_t00.mkv", type="file",
                                 size=1500000000, extension="mkv",
                                 category="video",
                                 modified="2024-01-15T10:35:00Z"),
            make_file_entry_dict(name="title_t01.mkv", type="file",
                                 size=1480000000, extension="mkv",
                                 category="video",
                                 modified="2024-01-15T10:36:00Z"),
        ],
        "/mnt/library": [
            make_file_entry_dict(name="Movies", type="directory",
                                 modified="2024-01-15T11:00:00Z"),
        ],
        "/mnt/library/Movies": [
            make_file_entry_dict(name="Blade Runner 2049 (2017).mkv", type="file",
                                 size=38000000000, extension="mkv",
                                 category="video",
                                 modified="2024-01-15T10:50:00Z"),
        ],
    }
    log_entries = [
        make_log_entry_dict(),
        make_log_entry_dict(level="DEBUG", event="Scanning disc",
                            raw="2024-01-15 10:29:00 DEBUG arm.ripper Scanning disc"),
        make_log_entry_dict(level="WARNING", logger="arm.transcode",
                            event="Low disk space",
                            raw="2024-01-15 10:31:00 WARNING arm.transcode Low disk space"),
        make_log_entry_dict(level="ERROR", logger="arm.makemkv",
                            event="Read retry on title 2",
                            raw="2024-01-15 10:32:00 ERROR arm.makemkv Read retry on title 2"),
    ]
    return DemoStore(
        jobs=jobs,
        tracks=tracks,
        job_config={"RIPMETHOD": "mkv", "MAINFEATURE": True, "MINLENGTH": 120,
                    "MAXLENGTH": 9000, "AUDIO_FORMAT": "aac",
                    "SKIP_TRANSCODE": False},
        drives=drives,
        notifications=notifications,
        channels=channels,
        dispatches=dispatches,
        transcode_jobs=transcode_jobs,
        presets=presets,
        config={"RIPMETHOD": "mkv", "MAINFEATURE": "False", "MINLENGTH": "60",
                "MAXLENGTH": "9999", "AUDIO_FORMAT": "aac", "SKIP_TRANSCODE": "False",
                "RAW_PATH": "/mnt/raw", "LIBRARY_PATH": "/mnt/library",
                "TV_TITLE_PATTERN": "{title} - S{season}E{episode}",
                "MOVIE_TITLE_PATTERN": "{title} ({year})",
                "MAKEMKV_PERMA_KEY": "T-DEMO0000demokeydemokeydemokey00",
                "MAKEMKV_COMMUNITY_KEYDB": "True",
                "MAX_CONCURRENT_MAKEMKVINFO": "0", "PRESCAN_TIMEOUT": "600",
                "PRESCAN_CACHE_MB": "64", "PRESCAN_RETRIES": "3",
                "DISC_ENUM_TIMEOUT": "120"},
        system_info={"id": 1, "name": "ARM Demo Server",
                     "cpu": "Intel Core i7-9700K",
                     "description": "Demo data", "mem_total": 32.0},
        system_stats={"cpu_percent": 22.5, "cpu_temp": 51.0,
                      "memory": {"total_gb": 32.0, "used_gb": 12.0,
                                 "free_gb": 20.0, "percent": 37.5},
                      "storage": [
                          {"name": "Raw", "path": "/mnt/raw", "total_gb": 2000.0,
                           "used_gb": 900.0, "free_gb": 1100.0, "percent": 45.0},
                          {"name": "Library", "path": "/mnt/library",
                           "total_gb": 8000.0, "used_gb": 7400.0,
                           "free_gb": 600.0, "percent": 92.5}],
                      "gpu": {"vendor": "nvidia", "utilization_percent": 48.0,
                              "memory_used_mb": 2048.0, "memory_total_mb": 8192.0,
                              "temperature_c": 58.0, "encoder_percent": 40.0,
                              "power_draw_w": 160.0, "power_limit_w": 250.0,
                              "clock_core_mhz": 1900.0, "clock_memory_mhz": 7000.0}},
        job_stats={"total": 6, "active": 2, "waiting": 1, "success": 2, "fail": 1},
        setup_status={"db_exists": True, "db_initialized": True, "db_current": True,
                      "db_version": "2.8.0", "db_head": "demo", "first_run": False,
                      "arm_version": "2.8.0"},
        ripping_enabled={"enabled": True, "makemkv_key_valid": True,
                         "makemkv_key_checked_at": "2024-01-15T09:00:00Z"},
        transcoder_health={"status": "online",
                           "gpu_support": {"h264": True, "h265": True, "av1": False},
                           "worker_running": True, "queue_size": 1,
                           "require_api_auth": False,
                           "webhook_secret_configured": True},
        transcoder_stats={"pending": 1, "processing": 1, "completed": 12,
                          "failed": 0, "cancelled": 0, "worker_running": True,
                          "current_job": "1", "active_count": 1,
                          "max_concurrent": 4},
        transcoder_config={"config": {"default_encoder": "h264",
                                      "output_container": "mkv",
                                      "audio_codec": "aac"},
                           "updatable_keys": ["default_encoder", "output_container"],
                           "paths": {"source": "/mnt/raw", "output": "/mnt/library",
                                     "logs": "/logs"},
                           "valid_video_encoders": ["h264", "h265", "vp9"],
                           "valid_audio_encoders": ["aac", "mp3", "opus"],
                           "valid_subtitle_modes": ["auto", "forced", "all"],
                           "valid_log_levels": ["debug", "info", "warning", "error"],
                           "valid_preset_files": ["builtin.json"],
                           "presets_by_file": {"builtin.json": ["h264-fast"]}},
        handbrake_presets={"General": ["Fast 1080p30", "HQ 1080p30"],
                           "Matroska": ["H.265 MKV 1080p30"]},
        log_files=log_files,
        log_entries=log_entries,
        file_roots=file_roots,
        file_tree=file_tree,
        movie_search=[
            {
                "title": "Blade Runner 2049",
                "year": "2017",
                "imdb_id": "tt1856101",
                "media_type": "movie",
                "poster_url": "https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg",
            },
            {
                "title": "Dune: Part Two",
                "year": "2024",
                "imdb_id": "tt15239678",
                "media_type": "movie",
                "poster_url": "https://image.tmdb.org/t/p/w500/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg",
            },
        ],
        media_detail={
            "title": "Blade Runner 2049",
            "year": "2017",
            "imdb_id": "tt1856101",
            "media_type": "movie",
            "poster_url": "https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg",
            "plot": "A young blade runner discovers a long-buried secret that leads him to track down former blade runner Rick Deckard.",
            "background_url": None,
        },
        music_search=[
            {
                "title": "Abbey Road",
                "artist": "The Beatles",
                "year": "1969",
                "release_id": "abbey-road-1",
                "media_type": "music",
                "poster_url": "https://coverartarchive.org/release-group/9162580e-5df4-32de-80cc-f45a8d8a9b1d/front-500",
                "track_count": 17,
                "country": "GB",
                "release_type": "Album",
                "format": "CD",
                "label": "Apple Records",
            },
            {
                "title": "Abbey Road (Remaster)",
                "artist": "The Beatles",
                "year": "2019",
                "release_id": "abbey-road-2",
                "media_type": "music",
                "poster_url": "https://coverartarchive.org/release-group/9162580e-5df4-32de-80cc-f45a8d8a9b1d/front-500",
                "track_count": 17,
                "country": "GB",
                "release_type": "Album",
                "format": "CD",
                "label": "Apple Records",
            },
        ],
        music_detail={
            "title": "Abbey Road",
            "artist": "The Beatles",
            "year": "1969",
            "release_id": "abbey-road-1",
            "media_type": "music",
            "poster_url": "https://coverartarchive.org/release-group/9162580e-5df4-32de-80cc-f45a8d8a9b1d/front-500",
            "track_count": 17,
            "country": "GB",
            "release_type": "Album",
            "format": "CD",
            "label": "Apple Records",
            "catalog_number": "PCS 7088",
            "barcode": None,
            "status": "Official",
            "disc_count": 1,
            "tracks": [
                {"number": "1", "title": "Come Together", "length_ms": 259000, "disc_number": 1},
                {"number": "2", "title": "Something", "length_ms": 182000, "disc_number": 1},
                {"number": "3", "title": "Maxwell's Silver Hammer", "length_ms": 207000, "disc_number": 1},
                {"number": "4", "title": "Oh! Darling", "length_ms": 207000, "disc_number": 1},
                {"number": "5", "title": "Octopus's Garden", "length_ms": 170000, "disc_number": 1},
                {"number": "6", "title": "I Want You (She's So Heavy)", "length_ms": 469000, "disc_number": 1},
                {"number": "7", "title": "Here Comes the Sun", "length_ms": 185000, "disc_number": 1},
                {"number": "8", "title": "Because", "length_ms": 165000, "disc_number": 1},
                {"number": "9", "title": "You Never Give Me Your Money", "length_ms": 242000, "disc_number": 1},
            ],
        },
    )
