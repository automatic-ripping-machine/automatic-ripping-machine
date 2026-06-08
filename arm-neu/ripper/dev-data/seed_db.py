"""Seed the ARM database with realistic fake data for UI development."""
import sqlite3
import sys
from datetime import datetime, timedelta

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "/home/arm/db/arm.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Clear existing data
for table in ("track", "config", "notifications", "job", "system_drives", "system_info"):
    c.execute(f"DELETE FROM {table}")
conn.commit()

now = datetime.now()

# --- System Info ---
c.execute(
    "INSERT INTO system_info (id, name, cpu, description, mem_total) VALUES (1, ?, ?, ?, ?)",
    ("arm-server", "AMD Ryzen 7 5800X", "ARM Ripping Server", 32768),
)

# --- Jobs ---
job_cols = (
    "arm_version", "crc_id", "logfile", "start_time", "stop_time",
    "job_length", "status", "no_of_titles",
    "title", "title_auto", "title_manual",
    "year", "year_auto", "year_manual",
    "video_type", "video_type_auto", "video_type_manual",
    "imdb_id", "imdb_id_auto", "imdb_id_manual",
    "poster_url", "poster_url_auto", "poster_url_manual",
    "devpath", "mountpoint", "hasnicetitle", "errors", "disctype",
    "label", "ejected", "updated", "pid", "pid_hash",
    "path", "stage", "is_iso", "manual_start", "manual_mode",
)
placeholders = ", ".join(["?"] * len(job_cols))
col_str = ", ".join(job_cols)

VER = "2.8.0"
TMDB = "https://image.tmdb.org/t/p/original"

