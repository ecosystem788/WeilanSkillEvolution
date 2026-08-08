#!/usr/bin/env python3
"""Read-only: trace provenance of the uncommitted checker drift.

Search the whole peer-chat ledger for the vocabulary introduced ONLY by the
worktree version of cited_artifact_receipt_check.py, to see whether the drift
was ever announced/proposed on the record, and by whom.
"""
import json
import subprocess
from pathlib import Path
import pathlib

REPO = pathlib.Path(
    subprocess.run(["git", "rev-parse", "--show-toplevel"],
                   cwd=str(pathlib.Path(__file__).resolve().parent),
                   capture_output=True, check=True)
    .stdout.decode("utf-8").strip()
)
LEDGER = REPO / "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"

TERMS = [
    "unresolvable_component",
    "invalid_path",
    "check_error",
    "cited_artifact_receipt_check",
    "warning_statuses",
]

hits = {t: [] for t in TERMS}
unparsed = []
with LEDGER.open(encoding="utf-8") as fh:
    for lineno, raw in enumerate(fh, 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except Exception:  # noqa: BLE001
            unparsed.append(lineno)
            continue
        text = rec.get("text") or ""
        for t in TERMS:
            if t in text:
                hits[t].append(
                    {
                        "line": lineno,
                        "from": rec.get("from"),
                        "time": rec.get("time"),
                        "excerpt": text[max(0, text.find(t) - 90) : text.find(t) + 110].replace("\n", " "),
                    }
                )

out = {"unparsed_lines": unparsed, "terms": {}}
for t in TERMS:
    out["terms"][t] = {
        "count": len(hits[t]),
        "first": hits[t][0] if hits[t] else None,
        "last": hits[t][-1] if hits[t] else None,
        "by_author": {},
    }
    for h in hits[t]:
        out["terms"][t]["by_author"][h["from"]] = out["terms"][t]["by_author"].get(h["from"], 0) + 1

print(json.dumps(out, ensure_ascii=False, indent=1))
