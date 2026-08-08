#!/usr/bin/env python3
"""Read-only post-fix live-ledger status census for the 2026-08-08 triad wrap-up.

Mirrors the fix-2 status_counts section of
_probe_20260801_adjudication_cost.py, re-run after the three 3239 fixes
landed so the before/after census can be compared. The original probe's
fix-1/fix-3 sections cannot run post-fix: their widened-pattern substitution
assertion only holds while the checker still carries the old lookbehind.
Nothing is written outside this probe's own .out.json.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess


IMPL = Path(__file__).resolve().parents[1] / "bounded-scheduler-v0.1" / "impl"
LEDGER = IMPL / "peer-chat.jsonl"


def load_checker():
    spec = importlib.util.spec_from_file_location(
        "cited_check", IMPL / "cited_artifact_receipt_check.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_checker()
    rows, parse_errors = module._ledger_rows(LEDGER)

    root_text = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=IMPL,
        capture_output=True, check=True
    ).stdout.decode().strip()
    root = Path(root_text).resolve()
    tracked = module._git_lines(root, "ls-files")
    historical = module._git_lines(root, "log", "--all", "--pretty=format:", "--name-only")

    status_counts = {}
    for _line_number, _raw, record in rows:
        for path in module.cited_paths(record.get("text")):
            try:
                status = module._classify(
                    root=root, path=path, tracked=tracked, historical=historical
                )
            except module.CheckError as exc:
                status = f"check_error:{exc.reason}"
            status_counts[status] = status_counts.get(status, 0) + 1

    payload = {
        "probe": "post_fix_live_census_triad_wrapup_20260808",
        "authority": "read_only_measurement",
        "ledger_rows": len(rows),
        "parse_errors": len(parse_errors),
        "total_citations": sum(status_counts.values()),
        "status_counts": dict(sorted(status_counts.items())),
        "boundary": "extraction and classification only; not evidentiary verifiability",
    }
    out = Path(__file__).with_suffix(".out.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
