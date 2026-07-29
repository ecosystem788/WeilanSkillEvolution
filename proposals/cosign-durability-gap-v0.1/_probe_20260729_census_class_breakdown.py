#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Class breakdown behind `_probe_20260729_ledger_anchored_denominator.py`'s "0 STRANDED".

Read-only. Run from repo root. Same pairing logic, same regexes, same
classification order as the parent probe -- this probe adds NO new judgement,
it only prints the per-path class the parent probe collapses into two counters.

Why this exists
---------------
The parent probe prints three numbers:

    paths whose declared bytes ARE in git history (or superseded): N
    paths named by receipts but missing from disk:                 M
    STRANDED ...:                                                  K

The first counter merges two structurally different verdicts (parent probe
lines 113-120):

  * MATCHED   -- worktree sha256 IS one of the receipt-declared digests AND
                 that sha256 is among the path's blobs over all refs.
                 This is the only class where a git-history lookup ran, and
                 therefore the only class the "0 STRANDED" result ranges over.
  * UNDECLARED -- worktree sha256 is NOT any digest the receipt declared, so
                 the probe returns early and never looks at history. The parent
                 probe's comment calls this "superseded by later work, or the
                 receipt quoted only a base". Both readings are consistent with
                 the bytes on disk; so is a third: the signed final was never
                 committed AND has since been overwritten. This probe does not
                 decide between them -- it only refuses to count them as
                 evidence of durability.

So the denominator of the "0" is |MATCHED|, not |paths|. This probe prints it.

Boundaries
----------
* Adds no new predicate. If the parent probe is wrong about a path, this probe
  is wrong about it identically, by construction.
* Says nothing about pushed/remote visibility (same as parent).
* UNDECLARED is not an accusation. It is an explicit "this instrument did not
  look", which is what the merged counter currently reads as "fine".
"""
import hashlib
import io
import json
import re
import subprocess
import sys

CHAT = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
PATH = re.compile(r"\b(?:proposals|theory|tools|evals|scripts)/[A-Za-z0-9_.\-/]+\.[A-Za-z0-9]{1,6}\b")


def git(*args, binary=False):
    r = subprocess.run(["git", *args], capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def load_chat():
    rows = []
    for i, line in enumerate(io.open(CHAT, encoding="utf-8", errors="replace"), 1):
        if not line.strip():
            continue
        try:
            rows.append((i, json.loads(line)))
        except Exception:
            rows.append((i, {"time": "<unparsed>", "from": "?", "text": line}))
    return rows


def path_history_sha256(path):
    out = git("log", "--all", "--pretty=format:%H", "--", path)
    if out is None:
        return {}, []
    seen = {}
    commits = [c for c in out.split() if c]
    for c in commits:
        blob = git("show", f"{c}:{path}", binary=True)
        if blob is None:
            continue
        seen.setdefault(hashlib.sha256(blob).hexdigest(), c)
    return seen, commits


def main():
    rows = load_chat()
    receipts = [(i, r) for i, r in rows if "执行收据" in str(r.get("text", ""))]

    pairs = {}
    paired_receipts, unpaired_receipts = [], []
    for i, r in receipts:
        text = str(r.get("text", ""))
        digests = set(HEX64.findall(text))
        paths = set(PATH.findall(text))
        if not digests or not paths:
            unpaired_receipts.append((i, r.get("time"), r.get("from")))
            continue
        paired_receipts.append((i, r.get("time"), r.get("from")))
        for p in paths:
            pairs.setdefault(p, {"digests": set(), "receipts": []})
            pairs[p]["digests"] |= digests
            pairs[p]["receipts"].append((i, r.get("time")))

    print(f"peer-chat rows: {len(rows)}")
    print(f"receipts (messages containing 执行收据): {len(receipts)}")
    print(f"  paired   (declare >=1 digest AND >=1 repo path): {len(paired_receipts)}")
    print(f"  unpaired (contribute nothing to the census):     {len(unpaired_receipts)}")
    print(f"distinct paths named by paired receipts: {len(pairs)}\n")

    classes = {"MATCHED": [], "UNDECLARED": [], "ABSENT": [], "STRANDED": []}
    for p in sorted(pairs):
        info = pairs[p]
        try:
            wt = open(p, "rb").read()
        except OSError:
            classes["ABSENT"].append({"path": p, "receipts": info["receipts"][-2:]})
            continue
        wt_sha = hashlib.sha256(wt).hexdigest()
        if wt_sha not in info["digests"]:
            classes["UNDECLARED"].append(
                {
                    "path": p,
                    "worktree_sha256": wt_sha,
                    "bytes": len(wt),
                    "declared_digest_count": len(info["digests"]),
                    "receipts": info["receipts"][-2:],
                }
            )
            continue
        hist, commits = path_history_sha256(p)
        rec = {
            "path": p,
            "worktree_sha256": wt_sha,
            "bytes": len(wt),
            "history_commits_touching_path": len(commits),
            "history_distinct_blob_sha256": len(hist),
            "receipts": info["receipts"][-2:],
        }
        if wt_sha in hist:
            rec["found_in_commit"] = hist[wt_sha]
            classes["MATCHED"].append(rec)
        else:
            classes["STRANDED"].append(rec)

    for name in ("MATCHED", "STRANDED", "UNDECLARED", "ABSENT"):
        print(f"{name}: {len(classes[name])}")
    n_matched, n_stranded = len(classes["MATCHED"]), len(classes["STRANDED"])
    checked = n_matched + n_stranded
    print(
        f"\nhistory lookup actually ran on {checked}/{len(pairs)} paths; "
        f"the '{n_stranded} STRANDED' verdict ranges over exactly those {checked}."
    )
    print()
    for name in ("MATCHED", "STRANDED", "UNDECLARED", "ABSENT"):
        print(f"--- {name} ---")
        for rec in classes[name]:
            print(json.dumps(rec, ensure_ascii=False))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
