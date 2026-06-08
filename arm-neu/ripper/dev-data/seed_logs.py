"""Generate realistic structured log files for all seed database jobs."""
import json
import os
import sys
from datetime import datetime, timedelta

LOG_DIR = sys.argv[1] if len(sys.argv) > 1 else "/home/arm/logs"


def entry(ts, level, logger, event, job_id=None, label=None, devpath=None, **extra):
    """Build a JSON log entry."""
    d = {"timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "level": level,
         "logger": logger, "event": event}
    if job_id is not None:
        d["job_id"] = job_id
    if label is not None:
        d["label"] = label
    if devpath is not None:
        d["devpath"] = devpath
    d.update(extra)
    return json.dumps(d)


def write_log(filename, lines):
    path = os.path.join(LOG_DIR, filename)
    with open(path, "w") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"  {filename} ({len(lines)} entries)")


now = datetime.now()


# --- Helper generators for common patterns ---

def movie_success_log(filename, job_id, label, title, year, imdb, devpath,
                      disc_type, num_titles, main_len, total_gb, duration,
                      start_offset_hours):
    """Generate a complete success log for a movie rip."""
    t = now - timedelta(hours=start_offset_hours)
    lines = [
        entry(t, "info", "arm.ripper.main", f"Processing new disc on {devpath}",
              job_id, label, devpath),
        entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
              f"Disc identified as {disc_type.title()}", job_id, label, devpath),
        entry(t + timedelta(minutes=1, seconds=30), "info", "arm.ripper.identify",
              f"Label: {label}", job_id, label, devpath),
        entry(t + timedelta(minutes=2), "info", "arm.ripper.identify",
              f"OMDb lookup: {title} ({year}) {imdb}", job_id, label, devpath),
        entry(t + timedelta(minutes=2, seconds=30), "info", "arm.ripper.identify",
              "Video type: movie", job_id, label, devpath),
        entry(t + timedelta(minutes=3), "debug", "arm.ripper.makemkv",
              "MakeMKV scan starting", job_id, label, devpath),
        entry(t + timedelta(minutes=4), "info", "arm.ripper.makemkv",
              f"Found {num_titles} titles on disc", job_id, label, devpath),
        entry(t + timedelta(minutes=5), "info", "arm.ripper.makemkv",
              f"Title 00 - {main_len} (main feature)", job_id, label, devpath),
        entry(t + timedelta(minutes=6), "debug", "arm.ripper.makemkv",
              f"Skipping {num_titles - 3} short titles (< 600s)", job_id, label, devpath),
        entry(t + timedelta(minutes=7), "info", "arm.ripper.makemkv",
              f"Ripping title 00 to /home/arm/media/raw/{title.replace(' ', '_')}_{year}/",
              job_id, label, devpath),
    ]
    end_offset = int(start_offset_hours * 60 * 0.6)
    lines += [
        entry(t + timedelta(minutes=end_offset), "info", "arm.ripper.makemkv",
              f"Rip complete. 3 titles, {total_gb} GB total", job_id, label, devpath),
        entry(t + timedelta(minutes=end_offset + 1), "info", "arm.ripper.main",
              "SKIP_TRANSCODE is enabled", job_id, label, devpath),
        entry(t + timedelta(minutes=end_offset + 2), "info", "arm.ripper.notify",
              "Sending notification: Rip complete", job_id, label, devpath),
        entry(t + timedelta(minutes=end_offset + 3), "info", "arm.ripper.main",
              f"Job completed successfully. Duration: {duration}", job_id, label, devpath),
    ]
    return lines


