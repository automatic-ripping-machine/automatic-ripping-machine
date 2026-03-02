#!/usr/bin/env python3
"""
Playwright-based screenshot generator for the ARM Batch Rename UI.

Starts the ARM Flask app with a test database seeded with sample data,
then uses Playwright to capture screenshots of the full batch rename workflow.
"""
import sys
import os
import tempfile
import threading
import time

# ── 1. Bootstrap mock config before any ARM imports ──────────────────────────
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

import types
from unittest.mock import MagicMock

# Mock discid (requires native lib)
for mod_name in ('discid', 'discid.disc', 'discid.libdiscid'):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

_screenshot_tmpdir = tempfile.mkdtemp(prefix='arm_screenshots_')
_tmpdb = os.path.join(_screenshot_tmpdir, 'arm_screenshot_test.db')
# Remove old test DB
if os.path.isfile(_tmpdb):
    os.remove(_tmpdb)

_minimal_arm_config = {
    'INSTALLPATH': _project_root + '/',
    'DBFILE': _tmpdb,
    'LOGLEVEL': 'WARNING',
    'DISABLE_LOGIN': True,
    'COMPLETED_PATH': os.path.join(_screenshot_tmpdir, 'completed'),
    'RAW_PATH': os.path.join(_screenshot_tmpdir, 'raw'),
    'TRANSCODE_PATH': os.path.join(_screenshot_tmpdir, 'transcode'),
    'MEDIA_DIR': os.path.join(_screenshot_tmpdir, 'media'),
    'ARMPATH': _project_root + '/',
    'RAWPATH': os.path.join(_screenshot_tmpdir, 'raw'),
    'USE_DISC_LABEL_FOR_TV': True,
    'GROUP_TV_DISCS_UNDER_SERIES': True,
    'EXTRAS_SUB': 'extras',
    'DEST_EXT': 'mkv',
    'DATE_FORMAT': '%m-%d-%Y %H:%M:%S',
    'BATCH_RENAME_NAMING_STYLE': 'underscore',
    'BATCH_RENAME_ZERO_PADDED': False,
    'BATCH_RENAME_CONSOLIDATE_DEFAULT': False,
}

_config_mod = types.ModuleType('arm.config.config')
_config_mod.arm_config = _minimal_arm_config
_config_mod.arm_config_path = os.path.join(_screenshot_tmpdir, 'arm.yaml')
_config_mod.abcde_config = ''
_config_mod.apprise_config = {}

_config_pkg = types.ModuleType('arm.config')
_config_pkg.config = _config_mod

_config_utils = types.ModuleType('arm.config.config_utils')
_config_utils.arm_yaml_check_groups = MagicMock(return_value='')
_config_utils.arm_yaml_test_bool = MagicMock(return_value='')

sys.modules['arm.config'] = _config_pkg
sys.modules['arm.config.config'] = _config_mod
sys.modules['arm.config.config_utils'] = _config_utils

# ── 2. Import ARM after mock config ──────────────────────────────────────────
from arm.ui import app, db  # noqa: E402
from arm.models.job import Job  # noqa: E402
from arm.models.ui_settings import UISettings  # noqa: E402

# Output directories
WIKI_IMG_DIR = os.path.join(_project_root, 'arm_wiki', 'images')
DOCS_IMG_DIR = os.path.join(_project_root, 'docs', 'images', 'batch-demo')


