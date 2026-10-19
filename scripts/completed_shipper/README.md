# ARM completed-rip shipper

A small sidecar that moves finished rips from an ARM ripping box to a media box
with `rsync`.  It lives next to ARM, not inside it: ARM keeps sorting rips into
`COMPLETED_PATH/movies`, `tv` and `unidentified` exactly as before, and this
script ships those folders over the network once ARM's database says the job is
done.

Typical setup: a box that only rips (here called **ts140**) and a box that runs
Plex (**t620**).  Recognized rips go straight into the Plex library folders on
the t620 at full speed.  Unidentified rips go to a staging folder on the t620
for you to rename by hand, at lower priority and with a bandwidth cap.

## What it does on every run

1. Opens ARM's sqlite database read-only and collects every `job` whose `path`
   is under `completed_path` and whose `status` is `success`.  A folder is only
   eligible if no other job (for example a re-rip of the same disc) is still
   unfinished on that same path.  Logs are never tailed.
2. Ships every eligible folder in `movies/`, then `tv/`, with
   `rsync -a --partial --remove-source-files`.  After rsync exits 0 the now-empty
   job folder is pruned.  Anything else is left in place for the next run.
3. Only when no recognized folder is pending, ships **one** eligible
   `unidentified/` folder with `--bwlimit=bwlimit_unidentified`, then goes back
   to step 1.  A movie that finishes while a long unidentified transfer is
   running therefore waits for at most that one folder.  If a recognized rsync
   failed, no unidentified transfer is started at all in that run.
4. Exits 0 when everything shipped, 1 when a transfer failed (systemd marks the
   unit failed so you notice), 2 on configuration problems or when another run
   still holds the lock.

Interrupting the script, rebooting, or a dropped link are all safe: rsync keeps
partial files, nothing local is deleted before rsync reports success, and the
next timer run simply resumes.  Running it twice in a row is a no-op.

Folders whose job is still `active`, `ripping`, `transcoding`, `waiting` or
`fail`, and folders ARM knows nothing about, are never touched.

## Requirements

* Ripping box: Python 3.6+ (stdlib only), `rsync`, `ssh` client.
* Media box: `rsync`, an ssh account that can write to the destination folders.
* Key-based ssh from the ripping box's `arm` user to the media box
  (`ssh_options` defaults to `BatchMode=yes` so a missing key fails fast
  instead of hanging on a password prompt).

## Installation (ripping box)

```bash
# 1. Config
sudo cp /opt/arm/scripts/completed_shipper/arm-completed-shipper.conf.example /etc/arm-completed-shipper.conf
sudo editor /etc/arm-completed-shipper.conf

# 2. ssh key for the arm user -> media box
sudo -u arm ssh-keygen -t ed25519 -f /home/arm/.ssh/id_ed25519 -N ''
sudo -u arm ssh-copy-id arm@t620
sudo -u arm ssh -o BatchMode=yes arm@t620 'mkdir -p /srv/plex/Movies /srv/plex/TV /srv/arm-staging/unidentified'

# 3. Try it by hand first
sudo -u arm python3 /opt/arm/scripts/completed_shipper/arm_completed_shipper.py -c /etc/arm-completed-shipper.conf --dry-run -v

# 4. systemd timer
sudo cp /opt/arm/scripts/completed_shipper/systemd/arm-completed-shipper.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now arm-completed-shipper.timer
```

The service unit assumes ARM is checked out at `/opt/arm` and runs as user
`arm`; adjust `ExecStart`, `User` and `Group` if yours differ.  Logs go to the
journal: `journalctl -u arm-completed-shipper.service`.

## Configuration

All settings live in one `[shipper]` section.  Defaults match a stock
`arm.yaml`.

| Key | Meaning |
| --- | --- |
| `db_path` | ARM's sqlite file, `DBFILE` in `arm.yaml`.  Read-only. |
| `completed_path` | ARM's `COMPLETED_PATH`.  Must be the same path ARM writes into `job.path`, so copy it from `arm.yaml` rather than using an alternative mount. |
| `remote_host` | `user@host` of the media box.  Leave empty if the destination paths are local mounts (NFS/SMB) on the ripping box. |
| `remote_movies_path` / `remote_tv_path` | Plex library folders on the media box.  Each rip lands as `<path>/<Title (Year)>/`. |
| `remote_unidentified_path` | Staging folder on the media box for manual review.  Keep it **outside** any Plex library. |
| `bwlimit_recognized` | rsync `--bwlimit` in KiB/s for movies/tv.  `0` = unlimited. |
| `bwlimit_unidentified` | rsync `--bwlimit` for unidentified rips.  `0` = unlimited. |
| `ssh_options` | Extra arguments for the ssh command rsync runs (`-i keyfile`, `-p port`, ...). |
| `rsync_path` / `rsync_extra_args` | rsync binary and extra flags, e.g. `--chown=plex:plex` or `--chmod=D775,F664` so Plex can read the files. |
| `rsync_timeout` | Seconds of I/O silence before rsync gives up; the folder is retried next run. |
| `lock_file` | Prevents overlapping runs. |
| `post_ship_command` | Optional shell command run after each folder ships, with `SHIPPER_TYPE`, `SHIPPER_FOLDER` and `SHIPPER_DESTINATION` in the environment. |