def series_success_log(filename, job_id, label, title, year, imdb, devpath,
                       disc_type, num_titles, eps, total_gb, duration,
                       start_offset_hours):
    """Generate a complete success log for a series rip."""
    t = now - timedelta(hours=start_offset_hours)
    lines = [
        entry(t, "info", "arm.ripper.main", f"Processing new disc on {devpath}",
              job_id, label, devpath),
        entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
              f"Disc identified as {disc_type.title()}", job_id, label, devpath),
        entry(t + timedelta(minutes=2), "info", "arm.ripper.identify",
              f"OMDb lookup: {title} ({year}) {imdb}", job_id, label, devpath),
        entry(t + timedelta(minutes=2, seconds=30), "info", "arm.ripper.identify",
              "Video type: series", job_id, label, devpath),
        entry(t + timedelta(minutes=3), "info", "arm.ripper.makemkv",
              f"Found {num_titles} titles on disc", job_id, label, devpath),
        entry(t + timedelta(minutes=4), "info", "arm.ripper.makemkv",
              f"Ripping {eps} titles matching length criteria", job_id, label, devpath),
    ]
    end_offset = int(start_offset_hours * 60 * 0.7)
    lines += [
        entry(t + timedelta(minutes=end_offset), "info", "arm.ripper.makemkv",
              f"Rip complete. {eps} titles, {total_gb} GB total", job_id, label, devpath),
        entry(t + timedelta(minutes=end_offset + 1), "info", "arm.ripper.main",
              "SKIP_TRANSCODE is enabled", job_id, label, devpath),
        entry(t + timedelta(minutes=end_offset + 2), "info", "arm.ripper.notify",
              "Sending notification: Rip complete", job_id, label, devpath),
        entry(t + timedelta(minutes=end_offset + 3), "info", "arm.ripper.main",
              f"Job completed successfully. Duration: {duration}", job_id, label, devpath),
    ]
    return lines


def ripping_log(job_id, label, title, year, devpath, disc_type, num_titles,
                start_offset_min):
    """Generate an in-progress ripping log."""
    t = now - timedelta(minutes=start_offset_min)
    return [
        entry(t, "info", "arm.ripper.main", f"Processing new disc on {devpath}",
              job_id, label, devpath),
        entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
              f"Disc identified as {disc_type.title()}", job_id, label, devpath),
        entry(t + timedelta(minutes=2), "info", "arm.ripper.identify",
              f"Label: {label}", job_id, label, devpath),
        entry(t + timedelta(minutes=2, seconds=30), "info", "arm.ripper.identify",
              f"OMDb lookup: {title} ({year})", job_id, label, devpath),
        entry(t + timedelta(minutes=3), "debug", "arm.ripper.makemkv",
              "MakeMKV scan starting", job_id, label, devpath),
        entry(t + timedelta(minutes=4), "info", "arm.ripper.makemkv",
              f"Found {num_titles} titles on disc", job_id, label, devpath),
        entry(t + timedelta(minutes=5), "info", "arm.ripper.makemkv",
              "Ripping title 00 (main feature)", job_id, label, devpath),
    ]


def waiting_log(job_id, label, devpath, disc_type, identified=True, title=None,
                year=None, imdb=None, start_offset_min=5):
    """Generate a waiting-for-review log."""
    t = now - timedelta(minutes=start_offset_min)
    lines = [
        entry(t, "info", "arm.ripper.main", f"Processing new disc on {devpath}",
              job_id, label, devpath),
        entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
              f"Disc identified as {disc_type.title()}", job_id, label, devpath),
        entry(t + timedelta(seconds=90), "info", "arm.ripper.identify",
              f"Label: {label}", job_id, label, devpath),
    ]
    if identified and title:
        lines.append(entry(t + timedelta(minutes=2), "info", "arm.ripper.identify",
                           f"OMDb lookup: {title} ({year}) {imdb or ''}", job_id, label, devpath))
    else:
        lines.append(entry(t + timedelta(minutes=2), "warning", "arm.ripper.identify",
                           "OMDb lookup failed: no match found", job_id, label, devpath))
    lines += [
        entry(t + timedelta(minutes=3), "info", "arm.ripper.main",
              "MANUAL_WAIT is enabled, waiting for user input", job_id, label, devpath),
        entry(t + timedelta(minutes=3, seconds=1), "info", "arm.ripper.main",
              f"Waiting for user review on {devpath}", job_id, label, devpath),
    ]
    return lines


