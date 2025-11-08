# Web Database Restore

The ARM web interface now lets administrators restore the application database directly from the browser. Use this feature to recover from a bad migration, roll back to a previous snapshot, or migrate data from another server.

## Prerequisites
- You must be signed in with an account that can access the **Database** page.
- Create or obtain a valid backup file:
  - SQLite installs accept `.db` files copied from the original `arm.db`.
  - All database engines accept JSON snapshots created from **Settings → Database Backup** or by calling `arm_db_backup()`.
- Ensure the backup file is stored locally on the machine you are using to access the UI.

## Downloading a Backup
1. Browse to the ARM UI and sign in if prompted.
2. Open **Database** from the navigation bar.
3. Locate the **Download Backup** card near the top of the page.
4. Click **Download Backup**. The UI generates a fresh backup using the current timestamp and streams it to your browser.
5. Save the file locally. ARM keeps an identical copy inside the configured `DATABASE_BACKUP_PATH`.

## Restoring a Backup
1. Browse to the ARM UI and sign in if prompted.
2. Open **Database** from the navigation bar.
3. Locate the **Restore Database** card below the backup controls.
4. Select **Choose File** and pick the `.json` or `.db` backup you want to restore.
5. Click **Restore**. The UI uploads the file and triggers the restore process.
6. Wait for the confirmation banner.
   - Success: "Database restored from backup '<file name>'." (The UI also notes where the safety backup was written.)
   - Failure: A red banner indicates the restore could not be completed. Review `armui.log` for the exact error.
7. Refresh the page or sign back in if prompted. Job history and settings now reflect the selected backup.

## Safety Backup Behavior
- Before applying the uploaded backup, ARM automatically creates a `pre_restore` backup in the directory configured by `DATABASE_BACKUP_PATH`.
- Uploaded backups are stored in the same directory (or `INSTALLPATH/db/uploads` when the backup path is not set) using the pattern `restore_<timestamp>_<original name>`.
- Keep or delete these files as needed after verifying the restore.

## Troubleshooting
- **Unsupported file type**: Only `.json` and `.db` uploads are accepted.
- **Permission errors**: Confirm the web server user can write to `DATABASE_BACKUP_PATH` (and the fallback upload directory).
- **Database unchanged**: Re-run the restore and check the log for SQL errors. For non-SQLite engines, verify the JSON backup was generated from a matching schema revision.
