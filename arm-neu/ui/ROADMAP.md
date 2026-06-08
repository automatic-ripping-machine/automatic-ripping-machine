# ARM UI Roadmap

Feature parity tracker against the ARM Flask UI. Organized into milestones by priority — each milestone is independently shippable.

---

## Milestone 1 — Authentication

The UI is currently unauthenticated. Anyone with network access can abandon jobs, change settings, and control drives. ARM's Flask UI has single-admin bcrypt auth with Flask-Login.

- [ ] Login page with username/password form
- [ ] Session management (JWT or cookie-based)
- [ ] Protected routes — redirect to login when unauthenticated
- [ ] Password change page (old + new password)
- [ ] Support ARM's `DISABLE_LOGIN` config flag to bypass auth
- [ ] Logout button in header/sidebar

**Backend work:** Proxy auth to ARM's `/login` endpoint or read the `User` table directly and issue our own tokens.

---

## Milestone 2 — Drive Controls

The drives page shows status but offers no physical controls. The Flask UI lets users eject trays, trigger manual rips, and manage the drive inventory.

- [ ] Eject / close tray button per drive
- [ ] Manual job trigger button (start rip on a specific drive)
- [ ] Drive mode toggle (auto / manual)
- [ ] Remove drive from database
- [ ] Scan for new drives button
- [ ] Confirmation dialog for destructive actions (remove)

**Backend work:** Add endpoints that proxy to ARM's `/drive/eject/<id>`, `/drive/manual/<id>`, `/drive/remove/<id>`, `/systemdrivescan`. Add `mode` field to `PATCH /api/drives/<id>`.

---

## Milestone 3 — Notification Management

Notifications can be viewed but not dismissed. They accumulate with no way to clear them.

- [ ] Mark individual notification as read (click or button)
- [ ] "Clear all" / "Mark all read" button
- [ ] Toast popup overlay for new notifications (configurable timeout)
- [ ] Unread count badge in sidebar nav (already on dashboard, extend to global)

**Backend work:** Add `PATCH /api/notifications/<id>` (mark read) and `POST /api/notifications/clear` endpoints. Proxy to ARM's notification API or write directly since we have DB access.

---

## Milestone 4 — Audio CD Configuration (abcde)

Users who rip audio CDs have no way to configure the abcde ripper from the UI.

- [ ] New tab or section in Settings page for abcde configuration
- [ ] Raw text editor for `abcde.conf` (same approach as Flask UI)
- [ ] Save button with validation feedback
- [ ] Link to abcde documentation for reference

**Backend work:** Add `GET /api/settings/abcde` and `PUT /api/settings/abcde` endpoints. Read/write the abcde.conf file at the configured path.

---

## Milestone 5 — Apprise Notification Configuration

The Flask UI has a dedicated tab for editing Apprise notification channels and a test button.

- [ ] Apprise config editor tab in Settings (YAML or structured form)
- [ ] Test notification button with success/failure feedback
- [ ] List of supported channels with documentation links

**Backend work:** Add `GET /api/settings/apprise`, `PUT /api/settings/apprise`, and `POST /api/settings/apprise/test` endpoints. Proxy to ARM for the test or invoke Apprise directly.

---

## Milestone 6 — Job Track Editing

The Flask UI allows manual track selection — users can toggle which tracks to rip and edit track metadata before starting a job.

- [ ] Track list table on job detail page (track number, length, aspect, fps, main feature flag)
- [ ] Checkbox per track to include/exclude from ripping
- [ ] Main feature toggle per track
- [ ] Save track selections
- [ ] Only show for jobs in "waiting" or "active" status

**Backend work:** Add `PATCH /api/jobs/<id>/tracks` endpoint to update track process/main_feature flags.

---

## Milestone 7 — Database Management

The Flask UI has database maintenance features needed for fresh installs and upgrades.

- [ ] Setup wizard for first-run (create database, set admin password)
- [ ] Database migration trigger (run Alembic upgrades from UI)
- [ ] Import untracked movies — scan COMPLETED_PATH, match against OMDb, add to database
- [ ] Import progress indicator

**Backend work:** Add `POST /api/system/db-migrate`, `POST /api/system/db-create`, and `POST /api/system/import-movies` endpoints. These proxy to ARM or execute directly.

---

## Milestone 8 — Log File Download

Logs can be viewed in the browser but not saved to disk.

- [ ] Download button on log viewer (serves raw file)
- [ ] Download from log file listing (direct link per file)

**Backend work:** Add `GET /api/logs/<filename>/download` that returns the file with `Content-Disposition: attachment`.

---

## Milestone 9 — System Controls & Info

Assorted system management features from the Flask UI.

- [ ] Restart ARM service button (with confirmation dialog)
- [ ] Version info display — local git hash, upstream version, update available indicator
- [ ] Ripping statistics card — total rips, movies/series/audio/failed counts
- [ ] Custom title for multi-disc series (set a shared title across jobs with same label)

**Backend work:** `POST /api/system/restart` proxy. `GET /api/system/version` to read git info. Stats can be computed from existing job queries.

---

## Milestone 10 — UI Settings Parity

The Flask UI has several UI-specific settings we don't expose.

- [ ] Dashboard refresh rate (currently hardcoded at 5s)
- [ ] Notification toast timeout
- [ ] Database page size (items per page)
- [ ] Toggle status icons on job cards
- [ ] Settings stored in browser localStorage or backend UISettings table