def music_success_log(job_id, label, title, year, devpath, num_tracks, duration,
                      start_offset_hours):
    """Generate a music CD rip success log."""
    t = now - timedelta(hours=start_offset_hours)
    lines = [
        entry(t, "info", "arm.ripper.main", f"Processing new disc on {devpath}",
              job_id, label, devpath),
        entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
              "Disc identified as Music CD", job_id, label, devpath),
        entry(t + timedelta(seconds=90), "info", "arm.ripper.identify",
              f"Label: {label}", job_id, label, devpath),
        entry(t + timedelta(minutes=2), "info", "arm.ripper.identify",
              f"MusicBrainz lookup: {title} ({year})", job_id, label, devpath),
        entry(t + timedelta(minutes=3), "info", "arm.ripper.music",
              f"Starting abcde rip: {num_tracks} tracks", job_id, label, devpath),
    ]
    # Add a few track progress entries
    for i in range(1, min(num_tracks + 1, 4)):
        lines.append(entry(t + timedelta(minutes=3 + i * 2), "debug", "arm.ripper.music",
                           f"Track {i:02d}/{num_tracks:02d} ripped", job_id, label, devpath))
    lines.append(entry(t + timedelta(minutes=3 + num_tracks * 2), "info", "arm.ripper.music",
                       f"Track {num_tracks:02d}/{num_tracks:02d} ripped", job_id, label, devpath))

    end_min = 5 + num_tracks * 2
    lines += [
        entry(t + timedelta(minutes=end_min), "info", "arm.ripper.music",
              f"abcde rip complete: {num_tracks} tracks", job_id, label, devpath),
        entry(t + timedelta(minutes=end_min + 1), "info", "arm.ripper.notify",
              "Sending notification: Rip complete", job_id, label, devpath),
        entry(t + timedelta(minutes=end_min + 2), "info", "arm.ripper.main",
              f"Job completed successfully. Duration: {duration}", job_id, label, devpath),
    ]
    return lines


# ============================================================
# Generate all log files
# ============================================================

print(f"Generating seed log files in {LOG_DIR}...")
os.makedirs(LOG_DIR, exist_ok=True)

# --- Video jobs from seed_db.py (jobs 1-13) ---

# 1: The Matrix — success, bluray
write_log("The_Matrix_1999.log", movie_success_log(
    "The_Matrix_1999.log", 1, "THE_MATRIX", "The Matrix", "1999", "tt0133093",
    "/dev/sr0", "Blu-ray", 24, "2:16:18", 32.1, "1:40:12", 3))

# 2: Inception — success, dvd, user-corrected title
t = now - timedelta(hours=5)
write_log("Inception_2010.log", [
    entry(t, "info", "arm.ripper.main", "Processing new disc on /dev/sr1",
          2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
          "Disc identified as DVD", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(seconds=90), "info", "arm.ripper.identify",
          "Label: INCEPTION_DISC1", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=2), "warning", "arm.ripper.identify",
          "OMDb lookup: no exact match for INCEPTION_DISC1", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=2, seconds=30), "info", "arm.ripper.identify",
          "Video type: movie (unverified)", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=3), "info", "arm.ripper.main",
          "MANUAL_WAIT is enabled, waiting for user input", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=15), "info", "arm.ripper.main",
          "User updated title: Inception (2010) tt1375666", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=16), "info", "arm.ripper.makemkv",
          "Found 18 titles on disc", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=17), "info", "arm.ripper.makemkv",
          "Ripping title 00 (main feature)", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=60), "info", "arm.ripper.makemkv",
          "Rip complete. 4 titles, 7.2 GB total", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=61), "info", "arm.ripper.main",
          "SKIP_TRANSCODE is enabled", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=62), "info", "arm.ripper.notify",
          "Sending notification: Rip complete", 2, "INCEPTION_DISC1", "/dev/sr1"),
    entry(t + timedelta(minutes=63), "info", "arm.ripper.main",
          "Job completed successfully. Duration: 1:15:33", 2, "INCEPTION_DISC1", "/dev/sr1"),
])

