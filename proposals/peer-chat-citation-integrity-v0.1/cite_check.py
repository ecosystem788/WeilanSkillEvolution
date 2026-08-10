# -*- coding: utf-8 -*-
"""Read-only peer-chat citation-integrity check (landed from
_probe_20260810_citation_integrity.py, peer-chat:3714).

Splits two different things -- this is the v2 stratification:

  SELF-STAMP   citing line N carries "re=<iso>(peer-chat:N)" about itself.
               <iso> is the DRAFTING time, line.time is the APPEND time.
               A gap here is the known draft-vs-append lag, NOT a misquote.

  CROSS-CITE   citing line C quotes "<iso>(peer-chat:N)" with N != C.
               line N.time is fixed in the file; an exact copy is expected.
               A gap here IS a misquote -- and is further diagnosable:
               if <iso> equals the time of some OTHER line M, the failure
               mode is index drift (report M-N), not fabrication.

No writes. No cursor movement. Does not import wake_brief. Does not move
the wake-cursor. Pure read-only peer-chat.jsonl scan.

Usage:
  python cite_check.py [PATH_TO_peer_chat_jsonl] [OUTPUT_JSON]
  Defaults: PATH = proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl
            OUTPUT_JSON = cite_check.out.json (next to this script)

Importable as a module: see `scan(path)` for the function that returns the
report dict (without writing).
"""
from __future__ import annotations

import collections
import datetime
import io
import json
import os
import sys

from peer_chat_locator import extract_with_iso

DEFAULT_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.pardir,
        "bounded-scheduler-v0.1",
        "impl",
        "peer-chat.jsonl",
    )
)

def _norm(t):
    return (t or "").replace(" ", "T").strip()


def _text_of(o):
    return o.get("text") or o.get("message") or ""


def _pct(v, p):
    if not v:
        return None
    return v[min(len(v) - 1, int(round(p / 100.0 * (len(v) - 1))))]


def scan(path):
    """Return the citation-integrity report dict for peer-chat.jsonl at `path`."""
    raw = io.open(path, encoding="utf-8").read().splitlines()
    recs = {}
    bad_parse = []
    for i, ln in enumerate(raw, start=1):
        if not ln.strip():
            continue
        try:
            recs[i] = json.loads(ln)
        except Exception:
            bad_parse.append(i)

    time_index = collections.defaultdict(list)
    for i, o in recs.items():
        time_index[_norm(o.get("time"))].append(i)

    self_stamp = []
    cross_ok = 0
    cross_bad = []
    for c, o in sorted(recs.items()):
        txt = _text_of(o)
        who = o.get("from") or "?"
        for iso, n in extract_with_iso(txt):
            n = int(n)
            tgt = recs.get(n)
            if n == c:
                if tgt is not None:
                    try:
                        a = datetime.datetime.fromisoformat(iso)
                        b = datetime.datetime.fromisoformat(_norm(tgt.get("time")))
                        self_stamp.append((c, int((b - a).total_seconds())))
                    except Exception:
                        pass
                continue
            if tgt is None:
                cross_bad.append((c, who, n, iso, None, None))
                continue
            if _norm(tgt.get("time")) == iso:
                cross_ok += 1
                continue
            owners = time_index.get(iso, [])
            offset = (owners[0] - n) if len(owners) == 1 else (owners if owners else None)
            cross_bad.append((c, who, n, iso, tgt.get("time"), offset))

    gaps = sorted(g for _, g in self_stamp)
    off_hist = collections.Counter()
    for r in cross_bad:
        o = r[5]
        off_hist[o if isinstance(o, int) else ("no-such-time" if o is None else "ambiguous")] += 1
    by_who = collections.Counter(r[1] for r in cross_bad)

    return {
        "path": path,
        "lines_total": len(raw),
        "records_parsed": len(recs),
        "bad_parse_lines": bad_parse,
        "self_stamp": {
            "n": len(self_stamp),
            "gap_seconds_min": gaps[0] if gaps else None,
            "gap_seconds_median": _pct(gaps, 50),
            "gap_seconds_p90": _pct(gaps, 90),
            "gap_seconds_max": gaps[-1] if gaps else None,
            "note": "draft-vs-append lag; NOT a misquote class",
        },
        "cross_cite": {
            "checked": cross_ok + len(cross_bad),
            "exact": cross_ok,
            "mismatched": len(cross_bad),
            "mismatch_rate": round(len(cross_bad) / float(cross_ok + len(cross_bad)), 4)
            if (cross_ok + len(cross_bad)) else None,
            "by_author": dict(by_who),
            "offset_histogram": {str(k): v for k, v in sorted(off_hist.items(), key=lambda kv: str(kv[0]))},
            "detail": [list(r) for r in cross_bad],
        },
    }


def _print_summary(report):
    payload = dict(report)
    payload["cross_cite"] = {k: v for k, v in report["cross_cite"].items() if k != "detail"}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv):
    # GBK-decode crash on Windows + BOM-leak on stdout: reconfigure.
    # See memory: append-clock fix landed this same reconfigure for the same reasons.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    path = argv[1] if len(argv) > 1 else DEFAULT_PATH
    out = argv[2] if len(argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "cite_check.out.json")
    report = scan(path)
    io.open(out, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=2))
    _print_summary(report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
