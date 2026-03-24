"""
Standalone disc title matcher for ARM (Automatic Ripping Machine).

Scores API search results against a disc label using string similarity,
year proximity, and type consistency. Picks the best match above a
confidence threshold — replacing ARM's blind Search[0] selection.

Zero ARM dependencies — can be tested and developed in isolation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class LabelInfo:
    """Parsed disc label with title and disc metadata."""
    title: str               # normalized title: "lotr fellowship of the ring"
    disc_number: int | None  # 1, 2, etc. (None if not a numbered disc)
    disc_type: str | None    # "part", "disc", "bonus", "extras", "special_features"
    raw_label: str           # original input: "LOTR_FELLOWSHIP_OF_THE_RING_P1"
    disc_total: int | None = None     # total discs in set (from "Disc N of M")
    season_number: int | None = None  # 1, 2, etc. (None if not a TV season disc)

    @property
    def disc_identifier(self) -> str | None:
        """Format season/disc as a compact identifier (e.g. 'S1D1', 'S2', 'D3').

        Returns None when neither season nor disc number is available.
        """
        if self.season_number is not None and self.disc_number is not None:
            return f"S{self.season_number}D{self.disc_number}"
        if self.season_number is not None:
            return f"S{self.season_number}"
        if self.disc_number is not None:
            return f"D{self.disc_number}"
        return None


@dataclass
class MatchResult:
    """A single scored API result."""
    title: str
    year: str
    type: str           # "movie", "series", "episode", etc.
    imdb_id: str
    poster_url: str | None  # None when unavailable (OMDb "N/A" normalized)
    score: float        # 0.0–1.0 composite
    title_score: float
    year_score: float
    type_score: float
    confident: bool     # score >= threshold
    raw_result: dict | None = None  # original search result dict for extra fields


@dataclass
class MatchSelection:
    """Result of scoring all API results for a disc."""
    best: MatchResult | None
    all_scored: list[MatchResult]
    hasnicetitle: bool
    label_info: LabelInfo | None = None


# ---------------------------------------------------------------------------
# Label normalization
# ---------------------------------------------------------------------------

# Numbered disc suffix: P1, D2, DISC1, DISC_1, etc.
# Captures (type_keyword, number) for LabelInfo.
# Won't match "Hotel Transylvania 3" because 3 isn't preceded by P/D/DISC.
# NOTE: PART is intentionally excluded — "PART_2" is usually title content
# (e.g., "The Godfather Part II", "Dune: Part Two"), not a disc indicator.
# Studios use P1/D1/DISC_1 for physical disc numbering.
_DISC_SUFFIX_RE = re.compile(
    r'[\s_-](P|D|DISC)[\s_-]?(\d+)(?:[\s_-](?:OF|of)[\s_-]?(\d+))?$',
    re.IGNORECASE,
)

# Word-number disc suffixes: DISC_ONE, DISC_TWO, etc.
# Only DISC — PART_ONE/PART_TWO is ambiguous (could be movie title).
_WORD_NUMBERS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
}
_DISC_WORD_SUFFIX_RE = re.compile(
    r'[\s_-](DISC)[\s_-](' + '|'.join(_WORD_NUMBERS) + r')$',
    re.IGNORECASE,
)

# Unnumbered special disc types at end of string
_SPECIAL_DISC_RE = re.compile(
    r'[\s_-](BONUS[\s_-]?DISC|BONUS|EXTRAS|SPECIAL[\s_-]?FEATURES|SUPPLEMENTAL)$',
    re.IGNORECASE,
)

# Season + disc combined: S1D1, S1_D1, S1_DISC_1, S1 D2, etc.
# Must be checked BEFORE the disc-only regex to avoid leaving "S1" behind.
_SEASON_DISC_RE = re.compile(
    r'[\s_-]S(\d+)[\s_-]?(D|DISC)[\s_-]?(\d+)$',
    re.IGNORECASE,
)

# Season-only suffix: S1, S2, SEASON_1, SEASON 2, etc.
# Requires separator before S to avoid matching "ALIAS" or "COSMOS".
_SEASON_SUFFIX_RE = re.compile(
    r'[\s_-]S(\d+)$',
    re.IGNORECASE,
)

# SEASON keyword: SEASON_1, SEASON 2, SEASON1, etc.
_SEASON_KEYWORD_RE = re.compile(
    r'[\s_-]SEASON[\s_-]?(\d+)$',
    re.IGNORECASE,
)

# SKU patterns at end of string
_SKU_RE = re.compile(r'\s*SKU\w*', re.IGNORECASE)

# Aspect ratio markers
_ASPECT_RE = re.compile(r'\b16[xX]9\b')

# Blu-ray branding suffixes (various capitalizations)
_BLURAY_SUFFIXES = [
    ' - Blu-rayTM', ' Blu-rayTM',
    ' - BLU-RAYTM', ' - BLU-RAY', ' - Blu-ray',
    ' Blu-ray', ' BLU-RAY',
]


def _classify_special_disc(raw_type):
    """Classify a special disc type string into a disc_type value."""
    normalized = re.sub(r'[\s_-]+', '_', raw_type.lower())
    if 'bonus' in normalized:
        return 'bonus'
    if 'extras' in normalized:
        return 'extras'
    if 'special' in normalized:
        return 'special_features'
    if 'supplemental' in normalized:
        return 'supplemental'
    return None


def _extract_disc_suffix(s):
    """Extract disc number/type/total from the label string.

    Returns (remaining_string, disc_number, disc_type, disc_total).
    """
    # Word-number suffixes first (DISC_ONE)
    m = _DISC_WORD_SUFFIX_RE.search(s)
    if m:
        keyword = m.group(1).lower()
        disc_type = 'part' if keyword == 'part' else 'disc'
        return s[:m.start()], _WORD_NUMBERS[m.group(2).lower()], disc_type, None

    # Numeric suffixes (P1, D2, DISC_1, DISC 4 OF 4)
    m = _DISC_SUFFIX_RE.search(s)
    if m:
        disc_total = int(m.group(3)) if m.group(3) else None
        return s[:m.start()], int(m.group(2)), 'disc', disc_total

    # Special disc types (BONUS, EXTRAS, SPECIAL_FEATURES)
    m = _SPECIAL_DISC_RE.search(s)
    if m:
        disc_type = _classify_special_disc(m.group(1))
        if disc_type:
            return s[:m.start()], None, disc_type, None

    return s, None, None, None


def _extract_season_suffix(s):
    """Extract season number from trailing season indicator.

    Returns (remaining_string, season_number).
    """
    m = _SEASON_KEYWORD_RE.search(s)
    if m:
        return s[:m.start()], int(m.group(1))
    m = _SEASON_SUFFIX_RE.search(s)
    if m:
        return s[:m.start()], int(m.group(1))
    return s, None


def parse_label(raw_label: str) -> LabelInfo:
    """
    Parse a disc label into a normalized title and disc metadata.

    Returns a LabelInfo with the cleaned title plus disc_number and disc_type
    when a disc/part suffix is detected.

    Years are NOT extracted — numbers like 2049, 1984, 1918 can be
    movie titles and cannot be reliably distinguished from release years.
    """
    if not raw_label:
        return LabelInfo(title='', disc_number=None, disc_type=None, raw_label=raw_label)

    s = raw_label
    disc_number = None
    disc_type = None
    disc_total = None
    season_number = None

    # 1-4. Basic cleanup
    s = s.replace('_', ' ')
    s = _ASPECT_RE.sub('', s)
    s = _SKU_RE.sub('', s)
    for suffix in _BLURAY_SUFFIXES:
        s = s.replace(suffix, '')

    # Treat hyphens and dots as word separators (after suffix removal to
    # preserve literal hyphens in _BLURAY_SUFFIXES like ' - Blu-rayTM')
    s = s.replace('-', ' ')
    s = s.replace('.', ' ')

    # 5a. Extract season+disc combined suffixes (S1D1, S1_D1)
    m = _SEASON_DISC_RE.search(s)
    if m:
        season_number = int(m.group(1))
        disc_number = int(m.group(3))
        disc_type = 'disc'
        s = s[:m.start()]
    else:
        # 5b. Extract disc-only suffixes (including "Disc N of M")
        s, disc_number, disc_type, disc_total = _extract_disc_suffix(s)
        # 5c. Extract season-only suffixes
        s, season_number = _extract_season_suffix(s)

    # 6. Collapse whitespace, strip, lowercase
    title = re.sub(r'\s+', ' ', s).strip().lower()

    return LabelInfo(
        title=title,
        disc_number=disc_number,
        disc_type=disc_type,
        raw_label=raw_label,
        disc_total=disc_total,
        season_number=season_number,
    )


def normalize_label(raw_label: str) -> str:
    """
    Clean a disc label for comparison. Returns just the normalized title.

    For disc metadata (disc number, type), use parse_label() instead.
    """
    return parse_label(raw_label).title


def normalize_api_title(raw_title: str) -> str:
    """
    Normalize an API result title for comparison.

    Strips punctuation so "The Lord of the Rings: The Fellowship of the Ring"
    and "lotr fellowship of the ring" can be compared fairly.
    """
    if not raw_title:
        return ''

    s = raw_title

    # Replace punctuation with spaces
    s = re.sub(r'[:\-&/]', ' ', s)

    # Remove other non-alphanumeric (keep spaces)
    s = re.sub(r"[^\w\s]", '', s)

    # Collapse whitespace, strip, lowercase
    s = re.sub(r'\s+', ' ', s).strip().lower()

    return s


def _tokenize(s: str) -> set[str]:
    """Split a normalized string into a set of lowercase tokens."""
    return set(s.split()) if s else set()


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def title_similarity(label: str, api_title: str) -> float:
    """
    Compare a normalized label to a normalized API title.

    Blends SequenceMatcher ratio with token overlap. Token overlap is
    weighted heavily so that sequel numbers (e.g., "3" in
    "Hotel Transylvania 3") and keyword matches beat character-level
    similarity against wrong sequels.

    When token overlap is zero (compound words like "antman" vs "ant man"),
    falls back to space-stripped character comparison.
    """
    if not label or not api_title:
        return 0.0

    # Full string ratio
    ratio = SequenceMatcher(None, label, api_title).ratio()

    # Token overlap: what fraction of label tokens appear in the API title
    label_tokens = _tokenize(label)
    api_tokens = _tokenize(api_title)

    if label_tokens:
        overlap = len(label_tokens & api_tokens) / len(label_tokens)
    else:
        overlap = 0.0

    # Compound word fallback: when no tokens match, the label may be a
    # single concatenated word (e.g., "antman" from Ant-Man, "faceoff"
    # from Face/Off). Compare with spaces stripped so "antman" == "antman".
    if abs(overlap) < 1e-9 and label_tokens:
        nospace_ratio = SequenceMatcher(
            None, label.replace(' ', ''), api_title.replace(' ', ''),
        ).ratio()
        return nospace_ratio

    # Blend: token overlap weighted heavily to distinguish sequels
    # and handle abbreviated labels
    return 0.4 * ratio + 0.6 * overlap


def year_proximity(disc_year: str | None, result_year: str | None) -> float:
    """
    Score year match between disc and API result.

    Returns 0.0–1.0.
    """
    if not disc_year or not result_year:
        return 0.5  # neutral when we don't have year info

    try:
        dy = int(disc_year)
        ry = int(re.sub(r'\D.*', '', str(result_year)))  # "2001–2003" → 2001
    except (ValueError, TypeError):
        return 0.5

    delta = abs(dy - ry)
    if delta == 0:
        return 1.0
    if delta == 1:
        return 0.8
    if delta == 2:
        return 0.5
    return 0.0


def type_consistency(type_hint: str | None, result_type: str | None) -> float:
    """
    Score whether the result type matches the expected type.

    type_hint: "movie" or "series" (from config VIDEOTYPE or prior identification)
    result_type: "movie", "series", "episode", etc.
    """
    if not type_hint or type_hint == 'auto' or not result_type:
        return 0.5  # neutral

    hint = type_hint.lower()
    rtype = result_type.lower()

    # Normalize "tv series" / "tv mini series" → "series"
    if 'series' in rtype:
        rtype = 'series'

    if hint == rtype:
        return 1.0
    return 0.0


def _score_one(
    label_norm: str,
    disc_year: str | None,
    result: dict,
    type_hint: str | None,
    min_confidence: float,
) -> MatchResult:
    """Score a single API result against the disc label."""
    result_title = result.get('Title', '')
    from arm.ripper.utils import extract_year
    result_year = extract_year(result.get('Year', ''))
    result_type = result.get('Type', '')
    result_imdb = result.get('imdbID', '')
    result_poster = result.get('Poster') or None
    if result_poster == 'N/A':
        result_poster = None

    api_norm = normalize_api_title(result_title)

    ts = title_similarity(label_norm, api_norm)
    ys = year_proximity(disc_year, result_year)
    tc = type_consistency(type_hint, result_type)

    # When no disc year is available, title drives the score
    if disc_year:
        composite = 0.70 * ts + 0.25 * ys + 0.05 * tc
    else:
        composite = 0.90 * ts + 0.05 * ys + 0.05 * tc

    return MatchResult(
        title=result_title,
        year=result_year,
        type=result_type,
        imdb_id=result_imdb,
        poster_url=result_poster,
        score=composite,
        title_score=ts,
        year_score=ys,
        type_score=tc,
        confident=composite >= min_confidence,
        raw_result=result,
    )


def score_results(
    label: str,
    year: str | None,
    results: list[dict],
    *,
    type_hint: str | None = None,
    min_confidence: float = 0.6,
) -> MatchSelection:
    """
    Score all API search results against a disc label.

    :param label: Normalized disc label (output of normalize_label)
    :param year: Year extracted from disc (or None)
    :param results: List of OMDb/TMDb Search result dicts
    :param type_hint: "movie", "series", or None
    :param min_confidence: Minimum score to accept a match
    :return: MatchSelection with best result and all scored results
    """
    if not results:
        return MatchSelection(best=None, all_scored=[], hasnicetitle=False)

    scored = [
        _score_one(label, year, r, type_hint, min_confidence)
        for r in results
    ]

    # Sort by score descending
    scored.sort(key=lambda m: m.score, reverse=True)

    best = scored[0] if scored and scored[0].confident else None

    return MatchSelection(
        best=best,
        all_scored=scored,
        hasnicetitle=best is not None,
    )


def match_disc(
    raw_label: str,
    search_results: dict | None,
    *,
    disc_year: str | None = None,
    type_hint: str | None = None,
    min_confidence: float = 0.6,
) -> MatchSelection:
    """
    Top-level convenience: parse label and score API results.

    :param raw_label: Raw disc label (e.g., "LOTR_FELLOWSHIP_OF_THE_RING_P1")
    :param search_results: OMDb/TMDb response dict with 'Search' key
    :param disc_year: Year from external source (e.g., Blu-ray XML timestamp)
    :param type_hint: "movie", "series", or None/"auto"
    :param min_confidence: Minimum score to accept (default 0.6)
    :return: MatchSelection (includes label_info with disc number/type)
    """
    label_info = parse_label(raw_label)

    if not search_results or 'Search' not in search_results:
        return MatchSelection(
            best=None, all_scored=[], hasnicetitle=False,
            label_info=label_info,
        )

    selection = score_results(
        label_info.title,
        disc_year,
        search_results['Search'],
        type_hint=type_hint,
        min_confidence=min_confidence,
    )
    selection.label_info = label_info
    return selection
