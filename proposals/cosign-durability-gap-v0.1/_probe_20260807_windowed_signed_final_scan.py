"""Windowed scan (2026-07-29T00:00:00+09:00 .. now): enumerate peer-chat messages
that carry digest(s) and co-sign / execution markers, so a reader can answer:
are there any NEW signed byte-bound finals since the 07-28/07-29 census that
would expand the FINDING section 7.2 universe beyond the five named instances?

Zero authority. Read-only. Never writes git objects. Writes one .out.json next to
this file. Exits 0 always.

Enumeration rule (mechanical, visible rather than assumed):
  candidate = a peer-chat message whose wall-clock time >= WINDOW and which
  contains at least one 64-hex sha256 digest, or at least one 8-63-hex truncated
  digest immediately followed by an ellipsis marker.
  A candidate is tagged with co-sign / execution markers when its text contains
  any of the marker terms (see MARK_TERMS).

This probe does NOT decide what is or is not a signed final; it lists the raw
candidates so the decision is a reading act, not a hidden filter.
"""
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CHAT = os.path.join(REPO, "proposals", "bounded-scheduler-v0.1", "impl",
                    "peer-chat.jsonl")
OUT = os.path.join(HERE, "_probe_20260807_windowed_signed_final_scan.out.json")

SHA256 = re.compile(r"[0-9a-f]{64}")
SHA_TRUNC = re.compile(r"[0-9a-f]{8,63}")
ELLIPSIS = re.compile(r"[.\u2026]")
LB = "\u3010"   # [
RB = "\u3011"   # ]
MARK_TERMS = ["\u540c\u610f", "\u53cd\u5bf9", "\u843d\u5730", "\u56de\u6267",
              "\u6267\u884c", "postcheck", "final", "\u88ab\u7b7e",
              "preflight"]
MARK = re.compile("(" + "|".join(MARK_TERMS) + ")")
WINDOW = "2026-07-29T00:00:00"


def norm_time(t):
    if not t:
        return None
    return t.strip()[:19]


def header(text):
    m = re.match(r"\s*" + LB + r"([^" + RB + r"]{0,120})" + RB, text)
    return m.group(1) if m else text[:60]


def main():
    rows = []
    with io.open(CHAT, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            s = line.strip()
            if not s:
                continue
            try:
                rows.append((i, json.loads(s)))
            except ValueError:
                rows.append((i, {"from": "PARSE_ERROR", "text": "",
                                 "time": ""}))

    candidates = []
    near_misses = []
    for i, r in rows:
        t = norm_time(r.get("time", ""))
        if t is None or t < WINDOW:
            continue
        text = r.get("text", "") or ""
        full = sorted(set(SHA256.findall(text)))
        trunc = []
        for m in re.finditer(r"[0-9a-f]{8,63}", text):
            tok = m.group(0)
            if len(tok) < 64 and ELLIPSIS.match(text, m.end()):
                trunc.append(tok)
        trunc = sorted(set(trunc))
        rec = {
            "line": i,
            "from": r.get("from"),
            "time": r.get("time"),
            "header": header(text),
            "markers": sorted(set(MARK.findall(text))),
            "full64": full,
            "trunc_ellipsis": trunc,
        }
        if full or trunc:
            candidates.append(rec)
        elif MARK.search(text):
            near_misses.append(rec)

    payload = {
        "probe": "_probe_20260807_windowed_signed_final_scan.py",
        "window_start": WINDOW + "+09:00",
        "peer_chat_path": os.path.relpath(CHAT, REPO),
        "peer_chat_rows": len(rows),
        "candidate_count": len(candidates),
        "near_miss_count": len(near_misses),
        "candidates": candidates,
        "near_misses": near_misses,
    }
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print("window >= " + WINDOW + "+09:00")
    print("peer-chat rows: %d" % len(rows))
    print("candidates (digest-bearing): %d" % len(candidates))
    for rec in candidates:
        print("L%-5d %-6s %s  markers=%s" %
              (rec["line"], rec["from"], rec["time"],
               ",".join(rec["markers"])))
        print("   %s" % rec["header"][:110])
        if rec["full64"]:
            print("   full64: %s" % ", ".join(d[:16] for d in rec["full64"]))
        if rec["trunc_ellipsis"]:
            print("   trunc : %s" % ", ".join(rec["trunc_ellipsis"][:12]))
    print("near-misses (marker, no digest): %d" % len(near_misses))
    for rec in near_misses:
        print("L%-5d %-6s %s  %s" %
              (rec["line"], rec["from"], rec["time"], rec["header"][:80]))
    print("out: " + os.path.relpath(OUT, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