def seed_database():
    """Seed the test database with sample completed TV series jobs."""
    with app.app_context():
        db.create_all()

        # Create UISettings if not exists
        if not db.session.get(UISettings, 1):
            ui_settings = UISettings()
            db.session.add(ui_settings)
            db.session.flush()

        # Use raw inserts to bypass Job.__init__ which needs udev
        from sqlalchemy import text

        bb_discs = [
            ('BB_S01D01', 'Season 1 Disc 1', '2025-10-15 10:00:00', '2025-10-15 11:30:00'),
            ('BB_S01D02', 'Season 1 Disc 2', '2025-10-15 11:00:00', '2025-10-15 12:30:00'),
            ('BB_S01D03', 'Season 1 Disc 3', '2025-10-15 12:00:00', '2025-10-15 13:30:00'),
            ('BB_S02D01', 'Season 2 Disc 1', '2025-10-15 13:00:00', '2025-10-15 14:30:00'),
            ('BB_S02D02', 'Season 2 Disc 2', '2025-10-15 14:00:00', '2025-10-15 15:30:00'),
        ]

        for i, (label, _desc, start, stop) in enumerate(bb_discs, start=1):
            db.session.execute(text("""
                INSERT INTO job (title, year, video_type, label, status, hasnicetitle,
                                 path, start_time, stop_time, logfile, imdb_id,
                                 poster_url, devpath, mountpoint, ejected, updated,
                                 disctype, stage)
                VALUES (:title, :year, :vtype, :label, :status, :nice,
                        :path, :start, :stop, :log, :imdb,
                        :poster, :dev, :mnt, :ej, :upd,
                        :dtype, :stage)
            """), {
                'title': 'Breaking Bad', 'year': '2008', 'vtype': 'series',
                'label': label, 'status': 'success', 'nice': True,
                'path': f'{_screenshot_tmpdir}/completed/tv/Breaking Bad (2008)_{i}',
                'start': start, 'stop': stop,
                'log': f'breaking_bad_{label.lower()}.log',
                'imdb': 'tt0903747', 'poster': '',
                'dev': '/dev/sr0', 'mnt': '/mnt/sr0',
                'ej': False, 'upd': False, 'dtype': 'dvd',
                'stage': str(i),
            })

        # Game of Thrones (outlier)
        db.session.execute(text("""
            INSERT INTO job (title, year, video_type, label, status, hasnicetitle,
                             path, start_time, stop_time, logfile, imdb_id,
                             poster_url, devpath, mountpoint, ejected, updated,
                             disctype, stage)
            VALUES (:title, :year, :vtype, :label, :status, :nice,
                    :path, :start, :stop, :log, :imdb,
                    :poster, :dev, :mnt, :ej, :upd,
                    :dtype, :stage)
        """), {
            'title': 'Game of Thrones', 'year': '2011', 'vtype': 'series',
            'label': 'GOT_S01D01', 'status': 'success', 'nice': True,
            'path': f'{_screenshot_tmpdir}/completed/tv/Game of Thrones (2011)_1',
            'start': '2025-10-16 14:00:00', 'stop': '2025-10-16 15:30:00',
            'log': 'got_s1d1.log', 'imdb': 'tt0944947', 'poster': '',
            'dev': '/dev/sr0', 'mnt': '/mnt/sr0',
            'ej': False, 'upd': False, 'dtype': 'dvd', 'stage': '6',
        })

        # Movie (to show type filter)
        db.session.execute(text("""
            INSERT INTO job (title, year, video_type, label, status, hasnicetitle,
                             path, start_time, stop_time, logfile, imdb_id,
                             poster_url, devpath, mountpoint, ejected, updated,
                             disctype, stage)
            VALUES (:title, :year, :vtype, :label, :status, :nice,
                    :path, :start, :stop, :log, :imdb,
                    :poster, :dev, :mnt, :ej, :upd,
                    :dtype, :stage)
        """), {
            'title': 'Inception', 'year': '2010', 'vtype': 'movie',
            'label': 'INCEPTION', 'status': 'success', 'nice': True,
            'path': f'{_screenshot_tmpdir}/completed/movies/Inception (2010)',
            'start': '2025-10-17 09:00:00', 'stop': '2025-10-17 10:00:00',
            'log': 'inception.log', 'imdb': 'tt1375666', 'poster': '',
            'dev': '/dev/sr0', 'mnt': '/mnt/sr0',
            'ej': False, 'upd': False, 'dtype': 'dvd', 'stage': '7',
        })

        db.session.commit()
        print(f"Seeded database with {len(bb_discs) + 2} jobs")


def start_flask_server(port=8199):
    """Start Flask in a background thread."""
    def run():
        app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    # Wait for server to start
    import urllib.request
    for _ in range(30):
        try:
            req = urllib.request.Request(f'http://127.0.0.1:{port}/batch_rename_view')
            resp = urllib.request.urlopen(req)
            if resp.status in (200, 302):
                return port
        except urllib.error.HTTPError as e:
            if e.code in (302, 404, 500):
                return port  # Server is responding
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Flask server didn't start in time")