**Note:** Some of these may not be needed — the replacement UI already has a cleaner UX. Evaluate each on merit rather than copying blindly.

---

## Already Implemented (no action needed)

These Flask UI features already exist in the replacement UI or are superseded:

| Flask UI Feature | Replacement UI Status |
|-----------------|----------------------|
| Active rips view | Dashboard |
| Job list with search/filter | Jobs page with status + type filters |
| Job detail + metadata editing | Job detail page with title search |
| Job abandon / delete / fix-perms | Job actions on detail page |
| Cancel / start waiting jobs | DiscReviewWidget + job actions |
| ARM config editing | Settings page |
| Transcoder config editing | Settings page (Flask UI didn't have this) |
| Drive listing with name/desc editing | Drives page |
| Log viewer (tail / full) | Logs page with ARM + transcoder tabs |
| Notification history | Dashboard notification count + history |
| System stats (CPU, RAM, disk) | Dashboard sidebar + settings |
| GPU detection | Settings GPU support display |
| Ripping pause toggle | Dashboard toggle |
| Dark mode | Theme system with color schemes |
| Metadata search (OMDb/TMDb) | Title search on job detail |
| Music metadata search (MusicBrainz) | MusicSearch with card flip tracklist preview |
| Disc track comparison | Duration match indicators on music search |
| Structured metadata editing | Artist, album, season, episode fields |
| CRC database lookup | Audio disc identification on job detail |
| Service connection status | Status indicators for ARM and transcoder |
| Job rip parameter editing | RipSettings component |
| Responsive mobile layout | Tailwind responsive design |
| History / completed jobs | Jobs page with status filters |

---

## Milestone 11 - Decoupled Transcoder Settings Integration

Status: done (v16.0.0)

Shipped in v16.0.0: global toggle on Settings > Ripping, per-disc toggle in DiscReviewWidget, Skip Transcode & Finalize recovery button on job detail page.

The Settings page already has working ARM and transcoder config editors. But the two are independent - there's no awareness that they're parts of a single pipeline. When ARM's `SKIP_TRANSCODE` is enabled and transcoding is offloaded, the two services must agree on paths, credentials, and behavior. Today users have to mentally coordinate these settings across tabs.

### Cross-Service Awareness

- [x] When `SKIP_TRANSCODE=True` in ARM config, visually de-emphasize ARM's transcoding settings (HB_PRESET, DEST_EXT, HANDBRAKE_LOCAL, etc.) with a banner: "Transcoding is handled by the dedicated transcoder service - edit those settings in the Transcoder tab"
- [x] When `SKIP_TRANSCODE=False`, show info on Transcoder tab: "ARM is using its built-in transcoder. These settings only apply if you enable SKIP_TRANSCODE in ARM config"
- [x] Link between tabs - clicking the banner jumps to the relevant tab

### Path Alignment Validation

- [x] Compare ARM's `RAW_PATH` / `COMPLETED_PATH` against transcoder's `raw_path` / `completed_path` at settings load time
- [x] Show warning banner if paths don't match (common misconfiguration that causes the transcoder to look in the wrong directory)
- [x] Display both sets of paths side-by-side for easy comparison

**Note:** Transcoder paths are read-only (set via env vars / Docker volumes). The validation is informational - it tells the user to fix their Docker Compose mounts, not to change a form field.

### Connection Testing

- [x] "Test Connection" button on Transcoder tab - calls transcoder health endpoint and verifies:
  - Service is reachable
  - API key is valid (if auth enabled)
  - GPU detection results
- [x] "Test Webhook" button - sends a test webhook from ARM to the transcoder's `/webhook/arm` endpoint, verifying the full notify path works (webhook URL + secret + reachability)
- [x] Results displayed inline with clear pass/fail for each check

**Backend work:** Add `POST /api/settings/transcoder/test` that calls the transcoder's `/health` endpoint. Add `POST /api/settings/transcoder/test-webhook` that calls ARM's bash_notify test or hits the transcoder webhook directly with a test payload.

### Notification Script Configuration

- [x] Display current `BASH_SCRIPT` path from ARM config
- [x] Show a read-only preview of the script contents (if accessible)
- [x] Guided setup: form to generate/update `notify_transcoder.sh` with the correct webhook URL, secret, and ARM env var mappings
- [x] Validate that `BASH_SCRIPT` points to an existing, executable file

**Backend work:** Add `GET /api/settings/bash-script` to read the current script. Add `PUT /api/settings/bash-script` to write an updated version. The script template would inject `ARM_UI_TRANSCODER_URL` and `webhook_secret` into the right places.

### Transcoder Auth Management (Stretch)

- [x] Display whether API auth is enabled on the transcoder
- [x] Show masked API key status (configured / not configured)
- [x] Guidance for rotating keys (link to docs or Docker env var instructions, since keys are set at deployment time)

**Note:** API keys and webhook secrets are intentionally not runtime-updatable (security boundary). The UI should surface their status and guide configuration, not manage the values directly.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Send to remote ARM DB | Niche federated setup; defer unless requested |
| Bootswatch theme picker | Replaced by custom color scheme system |
| Internationalization | Placeholder in Flask UI too; defer until demand |