# 3: Interstellar — ripping, bluray
write_log("INTERSTELLAR.log", ripping_log(
    3, "INTERSTELLAR", "Interstellar", "2014", "/dev/sr0", "Blu-ray", 31, 35))

# 4: Breaking Bad S1D1 — transcoding, dvd series
t = now - timedelta(hours=1, minutes=10)
write_log("BREAKING_BAD_S1D1.log", [
    entry(t, "info", "arm.ripper.main", "Processing new disc on /dev/sr1",
          4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
          "Disc identified as DVD", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=2), "info", "arm.ripper.identify",
          "OMDb lookup: Breaking Bad (2008) tt0903747", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=2, seconds=30), "info", "arm.ripper.identify",
          "Video type: series", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=3), "info", "arm.ripper.makemkv",
          "Found 14 titles on disc", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=4), "info", "arm.ripper.makemkv",
          "Ripping 7 titles matching length criteria", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=35), "info", "arm.ripper.makemkv",
          "Rip complete. 7 titles, 18.4 GB total", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=36), "info", "arm.ripper.main",
          "Starting transcoding", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=37), "info", "arm.ripper.handbrake",
          "Transcoding title 01/07: Breaking_Bad_S01E01.mkv", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
    entry(t + timedelta(minutes=50), "info", "arm.ripper.handbrake",
          "Transcoding title 02/07: Breaking_Bad_S01E02.mkv", 4, "BREAKING_BAD_S1D1", "/dev/sr1"),
])

# 5: DVDVIDEO — failed, unidentified
t = now - timedelta(hours=8)
write_log("DVDVIDEO_2025.log", [
    entry(t, "info", "arm.ripper.main", "Processing new disc on /dev/sr0",
          5, "DVDVIDEO", "/dev/sr0"),
    entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
          "Disc identified as DVD", 5, "DVDVIDEO", "/dev/sr0"),
    entry(t + timedelta(seconds=90), "info", "arm.ripper.identify",
          "Label: DVDVIDEO", 5, "DVDVIDEO", "/dev/sr0"),
    entry(t + timedelta(minutes=2), "warning", "arm.ripper.identify",
          "OMDb lookup failed: no match found", 5, "DVDVIDEO", "/dev/sr0"),
    entry(t + timedelta(minutes=3), "info", "arm.ripper.identify",
          "Video type: unknown - defaulting to movie", 5, "DVDVIDEO", "/dev/sr0"),
    entry(t + timedelta(minutes=4), "debug", "arm.ripper.makemkv",
          "MakeMKV scan starting", 5, "DVDVIDEO", "/dev/sr0"),
    entry(t + timedelta(minutes=10), "error", "arm.ripper.makemkv",
          "MakeMKV failed: no valid disc structure found", 5, "DVDVIDEO", "/dev/sr0"),
    entry(t + timedelta(minutes=11), "error", "arm.ripper.main",
          "Job failed with errors. Duration: 0:30:05", 5, "DVDVIDEO", "/dev/sr0"),
    entry(t + timedelta(minutes=12), "info", "arm.ripper.notify",
          "Sending notification: Rip FAILED - DVDVIDEO", 5, "DVDVIDEO", "/dev/sr0"),
])

# 6: Game of Thrones S1 — success, bluray series
write_log("GAME_OF_THRONES_S1.log", series_success_log(
    "GAME_OF_THRONES_S1.log", 6, "GAME_OF_THRONES_S1",
    "Game of Thrones", "2011", "tt0944947", "/dev/sr0",
    "Blu-ray", 20, 10, 38.5, "2:05:18", 26))

# 7: Blade Runner 2049 — success, dvd
write_log("BLADE_RUNNER_2049.log", movie_success_log(
    "BLADE_RUNNER_2049.log", 7, "BLADE_RUNNER_2049",
    "Blade Runner 2049", "2017", "tt1856101", "/dev/sr1",
    "DVD", 15, "2:44:22", 8.1, "2:55:41", 52))