def take_screenshots(port):
    """Use Playwright to capture UI screenshots."""
    from playwright.sync_api import sync_playwright

    base_url = f'http://127.0.0.1:{port}'
    os.makedirs(WIKI_IMG_DIR, exist_ok=True)
    os.makedirs(DOCS_IMG_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1440, 'height': 900},
            device_scale_factor=2,
        )
        page = context.new_page()

        # ── Screenshot 1: Batch Rename View - Job List ───────────────────
        print("Capturing: batch job list...")
        page.goto(f'{base_url}/batch_rename_view')
        page.wait_for_load_state('networkidle')
        time.sleep(0.5)

        save_screenshot(page, 'batch_rename_select',
                        '01-batch-job-list')

        # ── Screenshot 2: Select some jobs ───────────────────────────────
        print("Capturing: job selection...")
        # Use JavaScript to check boxes and trigger the selection logic
        page.evaluate("""() => {
            // Find all job checkboxes (could be .job-checkbox or .batch-checkbox)
            const checkboxes = document.querySelectorAll(
                'input[type="checkbox"].batch-checkbox, input[type="checkbox"].job-checkbox'
            );
            for (let i = 0; i < Math.min(5, checkboxes.length); i++) {
                checkboxes[i].checked = true;
                checkboxes[i].dispatchEvent(new Event('change', {bubbles: true}));
                checkboxes[i].click();  // trigger jQuery handlers
            }
        }""")
        time.sleep(0.5)

        save_screenshot(page, 'batch_rename_select_checked',
                        '02-batch-job-selection')

        # ── Screenshot 3: Open Batch Rename modal ────────────────────────
        print("Capturing: rename options modal...")
        # Directly invoke the modal open via JS
        page.evaluate("""() => {
            // Populate selectedJobs Set if it exists
            if (typeof selectedJobs !== 'undefined') {
                const checkboxes = document.querySelectorAll(
                    'input[type="checkbox"].batch-checkbox:checked, input[type="checkbox"].job-checkbox:checked'
                );
                checkboxes.forEach(cb => {
                    const jobId = cb.dataset.jobId || cb.value;
                    if (jobId) selectedJobs.add(parseInt(jobId));
                });
            }
            // Show the modal directly
            const modal = document.getElementById('batchRenameModal');
            if (modal) {
                // Show options step
                const optionsStep = document.getElementById('rename-options-step');
                if (optionsStep) optionsStep.style.display = 'block';
                // Use Bootstrap modal API
                if (typeof $ !== 'undefined' && $.fn.modal) {
                    $('#batchRenameModal').modal('show');
                } else if (typeof bootstrap !== 'undefined') {
                    new bootstrap.Modal(modal).show();
                } else {
                    modal.classList.add('show');
                    modal.style.display = 'block';
                }
            }
        }""")
        time.sleep(1.0)

        # Check if modal opened
        modal = page.locator('.modal.show, .modal[style*="display: block"]')
        if modal.count() > 0:
            save_screenshot(page, 'batch_rename_options',
                            '03-rename-options-modal')

            # ── Screenshot 4: Show options with defaults ─────────────────
            save_screenshot(page, 'batch_rename_options_defaults',
                            '04-rename-options-defaults')

            # Close modal
            page.keyboard.press('Escape')
            time.sleep(0.3)
        else:
            print("  (Modal didn't open, skipping modal screenshots)")

        # ── Screenshot 5: Database view ──────────────────────────────────
        print("Capturing: database view...")
        page.goto(f'{base_url}/database')
        page.wait_for_load_state('networkidle')
        time.sleep(0.5)

        save_screenshot(page, 'database_view',
                        'database-view')

        # ── Screenshot 6: Main index page ────────────────────────────────
        print("Capturing: main page...")
        page.goto(f'{base_url}/')
        page.wait_for_load_state('networkidle')
        time.sleep(0.5)

        save_screenshot(page, 'arm_main_page',
                        'arm-main-page')

        # ── Screenshot 7: Settings page ──────────────────────────────────
        print("Capturing: settings page...")
        page.goto(f'{base_url}/settings')
        page.wait_for_load_state('networkidle')
        time.sleep(0.5)

        save_screenshot(page, 'settings_general',
                        'settings-general')

        browser.close()


def save_screenshot(page, wiki_name, docs_name):
    """Save a screenshot to both wiki and docs locations."""
    wiki_path = os.path.join(WIKI_IMG_DIR, f'{wiki_name}.png')
    docs_path = os.path.join(DOCS_IMG_DIR, f'{docs_name}.png')

    page.screenshot(path=wiki_path, full_page=True)
    # Also save to docs
    page.screenshot(path=docs_path, full_page=True)
    print(f"  Saved: {wiki_name}.png -> wiki + docs")


def main():
    print("=== ARM Batch Rename Screenshot Generator ===")
    print(f"Project root: {_project_root}")
    print(f"Test DB: {_tmpdb}")

    # Seed database
    seed_database()

    # Start Flask
    print("Starting Flask server...")
    port = start_flask_server()
    print(f"Server running on port {port}")

    # Take screenshots
    print("\nCapturing screenshots...")
    take_screenshots(port)

    print("\nDone! Screenshots saved to:")
    print(f"  Wiki:  {WIKI_IMG_DIR}")
    print(f"  Docs:  {DOCS_IMG_DIR}")


if __name__ == '__main__':
    main()