jobs = [
    # 1: Completed bluray movie — correctly identified
    (VER, "a1b2c3d4e5f60001", "The_Matrix_1999.log",
     (now - timedelta(hours=3)).isoformat(), (now - timedelta(hours=1, minutes=20)).isoformat(),
     "1:40:12", "success", 24,
     "The Matrix", "The Matrix", None,
     "1999", "1999", None,
     "movie", "movie", None,
     "tt0133093", "tt0133093", None,
     f"{TMDB}/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", f"{TMDB}/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg", None,
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "bluray",
     "THE_MATRIX", 1, 0, 12345, 98765,
     "/home/arm/media/movies/The Matrix (1999)", "170000000001", 0, 0, 0),

    # 2: Completed dvd movie — user corrected title (auto was disc label)
    (VER, "b2c3d4e5f6a10002", "Inception_2010.log",
     (now - timedelta(hours=5)).isoformat(), (now - timedelta(hours=3, minutes=45)).isoformat(),
     "1:15:33", "success", 18,
     "Inception", "INCEPTION_DISC1", "Inception",
     "2010", "0000", "2010",
     "movie", "movie", "movie",
     "tt1375666", None, "tt1375666",
     f"{TMDB}/ljsZTbVsrQSqZgWeep2B1QiDKuh.jpg", None, f"{TMDB}/ljsZTbVsrQSqZgWeep2B1QiDKuh.jpg",
     "/dev/sr1", "/mnt/dev/sr1", 1, None, "dvd",
     "INCEPTION_DISC1", 1, 0, 12400, 98700,
     "/home/arm/media/movies/Inception (2010)", "170000000002", 0, 0, 0),

    # 3: Currently ripping — bluray
    (VER, "c3d4e5f6a1b20003", "INTERSTELLAR.log",
     (now - timedelta(minutes=35)).isoformat(), None,
     None, "ripping", 31,
     "Interstellar", "Interstellar", None,
     "2014", "2014", None,
     "movie", "movie", None,
     "tt0816692", "tt0816692", None,
     f"{TMDB}/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", f"{TMDB}/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg", None,
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "bluray",
     "INTERSTELLAR", 0, 0, 14200, 97600,
     "/home/arm/media/movies/Interstellar (2014)", "170000000003", 0, 0, 0),

    # 4: Transcoding — dvd series
    (VER, "d4e5f6a1b2c30004", "BREAKING_BAD_S1D1.log",
     (now - timedelta(hours=1, minutes=10)).isoformat(), None,
     None, "transcoding", 7,
     "Breaking Bad", "Breaking Bad", None,
     "2008", "2008", None,
     "series", "series", None,
     "tt0903747", "tt0903747", None,
     f"{TMDB}/ggFHVNu6YYI5L9pCfOacjizRGt.jpg", f"{TMDB}/ggFHVNu6YYI5L9pCfOacjizRGt.jpg", None,
     "/dev/sr1", "/mnt/dev/sr1", 1, None, "dvd",
     "BREAKING_BAD_S1D1", 1, 0, 14500, 97300,
     "/home/arm/media/tv/Breaking Bad (2008)", "170000000004", 0, 0, 0),

    # 5: Failed — unidentified dvd
    (VER, "e5f6a1b2c3d40005", "DVDVIDEO_2025.log",
     (now - timedelta(hours=8)).isoformat(), (now - timedelta(hours=7, minutes=30)).isoformat(),
     "0:30:05", "fail", 0,
     "DVDVIDEO", "DVDVIDEO", None,
     "0000", "0000", None,
     "unknown", "unknown", None,
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 0, "MakeMKV failed: no valid disc structure found", "dvd",
     "DVDVIDEO", 1, 0, 11000, 99000,
     "/home/arm/media/unidentified/DVDVIDEO", "170000000005", 0, 0, 0),

    # 6: Completed bluray series — user corrected title
    (VER, "f6a1b2c3d4e50006", "GAME_OF_THRONES_S1.log",
     (now - timedelta(days=1, hours=2)).isoformat(), (now - timedelta(days=1)).isoformat(),
     "2:05:18", "success", 12,
     "Game of Thrones", "GAME_OF_THRONES_S1", "Game of Thrones",
     "2011", "0000", "2011",
     "series", "series", "series",
     "tt0944947", None, "tt0944947",
     f"{TMDB}/1XS1oqL89opfnbLl8WnZY1O1uJx.jpg", None, f"{TMDB}/1XS1oqL89opfnbLl8WnZY1O1uJx.jpg",
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "bluray",
     "GAME_OF_THRONES_S1", 1, 0, 10500, 99500,
     "/home/arm/media/tv/Game of Thrones (2011)", "170000000006", 0, 0, 0),

    # 7: Completed dvd movie
    (VER, "a7b8c9d0e1f20007", "BLADE_RUNNER_2049.log",
     (now - timedelta(days=2, hours=4)).isoformat(), (now - timedelta(days=2, hours=1)).isoformat(),
     "2:55:41", "success", 15,
     "Blade Runner 2049", "Blade Runner 2049", None,
     "2017", "2017", None,
     "movie", "movie", None,
     "tt1856101", "tt1856101", None,
     f"{TMDB}/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg", f"{TMDB}/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg", None,
     "/dev/sr1", "/mnt/dev/sr1", 1, None, "dvd",
     "BLADE_RUNNER_2049", 1, 0, 10100, 99900,
     "/home/arm/media/movies/Blade Runner 2049 (2017)", "170000000007", 0, 0, 0),

    # 8: Waiting for user input — unidentified dvd (prime candidate for title search!)
    (VER, "b8c9d0e1f2a30008", "MYSTERY_DISC.log",
     (now - timedelta(seconds=15)).isoformat(), None,
     None, "waiting", 5,
     "MYSTERY_DISC", "MYSTERY_DISC", None,
     "0000", "0000", None,
     "unknown", "unknown", None,
     None, None, None,
     None, None, None,
     "/dev/sr2", "/mnt/dev/sr2", 0, None, "dvd",
     "MYSTERY_DISC", 0, 0, 14800, 97000,
     "/home/arm/media/unidentified/MYSTERY_DISC", "170000000008", 0, 0, 0),

    # 9: Music CD — completed
    (VER, "c9d0e1f2a3b40009", "Abbey_Road.log",
     (now - timedelta(days=3)).isoformat(), (now - timedelta(days=3) + timedelta(minutes=25)).isoformat(),
     "0:25:10", "success", 17,
     "Abbey Road", "Abbey Road", None,
     "1969", "1969", None,
     "unknown", "unknown", None,
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "music",
     "ABBEY_ROAD", 1, 0, 9500, 100500,
     "/home/arm/media/music/Abbey Road", "170000000009", 0, 0, 0),

    # 10: Completed bluray movie — Dune
    (VER, "d0e1f2a3b4c50010", "DUNE_2021.log",
     (now - timedelta(hours=12)).isoformat(), (now - timedelta(hours=9)).isoformat(),
     "2:35:08", "success", 28,
     "Dune", "Dune", None,
     "2021", "2021", None,
     "movie", "movie", None,
     "tt1160419", "tt1160419", None,
     f"{TMDB}/d5NXSklXo0qyIYkgV94XAgMIckC.jpg", f"{TMDB}/d5NXSklXo0qyIYkgV94XAgMIckC.jpg", None,
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "bluray",
     "DUNE_2021", 1, 0, 13000, 97000,
     "/home/arm/media/movies/Dune (2021)", "170000000010", 0, 0, 0),

    # 11: Waiting — well-identified bluray movie with poster (disc review demo)
    (VER, "e1f2a3b4c5d60011", "The_Dark_Knight_2008.log",
     (now - timedelta(seconds=10)).isoformat(), None,
     None, "waiting", 8,
     "The Dark Knight", "The Dark Knight", None,
     "2008", "2008", None,
     "movie", "movie", None,
     "tt0468569", "tt0468569", None,
     f"{TMDB}/qJ2tW6WMUDux911BTUgMe1VT0u0.jpg", f"{TMDB}/qJ2tW6WMUDux911BTUgMe1VT0u0.jpg", None,
     "/dev/sr0", "/mnt/dev/sr0", 0, None, "bluray",
     "THE_DARK_KNIGHT", 0, 0, 15200, 96800,
     "/home/arm/media/movies/The Dark Knight (2008)", "170000000011", 0, 1, 1),

    # 12: Waiting — unidentified dvd (great for testing IMDb ID search)
    (VER, "f2a3b4c5d6e70012", "DISC_UNKNOWN_01.log",
     (now - timedelta(minutes=5)).isoformat(), None,
     None, "waiting", 3,
     "DISC_UNKNOWN_01", "DISC_UNKNOWN_01", None,
     "0000", "0000", None,
     "unknown", "unknown", None,
     None, None, None,
     None, None, None,
     "/dev/sr1", "/mnt/dev/sr1", 0, None, "dvd",
     "DISC_UNKNOWN_01", 0, 0, 15300, 96700,
     "/home/arm/media/unidentified/DISC_UNKNOWN_01", "170000000012", 0, 0, 0),

    # 13: Currently ripping — bluray movie
    (VER, "a3b4c5d6e7f80013", "FIGHT_CLUB.log",
     (now - timedelta(minutes=20)).isoformat(), None,
     None, "ripping", 12,
     "Fight Club", "Fight Club", None,
     "1999", "1999", None,
     "movie", "movie", None,
     "tt0137523", "tt0137523", None,
     f"{TMDB}/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg", f"{TMDB}/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg", None,
     "/dev/sr2", "/mnt/dev/sr2", 1, None, "bluray",
     "FIGHT_CLUB", 0, 0, 15400, 96600,
     "/home/arm/media/movies/Fight Club (1999)", "170000000013", 0, 0, 0),

    # 14: Waiting — MULTI-TITLE dvd (double feature, fully configured per-track metadata)
    (VER, "b4c5d6e7f8a90014", "DOUBLE_FEATURE_DISC.log",
     (now - timedelta(minutes=10)).isoformat(), None,
     None, "waiting", 6,
     "DOUBLE_FEATURE", "DOUBLE_FEATURE", None,
     "0000", "0000", None,
     "unknown", "unknown", None,
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 0, None, "dvd",
     "DOUBLE_FEATURE", 0, 0, 15500, 96500,
     "/home/arm/media/unidentified/DOUBLE_FEATURE", "170000000014", 0, 0, 1),

    # 15: Waiting — MULTI-TITLE bluray (partial: only some tracks have overrides)
    (VER, "c5d6e7f8a9b00015", "JOHN_WATERS_COLLECTION.log",
     (now - timedelta(minutes=8)).isoformat(), None,
     None, "waiting", 8,
     "John Waters Collection", "JOHN_WATERS_COLLECTION", "John Waters Collection",
     "1994", "0000", "1994",
     "movie", "unknown", "movie",
     None, None, None,
     None, None, None,
     "/dev/sr1", "/mnt/dev/sr1", 0, None, "bluray",
     "JOHN_WATERS_COLLECTION", 0, 0, 15600, 96400,
     "/home/arm/media/movies/John Waters Collection (1994)", "170000000015", 0, 0, 1),

    # 16: Completed — MULTI-TITLE dvd (multi_title flag set, no per-track overrides yet)
    (VER, "d6e7f8a9b0c10016", "HORROR_DOUBLE.log",
     (now - timedelta(hours=6)).isoformat(), (now - timedelta(hours=4)).isoformat(),
     "2:10:00", "success", 4,
     "Horror Double Feature", "HORROR_DOUBLE", "Horror Double Feature",
     "2005", "0000", "2005",
     "movie", "unknown", "movie",
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "dvd",
     "HORROR_DOUBLE", 1, 0, 15700, 96300,
     "/home/arm/media/movies/Horror Double Feature (2005)", "170000000016", 0, 0, 0),
]

