# -*- coding: utf-8 -*-
"""Unit tests for peer_chat_locator.py (shared citation extraction family).

Covers the two extraction shapes:
  extract_with_iso  -- ISO-anchored "(<iso>)(peer-chat:N)" citations, the
                       shape cite_check.py scans for inside peer-chat bodies.
  extract_any       -- plain "peer-chat:N" citations (P1/P2 family), the
                       shape the pre-commit gate uses on commit messages.

Dual-sign landing: proposal peer-chat:3733, agree peer-chat:3734.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import peer_chat_locator as loc  # noqa: E402

ISO = "2026-08-10T14:05:50+09:00"


def test_extract_with_iso_basic():
    got = loc.extract_with_iso("re=%s(peer-chat:3733)" % ISO)
    assert got == [(ISO, 3733)]


def test_extract_with_iso_empty_and_plain():
    assert loc.extract_with_iso("") == []
    # Plain peer-chat:N without a nearby ISO timestamp is not the ISO shape.
    assert loc.extract_with_iso("peer-chat:3733") == []


def test_extract_with_iso_too_short_n():
    # \d{2,5}: a single digit is not a citation pointer.
    assert loc.extract_with_iso("%s(peer-chat:3)" % ISO) == []


def test_extract_with_iso_fullwidth_parens():
    assert loc.extract_with_iso("%s（peer-chat:3733）" % ISO) == [(ISO, 3733)]


def test_extract_with_iso_duplicates_kept():
    # List semantics (occurrence counts), not set semantics: scan() counts
    # occurrences, and that behavior is pinned here.
    text = "%s(peer-chat:3733) x %s(peer-chat:3734) y %s(peer-chat:3733)" % (ISO, ISO, ISO)
    assert loc.extract_with_iso(text) == [(ISO, 3733), (ISO, 3734), (ISO, 3733)]


def test_extract_any_basic():
    assert loc.extract_any("smoke: peer-chat:3730") == [3730]
    assert loc.extract_any("no citations here") == []


def test_extract_any_continuations():
    # P1 continuations: +N / N / 、N
    assert loc.extract_any("decision ... (peer-chat:3677+3678)") == [3677, 3678]
    assert loc.extract_any("see-also peer-chat:3621/3622/3623") == [3621, 3622, 3623]


def test_extract_any_range_form():
    # P2 range form, only expanded when 0 < b-a < 200.
    assert loc.extract_any("peer-chat 5 行账本轨迹 3473-3477") == [3473, 3474, 3475, 3476, 3477]
    # Non-range-eligible pair is kept as the two endpoints.
    assert loc.extract_any("peer-chat x 100-400") == [100, 400]


def test_extract_any_year_false_positive_kept():
    # Documented P1 blind spot: a year-like token after "peer-chat:" is
    # picked up. Kept on purpose so the caveat stays observable.
    assert loc.extract_any("peer-chat:2026") == [2026]


if __name__ == "__main__":
    failed = []
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        try:
            fn()
            print("PASS %s" % fn.__name__)
        except AssertionError as e:
            failed.append((fn.__name__, str(e)))
            print("FAIL %s: %s" % (fn.__name__, e))
        except Exception as e:
            failed.append((fn.__name__, "%s: %s" % (type(e).__name__, e)))
            print("ERROR %s: %s" % (fn.__name__, e))
    if failed:
        print("\n%d failure(s)" % len(failed))
        sys.exit(1)
    print("\n%d passed" % len(fns))
    sys.exit(0)