# 8: Mystery disc — waiting, unidentified
write_log("MYSTERY_DISC.log", waiting_log(
    8, "MYSTERY_DISC", "/dev/sr2", "DVD", identified=False, start_offset_min=15))

# 9: Abbey Road (music, completed from seed_db — different from seed_music version)
write_log("Abbey_Road.log", music_success_log(
    9, "ABBEY_ROAD", "Abbey Road", "1969", "/dev/sr0", 17, "0:25:10", 72))

# 10: Dune — success, bluray
write_log("DUNE_2021.log", movie_success_log(
    "DUNE_2021.log", 10, "DUNE_2021", "Dune", "2021", "tt1160419",
    "/dev/sr0", "Blu-ray", 28, "2:35:08", 45.2, "2:35:08", 12))

# 11: The Dark Knight — waiting, well-identified bluray
write_log("The_Dark_Knight_2008.log", waiting_log(
    11, "THE_DARK_KNIGHT", "/dev/sr0", "Blu-ray", identified=True,
    title="The Dark Knight", year="2008", imdb="tt0468569", start_offset_min=10))

# 12: Unknown disc — waiting, unidentified
write_log("DISC_UNKNOWN_01.log", waiting_log(
    12, "DISC_UNKNOWN_01", "/dev/sr1", "DVD", identified=False, start_offset_min=5))

# 13: Fight Club — ripping, bluray
write_log("FIGHT_CLUB.log", ripping_log(
    13, "FIGHT_CLUB", "Fight Club", "1999", "/dev/sr2", "Blu-ray", 12, 20))

# 14: Dune Part Two — waiting (from DB, not in seed scripts)
write_log("Dune_Part_Two.log", waiting_log(
    14, "DUNE_PART_TWO", "/dev/sr0", "Blu-ray", identified=True,
    title="Dune: Part Two", year="2024", imdb="tt15239678", start_offset_min=8))

# --- Music jobs from seed_music.py ---

# Dark Side of the Moon — success
write_log("Dark_Side_of_the_Moon.log", music_success_log(
    16, "DARK_SIDE_OF_THE_MOON", "Dark Side of the Moon", "1973",
    "/dev/sr0", 10, "0:22:15", 123))

# Rumours — success
write_log("Rumours.log", music_success_log(
    17, "RUMOURS", "Rumours", "1977", "/dev/sr1", 11, "0:20:05", 97))

# OK Computer — success
write_log("OK_Computer.log", music_success_log(
    18, "OK_COMPUTER", "OK Computer", "1997", "/dev/sr0", 12, "0:28:10", 54))

# Kind of Blue — success
write_log("Kind_of_Blue.log", music_success_log(
    19, "KIND_OF_BLUE", "Kind of Blue", "1959", "/dev/sr0", 5, "0:18:30", 32))

# Nevermind — ripping
t = now - timedelta(minutes=8)
write_log("Nevermind.log", [
    entry(t, "info", "arm.ripper.main", "Processing new disc on /dev/sr1",
          20, "NEVERMIND", "/dev/sr1"),
    entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
          "Disc identified as Music CD", 20, "NEVERMIND", "/dev/sr1"),
    entry(t + timedelta(seconds=90), "info", "arm.ripper.identify",
          "MusicBrainz lookup: Nevermind (1991)", 20, "NEVERMIND", "/dev/sr1"),
    entry(t + timedelta(minutes=2), "info", "arm.ripper.music",
          "Starting abcde rip: 13 tracks", 20, "NEVERMIND", "/dev/sr1"),
    entry(t + timedelta(minutes=3), "debug", "arm.ripper.music",
          "Track 01/13 ripped", 20, "NEVERMIND", "/dev/sr1"),
    entry(t + timedelta(minutes=4), "debug", "arm.ripper.music",
          "Track 02/13 ripped", 20, "NEVERMIND", "/dev/sr1"),
    entry(t + timedelta(minutes=5), "debug", "arm.ripper.music",
          "Track 03/13 ripped", 20, "NEVERMIND", "/dev/sr1"),
    entry(t + timedelta(minutes=6), "debug", "arm.ripper.music",
          "Track 04/13 ripped", 20, "NEVERMIND", "/dev/sr1"),
    entry(t + timedelta(minutes=7), "info", "arm.ripper.music",
          "Track 05/13 ripping...", 20, "NEVERMIND", "/dev/sr1"),
])