for j in jobs:
    c.execute(f"INSERT INTO job ({col_str}) VALUES ({placeholders})", j)
print(f"Inserted {len(jobs)} jobs")

# --- Configs (one per job) ---
for job_id in range(1, 17):
    c.execute(
        """INSERT INTO config (job_id, ARM_CHECK_UDF, GET_VIDEO_TITLE, SKIP_TRANSCODE,
           VIDEOTYPE, MINLENGTH, MAXLENGTH, MANUAL_WAIT, MANUAL_WAIT_TIME,
           TRANSCODE_PATH, RAW_PATH, COMPLETED_PATH, INSTALLPATH, LOGPATH, LOGLEVEL,
           DBFILE, RIPMETHOD, MAINFEATURE, DEST_EXT, NOTIFY_RIP, NOTIFY_TRANSCODE)
           VALUES (?,1,1,0,'auto','120','99999',1,120,
           '/home/arm/media/transcode','/home/arm/media/raw','/home/arm/media/completed',
           '/opt/arm','/home/arm/logs','DEBUG','/home/arm/db/arm.db','mkv',0,'mkv',1,1)""",
        (job_id,),
    )
print("Inserted 16 configs")

# --- Set multi_title flag on jobs 14, 15, 16 ---
for job_id in (14, 15, 16):
    c.execute("UPDATE job SET multi_title = 1 WHERE job_id = ?", (job_id,))
