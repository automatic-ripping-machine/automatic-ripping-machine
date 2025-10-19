# Using Disc Label for TV Series Output Folders

## Overview

ARM includes an opt-in feature to use disc labels for creating deterministic, organized folder names for TV series. This feature is particularly useful for:

- External batch renamers and automated importers
- Consistent, predictable folder structures
- Workflows that rely on disc-level identification
- Multi-disc TV series where each disc should have a unique folder

## How It Works

### Default Behavior (Feature Disabled)

By default, ARM creates folders for TV series using:
```
{Series Title} ({Year})
```
Example: `Breaking Bad (2008)`

If a folder already exists, ARM appends a timestamp to create a unique folder name.

### With Disc Label Feature (Feature Enabled)

When enabled, ARM intelligently combines:
- **Standardized series name** from the lookup service (OMDb/TMDb) or manual title
- **Season/disc identifier** parsed from the disc volume label

Result:
```
{Normalized_Series_Name}_{SxDx}
```
Example: `Breaking_Bad_S1D1`

## Configuration

### Enable the Feature

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

### Example 1: Standard Label Format
**Disc Label:** `BB_S01_D01`  
**Series from Lookup:** Breaking Bad  
**Output Folder:** `Breaking_Bad_S1D1`

### Example 2: Word Format
**Disc Label:** `SEASON_02_DISC_03`  
**Series from Lookup:** Game of Thrones  
**Output Folder:** `Game_of_Thrones_S2D3`

### Example 3: Manual Title Override
**Disc Label:** `S01D01`  
**Manual Title Set:** Breaking Bad (US)  
**Output Folder:** `Breaking_Bad_(US)_S1D1`

### Example 4: Fallback Scenario
**Disc Label:** `NO_IDENTIFIER_HERE`  
**Series from Lookup:** The Office  
**Lookup Year:** 2005  
**Output Folder:** `The Office (2005)` _(standard fallback naming)_

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

## Duplicate Folder Handling

Even with disc label-based naming, ARM's existing duplicate detection still applies:

- If `ALLOW_DUPLICATES: false` and the disc is detected as a duplicate, the job will fail
- If `ALLOW_DUPLICATES: true` or the disc is not a duplicate:
  - ARM creates the folder with the disc label-based name
  - If the folder already exists, ARM appends a timestamp to ensure uniqueness

## Best Practices

### 1. Consistent Disc Labeling
For best results, label your discs consistently:
- ✅ Good: `BreakingBad_S01_D01`, `BreakingBad_S01_D02`, `BreakingBad_S02_D01`
- ❌ Avoid: Random labels without season/disc information

### 2. Enable ALLOW_DUPLICATES for Series
```yaml
ALLOW_DUPLICATES: true
```
This is recommended for TV series to allow re-ripping if needed.

### 3. Use Manual Title Override for Ambiguous Series
If ARM picks the wrong series from the lookup service, use the manual title override in the web UI. The disc label parsing will still work with your corrected title.

### 4. Test Before Enabling
Try ripping a test disc with the feature enabled to verify folder names match your expectations before processing your entire library.

## Troubleshooting

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

### Problem: Incorrect series name in folder

**Check:** The series title from the metadata lookup or manual title field.

**Solution:** 
- Use the ARM web UI to set a manual title before ripping
- Verify OMDb/TMDb API is returning correct metadata

### Problem: Disc identifier not detected

**Check:** Your disc label format against the supported patterns above.

**Solution:**
- Relabel your disc using a supported format (e.g., `SeriesName_S01_D01`)
- ARM will fall back to standard naming if parsing fails

## Technical Details

### Parsing Priority

ARM tries patterns in this order:
1. Compact S##[E##]D## format (fastest)
2. Season/Disc word format
3. Separate S## and D## tokens (most flexible)

### Configuration Location

The feature is controlled by a single boolean in `arm.yaml`:
- **Key:** `USE_DISC_LABEL_FOR_TV`
- **Type:** Boolean
- **Default:** `false`
- **Scope:** Applies only to video_type "series"

### Logging

ARM logs all disc label parsing activity:
- Successful parsing with extracted identifiers
- Fallback scenarios with reasons
- Series name normalization steps

Check your ARM logs (default: `/home/arm/logs/`) for detailed information.

## See Also

- [ARM Configuration Guide](Config-arm.yaml.md)
- [Web UI Job Management](Web-Jobs.md)
- [Troubleshooting Guide](General-Troubleshooting.md)
