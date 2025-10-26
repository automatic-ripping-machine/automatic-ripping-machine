# TV Series Organization: Disc Labels and Folder Grouping

## Overview

ARM includes two complementary opt-in features for organizing TV series output:

1. **USE_DISC_LABEL_FOR_TV** - Parse disc labels for deterministic folder naming
2. **GROUP_TV_DISCS_UNDER_SERIES** - Organize multiple discs under a parent series folder

These features are particularly useful for:

- Creating organized, predictable folder structures for multi-disc series
- External batch renamers and automated importers
- Consistent naming across entire series
- Media server libraries with proper hierarchy
- Workflows that rely on disc-level identification

## How It Works

### Default Behavior (Both Features Disabled)

By default, ARM creates folders for TV series using:
```
{COMPLETED_PATH}/tv/{Series Title} ({Year})/
```
Example: `/media/tv/Breaking Bad (2008)/`

If a folder already exists, ARM appends a timestamp to create a unique folder name.

### With Disc Label Feature Only

When `USE_DISC_LABEL_FOR_TV` is enabled, ARM intelligently combines:
- **Standardized series name** from the lookup service (OMDb/TMDb) or manual title
- **Season/disc identifier** parsed from the disc volume label

Result:
```
{COMPLETED_PATH}/tv/{Normalized_Series_Name}_{SxDx}/
```
Example: `/media/tv/Breaking_Bad_S1D1/`

### With Both Features Enabled (Recommended)

When both `USE_DISC_LABEL_FOR_TV` and `GROUP_TV_DISCS_UNDER_SERIES` are enabled:
- **Parent folder** uses standard series naming: `{Series Title} ({Year})`
- **Disc subfolders** use parsed disc labels: `{Normalized_Series_Name}_{SxDx}`

Result:
```
{COMPLETED_PATH}/tv/{Series Title} ({Year})/{Normalized_Series_Name}_{SxDx}/
```
Example:
```
/media/tv/Breaking Bad (2008)/
  ├── Breaking_Bad_S1D1/
  ├── Breaking_Bad_S1D2/
  └── Breaking_Bad_S2D1/
```

This structure provides:
- Clear series-level organization
- Deterministic disc-level folders
- Easy navigation and management
- Compatibility with most media servers

## Configuration

### Enable Disc Label Naming

Edit your `arm.yaml` configuration file:

```yaml
# Use disc label for TV series output folder naming (opt-in feature)
# When enabled, ARM will parse the disc label for season/disc identifiers (e.g., S1D1, S01D02)
# and create folders like "Breaking_Bad_S1D1" instead of "Breaking Bad (2008)"
# The series name comes from the lookup service or manual title, ensuring consistency
# If parsing fails, ARM falls back to the standard naming (series name + timestamp)
# Default: false (disabled for backward compatibility)
USE_DISC_LABEL_FOR_TV: true
```

### Enable Series Folder Grouping (Optional)

For organizing multiple discs under a single series parent folder:

```yaml
# Group TV series discs under a parent series folder (opt-in feature)
# When enabled, ARM will organize multiple disc folders under a single series parent folder
# Structure: {COMPLETED_PATH}/tv/{Series Title (Year)}/{Breaking_Bad_S1D1, Breaking_Bad_S1D2, etc.}
# Example with both features enabled:
#   - Parent folder: "Breaking Bad (2008)"
#   - Disc folders: "Breaking_Bad_S1D1", "Breaking_Bad_S1D2", "Breaking_Bad_S2D1"
# When USE_DISC_LABEL_FOR_TV is disabled, disc folders will still be grouped but named with timestamps
# This feature works best when combined with USE_DISC_LABEL_FOR_TV for predictable folder names
# Default: false (disabled for backward compatibility)
GROUP_TV_DISCS_UNDER_SERIES: true
```

**Recommended Configuration** for organized TV series libraries:
```yaml
USE_DISC_LABEL_FOR_TV: true
GROUP_TV_DISCS_UNDER_SERIES: true
```

### Supported Disc Label Formats

ARM can parse season and disc identifiers from many common label formats (case-insensitive):

#### Pattern 1: Compact Format
- `S1D1`, `S01D02`, `S10D5` → `S1D1`, `S1D2`, `S10D5`
- `BB_S1D1`, `GOT_S05D03` → `S1D1`, `S5D3`

