"""
Verify arm_matcher integration inside the running ARM container.

Tests the full update_job() → match_disc() pipeline with mock OMDb
search results, exercising the same code path that runs during disc
identification.

Usage (exec into container):
    docker exec arm-rippers python3 /opt/arm/dev-data/verify_matcher.py
"""

import sys
import os

# ── Bootstrap ARM config before any ARM imports ──────────────────────
os.environ.setdefault("ARM_CONFIG_FILE", "/etc/arm/config/arm.yaml")

# Ensure arm package is importable
sys.path.insert(0, "/opt/arm")

import arm.config.config as cfg

# Now we can import ARM modules
from arm.ripper.arm_matcher import (
    match_disc, parse_label, normalize_label, MatchResult, MatchSelection,
)

# ─────────────────────────────────────────────────────────────────────
# Test cases: (label, disc_year, type_hint, search_results, expected_title, expected_imdb)
# ─────────────────────────────────────────────────────────────────────

TMDB = "https://image.tmdb.org/t/p/original"

TESTS = [
    # 1. LOTR — the original production bug: parody at [0], correct at [1]
    {
        "name": "LOTR Fellowship (parody at Search[0])",
        "label": "LOTR_FELLOWSHIP_OF_THE_RING_P1",
        "disc_year": "2001",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "LOTR: the Pronouns of Power",
                    "Year": "2022",
                    "imdbID": "tt22262280",
                    "Type": "movie",
                    "Poster": "N/A",
                },
                {
                    "Title": "The Lord of the Rings: The Fellowship of the Ring",
                    "Year": "2001",
                    "imdbID": "tt0120737",
                    "Type": "movie",
                    "Poster": f"{TMDB}/6oom5QYQ2yQTMJIbnvbkBL9cHo6.jpg",
                },
                {
                    "Title": "Lord of the Rings",
                    "Year": "1978",
                    "imdbID": "tt0077869",
                    "Type": "movie",
                    "Poster": f"{TMDB}/someanimated.jpg",
                },
            ],
        },
        "expect_imdb": "tt0120737",
        "expect_title": "The Lord of the Rings: The Fellowship of the Ring",
    },

    # 2. Hotel Transylvania 3 — "3" must NOT be stripped as disc suffix
    {
        "name": "Hotel Transylvania 3 (sequel number preserved)",
        "label": "HOTEL_TRANSYLVANIA_3",
        "disc_year": "2018",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "Hotel Transylvania 2",
                    "Year": "2015",
                    "imdbID": "tt2510894",
                    "Type": "movie",
                    "Poster": f"{TMDB}/ht2.jpg",
                },
                {
                    "Title": "Hotel Transylvania 3: Summer Vacation",
                    "Year": "2018",
                    "imdbID": "tt5220122",
                    "Type": "movie",
                    "Poster": f"{TMDB}/ht3.jpg",
                },
                {
                    "Title": "Hotel Transylvania",
                    "Year": "2012",
                    "imdbID": "tt0837562",
                    "Type": "movie",
                    "Poster": f"{TMDB}/ht1.jpg",
                },
            ],
        },
        "expect_imdb": "tt5220122",
        "expect_title": "Hotel Transylvania 3: Summer Vacation",
    },

    # 3. Blade Runner 2049 — year-in-title must NOT be extracted
    {
        "name": "Blade Runner 2049 (year-like number in title)",
        "label": "BLADE_RUNNER_2049",
        "disc_year": "2017",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "Blade Runner",
                    "Year": "1982",
                    "imdbID": "tt0083658",
                    "Type": "movie",
                    "Poster": f"{TMDB}/br1.jpg",
                },
                {
                    "Title": "Blade Runner 2049",
                    "Year": "2017",
                    "imdbID": "tt1856101",
                    "Type": "movie",
                    "Poster": f"{TMDB}/br2049.jpg",
                },
            ],
        },
        "expect_imdb": "tt1856101",
        "expect_title": "Blade Runner 2049",
    },

    # 4. Ant-Man — compound word (ANTMAN → "ant man")
    {
        "name": "Ant-Man (compound word matching)",
        "label": "ANTMAN",
        "disc_year": "2015",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "Ant-Man",
                    "Year": "2015",
                    "imdbID": "tt0478970",
                    "Type": "movie",
                    "Poster": f"{TMDB}/antman.jpg",
                },
                {
                    "Title": "Ant-Man and the Wasp",
                    "Year": "2018",
                    "imdbID": "tt5095030",
                    "Type": "movie",
                    "Poster": f"{TMDB}/antman2.jpg",
                },
            ],
        },
        "expect_imdb": "tt0478970",
        "expect_title": "Ant-Man",
    },

    # 5. Fargo — type_hint breaks tie (movie vs series)
    {
        "name": "Fargo (type hint: movie wins over series)",
        "label": "FARGO",
        "disc_year": "1996",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "Fargo",
                    "Year": "2014–",
                    "imdbID": "tt2802850",
                    "Type": "series",
                    "Poster": f"{TMDB}/fargo_series.jpg",
                },
                {
                    "Title": "Fargo",
                    "Year": "1996",
                    "imdbID": "tt0116282",
                    "Type": "movie",
                    "Poster": f"{TMDB}/fargo_movie.jpg",
                },
            ],
        },
        "expect_imdb": "tt0116282",
        "expect_title": "Fargo",
    },

    # 6. No match — all results are unrelated
    {
        "name": "No confident match (all unrelated)",
        "label": "SERIAL_MOM",
        "disc_year": "1994",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "Finding Nemo",
                    "Year": "2003",
                    "imdbID": "tt0266543",
                    "Type": "movie",
                    "Poster": f"{TMDB}/nemo.jpg",
                },
                {
                    "Title": "The Avengers",
                    "Year": "2012",
                    "imdbID": "tt0848228",
                    "Type": "movie",
                    "Poster": f"{TMDB}/avengers.jpg",
                },
            ],
        },
        "expect_imdb": None,
        "expect_title": None,
    },

    # 7. Multi-disc: disc suffix stripped, title preserved
    {
        "name": "Back to the Future Disc 1 (disc suffix stripped)",
        "label": "BACK_TO_THE_FUTURE_DISC_1",
        "disc_year": "1985",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "Back to the Future",
                    "Year": "1985",
                    "imdbID": "tt0088763",
                    "Type": "movie",
                    "Poster": f"{TMDB}/bttf.jpg",
                },
                {
                    "Title": "Back to the Future Part II",
                    "Year": "1989",
                    "imdbID": "tt0096874",
                    "Type": "movie",
                    "Poster": f"{TMDB}/bttf2.jpg",
                },
            ],
        },
        "expect_imdb": "tt0088763",
        "expect_title": "Back to the Future",
    },

    # 8. Dune Part Two — PART preserved in title (not a disc suffix)
    {
        "name": "Dune Part Two (PART preserved in title)",
        "label": "DUNE_PART_TWO",
        "disc_year": "2024",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "Dune",
                    "Year": "2021",
                    "imdbID": "tt1160419",
                    "Type": "movie",
                    "Poster": f"{TMDB}/dune1.jpg",
                },
                {
                    "Title": "Dune: Part Two",
                    "Year": "2024",
                    "imdbID": "tt15239678",
                    "Type": "movie",
                    "Poster": f"{TMDB}/dune2.jpg",
                },
            ],
        },
        "expect_imdb": "tt15239678",
        "expect_title": "Dune: Part Two",
    },

    # 9. Poster "N/A" normalization
    {
        "name": "Poster N/A → None normalization",
        "label": "THE_MATRIX",
        "disc_year": "1999",
        "type_hint": "movie",
        "search": {
            "Search": [
                {
                    "Title": "The Matrix",
                    "Year": "1999",
                    "imdbID": "tt0133093",
                    "Type": "movie",
                    "Poster": "N/A",
                },
            ],
        },
        "expect_imdb": "tt0133093",
        "expect_title": "The Matrix",
        "expect_poster_none": True,
    },

    # 10. Empty search results
    {
        "name": "Empty search (no Search key)",
        "label": "SOME_DISC",
        "disc_year": None,
        "type_hint": None,
        "search": {"Response": "False", "Error": "Movie not found!"},
        "expect_imdb": None,
        "expect_title": None,
    },
]


