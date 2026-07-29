#!/usr/bin/env python3
"""Read-only probe: does the line-hash convention's payload ambiguity have any
live instances?

Codex flagged (peer-chat 2026-07-30T00:20:01+09:00) that the corrections-sidecar
line-hash convention -- sha256(physical line payload bytes, no line terminator)
-- has never chosen, for a line that carries CR, between the WORKING-TREE payload
and the COMMIT-BLOB payload. This probe measures whether the two口径 can diverge
today, and on what they depend.

Nothing here writes. Nothing here judges. It prints counts.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def split_lines(blob: bytes) -> list[bytes]:
    """Physical lines, LF-separated, terminator stripped. A CRLF file yields
    payloads that still end in CR -- which is exactly the ambiguity."""
    if not blob:
        return []
    parts = blob.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    return parts


def main() -> int:
    tracked = [
        p for p in git("ls-files", "-z").decode("utf-8").split("\0")
        if p.endswith(".jsonl")
    ]

    report: dict[str, object] = {
        "head": git("rev-parse", "HEAD").decode().strip(),
        "core_autocrlf": git("config", "core.autocrlf").decode().strip(),
        "tracked_jsonl": len(tracked),
    }

    # 1. What do the attributes actually resolve to, per tracked file?
    attr_out = subprocess.run(
        ["git", "-C", str(REPO), "check-attr", "--stdin", "-z", "text", "eol"],
        input="\0".join(tracked).encode("utf-8"),
        check=True,
        stdout=subprocess.PIPE,
    ).stdout.decode("utf-8")
    fields = attr_out.split("\0")
    attrs: dict[str, dict[str, str]] = {}
    for i in range(0, len(fields) - 2, 3):
        path, attr, value = fields[i], fields[i + 1], fields[i + 2]
        attrs.setdefault(path, {})[attr] = value
    eol_hist: dict[str, int] = {}
    for path in tracked:
        key = f"text={attrs.get(path, {}).get('text')},eol={attrs.get(path, {}).get('eol')}"
        eol_hist[key] = eol_hist.get(key, 0) + 1
    report["attr_histogram"] = eol_hist

    # 2. Live instances: any CR-bearing physical line, in worktree or in HEAD blob?
    worktree_cr: dict[str, int] = {}
    blob_cr: dict[str, int] = {}
    divergent_prefix: dict[str, dict[str, object]] = {}

    for path in tracked:
        disk = REPO / path
        if disk.exists():
            wt_lines = split_lines(disk.read_bytes())
            n = sum(1 for line in wt_lines if line.endswith(b"\r"))
            if n:
                worktree_cr[path] = n
        else:
            wt_lines = None

        try:
            blob = git("show", f"HEAD:{path}")
        except subprocess.CalledProcessError:
            continue
        bl_lines = split_lines(blob)
        n = sum(1 for line in bl_lines if line.endswith(b"\r"))
        if n:
            blob_cr[path] = n

        # 3. For the common prefix, do the two口径 hash the same?
        if wt_lines is not None:
            mismatch = []
            for idx in range(min(len(wt_lines), len(bl_lines))):
                if wt_lines[idx] != bl_lines[idx]:
                    mismatch.append(
                        {
                            "line": idx + 1,
                            "worktree_sha256": hashlib.sha256(wt_lines[idx]).hexdigest(),
                            "blob_sha256": hashlib.sha256(bl_lines[idx]).hexdigest(),
                            "differs_only_by_trailing_cr": (
                                wt_lines[idx].rstrip(b"\r") == bl_lines[idx].rstrip(b"\r")
                            ),
                        }
                    )
            if mismatch:
                divergent_prefix[path] = {
                    "count": len(mismatch),
                    "first_three": mismatch[:3],
                }

    report["worktree_cr_lines"] = worktree_cr
    report["head_blob_cr_lines"] = blob_cr
    report["prefix_divergence"] = divergent_prefix

    # 4. Would a fresh checkout reintroduce CR? Ask git for the checkout form
    #    of one bearing file rather than reasoning about it.
    probe_path = "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"
    if probe_path in tracked:
        # `git show` gives blob bytes (normalized form). `cat-file --filters`
        # applies the checkout filters, i.e. what a fresh clone would land on disk.
        checkout_form = git("cat-file", "--filters", f"HEAD:{probe_path}")
        lines = split_lines(checkout_form)
        report["checkout_form_probe"] = {
            "path": probe_path,
            "lines": len(lines),
            "cr_bearing_lines": sum(1 for line in lines if line.endswith(b"\r")),
        }

    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