Command-line flags: `-c/--config`, `-n/--dry-run` (passes `--dry-run` to
rsync and deletes nothing), `-v/--verbose`, plus `--db-path`,
`--completed-path` and `--lock-file` overrides.

Destination parent folders must already exist.  rsync creates the per-title
folder itself.

## Pairing with Plex on the media box

Plex can pick new rips up on its own as soon as they land:

1. In Plex, open **Settings → Library** (server settings) and turn on
   **Scan my library automatically** and **Run a partial scan when changes are
   detected**.  Keep **Empty trash automatically after every scan** on if you
   want removed items to disappear too.
2. Point the Movies and TV libraries at `remote_movies_path` and
   `remote_tv_path`.  Do **not** add `remote_unidentified_path` to any library;
   it is a parking lot for folders you still have to rename.  Once you have
   identified a rip, move it into the library folder on the t620 (`mv` on the
   same filesystem is instant) and Plex scans it in.

Change detection on Linux uses inotify, which only works for folders on the
media box's **local** disks.  Because this shipper writes with rsync over ssh
*onto* the media box, the files are local there and the partial scan fires.  It
would not fire if Plex were watching a network mount instead.

rsync writes each file as a hidden temporary name (`.Title.mkv.XXXXXX`) and
renames it when complete, so Plex never sees a half-copied file.

If you prefer an explicit trigger, or your Plex lives in a container where
inotify is unreliable, use `post_ship_command` to call the Plex API from the
ripping box.  Find your section ids with
`curl "http://t620:32400/library/sections?X-Plex-Token=TOKEN"` and then, for
example:

```ini
post_ship_command = case "$SHIPPER_TYPE" in movies) s=1;; tv) s=2;; *) exit 0;; esac; curl -fsS "http://t620:32400/library/sections/$s/refresh?X-Plex-Token=TOKEN"
```

The hook is skipped for unidentified rips in that example so the staging folder
is never scanned.  (Finding the token: Plex support article "Finding an
authentication token / X-Plex-Token".)

## Optional: ship immediately when ARM finishes

The timer alone is enough; it fires every 15 minutes and catches up on anything
pending.  If you want rips to leave the box within seconds of ARM finishing,
let ARM's `BASH_SCRIPT` notification hook poke the service.  Add to the
ripping box:

```bash
# /etc/sudoers.d/arm-shipper
arm ALL=(root) NOPASSWD: /bin/systemctl start --no-block arm-completed-shipper.service
```

```bash
# /home/arm/shipper-notify.sh  (set BASH_SCRIPT to this path in arm.yaml)
#!/bin/bash
# ARM calls this with <title> <body> for every notification.  Starting the
# service is cheap: the lock file makes a run that finds nothing a no-op.
sudo /bin/systemctl start --no-block arm-completed-shipper.service
```

ARM's hook fires on job start too, which is harmless: the shipper only ships
jobs the database already marks `success`, so an early call just finds
nothing to do.

## Testing

The test builds a fake `COMPLETED_PATH`, a temporary ARM database and local
destination folders, and runs the shipper end to end through a wrapper around
the real `rsync` that records every call.  It covers priority order, the
bandwidth cap, skipped unfinished/failed/unknown folders, the failure
behaviour, resume after an interrupted copy, dry run and the lock.

```bash
python3 -m unittest scripts/completed_shipper/test_arm_completed_shipper.py
```

## Troubleshooting

* **Nothing ships, log says "not shippable yet".**  Run with `-v`: either the
  job is not `success` yet, or `completed_path` differs from what ARM wrote
  into `job.path`.  Check with
  `sqlite3 /home/arm/db/arm.db "select job_id,status,path from job order by job_id desc limit 5"`.
* **rsync exits 255.**  ssh could not connect or authenticate as the `arm`
  user non-interactively.  Test with
  `sudo -u arm ssh -o BatchMode=yes arm@t620 true`.
* **Unidentified rips never move.**  A recognized folder keeps failing (the
  log says which) and blocks them by design.  Fix or move that folder, then the
  next run proceeds.
* **Permissions on the media box.**  Use `rsync_extra_args = --chmod=D775,F664`
  (and `--chown=` if the ssh user may chown) so the Plex user can read the files.