def _check_no_match(i, name, selection):
    """Validate a test expecting no match. Returns (passed, error_msg)."""
    if selection.best is None:
        print(f"  ✓ {i:2d}. {name}")
        return True, None
    msg = (
        f"  ✗ {i:2d}. {name}\n"
        f"       Expected: no match\n"
        f"       Got: {selection.best.title} ({selection.best.imdb_id}) "
        f"score={selection.best.score:.3f}"
    )
    print(msg)
    return False, msg


def _check_expected_match(i, name, test, selection):
    """Validate a test expecting a specific match. Returns (passed, error_msg)."""
    if selection.best is None:
        msg = (
            f"  ✗ {i:2d}. {name}\n"
            f"       Expected: {test['expect_title']} ({test['expect_imdb']})\n"
            f"       Got: no match (hasnicetitle=False)\n"
            f"       Top scores: {[(m.title, f'{m.score:.3f}') for m in selection.all_scored[:3]]}"
        )
        print(msg)
        return False, msg
    if selection.best.imdb_id != test["expect_imdb"]:
        msg = (
            f"  ✗ {i:2d}. {name}\n"
            f"       Expected: {test['expect_title']} ({test['expect_imdb']})\n"
            f"       Got: {selection.best.title} ({selection.best.imdb_id}) "
            f"score={selection.best.score:.3f}"
        )
        print(msg)
        return False, msg
    # Correct match — check poster normalization
    if test.get("expect_poster_none") and selection.best.poster_url is not None:
        msg = (
            f"  ✗ {i:2d}. {name}\n"
            f"       Match correct but poster_url not None: {selection.best.poster_url!r}"
        )
        print(msg)
        return False, msg

    extra = " [poster=None ✓]" if test.get("expect_poster_none") else ""
    if selection.label_info and selection.label_info.disc_number is not None:
        li = selection.label_info
        extra += f" [disc#{li.disc_number} type={li.disc_type}]"
    print(f"  ✓ {i:2d}. {name} → score={selection.best.score:.3f}{extra}")
    return True, None


