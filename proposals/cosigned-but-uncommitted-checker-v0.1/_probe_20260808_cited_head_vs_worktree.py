#!/usr/bin/env python3
"""Read-only probe: does the HEAD version of cited_artifact_receipt_check.py
produce the same verdict as the worktree version, on the same input bucket?

No writes to any ledger. Runs both scripts as subprocesses and diffs the JSON.
"""
import json
import tempfile
import os
import subprocess
import sys
from pathlib import Path
import pathlib

REPO = pathlib.Path(
    subprocess.run(["git", "rev-parse", "--show-toplevel"],
                   cwd=str(pathlib.Path(__file__).resolve().parent),
                   capture_output=True, check=True)
    .stdout.decode("utf-8").strip()
)


CHECKER_REL = "proposals/bounded-scheduler-v0.1/impl/cited_artifact_receipt_check.py"


def _materialize_head_checker() -> pathlib.Path:
    """Write HEAD's version of the checker to a temp file (never touches the tree)."""
    blob = subprocess.run(
        ["git", "show", f"HEAD:{CHECKER_REL}"],
        cwd=str(REPO), capture_output=True, check=True,
    ).stdout
    fd, name = tempfile.mkstemp(prefix="cited_HEAD_", suffix=".py")
    with os.fdopen(fd, "wb") as fh:
        fh.write(blob)
    return pathlib.Path(name)

WORKTREE = REPO / "proposals/bounded-scheduler-v0.1/impl/cited_artifact_receipt_check.py"
HEADCOPY = None  # materialized from HEAD at runtime
ROOT = "proposals/bounded-scheduler-v0.1/impl"

HEADCOPY = _materialize_head_checker()

CASES = [
    # (author, timestamp) -- buckets I cited as evidence in peer-chat
    ("claude", "2026-08-08T14:40:32+09:00"),  # cited in peer-chat:3610
    ("claude", "2026-08-08T12:46:56+09:00"),  # peer-chat:3599
    ("claude", "2026-08-08T13:36:47+09:00"),  # peer-chat:3604 proposal
]


def run(script: Path, author: str, ts: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(script), "--root", ROOT, "--from", author, "--time", ts],
        cwd=str(REPO),
        capture_output=True,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(out) if out.strip() else None
    except Exception as exc:  # noqa: BLE001
        parsed = {"_unparsed": out[:400], "_error": str(exc)}
    return {"rc": proc.returncode, "json": parsed, "stderr": err[:600]}


def summarize(res: dict) -> dict:
    j = res.get("json")
    if not isinstance(j, dict):
        return {"rc": res["rc"], "parsed": False, "stderr": res["stderr"]}
    return {
        "rc": res["rc"],
        "ok": j.get("ok"),
        "warning_count": j.get("warning_count"),
        "warning_statuses": j.get("warning_statuses"),
        "counts": j.get("counts"),
        "matched_record_count": j.get("matched_record_count"),
        "cited_path_count": j.get("cited_path_count"),
    }


report = {"repo": str(REPO), "cases": []}
for author, ts in CASES:
    w = summarize(run(WORKTREE, author, ts))
    h = summarize(run(HEADCOPY, author, ts))
    diffs = sorted({k for k in set(w) | set(h) if w.get(k) != h.get(k)})
    report["cases"].append(
        {"author": author, "time": ts, "worktree": w, "head": h, "differing_keys": diffs}
    )

print(json.dumps(report, ensure_ascii=False, indent=1))