#### Pattern 2: With Separators
- `S1_D1`, `S01_D02` → `S1D1`, `S1D2`
- `S1-D1`, `S01-D02` → `S1D1`, `S1D2`
- `S1 D1` → `S1D1`

#### Pattern 3: With Episode Numbers
- `S1E1D1`, `S01E01D1` → `S1E1D1`
- `S1E1_D1`, `S01_E05_D2` → `S1E1D1`, `S1E5D2`

#### Pattern 4: Word Format
- `Season1Disc1`, `SEASON01DISC02` → `S1D1`, `S1D2`
- `Season 1 Disc 1` → `S1D1`
- `Season_01_Disc_02` → `S1D2`

#### Pattern 5: Separate Tokens
- `Breaking Bad S01 D1` → `S1D1`
- `Disc1_S2`, `GOT S5 D3` → `S2D1`, `S5D3`

**Note:** Leading zeros are automatically stripped (e.g., `S01D01` becomes `S1D1`).

## Examples

### Example 1: Disc Label Only (No Grouping)
**Configuration:**
- `USE_DISC_LABEL_FOR_TV: true`
- `GROUP_TV_DISCS_UNDER_SERIES: false`

**Disc Label:** `BB_S01_D01`  
**Series from Lookup:** Breaking Bad  
**Output Structure:**
```
{COMPLETED_PATH}/tv/Breaking_Bad_S1D1/
```

### Example 2: Disc Label + Series Grouping (Recommended)
**Configuration:**
- `USE_DISC_LABEL_FOR_TV: true`
- `GROUP_TV_DISCS_UNDER_SERIES: true`

**Multiple Discs:**
- Disc 1: `BB_S01_D01`
- Disc 2: `BB_S01_D02`
- Disc 3: `BB_S02_D01`

**Series from Lookup:** Breaking Bad (2008)

**Output Structure:**
```
{COMPLETED_PATH}/tv/Breaking Bad (2008)/
  ├── Breaking_Bad_S1D1/
  ├── Breaking_Bad_S1D2/
  └── Breaking_Bad_S2D1/
```

### Example 3: Grouping Only (No Disc Labels)
**Configuration:**
- `USE_DISC_LABEL_FOR_TV: false`
- `GROUP_TV_DISCS_UNDER_SERIES: true`

**Series from Lookup:** The Office (2005)

**Output Structure:**
```
{COMPLETED_PATH}/tv/The Office (2005)/
  ├── The Office (2005)/
  ├── The Office (2005)_20231015_143022/
  └── The Office (2005)_20231016_092145/
```
*Note: Without disc labels, folders use timestamps to ensure uniqueness*

### Example 4: Word Format with Grouping
**Configuration:**
- `USE_DISC_LABEL_FOR_TV: true`
- `GROUP_TV_DISCS_UNDER_SERIES: true`

**Disc Label:** `SEASON_02_DISC_03`  
**Series from Lookup:** Game of Thrones (2011)  

**Output Structure:**
```
{COMPLETED_PATH}/tv/Game of Thrones (2011)/
  └── Game_of_Thrones_S2D3/
```

### Example 5: Manual Title Override with Grouping
**Configuration:**
- `USE_DISC_LABEL_FOR_TV: true`
- `GROUP_TV_DISCS_UNDER_SERIES: true`

**Disc Label:** `S01D01`  
**Manual Title Set:** Breaking Bad (US)  
**Lookup Year:** 2008

**Output Structure:**
```
{COMPLETED_PATH}/tv/Breaking Bad (US) (2008)/
  └── Breaking_Bad_(US)_S1D1/
```

### Example 6: Fallback Scenario with Grouping
**Configuration:**
- `USE_DISC_LABEL_FOR_TV: true`
- `GROUP_TV_DISCS_UNDER_SERIES: true`

**Disc Label:** `NO_IDENTIFIER_HERE`  
**Series from Lookup:** The Office (2005)

**Output Structure:**
```
{COMPLETED_PATH}/tv/The Office (2005)/
  └── The Office (2005)/
```
*Note: Falls back to standard naming when parsing fails*

### Example 7: Standard Naming (No Features Enabled)
**Configuration:**
- `USE_DISC_LABEL_FOR_TV: false`
- `GROUP_TV_DISCS_UNDER_SERIES: false`

**Series from Lookup:** Breaking Bad (2008)

