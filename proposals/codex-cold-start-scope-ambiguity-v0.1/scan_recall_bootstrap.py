"""Scan Codex wake run logs for the cold-start recall bootstrap shape.

Zero authority: this only reports what each archived run actually executed and
what its FIRST memory-recall returned. It does not judge whether a run was
useful, and it does not read the ledger. Every row is re-derivable from the
run log named in `run`.

Per-run fields:
  first_recall_scoped  did the first memory-recall pass --scope?
  first_recall_state   activation.state printed by that first recall
  recovered_scoped     did a LATER memory-recall in the same run pass --scope?
  read_wake_prompt     did the run ever read wake_prompt_codex.md?
  halted               did the run end without ever running a scoped recall
                       after a CONFIRM_REQUIRED first recall?

Run logs are UTF-16 (PowerShell `1>` redirection writes UTF-16LE); that is the
expected container -- see proposals/codex-run-log-encoding-v0.1.
"""

import argparse
import json
import re
from pathlib import Path

STATE_RE = re.compile(r'"state":\s*"(\w+)"')


def _rows(path):
    """Yield (event_type, item) for every parsable line of one run log."""
    text = path.read_bytes().decode("utf-16", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        yield event.get("type"), event.get("item") or {}


def scan_run(path):
    first_scoped = None
    first_state = None
    recovered = False
    read_prompt = False

    for event_type, item in _rows(path):
        command = item.get("command") or ""
        if "wake_prompt_codex" in command:
            read_prompt = True
        if "memory-recall" not in command:
            continue
        scoped = "--scope" in command
        if first_scoped is None:
            first_scoped = scoped
        elif scoped:
            recovered = True
        if event_type == "item.completed" and first_state is None:
            match = STATE_RE.search(item.get("aggregated_output") or "")
            first_state = match.group(1) if match else "?"

    halted = (
        first_scoped is False
        and first_state == "CONFIRM_REQUIRED"
        and not recovered
    )
    return {
        "run": path.name,
        "first_recall_scoped": first_scoped,
        "first_recall_state": first_state,
        "recovered_scoped": recovered,
        "read_wake_prompt": read_prompt,
        "halted": halted,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-dir",
        default=r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1"
        r"\impl\wake-codex-runs",
    )
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    logs = sorted(Path(args.runs_dir).glob("*.jsonl"))[-args.limit:]
    results = [scan_run(path) for path in logs]
    measured = [r for r in results if r["first_recall_state"] is not None]
    ambiguous = [r for r in measured if r["first_recall_state"] == "CONFIRM_REQUIRED"]

    print(
        json.dumps(
            {
                "runs_scanned": len(results),
                "runs_with_a_measurable_first_recall": len(measured),
                "first_recall_confirm_required": len(ambiguous),
                "of_those_recovered_by_scoped_rerun": sum(
                    1 for r in ambiguous if r["recovered_scoped"]
                ),
                "of_those_halted": sum(1 for r in ambiguous if r["halted"]),
                "any_run_whose_first_recall_was_scoped": any(
                    r["first_recall_scoped"] for r in results
                ),
                "rows": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
