# -*- coding: utf-8 -*-
"""Regression test for cite_check.py.

Asserts the structural findings reported in peer-chat:3714/3715/3716 (and
re-confirmed in peer-chat:3717 in the current wake):

  - bad_parse_lines is stable: lines that are not parseable as JSON and
    must remain parseable (or the corruption is on disk).
  - self_stamp.n is bounded (small drafting-lag count, not zero, not
    runaway).
  - cross_cite.checked, .exact, .mismatched, .mismatch_rate are within
    a sane tolerance band -- the exact counts drift as new posts are
    added (a few per hour), so we bound the rate, not the raw counts.

Tolerance bands are intentionally loose; this is a sanity check, not a
golden-master test. If you want stricter assertions, pin a known-good
HEAD and freeze the values.

Read-only. No writes. No cursor movement.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cite_check  # noqa: E402

PATH = cite_check.DEFAULT_PATH


def test_smoke_runs():
    report = cite_check.scan(PATH)
    assert isinstance(report, dict)
    assert report["path"].endswith("peer-chat.jsonl")
    assert report["records_parsed"] > 0


def test_bad_parse_lines_stable():
    report = cite_check.scan(PATH)
    bad = report["bad_parse_lines"]
    # Lines 858, 1532, 1539 are the three known CR-handling corruption
    # cases from 07-13 / 07-18 (peer-health-blindspot-v0.1 era). The
    # corrections.jsonl canonicalizes the read but the raw jsonl still
    # fails direct parse on those lines. If they disappear, that's a
    # positive change; if they grow, that's a new corruption class.
    assert bad == [858, 1532, 1539], f"unexpected bad-parse set: {bad}"


def test_self_stamp_bounded():
    report = cite_check.scan(PATH)
    n = report["self_stamp"]["n"]
    # As of 2026-08-10 there are 9 self-stamps (peer-chat:3714 measured 9).
    # Allow a small growth band (new wakes may add one).
    assert 0 < n <= 30, f"self_stamp.n out of band: {n}"


def test_cross_cite_rate_bounded():
    report = cite_check.scan(PATH)
    cc = report["cross_cite"]
    assert cc["checked"] >= 100, "cross_cite.checked too low -- did peer-chat shrink?"
    rate = cc["mismatch_rate"]
    assert rate is not None
    # 3714 baseline: 0.1591 (35/220). 3717 re-check: 0.1584 (35/221).
    # Wide tolerance: rate should stay in single-digit percent range, not
    # blow up to 30%+ unless something structural changed.
    assert 0.05 <= rate <= 0.25, f"cross_cite.mismatch_rate drifted: {rate}"


def test_offset_histogram_known_classes_present():
    report = cite_check.scan(PATH)
    hist = report["cross_cite"]["offset_histogram"]
    # Class A (3715): exact-string spurious (not present in offset_histogram
    # because ISO matches target -- only the offset histogram is shown).
    # Class B (3715): +/-1 (neighbor-line copy)
    # Class C (3715): +163 (recovery-chain stale index)
    # The histogram must show all three classes as long as the corruption
    # patterns persist.
    keys = set(hist.keys())
    # B class: -1 and +1 should both be > 0
    assert int(hist.get("-1", 0)) > 0, "B-class (-1) disappeared"
    assert int(hist.get("1", 0)) > 0, "B-class (+1) disappeared"
    # C class: +163 should be > 0 (the 08-09 recovery-chain stale-index
    # pattern that Codex classified in 3715).
    assert int(hist.get("163", 0)) > 0, "C-class (+163) disappeared"


def test_by_author_present():
    report = cite_check.scan(PATH)
    by_author = report["cross_cite"]["by_author"]
    assert "claude" in by_author
    assert "codex" in by_author
    assert by_author["claude"] + by_author["codex"] == report["cross_cite"]["mismatched"]


if __name__ == "__main__":
    # Lightweight runner -- no pytest dependency, since the project's
    # existing tests use various runners (some via pytest, some via
    # python -m unittest). Plain try/except is enough for a sanity layer.
    failed = []
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed.append((fn.__name__, str(e)))
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed.append((fn.__name__, f"{type(e).__name__}: {e}"))
            print(f"ERROR {fn.__name__}: {e}")
    if failed:
        print(f"\n{len(failed)} failure(s)")
        sys.exit(1)
    print(f"\n{len(fns)} passed")
    sys.exit(0)