def _run_match_tests(errors):
    """Run disc matching tests. Returns (passed, failed)."""
    passed = failed = 0
    for i, test in enumerate(TESTS, 1):
        name = test["name"]
        try:
            selection = match_disc(
                test["label"], test["search"],
                disc_year=test.get("disc_year"), type_hint=test.get("type_hint"),
            )
            if test["expect_imdb"] is None:
                ok, msg = _check_no_match(i, name, selection)
            else:
                ok, msg = _check_expected_match(i, name, test, selection)
            if ok:
                passed += 1
            else:
                errors.append(msg)
                failed += 1
        except Exception as e:
            msg = f"  ✗ {i:2d}. {name}\n       ERROR: {e}"
            print(msg)
            errors.append(msg)
            failed += 1
    return passed, failed


def _run_label_tests(errors):
    """Run parse_label validation tests. Returns (passed, failed)."""
    print("\n  Label parsing checks:")
    label_tests = [
        ("LOTR_FELLOWSHIP_OF_THE_RING_P1", "lotr fellowship of the ring", 1, "disc"),
        ("HOTEL_TRANSYLVANIA_3", "hotel transylvania 3", None, None),
        ("BLADE_RUNNER_2049", "blade runner 2049", None, None),
        ("BACK_TO_THE_FUTURE_DISC_1", "back to the future", 1, "disc"),
        ("DUNE_PART_TWO", "dune part two", None, None),
        ("STAR_WARS_BONUS", "star wars", None, "bonus"),
        ("ALIEN_16x9", "alien", None, None),
    ]
    passed = failed = 0
    for raw, exp_title, exp_num, exp_type in label_tests:
        info = parse_label(raw)
        if info.title == exp_title and info.disc_number == exp_num and info.disc_type == exp_type:
            suffix = ""
            if info.disc_number is not None:
                suffix = f" [disc#{info.disc_number}]"
            elif info.disc_type is not None:
                suffix = f" [{info.disc_type}]"
            print(f"  ✓ {raw} → \"{info.title}\"{suffix}")
            passed += 1
        else:
            msg = (
                f"  ✗ {raw}\n"
                f"       Expected: title=\"{exp_title}\" num={exp_num} type={exp_type}\n"
                f"       Got:      title=\"{info.title}\" num={info.disc_number} type={info.disc_type}"
            )
            print(msg)
            errors.append(msg)
            failed += 1
    return passed, failed


def run_tests():
    """Run all matcher integration tests."""
    errors = []
    p1, f1 = _run_match_tests(errors)
    p2, f2 = _run_label_tests(errors)

    passed = p1 + p2
    failed = f1 + f2
    total = passed + failed
    print(f"\n{'='*60}")
    if failed == 0:
        print(f"  ALL {total} CHECKS PASSED")
    else:
        print(f"  {passed}/{total} passed, {failed} FAILED")
        print()
        for e in errors:
            print(e)
    print(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("  ARM Disc Matcher — Integration Verification")
    print("=" * 60)
    print()

    # Verify the module is imported from the right place
    import arm.ripper.arm_matcher as mod
    print(f"  Module: {mod.__file__}")
    print()

    success = run_tests()
    sys.exit(0 if success else 1)
