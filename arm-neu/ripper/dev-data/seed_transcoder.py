"""Seed the transcoder database with fake jobs in various states."""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("/data/db/transcoder.db")
c = conn.cursor()

now = datetime.now()

jobs = [
    # Pending jobs (queued, not started)
    {
        "title": "Dune (2021)", "source_path": "/data/raw/Dune (2021)",
        "output_path": None, "status": "PENDING", "progress": 0.0,
        "arm_job_id": "10", "error": None, "retry_count": 0,
        "created_at": (now - timedelta(minutes=5)).isoformat(),
        "started_at": None, "completed_at": None,
        "video_type": "movie", "year": "2021", "total_tracks": 4,
        "main_feature_file": "Dune_t00.mkv",
    },
    {
        "title": "Blade Runner 2049 (2017)", "source_path": "/data/raw/Blade Runner 2049 (2017)",
        "output_path": None, "status": "PENDING", "progress": 0.0,
        "arm_job_id": "7", "error": None, "retry_count": 0,
        "created_at": (now - timedelta(minutes=3)).isoformat(),
        "started_at": None, "completed_at": None,
        "video_type": "movie", "year": "2017", "total_tracks": 3,
        "main_feature_file": "Blade_Runner_2049_t00.mkv",
    },
    # Processing jobs (actively transcoding)
    {
        "title": "Breaking Bad S01E01", "source_path": "/data/raw/Breaking Bad (2008)/Breaking_Bad_S01E01.mkv",
        "output_path": "/data/completed/tv/Breaking Bad (2008)/Breaking_Bad_S01E01.mkv",
        "status": "PROCESSING", "progress": 72.5,
        "arm_job_id": "4", "error": None, "retry_count": 0,
        "created_at": (now - timedelta(hours=1)).isoformat(),
        "started_at": (now - timedelta(minutes=40)).isoformat(),
        "completed_at": None,
        "video_type": "tv", "year": "2008", "total_tracks": 1,
        "main_feature_file": "Breaking_Bad_S01E01.mkv",
    },
    {
        "title": "Breaking Bad S01E02", "source_path": "/data/raw/Breaking Bad (2008)/Breaking_Bad_S01E02.mkv",
        "output_path": "/data/completed/tv/Breaking Bad (2008)/Breaking_Bad_S01E02.mkv",
        "status": "PROCESSING", "progress": 18.3,
        "arm_job_id": "4", "error": None, "retry_count": 0,
        "created_at": (now - timedelta(hours=1)).isoformat(),
        "started_at": (now - timedelta(minutes=12)).isoformat(),
        "completed_at": None,
        "video_type": "tv", "year": "2008", "total_tracks": 1,
        "main_feature_file": "Breaking_Bad_S01E02.mkv",
    },
    # Failed jobs
    {
        "title": "The Matrix (1999) - t03", "source_path": "/data/raw/The Matrix (1999)/The_Matrix_t03.mkv",
        "output_path": None, "status": "FAILED", "progress": 45.2,
        "arm_job_id": "1",
        "error": "HandBrake exited with code 3: Encoding failed at 45%"
                 " - audio track 2 unsupported codec (TrueHD Atmos)",
        "retry_count": 2,
        "created_at": (now - timedelta(hours=6)).isoformat(),
        "started_at": (now - timedelta(hours=5, minutes=30)).isoformat(),
        "completed_at": (now - timedelta(hours=5)).isoformat(),
        "video_type": "movie", "year": "1999", "total_tracks": 1,
        "main_feature_file": "The_Matrix_t03.mkv",
    },
    {
        "title": "Inception (2010) - t02", "source_path": "/data/raw/Inception (2010)/Inception_t02.mkv",
        "output_path": None, "status": "FAILED", "progress": 0.0,
        "arm_job_id": "2",
        "error": "Source file not found: /data/raw/Inception (2010)/Inception_t02.mkv",
        "retry_count": 1,
        "created_at": (now - timedelta(hours=4)).isoformat(),
        "started_at": (now - timedelta(hours=4)).isoformat(),
        "completed_at": (now - timedelta(hours=4)).isoformat(),
        "video_type": "movie", "year": "2010", "total_tracks": 1,
        "main_feature_file": "Inception_t02.mkv",
    },
    # More completed jobs for history
    {
        "title": "The Matrix (1999)", "source_path": "/data/raw/The Matrix (1999)",
        "output_path": "/data/completed/movies/The Matrix (1999) 1080p Blu-ray HEVC",
        "status": "COMPLETED", "progress": 100.0,
        "arm_job_id": "1", "error": None, "retry_count": 0,
        "created_at": (now - timedelta(hours=5)).isoformat(),
        "started_at": (now - timedelta(hours=4, minutes=30)).isoformat(),
        "completed_at": (now - timedelta(hours=3)).isoformat(),
        "video_type": "movie", "year": "1999", "total_tracks": 5,
        "main_feature_file": "The_Matrix_t00.mkv",
    },
    {
        "title": "Inception (2010)", "source_path": "/data/raw/Inception (2010)",
        "output_path": "/data/completed/movies/Inception (2010) 720p DVD HEVC",
        "status": "COMPLETED", "progress": 100.0,
        "arm_job_id": "2", "error": None, "retry_count": 0,
        "created_at": (now - timedelta(hours=8)).isoformat(),
        "started_at": (now - timedelta(hours=7, minutes=30)).isoformat(),
        "completed_at": (now - timedelta(hours=6)).isoformat(),
        "video_type": "movie", "year": "2010", "total_tracks": 4,
        "main_feature_file": "Inception_t00.mkv",
    },
    {
        "title": "Game of Thrones S01 (2011)", "source_path": "/data/raw/Game of Thrones (2011)",
        "output_path": "/data/completed/tv/Game of Thrones (2011) 1080p Blu-ray HEVC",
        "status": "COMPLETED", "progress": 100.0,
        "arm_job_id": "6", "error": None, "retry_count": 0,
        "created_at": (now - timedelta(days=1, hours=3)).isoformat(),
        "started_at": (now - timedelta(days=1, hours=2)).isoformat(),
        "completed_at": (now - timedelta(days=1)).isoformat(),
        "video_type": "tv", "year": "2011", "total_tracks": 10,
        "main_feature_file": "GoT_S01E01.mkv",
    },
]

cols = list(jobs[0].keys())
placeholders = ", ".join(["?"] * len(cols))
col_str = ", ".join(cols)

for j in jobs:
    vals = [j[col] for col in cols]
    c.execute(f"INSERT INTO transcode_jobs ({col_str}) VALUES ({placeholders})", vals)

conn.commit()

counts = {}
for row in c.execute("SELECT status, count(*) FROM transcode_jobs GROUP BY status"):
    counts[row[0]] = row[1]
total = sum(counts.values())
print(f"Total transcoder jobs: {total}")
for s, n in sorted(counts.items()):
    print(f"  {s}: {n}")
conn.close()
