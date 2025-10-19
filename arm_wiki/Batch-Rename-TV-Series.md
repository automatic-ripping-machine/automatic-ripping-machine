# Batch Rename TV Series Discs

<!-- TOC -->
* [Batch Rename TV Series Discs](#batch-rename-tv-series-discs)
  * [Overview](#overview)
  * [Features](#features)
  * [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Configuration](#configuration)
  * [Using Batch Rename](#using-batch-rename)
    * [Step 1: Select Jobs](#step-1-select-jobs)
    * [Step 2: Configure Rename Options](#step-2-configure-rename-options)
    * [Step 3: Preview Changes](#step-3-preview-changes)
    * [Step 4: Execute Rename](#step-4-execute-rename)
    * [Step 5: Rollback (If Needed)](#step-5-rollback-if-needed)
  * [Rename Options Explained](#rename-options-explained)
    * [Naming Style](#naming-style)
    * [Zero-Padded Numbers](#zero-padded-numbers)
    * [Consolidate into Series Parent Folder](#consolidate-into-series-parent-folder)
    * [Include Year in Parent Folder](#include-year-in-parent-folder)
  * [Understanding Preview Information](#understanding-preview-information)
    * [Series Outliers](#series-outliers)
    * [Path Conflicts](#path-conflicts)
    * [Preview Table](#preview-table)
  * [Examples](#examples)
    * [Example 1: Basic Rename with Underscores](#example-1-basic-rename-with-underscores)
    * [Example 2: Consolidation with Year](#example-2-consolidation-with-year)
    * [Example 3: Hyphen Style with Zero-Padding](#example-3-hyphen-style-with-zero-padding)
    * [Example 4: Space Style Without Year](#example-4-space-style-without-year)
  * [Rollback History](#rollback-history)
  * [Best Practices](#best-practices)
  * [Troubleshooting](#troubleshooting)
  * [Technical Details](#technical-details)
    * [Database Audit Trail](#database-audit-trail)
    * [API Endpoint](#api-endpoint)
  * [See Also](#see-also)
<!-- TOC -->

## Overview

The Batch Rename feature allows you to select multiple completed TV series disc rips and rename their output folders using a consistent, organized naming scheme based on the series name and disc label.

This feature is ideal for:
- **Organizing completed rips** with consistent folder naming
- **Preparing media for external tools** like Plex, Jellyfin, or Sonarr
- **Consolidating multi-disc series** into series parent folders
- **Cleaning up inconsistent naming** from earlier rips

All batch rename operations are tracked in an audit database with full rollback capability, so you can safely experiment with different naming schemes.

## Features

✅ **Multi-select interface** - Select multiple TV series jobs from the database view  
✅ **Preview before execution** - See exactly what changes will be made  
✅ **Multiple naming styles** - Underscore, hyphen, or space-separated names  
✅ **Optional zero-padding** - S01D01 vs S1D1 per your preference  
✅ **Series consolidation** - Group all discs under a parent folder (e.g., `Breaking Bad (2008)/`)  
✅ **Outlier detection** - Warns if selected jobs belong to different series  
✅ **Conflict detection** - Prevents renaming if target paths already exist  
✅ **Full rollback capability** - Undo any batch operation with one click  
✅ **Audit trail** - All operations tracked with user, timestamp, and paths  

## Getting Started

### Prerequisites

1. **ARM version 2.7+** with the batch rename feature installed
2. **Completed TV series rips** in the ARM database with status "success"
3. **Disc labels configured** on your discs (see [Using Disc Label for TV Series](Using-Disc-Label-for-TV-Series))
4. **Web UI access** - Navigate to the Database view

### Configuration

The batch rename feature uses default settings from your `arm.yaml` configuration file. These can be overridden per-batch in the UI.

```yaml
# Default naming style for batch rename operations
# Options: "underscore", "hyphen", "space"
# Example: "underscore" → Breaking_Bad_S1D1
#          "hyphen" → breaking-bad-s1d1
#          "space" → Breaking Bad S1D1
BATCH_RENAME_NAMING_STYLE: "underscore"

# Use zero-padded numbers by default (S01D01 instead of S1D1)
BATCH_RENAME_ZERO_PADDED: false

# Consolidate discs into series parent folder by default
# When true, creates: Breaking Bad (2008)/Breaking_Bad_S1D1/
# When false, creates: Breaking_Bad_S1D1/
BATCH_RENAME_CONSOLIDATE_DEFAULT: false
```

## Using Batch Rename

### Step 1: Select Jobs

1. Navigate to **Database** in the ARM Web UI
2. Find completed TV series jobs (status: success, video type: series)
3. Check the boxes next to the jobs you want to rename
   - Only TV series with "success" status can be selected
   - You can select jobs from the same series or use "Select All"
4. Click the **"Batch Rename Selected"** button

<img title="Selecting Jobs" alt="Database view with job checkboxes" src="images/batch_rename_select.png" width="80%"/>

> [!TIP]
> Use **Select All** to quickly select all eligible TV series jobs, then uncheck any you don't want to rename.

### Step 2: Configure Rename Options

The Batch Rename modal opens with configuration options:

<img title="Rename Options" alt="Batch rename options dialog" src="images/batch_rename_options.png" width="60%"/>

Configure the following:

| Option | Description | Default |
|--------|-------------|---------|
| **Naming Style** | How to separate words (underscore/hyphen/space) | underscore |
| **Zero-pad numbers** | Use S01D01 instead of S1D1 | unchecked |
| **Consolidate** | Group discs under series parent folder | unchecked |
| **Include year** | Add year to parent folder name | checked |

Click **"Generate Preview"** to see what the new folder names will look like.

### Step 3: Preview Changes

The preview shows:
- **Old folder name** → **New folder name** for each job
- **Warnings** about any potential issues
- **Series outliers** (jobs that don't match the majority series)
- **Path conflicts** (if new names already exist)

<img title="Preview Changes" alt="Batch rename preview table" src="images/batch_rename_preview.png" width="90%"/>

Review the preview carefully:

✅ **Green badges** (Ready) - Job will be renamed  
⚪ **Gray badges** (Skipped) - Job will be skipped (outlier or no disc label)  
🔴 **Red badges** (Conflict) - Target path already exists  

> [!WARNING]
> If any conflicts are detected, you must resolve them before proceeding. The "Execute" button will be disabled.

If everything looks good, click **"Execute Batch Rename"**.

To change options, click **"Back to Options"**.

### Step 4: Execute Rename

ARM performs the following actions:

1. **Validates** all selected jobs are still valid
2. **Creates parent folders** if consolidation is enabled
3. **Renames folders** on the filesystem using atomic operations
4. **Updates database** with new folder paths
5. **Records history** for rollback capability

<img title="Rename Results" alt="Batch rename success message" src="images/batch_rename_results.png" width="70%"/>

The results screen shows:
- **Batch ID** for tracking and rollback
- **Number of folders renamed** successfully
- **Skipped jobs** with reasons
- **Rollback button** to undo the operation

> [!NOTE]
> Batch rename operations are **atomic per job** - if one rename fails, others still succeed. The history tracks which jobs were renamed so rollback can restore them.

### Step 5: Rollback (If Needed)

If you need to undo a batch rename operation:

1. Click the **"Rollback This Operation"** button on the results screen, OR
2. Navigate to the Database view and find recent batch operations
3. Click **"Undo"** next to the batch you want to rollback

ARM will:
- Restore all original folder names
- Update the database to reflect the old paths
- Mark the batch as "rolled back" in the history

<img title="Rollback Confirmation" alt="Rollback dialog" src="images/batch_rename_rollback.png" width="60%"/>

> [!WARNING]
> Rollback only works if the **original folders have not been manually modified or deleted** since the rename. If ARM can't find the renamed folders, rollback will fail.

## Rename Options Explained

### Naming Style

Controls how words are separated in the folder name:

| Style | Example Output | Notes |
|-------|----------------|-------|
| **Underscore** | `Breaking_Bad_S1D1` | Default, filesystem-safe |
| **Hyphen** | `breaking-bad-s1d1` | Lowercase, URL-friendly |
| **Space** | `Breaking Bad S1D1` | Human-readable, may need quoting in shells |

### Zero-Padded Numbers

Controls whether season/disc numbers use leading zeros:

| Option | Example | Notes |
|--------|---------|-------|
| **Unchecked** | `S1D1`, `S2D10` | Compact, matches common disc labels |
| **Checked** | `S01D01`, `S02D10` | Consistent width, better sorting |

> [!TIP]
> Zero-padding is recommended if you have series with 10+ seasons or discs, as it ensures proper alphabetical sorting.

### Consolidate into Series Parent Folder

Groups all discs of a series under a parent folder:

| Option | Example Structure |
|--------|-------------------|
| **Unchecked** | `Breaking_Bad_S1D1/`<br>`Breaking_Bad_S1D2/`<br>`Breaking_Bad_S2D1/` |
| **Checked** | `Breaking Bad (2008)/`<br>├── `Breaking_Bad_S1D1/`<br>├── `Breaking_Bad_S1D2/`<br>└── `Breaking_Bad_S2D1/` |

> [!NOTE]
> The parent folder name is derived from the series title and year from the metadata lookup (OMDb/TMDb). If jobs have inconsistent titles, ARM uses the most common one.

### Include Year in Parent Folder

Only applies when consolidation is enabled:

| Option | Example Parent Folder |
|--------|----------------------|
| **Checked** | `Breaking Bad (2008)` |
| **Unchecked** | `Breaking Bad` |

## Understanding Preview Information

### Series Outliers

ARM detects when selected jobs belong to different series by comparing:
- **IMDb ID** (if available)
- **Normalized series title**

Example outlier warning:
```
Series Outliers Detected:
The following jobs have different series identifiers:
• Job 42: Game of Thrones (IMDb: tt0944947)
• Job 43: The Office (IMDb: tt0386676)

These will be skipped unless you override series detection.
```

**What to do:**
- If you meant to select jobs from the same series, **deselect the outliers** and regenerate the preview
- If you want to rename multiple different series at once, **they will be skipped** (batch rename works best for single-series operations)

### Path Conflicts

ARM checks if the new folder names already exist:

```
Path Conflicts Detected:
• /home/arm/media/Breaking_Bad_S1D1 already exists
```

**What to do:**
- **Rename or move the conflicting folder** manually, then regenerate preview
- **Delete the conflicting folder** if it's a duplicate or unwanted
- **Choose different rename options** (e.g., add zero-padding) to generate unique names

> [!WARNING]
> ARM will **not** overwrite existing folders. You must resolve conflicts before proceeding.

### Preview Table

The preview table shows:

| Column | Description |
|--------|-------------|
| **Job ID** | Database job identifier |
| **Title** | Series title from metadata |
| **Label** | Disc volume label |
| **Old Folder** | Current folder path |
| **New Folder** | Proposed new folder path |
| **Status** | Ready / Skipped / Conflict |

## Examples

### Example 1: Basic Rename with Underscores

**Settings:**
- Naming Style: Underscore
- Zero-Padded: No
- Consolidate: No

**Selected Jobs:**
- Job 101: Breaking Bad, Disc Label: `BB_S01D01`
- Job 102: Breaking Bad, Disc Label: `BB_S01D02`
- Job 103: Breaking Bad, Disc Label: `BB_S02D01`

**Before:**
```
/home/arm/media/Breaking Bad (2008)
/home/arm/media/Breaking Bad (2008)_20250101_120000
/home/arm/media/Breaking Bad (2008)_20250101_130000
```

**After:**
```
/home/arm/media/Breaking_Bad_S1D1
/home/arm/media/Breaking_Bad_S1D2
/home/arm/media/Breaking_Bad_S2D1
```

### Example 2: Consolidation with Year

**Settings:**
- Naming Style: Underscore
- Zero-Padded: No
- Consolidate: **Yes**
- Include Year: **Yes**

**Before:**
```
/home/arm/media/Breaking_Bad_S1D1
/home/arm/media/Breaking_Bad_S1D2
/home/arm/media/Breaking_Bad_S2D1
```

**After:**
```
/home/arm/media/Breaking Bad (2008)/Breaking_Bad_S1D1
/home/arm/media/Breaking Bad (2008)/Breaking_Bad_S1D2
/home/arm/media/Breaking Bad (2008)/Breaking_Bad_S2D1
```

### Example 3: Hyphen Style with Zero-Padding

**Settings:**
- Naming Style: **Hyphen**
- Zero-Padded: **Yes**
- Consolidate: No

**Before:**
```
/home/arm/media/Breaking_Bad_S1D1
/home/arm/media/Breaking_Bad_S1D2
/home/arm/media/Breaking_Bad_S10D1
```

**After:**
```
/home/arm/media/breaking-bad-s01d01
/home/arm/media/breaking-bad-s01d02
/home/arm/media/breaking-bad-s10d01
```

> [!NOTE]
> Hyphen style uses all lowercase for consistency and URL-friendliness.

### Example 4: Space Style Without Year

**Settings:**
- Naming Style: **Space**
- Zero-Padded: No
- Consolidate: Yes
- Include Year: **No**

**After:**
```
/home/arm/media/Breaking Bad/Breaking Bad S1D1
/home/arm/media/Breaking Bad/Breaking Bad S1D2
/home/arm/media/Breaking Bad/Breaking Bad S2D1
```

## Rollback History

All batch rename operations are stored in the database with:
- **Batch ID** - Unique identifier (UUID)
- **Timestamp** - When the operation was performed
- **User** - Who performed the operation (email)
- **Job mappings** - Old path → New path for each job
- **Rollback status** - Whether it's been rolled back

You can view recent batches in the Database view (feature coming soon) or use the rollback button immediately after a rename.

## Best Practices

### 1. Start with a Test Batch

Before renaming your entire library, test with 2-3 discs from one series:
- Select a few jobs
- Preview the changes
- Execute the rename
- Verify the folders look correct
- Try the rollback feature
- Once comfortable, proceed with larger batches

### 2. Enable Disc Label Feature First

For best results, enable `USE_DISC_LABEL_FOR_TV: true` in `arm.yaml` **before ripping**. This ensures your discs are already named consistently. See [Using Disc Label for TV Series](Using-Disc-Label-for-TV-Series).

If you didn't enable it before ripping, batch rename can still work if:
- Your disc labels contain season/disc identifiers
- ARM successfully parsed them during the rip

### 3. Check for Outliers

Before executing:
- Review the outlier warnings
- Deselect jobs that don't belong to the same series
- Batch rename works best when all selected jobs are from one series

### 4. Resolve Conflicts First

If you see conflict warnings:
- Don't force-execute (it won't work)
- Investigate why the target path exists
- Rename or delete the conflicting folder manually
- Regenerate the preview

### 5. Use Consolidation for Multi-Disc Series

If you have many discs from one series:
- Enable consolidation to group them under a parent folder
- This makes it easier to manage series with 20+ discs
- Example: `Game of Thrones (2011)/` with 40+ disc folders inside

### 6. Keep Rollback Available

- Don't manually rename folders after a batch operation until you're sure you want to keep the changes
- The rollback button is only available immediately after execution
- Rollback history is permanent (stored in database) but requires original folders to exist

## Troubleshooting

### Problem: "Only completed jobs can be batch renamed"

**Cause:** You selected a job with status other than "success"

**Solution:** 
- Only select jobs that have finished successfully
- Check the job status in the database view
- Failed or in-progress jobs cannot be renamed

### Problem: "Only TV series can be batch renamed"

**Cause:** You selected a movie or unknown video type

**Solution:**
- Batch rename only works for video type "series"
- Deselect any movie jobs
- If a TV series shows as "movie", you may need to fix the metadata

### Problem: Preview shows all jobs as "Skipped"

**Cause:** ARM couldn't parse disc identifiers from the disc labels

**Solution:**
- Check the disc labels in the database view
- Ensure labels contain patterns like `S1D1`, `Season1Disc1`, etc.
- See [Using Disc Label for TV Series](Using-Disc-Label-for-TV-Series) for supported formats
- If labels don't contain identifiers, you'll need to manually rename

### Problem: "Path conflicts detected"

**Cause:** The target folder names already exist

**Solution:**
1. Check if the existing folders are duplicates you can delete
2. If they're valid, rename them manually or choose different batch rename options
3. Try enabling zero-padding to generate unique names
4. Use consolidation to nest under a parent folder

### Problem: Rollback fails with "Folder not found"

**Cause:** The renamed folders were manually moved or deleted after the batch operation

**Solution:**
- Rollback requires the renamed folders to still exist at the new paths
- If you've already manually renamed them back, the rollback is unnecessary
- If they're deleted, rollback cannot restore them

### Problem: Series consolidation uses wrong series name

**Cause:** Jobs have different series titles from metadata lookup

**Solution:**
- Check the "Title" column in the preview table
- ARM uses the most common series title among selected jobs
- If titles are inconsistent, use manual title override in the web UI before ripping
- Alternatively, deselect jobs with different titles

## Technical Details

### Database Audit Trail

Every batch rename operation creates records in the `batch_rename_history` table:

```sql
CREATE TABLE batch_rename_history (
    id INTEGER PRIMARY KEY,
    batch_id VARCHAR(36) NOT NULL,      -- UUID for this batch operation
    job_id INTEGER,                      -- Foreign key to jobs table
    old_path TEXT NOT NULL,              -- Original folder path
    new_path TEXT NOT NULL,              -- New folder path after rename
    renamed_by VARCHAR(255),             -- User email who performed the operation
    renamed_at TIMESTAMP DEFAULT NOW,    -- When the rename occurred
    rolled_back BOOLEAN DEFAULT FALSE,   -- Whether this has been rolled back
    rolled_back_at TIMESTAMP,            -- When the rollback occurred
    error_message TEXT                   -- Any error that occurred during rename
);
```

Indexes on `batch_id`, `job_id`, and `renamed_at` ensure fast queries.

### API Endpoint

The batch rename feature exposes a REST API at `/batch_rename`:

**Request:**
```json
POST /batch_rename
{
  "action": "preview",
  "job_ids": [101, 102, 103],
  "naming_style": "underscore",
  "zero_padded": false,
  "consolidate": true,
  "include_year": true
}
```

**Actions:**
- `preview` - Generate preview of changes without executing
- `execute` - Perform the batch rename operation
- `rollback` - Undo a previous batch operation (requires `batch_id`)
- `recent_batches` - List recent batch operations

**Response:**
```json
{
  "success": true,
  "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "renamed_count": 3,
  "preview": {
    "previews": [...],
    "warnings": [...],
    "outliers": [...],
    "conflicts": [...]
  }
}
```

## See Also

- [Using Disc Label for TV Series](Using-Disc-Label-for-TV-Series) - Enable disc label-based naming during rips
- [ARM Configuration Guide](Config-arm.yaml) - Configure batch rename defaults
- [Web UI Job Management](Web-Jobs) - Managing jobs in the web interface
- [Database View](Web-Settings) - Accessing the database view
- [General Troubleshooting](General-Troubleshooting) - Common ARM issues

---

**Questions or Issues?** Open a [GitHub Issue](https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/new/choose) or check the [FAQ](FAQ).
