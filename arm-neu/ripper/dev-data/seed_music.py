"""Seed music CD jobs into the ARM database."""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("/home/arm/db/arm.db")
c = conn.cursor()

now = datetime.now()
VER = "2.8.0"

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

jobs = [
    # 11: Dark Side of the Moon — completed
    (VER, "m1a2b3c4d5e60011", "Dark_Side_of_the_Moon.log",
     (now - timedelta(days=5, hours=3)).isoformat(),
     (now - timedelta(days=5, hours=2, minutes=38)).isoformat(),
     "0:22:15", "success", 10,
     "Dark Side of the Moon", "Dark Side of the Moon", None,
     "1973", "1973", None,
     "music", "music", None,
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "music",
     "DARK_SIDE_OF_THE_MOON", 1, 0, 15100, 96100,
     "/home/arm/media/music/Dark Side of the Moon", "170000000011", 0, 0, 0),

    # 12: Rumours — completed
    (VER, "m2b3c4d5e6f70012", "Rumours.log",
     (now - timedelta(days=4, hours=1)).isoformat(),
     (now - timedelta(days=4, minutes=40)).isoformat(),
     "0:20:05", "success", 11,
     "Rumours", "Rumours", None,
     "1977", "1977", None,
     "music", "music", None,
     None, None, None,
     None, None, None,
     "/dev/sr1", "/mnt/dev/sr1", 1, None, "music",
     "RUMOURS", 1, 0, 15200, 96200,
     "/home/arm/media/music/Rumours", "170000000012", 0, 0, 0),

    # 13: OK Computer — completed
    (VER, "m3c4d5e6f7a80013", "OK_Computer.log",
     (now - timedelta(days=2, hours=6)).isoformat(),
     (now - timedelta(days=2, hours=5, minutes=32)).isoformat(),
     "0:28:10", "success", 12,
     "OK Computer", "OK Computer", None,
     "1997", "1997", None,
     "music", "music", None,
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "music",
     "OK_COMPUTER", 1, 0, 15300, 96300,
     "/home/arm/media/music/OK Computer", "170000000013", 0, 0, 0),

    # 14: Kind of Blue — completed
    (VER, "m4d5e6f7a8b90014", "Kind_of_Blue.log",
     (now - timedelta(days=1, hours=8)).isoformat(),
     (now - timedelta(days=1, hours=7, minutes=42)).isoformat(),
     "0:18:30", "success", 5,
     "Kind of Blue", "Kind of Blue", None,
     "1959", "1959", None,
     "music", "music", None,
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 1, None, "music",
     "KIND_OF_BLUE", 1, 0, 15400, 96400,
     "/home/arm/media/music/Kind of Blue", "170000000014", 0, 0, 0),

    # 15: Currently ripping a music CD
    (VER, "m5e6f7a8b9c00015", "Nevermind.log",
     (now - timedelta(minutes=8)).isoformat(), None,
     None, "ripping", 13,
     "Nevermind", "Nevermind", None,
     "1991", "1991", None,
     "music", "music", None,
     None, None, None,
     None, None, None,
     "/dev/sr1", "/mnt/dev/sr1", 1, None, "music",
     "NEVERMIND", 0, 0, 15500, 96500,
     "/home/arm/media/music/Nevermind", "170000000015", 0, 0, 0),

    # 16: Failed music rip — unidentified
    (VER, "m6f7a8b9c0d10016", "music_cd.log",
     (now - timedelta(hours=20)).isoformat(),
     (now - timedelta(hours=19, minutes=55)).isoformat(),
     "0:05:02", "fail", 0,
     "not identified", "not identified", None,
     "0000", "0000", None,
     "music", "music", None,
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 0,
     "abcde: cdparanoia could not read disc — possible scratched or damaged media",
     "music",
     "AUDIO_CD", 1, 0, 15600, 96600,
     "/home/arm/media/music/not identified", "170000000016", 0, 0, 0),

    # 17: Waiting — TOC only (MB disc ID lookup failed, only track lengths from TOC)
    (VER, "", "AUDIO_CD.log",
     (now - timedelta(minutes=2)).isoformat(), None,
     None, "waiting", 0,
     "AUDIO_CD", "AUDIO_CD", None,
     "0000", "0000", None,
     "music", "music", None,
     None, None, None,
     None, None, None,
     "/dev/sr0", "/mnt/dev/sr0", 0, None, "music",
     "AUDIO_CD", 0, 0, 15700, 96700,
     None, "170000000017", 0, 0, 0),

    # 18: Waiting — MB identified (disc ID matched, full metadata + track names)
    (VER, "ac496d60-9b3a-497c-b650-1810f0b730bf", "Abbey_Road.log",
     (now - timedelta(minutes=1)).isoformat(), None,
     None, "waiting", 17,
     "The Beatles Abbey Road", "The Beatles Abbey Road", None,
     "1969", "1969", None,
     "music", "music", None,
     None, None, None,
     "https://coverartarchive.org/release/ac496d60-9b3a-497c-b650-1810f0b730bf/front-250",
     "https://coverartarchive.org/release/ac496d60-9b3a-497c-b650-1810f0b730bf/front-250",
     None,
     "/dev/sr1", "/mnt/dev/sr1", 1, None, "music",
     "ABBEY_ROAD", 0, 0, 15800, 96800,
     None, "170000000018", 0, 0, 0),
]

