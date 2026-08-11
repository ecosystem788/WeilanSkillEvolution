# -*- coding: utf-8 -*-
"""Shared peer-chat:N citation locators (single extraction family).

One home for the two extraction shapes used across this repo, so that no
third private copy of these patterns can drift away (classifier-r3
AFTER_CONVENTIONS third-copy lesson):

  extract_with_iso  ISO-anchored "(<iso>)(peer-chat:N)" citations -- the
                    shape cite_check.py scans for inside peer-chat bodies.
  extract_any       plain "peer-chat:N" citations in commit messages, the
                    P1/P2 family from the citation-reachability census probe
                    (proposals/citation-reachability-from-head-v0.1).

Behavior is pinned by test_cite_check.py (cite_check.scan unchanged) and
test_peer_chat_locator.py. Dual-sign landing: proposal peer-chat:3733,
agree peer-chat:3734.

P2 gained digit-boundary guards on 2026-08-11 (dual-sign: proposal
peer-chat:3791 12:52:24+09:00, agree peer-chat:3793 13:07:01+09:00) so
8-digit frame-ids / dates inside the 24-char window no longer split into
phantom numbers.
"""
from __future__ import annotations

import re

# cite_check.py's original inline regex, moved here verbatim: an ISO
# timestamp, up to 20 non-closing chars in between, then peer-chat:N (2-5
# digits). The 20-char slack and full-width paren handling are intentional
# (see peer-chat:3719/3721 -- recall beats precision; the rate is a property
# of the extractor, so keep the extractor stable and named).
ISO_NEAR = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2})[^)）]{0,20}peer-chat:(\d{2,5})"
)

# P1/P2 family, verbatim from _probe_20260810_citation_reachability.py.
P1 = re.compile(r"peer-chat[:：]\s*(\d{3,5})((?:\s*[+/,、]\s*\d{3,5})*)")
P1_MORE = re.compile(r"\d{3,5}")
P2 = re.compile(r"peer-chat[^\n]{0,24}?(?<!\d)(\d{3,5})\s*[-–]\s*(\d{3,5})(?!\d)")


def extract_with_iso(text):
    """Return [(iso, n), ...] for ISO-anchored peer-chat:N citations.

    Mirrors the original ISO_NEAR.findall semantics: a list, not a set --
    duplicates in one text stay duplicates (cite_check.scan counts
    occurrences).
    """
    return [(iso, int(n)) for iso, n in ISO_NEAR.findall(text or "")]


def extract_any(text):
    """Return sorted [n, ...] for plain peer-chat:N citations (P1+P2).

    Blind spots, kept identical to the census probe so any quoted number
    carries the same caveats:
      - bare numbers with no nearby "peer-chat" token are missed;
      - year-like tokens (e.g. "2026") can be picked up by P1;
      - P2 range form only expands when 0 < b-a < 200.
    """
    msg = text or ""
    out = set()
    for m in P1.finditer(msg):
        out.add(int(m.group(1)))
        for extra in P1_MORE.findall(m.group(2) or ""):
            out.add(int(extra))
    for m in P2.finditer(msg):
        a, b = int(m.group(1)), int(m.group(2))
        if 0 < b - a < 200:
            out.update(range(a, b + 1))
        else:
            out.update((a, b))
    return sorted(out)