print("Set multi_title=1 on jobs 14, 15, 16")

# --- Tracks ---
tracks = [
    # (job_id, track#, length_sec, aspect, fps, main, basename, filename, status)
    # Job 1 — The Matrix
    (1, "01", 8166, "16:9", 23.976, 1, "t00.mkv", "The_Matrix_t00.mkv", "success"),
    (1, "02", 120,  "16:9", 23.976, 0, "t01.mkv", "The_Matrix_t01.mkv", "success"),
    (1, "03", 85,   "16:9", 23.976, 0, "t02.mkv", "The_Matrix_t02.mkv", "success"),
    (1, "04", 1800, "16:9", 23.976, 0, "t03.mkv", "The_Matrix_t03.mkv", "success"),
    (1, "05", 45,   "16:9", 23.976, 0, "t04.mkv", "The_Matrix_t04.mkv", "success"),
    # Job 2 — Inception
    (2, "01", 8880, "2.39:1", 23.976, 1, "t00.mkv", "Inception_t00.mkv", "success"),
    (2, "02", 360,  "16:9",  29.97,  0, "t01.mkv", "Inception_t01.mkv", "success"),
    (2, "03", 180,  "16:9",  29.97,  0, "t02.mkv", "Inception_t02.mkv", "success"),
    (2, "04", 90,   "16:9",  29.97,  0, "t03.mkv", "Inception_t03.mkv", "success"),
    # Job 3 — Interstellar (ripping)
    (3, "01", 10080, "2.39:1", 23.976, 1, "t00.mkv", "Interstellar_t00.mkv", "ripping"),
    (3, "02", 420,   "16:9",  23.976, 0, "t01.mkv", "Interstellar_t01.mkv", "success"),
    (3, "03", 240,   "16:9",  23.976, 0, "t02.mkv", "Interstellar_t02.mkv", "success"),
    (3, "04", 180,   "16:9",  23.976, 0, "t03.mkv", None, None),
    (3, "05", 600,   "16:9",  23.976, 0, "t04.mkv", None, None),
    (3, "06", 90,    "16:9",  23.976, 0, "t05.mkv", None, None),
    # Job 4 — Breaking Bad (transcoding)
    (4, "01", 3480, "16:9", 23.976, 0, "t00.mkv", "Breaking_Bad_S01E01.mkv", "transcoding"),
    (4, "02", 3420, "16:9", 23.976, 0, "t01.mkv", "Breaking_Bad_S01E02.mkv", "transcoding"),
    (4, "03", 3300, "16:9", 23.976, 0, "t02.mkv", "Breaking_Bad_S01E03.mkv", "waiting_transcode"),
    (4, "04", 3360, "16:9", 23.976, 0, "t03.mkv", "Breaking_Bad_S01E04.mkv", "waiting_transcode"),
    (4, "05", 3240, "16:9", 23.976, 0, "t04.mkv", "Breaking_Bad_S01E05.mkv", "waiting_transcode"),
    (4, "06", 3180, "16:9", 23.976, 0, "t05.mkv", "Breaking_Bad_S01E06.mkv", "waiting_transcode"),
    (4, "07", 3540, "16:9", 23.976, 0, "t06.mkv", "Breaking_Bad_S01E07.mkv", "waiting_transcode"),
    # Job 6 — Game of Thrones
    (6, "01", 3660, "16:9", 23.976, 0, "t00.mkv", "GoT_S01E01.mkv", "success"),
    (6, "02", 3360, "16:9", 23.976, 0, "t01.mkv", "GoT_S01E02.mkv", "success"),
    (6, "03", 3420, "16:9", 23.976, 0, "t02.mkv", "GoT_S01E03.mkv", "success"),
    (6, "04", 3300, "16:9", 23.976, 0, "t03.mkv", "GoT_S01E04.mkv", "success"),
    (6, "05", 3240, "16:9", 23.976, 0, "t04.mkv", "GoT_S01E05.mkv", "success"),
    (6, "06", 3180, "16:9", 23.976, 0, "t05.mkv", "GoT_S01E06.mkv", "success"),
    (6, "07", 3600, "16:9", 23.976, 0, "t06.mkv", "GoT_S01E07.mkv", "success"),
    (6, "08", 3480, "16:9", 23.976, 0, "t07.mkv", "GoT_S01E08.mkv", "success"),
    (6, "09", 3540, "16:9", 23.976, 0, "t08.mkv", "GoT_S01E09.mkv", "success"),
    (6, "10", 3900, "16:9", 23.976, 0, "t09.mkv", "GoT_S01E10.mkv", "success"),
    # Job 7 — Blade Runner 2049
    (7, "01", 9900, "2.39:1", 23.976, 1, "t00.mkv", "Blade_Runner_2049_t00.mkv", "success"),
    (7, "02", 600,  "16:9",  23.976, 0, "t01.mkv", "Blade_Runner_2049_t01.mkv", "success"),
    (7, "03", 300,  "16:9",  23.976, 0, "t02.mkv", "Blade_Runner_2049_t02.mkv", "success"),
    # Job 10 — Dune
    (10, "01", 9300, "2.39:1", 23.976, 1, "t00.mkv", "Dune_t00.mkv", "success"),
    (10, "02", 480,  "16:9",  23.976, 0, "t01.mkv", "Dune_t01.mkv", "success"),
    (10, "03", 240,  "16:9",  23.976, 0, "t02.mkv", "Dune_t02.mkv", "success"),
    (10, "04", 120,  "16:9",  23.976, 0, "t03.mkv", "Dune_t03.mkv", "success"),
    # Job 8 — Mystery Disc (waiting, unidentified)
    (8, "01", 5400, "16:9", 29.97,  0, "t00.mkv", None, None),
    (8, "02", 3600, "16:9", 29.97,  0, "t01.mkv", None, None),
    (8, "03", 120,  "16:9", 29.97,  0, "t02.mkv", None, None),
    (8, "04", 45,   "16:9", 29.97,  0, "t03.mkv", None, None),
    (8, "05", 30,   "16:9", 29.97,  0, "t04.mkv", None, None),
    # Job 11 — The Dark Knight (waiting, well-identified bluray)
    (11, "01", 9120, "2.39:1", 23.976, 1, "t00.mkv", "The_Dark_Knight_t00.mkv", None),
    (11, "02", 780,  "16:9",  23.976, 0, "t01.mkv", "The_Dark_Knight_t01.mkv", None),
    (11, "03", 420,  "16:9",  23.976, 0, "t02.mkv", "The_Dark_Knight_t02.mkv", None),
    (11, "04", 240,  "16:9",  23.976, 0, "t03.mkv", "The_Dark_Knight_t03.mkv", None),
    (11, "05", 180,  "16:9",  23.976, 0, "t04.mkv", "The_Dark_Knight_t04.mkv", None),
    (11, "06", 90,   "16:9",  23.976, 0, "t05.mkv", "The_Dark_Knight_t05.mkv", None),
    (11, "07", 45,   "16:9",  23.976, 0, "t06.mkv", "The_Dark_Knight_t06.mkv", None),
    (11, "08", 30,   "16:9",  23.976, 0, "t07.mkv", "The_Dark_Knight_t07.mkv", None),
    # Job 12 — Unknown disc (waiting, unidentified)
    (12, "01", 6300, "16:9", 29.97, 0, "t00.mkv", None, None),
    (12, "02", 1800, "16:9", 29.97, 0, "t01.mkv", None, None),
    (12, "03", 60,   "16:9", 29.97, 0, "t02.mkv", None, None),
    # Job 13 — Fight Club (ripping)
    (13, "01", 8160, "2.39:1", 23.976, 1, "t00.mkv", "Fight_Club_t00.mkv", "ripping"),
    (13, "02", 360,  "16:9",  23.976, 0, "t01.mkv", "Fight_Club_t01.mkv", "success"),
    (13, "03", 180,  "16:9",  23.976, 0, "t02.mkv", "Fight_Club_t02.mkv", "success"),
    (13, "04", 120,  "16:9",  23.976, 0, "t03.mkv", None, None),
    (13, "05", 90,   "16:9",  23.976, 0, "t04.mkv", None, None),
    # Job 14 — Double Feature DVD (multi-title, fully configured)
    (14, "01", 5700, "16:9", 29.97, 1, "t00.mkv", "title_t00.mkv", None),
    (14, "02", 5400, "16:9", 29.97, 1, "t01.mkv", "title_t01.mkv", None),
    (14, "03", 120,  "16:9", 29.97, 0, "t02.mkv", "title_t02.mkv", None),
    (14, "04", 90,   "16:9", 29.97, 0, "t03.mkv", "title_t03.mkv", None),
    (14, "05", 45,   "16:9", 29.97, 0, "t04.mkv", "title_t04.mkv", None),
    (14, "06", 30,   "16:9", 29.97, 0, "t05.mkv", "title_t05.mkv", None),
    # Job 15 — John Waters Collection (multi-title, partial overrides)
    (15, "01", 5280, "16:9", 23.976, 1, "t00.mkv", "title_t00.mkv", None),
    (15, "02", 5160, "16:9", 23.976, 1, "t01.mkv", "title_t01.mkv", None),
    (15, "03", 600,  "16:9", 23.976, 0, "t02.mkv", "title_t02.mkv", None),
    (15, "04", 420,  "16:9", 23.976, 0, "t03.mkv", "title_t03.mkv", None),
    (15, "05", 180,  "16:9", 23.976, 0, "t04.mkv", "title_t04.mkv", None),
    (15, "06", 90,   "16:9", 23.976, 0, "t05.mkv", "title_t05.mkv", None),
    (15, "07", 45,   "16:9", 23.976, 0, "t06.mkv", "title_t06.mkv", None),
    (15, "08", 30,   "16:9", 23.976, 0, "t07.mkv", "title_t07.mkv", None),
    # Job 16 — Horror Double Feature (multi-title, completed, no per-track overrides)
    (16, "01", 5400, "16:9", 29.97, 1, "t00.mkv", "title_t00.mkv", "success"),
    (16, "02", 5100, "16:9", 29.97, 1, "t01.mkv", "title_t01.mkv", "success"),
    (16, "03", 180,  "16:9", 29.97, 0, "t02.mkv", "title_t02.mkv", "success"),
    (16, "04", 60,   "16:9", 29.97, 0, "t03.mkv", "title_t03.mkv", "success"),
]

