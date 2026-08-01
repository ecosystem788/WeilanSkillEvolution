#!/usr/bin/env python3
"""Read-only: cost of the three adjudicated fixes, measured on the live ledger.

Answers, for each fix proposed in the 2026-08-01 adjudication of the three
non-blocking differences raised in the post-fix review:

  fix-1 (dots-only component)  how many live citations change class when the
                               literal "..." test becomes "dots only, len>=3"
  fix-2 (clean-set inversion)  how many buckets currently report warning_count=0
                               while holding an unclassifiable citation
  fix-3 (rev-suffix guard)     which live citations the widened lookbehind
                               (?<![A-Za-z0-9^}~]:) stops extracting

Nothing is written outside this probe's own .out.json. Boundary: this measures
extraction and classification only; it does not claim the cited bytes are
verifiable, nor that non-ASCII paths are visible.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

IMPL = Path(__file__).resolve().parents[1] / "bounded-scheduler-v0.1" / "impl"
LEDGER = IMPL / "peer-chat.jsonl"


def load_checker():
    spec = importlib.util.spec_from_file_location(
        "cited_check", IMPL / "cited_artifact_receipt_check.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ledger_records(module) -> list[dict]:
    rows, parse_errors = module._ledger_rows(LEDGER)
    return rows, parse_errors


def main() -> int:
    module = load_checker()
    rows, parse_errors = ledger_records(module)

    # Widened pattern for fix-3: same source, one extra guarded character class.
    widened = re.compile(
        module.PATH_RE.pattern.replace(r"(?<![A-Za-z0-9]:)", r"(?<![A-Za-z0-9^}~]:)")
    )
    assert widened.pattern != module.PATH_RE.pattern, "pattern substitution failed"

    def widened_paths(text: object) -> list[str]:
        if not isinstance(text, str):
            return []
        found: list[str] = []
        for match in widened.finditer(text):
            candidate = module._strip_tail(match.group(0))
            if not candidate.lower().endswith(module.EXTENSIONS):
                continue
            path = PurePosixPath(candidate)
            if path.is_absolute() or any(p in ("", ".", "..") for p in path.parts):
                continue
            if path.as_posix() not in found:
                found.append(path.as_posix())
        return found

    fix1_would_change: list[dict] = []
    fix3_dropped: list[dict] = []
    total_citations = 0

    for line_number, _raw, record in rows:
        text = record.get("text")
        current = module.cited_paths(text)
        total_citations += len(current)

        for path in current:
            parts = PurePosixPath(path).parts
            literal = any(part == "..." for part in parts)
            dots_only = any(set(part) == {"."} and len(part) >= 3 for part in parts)
            if dots_only and not literal:
                fix1_would_change.append(
                    {"physical_line": line_number, "path": path,
                     "from": record.get("from"), "time": record.get("time")}
                )

        after = widened_paths(text)
        for path in current:
            if path not in after:
                idx = text.find(path)
                fix3_dropped.append(
                    {"physical_line": line_number, "path": path,
                     "from": record.get("from"), "time": record.get("time"),
                     "context": text[max(0, idx - 24):idx + len(path)] if idx >= 0 else None}
                )

    # fix-2: which currently-observed statuses sit outside the clean set.
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=IMPL,
                          capture_output=True, check=True).stdout.decode().strip()
    root_path = Path(root).resolve()
    tracked = module._git_lines(root_path, "ls-files")
    historical = module._git_lines(root_path, "log", "--all", "--pretty=format:", "--name-only")

    clean = ("tracked_head", "history_only")
    current_warning = ("disk_only", "ignored", "missing", "unresolvable_component")
    invisible: list[dict] = []
    status_counts: dict[str, int] = {}
    for line_number, _raw, record in rows:
        for path in module.cited_paths(record.get("text")):
            try:
                status = module._classify(root=root_path, path=path,
                                          tracked=tracked, historical=historical)
            except module.CheckError as exc:
                status = f"check_error:{exc.reason}"
            status_counts[status] = status_counts.get(status, 0) + 1
            if status not in clean and status not in current_warning:
                invisible.append({"physical_line": line_number, "path": path,
                                  "status": status, "from": record.get("from"),
                                  "time": record.get("time")})

    payload = {
        "probe": "adjudication_cost_of_three_fixes",
        "authority": "read_only_measurement",
        "ledger_rows": len(rows),
        "parse_errors": len(parse_errors),
        "total_citations": total_citations,
        "fix1_dots_only_component": {
            "question": "citations a dots-only(>=3) test catches that the literal '...' test misses",
            "count": len(fix1_would_change),
            "items": fix1_would_change,
        },
        "fix2_clean_set_inversion": {
            "question": "citations counted by neither clean-set nor current warning_statuses",
            "current_warning_statuses": list(current_warning),
            "proposed_clean_statuses": list(clean),
            "status_counts": dict(sorted(status_counts.items())),
            "invisible_to_current_warning_count": len(invisible),
            "items": invisible,
        },
        "fix3_rev_suffix_guard": {
            "question": "citations the widened lookbehind stops extracting",
            "widened_lookbehind": "(?<![A-Za-z0-9^}~]:)",
            "dropped_count": len(fix3_dropped),
            "items": fix3_dropped,
        },
        "boundary": "extraction and classification only; not evidentiary verifiability, not non-ASCII path coverage",
    }
    out = Path(__file__).with_suffix(".out.json")
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("ledger_rows", "total_citations")}, ensure_ascii=False))
    print(json.dumps(payload["fix1_dots_only_component"], ensure_ascii=False)[:400])
    print(json.dumps(payload["fix2_clean_set_inversion"]["status_counts"], ensure_ascii=False))
    print("fix2 invisible:", len(invisible))
    print("fix3 dropped:", len(fix3_dropped))
    for item in fix3_dropped[:12]:
        print("  ", item["physical_line"], item["path"], "|", (item.get("context") or "")[-60:])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