job_ids = []
for j in jobs:
    c.execute(f"INSERT INTO job ({col_str}) VALUES ({placeholders})", j)
    job_ids.append(c.lastrowid)
print(f"Inserted {len(jobs)} music jobs (IDs {job_ids[0]}-{job_ids[-1]})")

# Map ordinal index to actual job_id for track references
toc_job_id = job_ids[6]     # 7th job = TOC-only waiting
abbey_job_id = job_ids[7]   # 8th job = MB-identified waiting

# Configs
for job_id in job_ids:
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

# Tracks — music CDs have audio tracks with lengths in seconds
# Uses ordinal index (0-based) into job_ids for the job_id reference
#   (job_index, track_number, length, aspect_ratio, fps, main_feature, basename, filename, status)
music_tracks = [
    # [0] Dark Side of the Moon
    (0, "01", 65, None, None, 0, "01-Speak_to_Me.flac", "01-Speak_to_Me.flac", "success"),
    (0, "02", 169, None, None, 0, "02-Breathe.flac", "02-Breathe.flac", "success"),
    (0, "03", 214, None, None, 0, "03-On_the_Run.flac", "03-On_the_Run.flac", "success"),
    (0, "04", 405, None, None, 0, "04-Time.flac", "04-Time.flac", "success"),
    (0, "05", 305, None, None, 0, "05-The_Great_Gig_in_the_Sky.flac", "05-The_Great_Gig_in_the_Sky.flac", "success"),
    (0, "06", 382, None, None, 0, "06-Money.flac", "06-Money.flac", "success"),
    (0, "07", 471, None, None, 0, "07-Us_and_Them.flac", "07-Us_and_Them.flac", "success"),
    (0, "08", 180, None, None, 0, "08-Any_Colour_You_Like.flac", "08-Any_Colour_You_Like.flac", "success"),
    (0, "09", 228, None, None, 0, "09-Brain_Damage.flac", "09-Brain_Damage.flac", "success"),
    (0, "10", 126, None, None, 0, "10-Eclipse.flac", "10-Eclipse.flac", "success"),
    # [1] Rumours
    (1, "01", 155, None, None, 0, "01-Second_Hand_News.flac", "01-Second_Hand_News.flac", "success"),
    (1, "02", 238, None, None, 0, "02-Dreams.flac", "02-Dreams.flac", "success"),
    (1, "03", 195, None, None, 0, "03-Never_Going_Back_Again.flac", "03-Never_Going_Back_Again.flac", "success"),
    (1, "04", 222, None, None, 0, "04-Dont_Stop.flac", "04-Dont_Stop.flac", "success"),
    (1, "05", 219, None, None, 0, "05-Go_Your_Own_Way.flac", "05-Go_Your_Own_Way.flac", "success"),
    (1, "06", 258, None, None, 0, "06-Songbird.flac", "06-Songbird.flac", "success"),
    (1, "07", 271, None, None, 0, "07-The_Chain.flac", "07-The_Chain.flac", "success"),
    (1, "08", 230, None, None, 0, "08-You_Make_Loving_Fun.flac", "08-You_Make_Loving_Fun.flac", "success"),
    (1, "09", 185, None, None, 0, "09-I_Dont_Want_to_Know.flac", "09-I_Dont_Want_to_Know.flac", "success"),
    (1, "10", 211, None, None, 0, "10-Oh_Daddy.flac", "10-Oh_Daddy.flac", "success"),
    (1, "11", 272, None, None, 0, "11-Gold_Dust_Woman.flac", "11-Gold_Dust_Woman.flac", "success"),
    # [2] OK Computer
    (2, "01", 284, None, None, 0, "01-Airbag.flac", "01-Airbag.flac", "success"),
    (2, "02", 369, None, None, 0, "02-Paranoid_Android.flac", "02-Paranoid_Android.flac", "success"),
    (2, "03", 293, None, None, 0, "03-Subterranean_Homesick_Alien.flac",
     "03-Subterranean_Homesick_Alien.flac", "success"),
    (2, "04", 290, None, None, 0, "04-Exit_Music.flac", "04-Exit_Music.flac", "success"),
    (2, "05", 247, None, None, 0, "05-Let_Down.flac", "05-Let_Down.flac", "success"),
    (2, "06", 264, None, None, 0, "06-Karma_Police.flac", "06-Karma_Police.flac", "success"),
    (2, "07", 79, None, None, 0, "07-Fitter_Happier.flac", "07-Fitter_Happier.flac", "success"),
    (2, "08", 229, None, None, 0, "08-Electioneering.flac", "08-Electioneering.flac", "success"),
    (2, "09", 285, None, None, 0, "09-Climbing_Up_the_Walls.flac", "09-Climbing_Up_the_Walls.flac", "success"),
    (2, "10", 263, None, None, 0, "10-No_Surprises.flac", "10-No_Surprises.flac", "success"),
    (2, "11", 318, None, None, 0, "11-Lucky.flac", "11-Lucky.flac", "success"),
    (2, "12", 338, None, None, 0, "12-The_Tourist.flac", "12-The_Tourist.flac", "success"),
    # [3] Kind of Blue
    (3, "01", 561, None, None, 0, "01-So_What.flac", "01-So_What.flac", "success"),
    (3, "02", 579, None, None, 0, "02-Freddie_Freeloader.flac", "02-Freddie_Freeloader.flac", "success"),
    (3, "03", 690, None, None, 0, "03-Blue_in_Green.flac", "03-Blue_in_Green.flac", "success"),
    (3, "04", 693, None, None, 0, "04-All_Blues.flac", "04-All_Blues.flac", "success"),
    (3, "05", 567, None, None, 0, "05-Flamenco_Sketches.flac", "05-Flamenco_Sketches.flac", "success"),
    # [4] Nevermind (ripping — partial)
    (4, "01", 301, None, None, 0, "01-Smells_Like_Teen_Spirit.flac", "01-Smells_Like_Teen_Spirit.flac", "success"),
    (4, "02", 216, None, None, 0, "02-In_Bloom.flac", "02-In_Bloom.flac", "success"),
    (4, "03", 206, None, None, 0, "03-Come_as_You_Are.flac", "03-Come_as_You_Are.flac", "success"),
    (4, "04", 176, None, None, 0, "04-Breed.flac", "04-Breed.flac", "success"),
    (4, "05", 249, None, None, 0, "05-Lithium.flac", "05-Lithium.flac", "ripping"),
    (4, "06", 157, None, None, 0, "06-Polly.flac", None, None),
    (4, "07", 211, None, None, 0, "07-Territorial_Pissings.flac", None, None),
    (4, "08", 242, None, None, 0, "08-Drain_You.flac", None, None),
    (4, "09", 218, None, None, 0, "09-Lounge_Act.flac", None, None),
    (4, "10", 156, None, None, 0, "10-Stay_Away.flac", None, None),
    (4, "11", 204, None, None, 0, "11-On_a_Plain.flac", None, None),
    (4, "12", 225, None, None, 0, "12-Something_in_the_Way.flac", None, None),
    (4, "13", 403, None, None, 0, "13-Endless_Nameless.flac", None, None),
    # [6] TOC-only waiting — track lengths from CD TOC, no names (MB lookup failed)
    #     source="TOC", basename=job.title, filename="" (empty)
    (6, "1", 247, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "2", 312, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "3", 198, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "4", 276, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "5", 341, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "6", 189, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "7", 224, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "8", 295, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "9", 263, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "10", 358, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "11", 201, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    (6, "12", 445, "n/a", 0.1, 0, "AUDIO_CD", "", None),
    # [7] MB-identified waiting — full metadata from MusicBrainz disc ID lookup
    #     source="ABCDE", basename=job.title, filename=recording title
    (7, "1", 259, "n/a", 0.1, 0, "The Beatles Abbey Road", "Come Together", None),
    (7, "2", 181, "n/a", 0.1, 0, "The Beatles Abbey Road", "Something", None),
    (7, "3", 226, "n/a", 0.1, 0, "The Beatles Abbey Road", "Maxwell's Silver Hammer", None),
    (7, "4", 165, "n/a", 0.1, 0, "The Beatles Abbey Road", "Oh! Darling", None),
    (7, "5", 193, "n/a", 0.1, 0, "The Beatles Abbey Road", "Octopus's Garden", None),
    (7, "6", 462, "n/a", 0.1, 0, "The Beatles Abbey Road", "I Want You (She's So Heavy)", None),
    (7, "7", 165, "n/a", 0.1, 0, "The Beatles Abbey Road", "Here Comes the Sun", None),
    (7, "8", 188, "n/a", 0.1, 0, "The Beatles Abbey Road", "Because", None),
    (7, "9", 260, "n/a", 0.1, 0, "The Beatles Abbey Road", "You Never Give Me Your Money", None),
    (7, "10", 206, "n/a", 0.1, 0, "The Beatles Abbey Road", "Sun King", None),
    (7, "11", 85, "n/a", 0.1, 0, "The Beatles Abbey Road", "Mean Mr. Mustard", None),
    (7, "12", 56, "n/a", 0.1, 0, "The Beatles Abbey Road", "Polythene Pam", None),
    (7, "13", 123, "n/a", 0.1, 0, "The Beatles Abbey Road", "She Came In Through the Bathroom Window", None),
    (7, "14", 246, "n/a", 0.1, 0, "The Beatles Abbey Road", "Golden Slumbers", None),
    (7, "15", 157, "n/a", 0.1, 0, "The Beatles Abbey Road", "Carry That Weight", None),
    (7, "16", 145, "n/a", 0.1, 0, "The Beatles Abbey Road", "The End", None),
    (7, "17", 26, "n/a", 0.1, 0, "The Beatles Abbey Road", "Her Majesty", None),
]

_SOURCE_BY_IDX = {6: "TOC", 7: "ABCDE"}
for t in music_tracks:
    job_id = job_ids[t[0]]
    ripped = 1 if t[8] == "success" else 0
    source = _SOURCE_BY_IDX.get(t[0], "flac")
    c.execute(
        """INSERT INTO track (job_id, track_number, length, aspect_ratio, fps,
           main_feature, basename, filename, ripped, status, source)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (job_id, t[1], t[2], t[3], t[4], t[5], t[6], t[7], ripped, t[8], source),
    )
print(f"Inserted {len(music_tracks)} tracks")

# Notifications
notifs = [
    ("Job: 11 completed", "Dark Side of the Moon (1973) ripped successfully",
     now - timedelta(days=5, hours=2, minutes=38)),
    ("Job: 12 completed", "Rumours (1977) ripped successfully",
     now - timedelta(days=4, minutes=40)),
    ("Job: 13 completed", "OK Computer (1997) ripped successfully",
     now - timedelta(days=2, hours=5, minutes=32)),
    ("Job: 14 completed", "Kind of Blue (1959) ripped successfully",
     now - timedelta(days=1, hours=7, minutes=42)),
    ("Job: 15 started", "Nevermind (1991) rip started on /dev/sr1",
     now - timedelta(minutes=8)),
    ("Job: 16 failed", "Audio CD: cdparanoia could not read disc",
     now - timedelta(hours=19, minutes=55)),
    ("Job: 17 waiting", "Audio CD on /dev/sr0 — unidentified, awaiting review",
     now - timedelta(minutes=2)),
    ("Job: 18 waiting", "The Beatles Abbey Road (1969) on /dev/sr1 — awaiting review",
     now - timedelta(minutes=1)),
]
for title, msg, t in notifs:
    c.execute(
        "INSERT INTO notifications (seen, trigger_time, title, message, cleared) VALUES (0,?,?,?,0)",
        (t.isoformat(), title, msg),
    )
print(f"Inserted {len(notifs)} notifications")

conn.commit()
conn.close()
print("Done!")
