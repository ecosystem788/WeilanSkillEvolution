#!/usr/bin/env python3
"""Read-only: census of citation status classes across the whole peer-chat ledger.

Question under review: cited_artifact_receipt_check counts only disk_only+missing as
warnings. Does the ledger actually contain citations that land in the other
non-tracked classes (ignored / history_only), i.e. would a real receipt print
warning=0 while naming a file no third party can retrieve from the landing tree?
"""
from __future__ import annotations

import io
import json
from collections import Counter
from pathlib import Path
import sys

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
REPO = Path(r"D:\WeilanSkillEvolution")
sys.path.insert(0, str(IMPL))

import cited_artifact_receipt_check as gate  # noqa: E402


def main() -> int:
    rows, parse_errors = gate._ledger_rows(IMPL / "peer-chat.jsonl")
    tracked = gate._git_lines(REPO, "ls-files")
    historical = gate._git_lines(REPO, "log", "--all", "--pretty=format:", "--name-only")

    cache: dict[str, str] = {}
    counts: Counter[str] = Counter()
    # messages that would print warning_count == 0 yet cite an unreachable-from-tree path
    silent_hits: list[dict[str, object]] = []
    per_class_examples: dict[str, list[str]] = {}

    for line_number, _raw, record in rows:
        paths = gate.cited_paths(record.get("text"))
        if not paths:
            continue
        statuses = []
        for path in paths:
            status = cache.get(path)
            if status is None:
                try:
                    status = gate._classify(
                        root=REPO, path=path, tracked=tracked, historical=historical
                    )
                except gate.CheckError as exc:
                    # the gate aborts the whole bucket here; this census keeps going and
                    # records the class so the blast radius stays visible rather than fatal
                    status = f"check_error:{exc.reason}"
                cache[path] = status
            counts[status] += 1
            statuses.append((path, status))
            per_class_examples.setdefault(status, [])
            if len(per_class_examples[status]) < 6 and path not in per_class_examples[status]:
                per_class_examples[status].append(path)
        warning = sum(1 for _p, s in statuses if s in ("disk_only", "missing"))
        quiet = [p for p, s in statuses if s in ("ignored", "history_only")]
        if warning == 0 and quiet:
            silent_hits.append(
                {
                    "physical_line": line_number,
                    "from": record.get("from"),
                    "time": record.get("time"),
                    "quiet_paths": quiet,
                    "quiet_statuses": [s for _p, s in statuses if s in ("ignored", "history_only")],
                }
            )

    payload = {
        "probe": "status_class_census",
        "authority": "read_only_report",
        "ledger_rows": len(rows),
        "parse_error_count": len(parse_errors),
        "distinct_paths": len(cache),
        "citation_status_counts": dict(sorted(counts.items())),
        "distinct_path_status_counts": dict(sorted(Counter(cache.values()).items())),
        "messages_warning_zero_but_quiet_unreachable": len(silent_hits),
        "silent_hit_examples": silent_hits[:10],
        "per_class_examples": per_class_examples,
        "boundary": "counts citations as the gate's own regex sees them; non-ASCII paths are invisible to that regex and are not counted here either",
    }
    out = io.open(
        r"D:\WeilanSkillEvolution\proposals\cited-artifact-clone-reachability-v0.1\_probe_20260801_status_class_census.out.json",
        "w",
        encoding="utf-8",
    )
    json.dump(payload, out, ensure_ascii=False, indent=2, sort_keys=True)
    out.close()
    print(json.dumps({k: payload[k] for k in (
        "ledger_rows", "distinct_paths", "citation_status_counts",
        "distinct_path_status_counts", "messages_warning_zero_but_quiet_unreachable"
    )}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