**Output Structure:**
```
{COMPLETED_PATH}/tv/Breaking Bad (2008)/
```
*Note: This is the default ARM behavior*

## Series Name Normalization

To ensure folder names are filesystem-safe, ARM normalizes series names:

1. **Spaces** → Underscores: `Breaking Bad` → `Breaking_Bad`
2. **Special characters** → Underscores: `Series: Name` → `Series__Name`
3. **Multiple spaces/underscores** → Single underscore
4. **Accented characters** → ASCII equivalents (or stripped)
5. **Preserves:** Hyphens, parentheses, alphanumerics

## Fallback Behavior

ARM automatically falls back to standard naming when:

1. **Feature is disabled** in configuration
2. **Video type is not "series"** (movies use standard naming)
3. **Disc label parsing fails** (no valid season/disc pattern found)
4. **Series title is missing** from metadata

In fallback mode, ARM uses the existing behavior: `{Series Title} ({Year})` with timestamp appended if the folder exists.

## Feature Combinations

The two features can be used independently or together:

| USE_DISC_LABEL_FOR_TV | GROUP_TV_DISCS_UNDER_SERIES | Result |
|---|---|---|
| `false` | `false` | Default: `/tv/Breaking Bad (2008)/` |
| `true` | `false` | Disc labels: `/tv/Breaking_Bad_S1D1/` |
| `false` | `true` | Grouped with timestamps: `/tv/Breaking Bad (2008)/Breaking Bad (2008)_timestamp/` |
| `true` | `true` | **Recommended**: `/tv/Breaking Bad (2008)/Breaking_Bad_S1D1/` |

### Recommended Configuration

For the best organization:
```yaml
USE_DISC_LABEL_FOR_TV: true
GROUP_TV_DISCS_UNDER_SERIES: true
ALLOW_DUPLICATES: true
```

This creates predictable, organized structures that work well with media servers and automated tools.

## Duplicate Folder Handling

Even with these features, ARM's existing duplicate detection still applies:

- If `ALLOW_DUPLICATES: false` and the disc is detected as a duplicate, the job will fail
- If `ALLOW_DUPLICATES: true` or the disc is not a duplicate:
  - ARM creates the folder structure based on your configuration
  - If the exact folder already exists, ARM appends a timestamp to ensure uniqueness
  - With grouping enabled, duplicate detection applies to the disc subfolder, not the parent

## Best Practices

### 1. Enable Both Features for Organized Libraries
For the best TV series organization, enable both features:
```yaml
USE_DISC_LABEL_FOR_TV: true
GROUP_TV_DISCS_UNDER_SERIES: true
```

This creates a clean structure like:
```
Breaking Bad (2008)/
  ├── Breaking_Bad_S1D1/
  ├── Breaking_Bad_S1D2/
  └── Breaking_Bad_S2D1/
```

### 2. Consistent Disc Labeling
For best results, label your discs consistently:
- ✅ Good: `BreakingBad_S01_D01`, `BreakingBad_S01_D02`, `BreakingBad_S02_D01`
- ❌ Avoid: Random labels without season/disc information

### 3. Enable ALLOW_DUPLICATES for Series
```yaml
ALLOW_DUPLICATES: true
```
This is recommended for TV series to allow re-ripping if needed.

### 4. Use Manual Title Override for Ambiguous Series
If ARM picks the wrong series from the lookup service, use the manual title override in the web UI. The disc label parsing will still work with your corrected title, and both the parent folder and disc folder will update accordingly.

### 5. Test Before Processing Your Library
Try ripping a test disc with both features enabled to verify the folder structure matches your expectations before processing your entire library.

### 6. Media Server Compatibility
The grouped structure works well with:
- **Plex**: Recognizes series folders with season subfolders
- **Emby/Jellyfin**: Handles nested series structures
- **Kodi**: Supports multi-folder series organization

Test with your specific media server to ensure proper detection.

## Troubleshooting

### Problem: Discs not grouped under parent folder

**Check:**
1. `GROUP_TV_DISCS_UNDER_SERIES: true` in `arm.yaml`
2. Job video_type is "series"
3. ARM has been restarted after configuration change

**Solution:** Check ARM logs for:
```
Grouping TV discs under series folder: 'Breaking Bad (2008)'
```

If not present, verify configuration and restart ARM.

### Problem: Folder names still use standard format

