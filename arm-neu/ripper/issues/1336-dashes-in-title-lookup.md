# #1336 — Dashes/underscores in disc labels break title lookup

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1336
**Priority:** Low
**Verdict:** LARGELY FIXED — arm_matcher compound word fallback handles matching correctly; only sequel disambiguation margins reduced

## Problem

Disc labels like `The-Batman`, `The-Boondock-Saints`, `The-Fox-and-the-Hound` fail to match metadata because hyphens aren't replaced with spaces before the API query. Users report manually editing the title to remove dashes resolves the issue.

## Upstream Reports

- **Multiple users** with specific disc labels containing hyphens
- One commenter noted Jellyfin also struggles with these filenames
- Simple reproducible issue — any disc label with hyphens fails initial lookup

## Root Cause (Upstream)

Upstream ARM uses simple string comparison for matching API results to disc labels. When a disc label contains hyphens (`The-Boondock-Saints`) but the API result has spaces (`The Boondock Saints`), the comparison fails.

## Our Fork's Status

**Largely fixed.** Verified empirically (2025-02-25):

### API Query — NOT a problem
OMDb handles hyphens in search queries identically to spaces:
- `?s=The-Batman` → 44 results, correct top match ✓
- `?s=The+Batman` → 232 results, correct top match ✓
- `?s=The%2BBatman` → 44 results, correct top match ✓

The `_search_metadata()` regex at `identify.py:158` (`re.sub('[_ ]', "+", ...)`) preserving hyphens is harmless — OMDb treats them as word separators anyway.

### Scoring — Works via compound word fallback
`arm_matcher.py`'s `title_similarity()` has a compound word fallback (line 286) that activates when token overlap is zero (which happens when the label is one hyphenated token). Scores for all tested cases exceed the 0.6 confidence threshold:

| Label | API Title | Score | Correct? |
|-------|-----------|-------|----------|
| `the-batman` | The Batman | 0.95 | ✓ |
| `the-boondock-saints` | The Boondock Saints | 0.94 | ✓ |
| `spider-man-2` | Spider-Man 2 | 0.91 | ✓ (highest) |
| `x-men-first-class` | X-Men: First Class | 0.90 | ✓ (highest) |

### Remaining weakness — Narrower sequel discrimination
The compound word fallback uses character-level SequenceMatcher instead of token overlap, giving narrower margins between correct and wrong sequels:

| | Correct (Spider-Man 2) | Runner-up | Gap |
|---|---|---|---|
| Hyphenated label | 0.91 | 0.86 | 0.05 |
| Fixed label (spaces) | 1.00 | 0.77 | **0.23** |

Token overlap (60% weight in blended path) provides much stronger sequel disambiguation, but it's bypassed when the label is one hyphenated token.

### Cosmetic: `_apply_label_as_title`
The last-resort fallback at `identify.py:182` produces `The-Boondock-Saints` instead of `The Boondock Saints`. However, replacing hyphens here would degrade legitimate titles like `Spider-Man` → `Spider Man`.

## Suggested Fix

One change in `arm_matcher.py` for improved robustness:

**`arm/ripper/arm_matcher.py:138`** — add `s = s.replace('-', ' ')` after the underscore replace:
```python
s = s.replace('_', ' ')
s = s.replace('-', ' ')  # Treat hyphens as word separators
```

This routes through the token overlap path instead of compound word fallback, giving:
- Perfect 1.0 scores for exact matches
- 4.6x better sequel disambiguation margins
- No regression for legitimate hyphenated titles (API returns canonical form)

**NOT recommended:**
- `identify.py:158` — no change needed (OMDb handles hyphens)
- `identify.py:182` — no change (would degrade `Spider-Man` display title)
