# #1294 — TV series loses season/disc info from label

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1294
**Priority:** Medium
**Verdict:** REAL BUG / design limitation — partially mitigated by `arm_matcher`, suffix still lost in paths

## Problem

When ripping TV series DVDs with labels like `STARGATE_ATLANTIS_S1_D2`, ARM produces a folder path of `Stargate Atlantis (2004-2009)` — losing the season and disc information (S1, D2). Multiple discs from the same series go to the same folder, causing file collisions (related to #1161).

## Upstream Reports

- **Multiple users:** ARM 2.10.0 through 2.18.3, various Ubuntu and Docker setups
- Disc labels like `The-Batman`, `STARGATE_ATLANTIS_S1_D2` all lose suffix info
- OMDb returning 401 Unauthorized causes everything to be classified as `unknown`
- Confirmed across multiple ARM versions

## Root Cause

The `identify_loop()` at `arm/ripper/identify.py:462-496` progressively strips words from the title until OMDB matches:

```python
while response is None and title.find("-") > 0:
    title = title.rsplit('-', 1)[0]        # strips S1_D2
```

When OMDB returns "Stargate Atlantis", the season/disc suffixes are discarded. The `formatted_title` property at `arm/models/job.py:346-353` does not incorporate label suffixes.

## Our Fork's Mitigations

- `arm_matcher.py` uses fuzzy matching and scoring for more accurate identification
- `job.label` is preserved separately from `job.title` (available to transcoder via `ARM_LABEL` env var)
- But `formatted_title` (used for `build_final_path()`) still discards suffix info

## Affected Code

- `arm/ripper/identify.py:462-496` — `identify_loop()` strips label suffixes
- `arm/models/job.py:346-353` — `formatted_title` doesn't include disc suffix
- `arm/ripper/identify.py:182` — `_apply_label_as_title()` only replaces underscores, not hyphens

## Suggested Fix

1. **Add `disc_suffix` property** to `Job` model at `arm/models/job.py`:
   ```python
   @property
   def disc_suffix(self):
       if not self.label:
           return ""
       match = re.search(r'[_\s](S\d+[_\s]*D\d+|D\d+|DISC[_\s]*\d+)$', self.label, re.IGNORECASE)
       return match.group(1).replace('_', ' ') if match else ""
   ```

2. **Incorporate suffix into `formatted_title`** for series type:
   ```python
   @property
   def formatted_title(self):
       title = self.title_manual if self.title_manual else self.title
       suffix = self.disc_suffix if self.video_type == "series" else ""
       if self.year and self.year != "0000" and self.year != "":
           base = f"{title} ({self.year})"
       else:
           base = f"{title}"
       return f"{base} {suffix}".strip() if suffix else base
   ```
