#!/usr/bin/env python3
"""Read-only: pin down the CR-bearing lines in the ledgers the line-hash
convention actually governs, and test whether the corrections sidecar's
before_hash values are worktree-form or blob-form."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IMPL = REPO / "proposals/bounded-scheduler-v0.1/impl"

GOVERNED = [
    "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/peer-chat.corrections.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/owner-inbox.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/owner-inbox-replies.jsonl",
    "proposals/bounded-scheduler-v0.1/impl/owner-inbox-processed.jsonl",
]


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], check=True, stdout=subprocess.PIPE
    ).stdout


def split_lines(blob: bytes) -> list[bytes]:
    if not blob:
        return []
    parts = blob.split(b"\n")
    if parts and parts[-1] == b"":
        parts.pop()
    return parts


def main() -> int:
    out: dict[str, object] = {"head": git("rev-parse", "HEAD").decode().strip()}

    per_file = {}
    for path in GOVERNED:
        wt = split_lines((REPO / path).read_bytes())
        blob = split_lines(git("show", f"HEAD:{path}"))
        cr = [i + 1 for i, line in enumerate(wt) if line.endswith(b"\r")]
        per_file[path] = {
            "worktree_lines": len(wt),
            "head_blob_lines": len(blob),
            "cr_line_numbers": cr,
            "cr_lines_inside_committed_prefix": [n for n in cr if n <= len(blob)],
            "cr_line_previews": {
                str(n): wt[n - 1][:110].decode("utf-8", "replace") for n in cr
            },
        }
    out["governed"] = per_file

    # Do the sidecar's before_hash values name worktree bytes or blob bytes?
    corrections_path = IMPL / "peer-chat.corrections.jsonl"
    chat_wt = split_lines((IMPL / "peer-chat.jsonl").read_bytes())
    chat_blob = split_lines(
        git("show", "HEAD:proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl")
    )

    def index_by_hash(lines: list[bytes]) -> dict[str, int]:
        table: dict[str, int] = {}
        for i, line in enumerate(lines):
            table.setdefault(hashlib.sha256(line).hexdigest(), i + 1)
        return table

    wt_index = index_by_hash(chat_wt)
    blob_index = index_by_hash(chat_blob)
    wt_index_stripped = index_by_hash([line.rstrip(b"\r") for line in chat_wt])

    findings = []
    for lineno, raw in enumerate(
        corrections_path.read_bytes().split(b"\n"), start=1
    ):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw.rstrip(b"\r").decode("utf-8"))
        except json.JSONDecodeError as exc:
            findings.append({"corrections_line": lineno, "parse_error": str(exc)})
            continue
        before = row.get("before_hash")
        if not before:
            continue
        findings.append(
            {
                "corrections_line": lineno,
                "before_hash": before,
                "hits_worktree_payload_at_line": wt_index.get(before),
                "hits_head_blob_payload_at_line": blob_index.get(before),
                "hits_cr_stripped_worktree_at_line": wt_index_stripped.get(before),
            }
        )
    out["corrections_before_hash_resolution"] = findings

    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