# music_cd — failed
t = now - timedelta(hours=20)
write_log("music_cd.log", [
    entry(t, "info", "arm.ripper.main", "Processing new disc on /dev/sr0",
          21, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
          "Disc identified as Music CD", 21, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(seconds=90), "info", "arm.ripper.identify",
          "Label: AUDIO_CD", 21, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(minutes=2), "warning", "arm.ripper.identify",
          "MusicBrainz disc ID lookup failed", 21, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(minutes=3), "info", "arm.ripper.music",
          "Starting abcde rip", 21, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(minutes=4), "error", "arm.ripper.music",
          "abcde: cdparanoia could not read disc — possible scratched or damaged media",
          21, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(minutes=5), "error", "arm.ripper.main",
          "Job failed with errors. Duration: 0:05:02", 21, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(minutes=5, seconds=30), "info", "arm.ripper.notify",
          "Sending notification: Rip FAILED - AUDIO_CD", 21, "AUDIO_CD", "/dev/sr0"),
])

# AUDIO_CD — waiting, unidentified music
t = now - timedelta(minutes=2)
write_log("AUDIO_CD.log", [
    entry(t, "info", "arm.ripper.main", "Processing new disc on /dev/sr0",
          23, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(seconds=30), "info", "arm.ripper.main",
          "Disc identified as Music CD", 23, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(seconds=45), "info", "arm.ripper.identify",
          "Label: AUDIO_CD", 23, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(minutes=1), "warning", "arm.ripper.identify",
          "MusicBrainz disc ID lookup failed: no match", 23, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(seconds=90), "info", "arm.ripper.main",
          "MANUAL_WAIT is enabled, waiting for user input", 23, "AUDIO_CD", "/dev/sr0"),
    entry(t + timedelta(seconds=91), "info", "arm.ripper.main",
          "Waiting for user review on /dev/sr0", 23, "AUDIO_CD", "/dev/sr0"),
])

# BACKUP_2026 — data disc success
t = now - timedelta(hours=6)
write_log("BACKUP_2026.log", [
    entry(t, "info", "arm.ripper.main", "Processing new disc on /dev/sr0",
          22, "BACKUP_2026", "/dev/sr0"),
    entry(t + timedelta(minutes=1), "info", "arm.ripper.main",
          "Disc identified as Data disc", 22, "BACKUP_2026", "/dev/sr0"),
    entry(t + timedelta(seconds=90), "info", "arm.ripper.identify",
          "Label: BACKUP_2026", 22, "BACKUP_2026", "/dev/sr0"),
    entry(t + timedelta(minutes=2), "info", "arm.ripper.identify",
          "Data disc — creating ISO backup", 22, "BACKUP_2026", "/dev/sr0"),
    entry(t + timedelta(minutes=3), "info", "arm.ripper.main",
          "Starting dd ISO copy", 22, "BACKUP_2026", "/dev/sr0"),
    entry(t + timedelta(minutes=15), "info", "arm.ripper.main",
          "ISO copy complete: 4.2 GB", 22, "BACKUP_2026", "/dev/sr0"),
    entry(t + timedelta(minutes=16), "info", "arm.ripper.notify",
          "Sending notification: Backup complete", 22, "BACKUP_2026", "/dev/sr0"),
    entry(t + timedelta(minutes=17), "info", "arm.ripper.main",
          "Job completed successfully. Duration: 0:17:22", 22, "BACKUP_2026", "/dev/sr0"),
])

print(f"\nDone! Generated log files in {LOG_DIR}")
