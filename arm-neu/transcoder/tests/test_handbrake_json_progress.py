"""Unit tests for the HandBrake --json progress parser.

HandBrakeCLI 1.10.2 does not emit the human `\\r12.3 % (45 fps)` progress
line when stdout is a pipe (no TTY), so the old %-scraping handler never
fired and the UI showed jobs as hung at 0%. The fix runs HandBrake with
--json and parses the multi-line `Progress: {...}` blocks. The stdout
reader feeds the handler ONE line at a time (it splits on \\r and \\n), so
the parser must accumulate a JSON block across calls.
"""
from __future__ import annotations


def _feed(parser, text: str):
    """Feed a multi-line block one line at a time; return the list of
    non-None results the parser yielded."""
    results = []
    for line in text.splitlines():
        out = parser.feed(line)
        if out is not None:
            results.append(out)
    return results


# A real HandBrake --json progress block.
PROGRESS_BLOCK = """Progress:
{
    "Progress": {
        "ETASeconds": 123,
        "Hours": 0,
        "Minutes": 2,
        "Pass": 1,
        "PassID": 0,
        "Paused": 0,
        "Progress": 0.4231,
        "Rate": 45.6,
        "RateAvg": 40.1,
        "Seconds": 3,
        "SequenceID": 0
    },
    "State": "WORKING"
}"""


def test_complete_block_returns_fraction_and_fps_once_on_close():
    from transcoder import _HandBrakeJsonProgress
    p = _HandBrakeJsonProgress()
    results = _feed(p, PROGRESS_BLOCK)
    assert len(results) == 1, f"expected exactly one result on block close, got {results}"
    fraction, fps = results[0]
    assert abs(fraction - 0.4231) < 1e-6
    assert abs(fps - 45.6) < 1e-6


def test_intermediate_lines_return_none():
    from transcoder import _HandBrakeJsonProgress
    p = _HandBrakeJsonProgress()
    lines = PROGRESS_BLOCK.splitlines()
    # every line except the last (closing brace) must return None
    for line in lines[:-1]:
        assert p.feed(line) is None
    # the final closing brace yields the result
    assert p.feed(lines[-1]) is not None


def test_rate_falls_back_to_rateavg_when_rate_zero():
    from transcoder import _HandBrakeJsonProgress
    block = PROGRESS_BLOCK.replace('"Rate": 45.6,', '"Rate": 0.0,')
    p = _HandBrakeJsonProgress()
    results = _feed(p, block)
    assert len(results) == 1
    _, fps = results[0]
    assert abs(fps - 40.1) < 1e-6, "Rate=0 should fall back to RateAvg"


def test_rate_falls_back_to_rateavg_when_rate_absent():
    from transcoder import _HandBrakeJsonProgress
    block = PROGRESS_BLOCK.replace('        "Rate": 45.6,\n', '')
    p = _HandBrakeJsonProgress()
    results = _feed(p, block)
    assert len(results) == 1
    _, fps = results[0]
    assert abs(fps - 40.1) < 1e-6


def test_non_progress_json_block_is_ignored():
    from transcoder import _HandBrakeJsonProgress
    version_block = """Version:
{
    "Arch": "x86_64",
    "Name": "HandBrake",
    "Official": true,
    "Version": {"Major": 1, "Minor": 10, "Point": 2}
}"""
    p = _HandBrakeJsonProgress()
    assert _feed(p, version_block) == []


def test_title_set_block_then_progress_block():
    """A JSON Title Set block (also emitted by --json) is ignored, and a
    following Progress block still parses."""
    from transcoder import _HandBrakeJsonProgress
    title_block = """JSON Title Set:
{
    "MainFeature": 0,
    "TitleList": [{"Index": 1, "Duration": {"Hours": 1}}]
}"""
    p = _HandBrakeJsonProgress()
    assert _feed(p, title_block) == []
    results = _feed(p, PROGRESS_BLOCK)
    assert len(results) == 1
    assert abs(results[0][0] - 0.4231) < 1e-6


def test_malformed_progress_json_resets_and_recovers():
    from transcoder import _HandBrakeJsonProgress
    bad = """Progress:
{
    "Progress": { this is not json }
}"""
    p = _HandBrakeJsonProgress()
    # malformed block must not raise and must yield nothing
    assert _feed(p, bad) == []
    # parser recovers on the next valid block
    results = _feed(p, PROGRESS_BLOCK)
    assert len(results) == 1
    assert abs(results[0][1] - 45.6) < 1e-6


def test_two_sequential_progress_blocks():
    from transcoder import _HandBrakeJsonProgress
    block2 = PROGRESS_BLOCK.replace('"Progress": 0.4231', '"Progress": 0.8765') \
                           .replace('"Rate": 45.6', '"Rate": 50.0')
    p = _HandBrakeJsonProgress()
    results = _feed(p, PROGRESS_BLOCK + "\n" + block2)
    assert len(results) == 2
    assert abs(results[0][0] - 0.4231) < 1e-6
    assert abs(results[1][0] - 0.8765) < 1e-6
    assert abs(results[1][1] - 50.0) < 1e-6


def test_progress_missing_returns_none():
    """A Progress block without a numeric Progress field yields nothing."""
    from transcoder import _HandBrakeJsonProgress
    block = """Progress:
{
    "Progress": {"State": "SCANNING", "SequenceID": 0}
}"""
    p = _HandBrakeJsonProgress()
    assert _feed(p, block) == []
