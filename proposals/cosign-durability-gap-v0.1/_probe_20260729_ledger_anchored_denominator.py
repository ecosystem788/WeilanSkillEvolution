#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ledger-anchored denominator for cosigned-execution durability.

Read-only. Run from repo root.

Why this exists
---------------
`_audit_cosign_durability.py` enumerates executions from a hand-written
EXECUTIONS literal (5 entries) and, when made discovery-based, from
`execution/preflight-state.json` artifacts (7 on disk). Both anchors are
ARTIFACT anchors, and both structurally miss the 2026-07-28T07:55:01
wake_prompt_codex.md execution, which produced no such artifact.

This probe uses a different anchor: the ledger's own execution receipts
(peer-chat messages containing the token 执行收据). The ledger, not the
artifact, is what every cosigned execution is required to write.

For each receipt we extract (a) declared sha256 digests and (b) repo-relative
paths, then ask, per path, whether ANY version of that path in git history has
a blob whose sha256 equals a digest declared in that receipt.

Boundaries this probe does NOT cross
------------------------------------
* It cannot prove a receipt's digest was *meant* as a post/final digest; a
  receipt may quote a base digest too. A path is only reported STRANDED when
  the receipt's digests are matched by NO version of the path in history AND
  the current worktree bytes match one of them (i.e. a live, on-disk final).
* It says nothing about pushed/remote visibility (out of scope by design).
* Receipts that name no path, or name paths outside the repo, are counted
  separately as UNPAIRED rather than silently dropped.
"""
import hashlib
import io
import json
import re
import subprocess
import sys

CHAT = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
# repo-relative paths that look like real files
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
    """sha256 of every distinct blob this path ever had, over ALL refs."""
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
    print(f"peer-chat rows: {len(rows)}")
    print(f"messages containing 执行收据: {len(receipts)}")

    # Collect candidate (path -> declared digests) pairs across receipts.
    pairs = {}
    unpaired = 0
    for i, r in receipts:
        text = str(r.get("text", ""))
        digests = set(HEX64.findall(text))
        paths = set(PATH.findall(text))
        if not digests or not paths:
            unpaired += 1
            continue
        for p in paths:
            pairs.setdefault(p, {"digests": set(), "receipts": []})
            pairs[p]["digests"] |= digests
            pairs[p]["receipts"].append((i, r.get("time")))

    print(f"receipts with no (digest,path) pair: {unpaired}")
    print(f"distinct paths named by receipts: {len(pairs)}\n")

    matched, stranded, undeclared, absent = 0, [], 0, 0
    for p in sorted(pairs):
        info = pairs[p]
        try:
            wt = open(p, "rb").read()
        except OSError:
            absent += 1
            continue
        wt_sha = hashlib.sha256(wt).hexdigest()
        if wt_sha not in info["digests"]:
            # current bytes are not any digest this receipt declared:
            # either superseded by later work, or the receipt quoted only a base.
            undeclared += 1
            continue
        hist, commits = path_history_sha256(p)
        if wt_sha in hist:
            matched += 1
            continue
        stranded.append(
            {
                "path": p,
                "worktree_sha256": wt_sha,
                "bytes": len(wt),
                "history_commits_touching_path": len(commits),
                "history_sha256_count": len(hist),
                "receipts": info["receipts"][-3:],
            }
        )

    print(f"MATCHED: {matched}")
    print(f"STRANDED: {len(stranded)}")
    print(f"UNDECLARED: {undeclared}")
    print(f"ABSENT: {absent}")
    checked = matched + len(stranded)
    print(
        f"\nhistory lookup actually ran on {checked}/{len(pairs)} paths; "
        f"the '{len(stranded)} STRANDED' verdict ranges over exactly those {checked}.\n"
    )
    for s in stranded:
        print(json.dumps(s, ensure_ascii=False, indent=2))

    return 0 if not stranded else 1


if __name__ == "__main__":
    sys.exit(main())
