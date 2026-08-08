#!/usr/bin/env python3
"""Read-only census: non-ledger worktree drift vs HEAD.

For each tracked file whose worktree bytes differ from HEAD and which is NOT an
append-only ledger (.jsonl) or probe output (.out.json), report:
  - diff size (added/removed lines)
  - HEAD's last commit that touched the file (age)
  - how many peer-chat records cite this path (i.e. it was used as evidence)
  - whether the path is cited by *me* (claude) and when most recently

Writes nothing. Prints JSON.
"""
import json
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
LEDGER = REPO / "proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(REPO), capture_output=True
    ).stdout.decode("utf-8", errors="replace")


# 1. drifted tracked files, excluding ledgers and probe outputs
drifted = []
for line in git("diff", "--numstat", "HEAD").splitlines():
    parts = line.split("\t")
    if len(parts) != 3:
        continue
    added, removed, path = parts
    if path.endswith(".jsonl") or path.endswith(".out.json"):
        continue
    drifted.append({"path": path, "added": added, "removed": removed})

# 2. citation census over the whole peer-chat ledger
cites: dict[str, list[dict]] = {d["path"]: [] for d in drifted}
total_lines = 0
unparsed = 0
with LEDGER.open(encoding="utf-8") as fh:
    for lineno, raw in enumerate(fh, 1):
        raw = raw.strip()
        if not raw:
            continue
        total_lines += 1
        try:
            rec = json.loads(raw)
        except Exception:  # noqa: BLE001
            unparsed += 1
            continue
        text = rec.get("text") or ""
        for path in cites:
            if path in text:
                cites[path].append(
                    {
                        "line": lineno,
                        "from": rec.get("from"),
                        "time": rec.get("time"),
                    }
                )

for d in drifted:
    path = d["path"]
    hits = cites[path]
    d["cited_records"] = len(hits)
    d["cited_by_claude"] = sum(1 for h in hits if h["from"] == "claude")
    d["cited_by_codex"] = sum(1 for h in hits if h["from"] == "codex")
    d["most_recent_citation"] = hits[-1] if hits else None
    log = git("log", "-1", "--format=%h|%ad|%s", "--date=short", "--", path).strip()
    d["head_last_touch"] = log

print(
    json.dumps(
        {
            "ledger_lines": total_lines,
            "ledger_unparsed": unparsed,
            "drifted_non_ledger_count": len(drifted),
            "files": sorted(drifted, key=lambda x: -x["cited_records"]),
        },
        ensure_ascii=False,
        indent=1,
    )
)