for t in tracks:
    ripped = 1 if t[8] == "success" else 0
    c.execute(
        """INSERT INTO track (job_id, track_number, length, aspect_ratio, fps,
           main_feature, basename, filename, ripped, status, source)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7], ripped, t[8], "mkv"),
    )
print(f"Inserted {len(tracks)} tracks")

# --- Per-track metadata for multi-title discs ---
# Job 14 — Double Feature: both main features have per-track titles
per_track_meta = [
    # (job_id, track_number, title, year, imdb_id, poster_url, video_type)
    (14, "01", "Serial Mom", "1994", "tt0111127",
     f"{TMDB}/xVWGkqMpJPAkyND9sJZ4lnSHj8k.jpg", "movie"),
    (14, "02", "Pecker", "1998", "tt0126604",
     f"{TMDB}/aYOo6A0qY1SYoTO4hFmMRYxMQPT.jpg", "movie"),
    # Job 15 — John Waters Collection: only first track has override (partial)
    (15, "01", "Serial Mom", "1994", "tt0111127",
     f"{TMDB}/xVWGkqMpJPAkyND9sJZ4lnSHj8k.jpg", "movie"),
    # Track 02 has NO override — will inherit job-level metadata
]
for pm in per_track_meta:
    c.execute(
        """UPDATE track SET title=?, year=?, imdb_id=?, poster_url=?, video_type=?
           WHERE job_id=? AND track_number=?""",
        (pm[2], pm[3], pm[4], pm[5], pm[6], pm[0], pm[1]),
    )
print(f"Set per-track metadata on {len(per_track_meta)} tracks")

# --- Notifications ---
notifs = [
    ("Job: 1 completed", "The Matrix (1999) ripped successfully",
     now - timedelta(hours=1, minutes=20)),
    ("Job: 2 was updated", "Title: INCEPTION_DISC1 (0000) was updated to Inception (2010)",
     now - timedelta(hours=4)),
    ("Job: 2 completed", "Inception (2010) ripped successfully",
     now - timedelta(hours=3, minutes=45)),
    ("Job: 3 started", "Interstellar (2014) rip started on /dev/sr0",
     now - timedelta(minutes=35)),
    ("Job: 4 transcoding", "Breaking Bad (2008) transcoding started",
     now - timedelta(hours=1)),
    ("Job: 5 failed", "DVDVIDEO: MakeMKV failed: no valid disc structure found",
     now - timedelta(hours=7, minutes=30)),
    ("Job: 6 completed", "Game of Thrones (2011) ripped successfully",
     now - timedelta(days=1)),
    ("Job: 8 waiting", "MYSTERY_DISC: waiting for user input on /dev/sr2",
     now - timedelta(minutes=15)),
    ("Job: 10 completed", "Dune (2021) ripped successfully",
     now - timedelta(hours=9)),
    ("Job: 11 waiting", "The Dark Knight: waiting for user input on /dev/sr0",
     now - timedelta(seconds=20)),
    ("Job: 12 waiting", "DISC_UNKNOWN_01: waiting for user input on /dev/sr1",
     now - timedelta(minutes=5)),
    ("Job: 13 started", "Fight Club (1999) rip started on /dev/sr2",
     now - timedelta(minutes=20)),
    ("Job: 14 waiting", "DOUBLE_FEATURE: multi-title disc waiting for user input on /dev/sr0",
     now - timedelta(minutes=10)),
    ("Job: 15 waiting", "John Waters Collection: multi-title disc waiting for user input on /dev/sr1",
     now - timedelta(minutes=8)),
    ("Job: 16 completed", "Horror Double Feature (2005) ripped successfully (multi-title)",
     now - timedelta(hours=4)),
]
for title, msg, t in notifs:
    c.execute(
        "INSERT INTO notifications (seen, trigger_time, title, message, cleared) VALUES (0,?,?,?,0)",
        (t.isoformat(), title, msg),
    )
print(f"Inserted {len(notifs)} notifications")

# --- Drives ---
drives = [
    ("sr0", "/mnt/dev/sr0", 11, 3, "Primary Blu-ray Drive", "manual",
     "ASUS", "BW-16D1HT", "K8N0AH123456", "USB", 1, 1, 1, "3.10", "/dev/sr0", 0),
    ("sr1", "/mnt/dev/sr1", 12, 4, "Secondary DVD Drive", "auto",
     "LG", "GH24NSD5", "LG92BF789012", "SATA", 1, 1, 0, "1.01", "/dev/sr1", 0),
    ("sr2", "/mnt/dev/sr2", 13, 8, "Third DVD Drive", "auto",
     "Pioneer", "DVR-221L", "PNRX45678901", "USB", 1, 1, 0, "2.05", "/dev/sr2", 0),
]
for d in drives:
    c.execute(
        """INSERT INTO system_drives
           (name, mount, job_id_current, job_id_previous, description, drive_mode,
            maker, model, serial, connection, read_cd, read_dvd, read_bd, firmware, location, stale)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        d,
    )
print(f"Inserted {len(drives)} drives")

conn.commit()
conn.close()
print("\nDone! Database seeded successfully.")