**Check:**
1. `USE_DISC_LABEL_FOR_TV: true` in `arm.yaml`
2. Job video_type is "series" (not "movie" or "unknown")
3. Disc label contains a valid season/disc pattern
4. ARM logs for parsing messages

**Solution:** Check ARM logs for messages like:
```
Using disc label-based folder name: 'Breaking_Bad_S1D1' (from series 'Breaking Bad' and label 'BB_S1D1')
```

Or:
```
Could not parse disc identifier from label 'INVALID', falling back to standard naming
```

### Problem: Parent folder has wrong title

**Check:** The series title from the metadata lookup or manual title field.

**Solution:** 
- Use the ARM web UI to set a manual title before ripping
- Both the parent folder and disc folder will use the updated title
- Verify OMDb/TMDb API is returning correct metadata

### Problem: Disc identifier not detected

**Check:** Your disc label format against the supported patterns above.

**Solution:**
- Relabel your disc using a supported format (e.g., `SeriesName_S01_D01`)
- ARM will fall back to standard naming if parsing fails
- With grouping enabled, fallback folders will still be organized under the parent

### Problem: Duplicate parent folders with slight differences

**Check:** Series title consistency across multiple rips.

**Solution:**
- Ensure all discs from the same series use the same title (manual or auto)
- Use manual title override if metadata lookup returns inconsistent results
- Parent folder is based on `{Title} ({Year})`, so both must match

### Problem: Mixed folder structures in existing library

**Scenario:** You have existing TV series ripped without these features.

**Solution:**
1. For new series: Enable both features for organized structure
2. For existing series: 
   - Leave old rips as-is
   - Enable features only for new series
   - Or manually reorganize existing folders to match new structure

## Technical Details

### Folder Structure Logic

ARM constructs folder paths differently based on configuration:

1. **Both Features Enabled:**
   ```
   {COMPLETED_PATH}/{type}/({parent_folder})/{disc_folder}/
   Example: /media/tv/Breaking Bad (2008)/Breaking_Bad_S1D1/
   ```

2. **Disc Label Only:**
   ```
   {COMPLETED_PATH}/{type}/{disc_folder}/
   Example: /media/tv/Breaking_Bad_S1D1/
   ```

3. **Grouping Only:**
   ```
   {COMPLETED_PATH}/{type}/{parent_folder}/{disc_folder_with_timestamp}/
   Example: /media/tv/Breaking Bad (2008)/Breaking Bad (2008)_20231015_143022/
   ```

4. **Neither Feature:**
   ```
   {COMPLETED_PATH}/{type}/{standard_folder}/
   Example: /media/tv/Breaking Bad (2008)/
   ```

### Parsing Priority

ARM tries patterns in this order:
1. Compact S##[E##]D## format (fastest)
2. Season/Disc word format
3. Separate S## and D## tokens (most flexible)

### Configuration Location

The features are controlled by two booleans in `arm.yaml`:

**USE_DISC_LABEL_FOR_TV:**
- **Type:** Boolean
- **Default:** `false`
- **Scope:** Applies only to video_type "series"
- **Purpose:** Controls disc folder naming

**GROUP_TV_DISCS_UNDER_SERIES:**
- **Type:** Boolean
- **Default:** `false`
- **Scope:** Applies only to video_type "series"
- **Purpose:** Controls parent folder grouping

### Database Storage

Both configuration values are stored per-job in the `config` table. This ensures:
- Configuration changes don't affect in-progress jobs
- Each disc ripped with its original settings
- Consistent folder structure across multi-disc series

### Logging

ARM logs all folder construction activity:
- Disc label parsing with extracted identifiers
- Parent folder creation when grouping is enabled
- Fallback scenarios with reasons
- Series name normalization steps

Check your ARM logs (default: `/home/arm/logs/`) for detailed information.

**Example Log Messages:**
```
Grouping TV discs under series folder: 'Breaking Bad (2008)'
Using disc label-based folder name: 'Breaking_Bad_S1D1' (from series 'Breaking Bad' and label 'BB_S01_D01')
Could not parse disc identifier from label 'INVALID', falling back to standard naming
```

## See Also

- [ARM Configuration Guide](Config-arm.yaml.md)
- [Web UI Job Management](Web-Jobs.md)
- [Troubleshooting Guide](General-Troubleshooting.md)
