"""Independent review probe for frame_abandoned v3 (Claude, 2026-07-31).

Read-only against every real ledger: everything happens inside a throwaway
WEILAN_METHOD_HOME under tempfile.mkdtemp(). Nothing here touches
$CODEX_HOME/method-state or the repo working tree.

Question under test (three parts, all named by Codex's own receipt):
  8) v2 shape                     -> what does each read surface say?
  9) future basis marker, and is the current basis still strict at write time?
     plus: which surfaces expose `markers` at all?

Method: build one frame that carries a genuinely unmet obligation
(minimal_unit_collapsed with no following trace_emitted), abandon it through
the real CLI, then rewrite ONLY the terminal event's data into four shapes and
ask several commands what they think of each.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path("C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py")
SCOPE = "abandon-v3-review"


def run(args, env, check=False):
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    if check and result.returncode:
        raise AssertionError(f"command failed: {args}\n{result.stderr}")
    return result


def load_json(result):
    try:
        return json.loads(result.stdout)
    except Exception:
        return None


def frame_path(home, frame_id):
    matches = list(Path(home).glob(f"frames/*/{frame_id}.jsonl"))
    if len(matches) != 1:
        raise AssertionError(f"expected one frame file: {matches}")
    return matches[0]


def read_events(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_events(path, events):
    path.write_text(
        "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            for event in events
        ),
        encoding="utf-8",
    )


def main():
    tmp = Path(tempfile.mkdtemp(prefix="abandon-v3-review-"))
    findings = {"probe": "abandon_v3_review", "cases": {}}
    try:
        home = tmp / "method-state"
        workspace = tmp / "workspace"
        workspace.mkdir()
        env = os.environ.copy()
        env["WEILAN_METHOD_HOME"] = str(home)

        opened = load_json(
            run(
                [
                    "open", "--level", "L2",
                    "--workspace", str(workspace),
                    "--problem", "independent review of frame_abandoned v3",
                    "--success", "the relaxation is keyed on what it claims",
                    "--scope", SCOPE, "--branch", "main", "--relation", "root",
                ],
                env,
                check=True,
            )
        )
        frame_id = opened["frame_id"]

        # Manufacture a genuinely unmet obligation: collapse with no trace after.
        run(
            [
                "event", "--frame-id", frame_id,
                "--type", "minimal_unit_collapsed",
                "--field", "scope=assumption",
                "--field", "former_holder=probe-holder",
                "--field", "invalidating_evidence=probe evidence",
            ],
            env,
            check=True,
        )

        # Age the frame past the silence threshold so abandonment is legal.
        path = frame_path(home, frame_id)
        events = read_events(path)
        events[-1]["timestamp_utc"] = (
            datetime.now(timezone.utc) - timedelta(seconds=10800)
        ).replace(microsecond=0).isoformat()
        write_events(path, events)

        abandoned = run(
            [
                "frame-abandon", "--frame-id", frame_id,
                "--silence-threshold-seconds", "7200",
                "--evidence", json.dumps(
                    {
                        "alert_id": "review-probe",
                        "consecutive_count": 10,
                        "source_ref": "probe:claude-independent-review",
                    }
                ),
                "--reason", "independent review probe",
            ],
            env,
        )
        findings["abandon_returncode"] = abandoned.returncode
        findings["abandon_stderr"] = abandoned.stderr.strip()[:400]

        events = read_events(path)
        terminal = events[-1]
        findings["recorded_terminal_data"] = terminal.get("data")

        shapes = {
            "v3_as_written": dict(terminal["data"]),
            "v3_current_basis_emptied": {
                **terminal["data"],
                "unmet_obligations": [],
            },
            "v2_no_fields": {
                key: value
                for key, value in terminal["data"].items()
                if key not in {"unmet_obligations", "unmet_obligations_basis"}
            },
            "future_basis_emptied": {
                **terminal["data"],
                "unmet_obligations_basis": "weilan_frame_abandon_unmet_obligations_v99",
                "unmet_obligations": [],
            },
        }

        readers = [
            ("validate", ["validate", "--frame-id", frame_id]),
            ("show", ["show", "--frame-id", frame_id]),
            (
                "persistence-audit-show",
                ["persistence-audit-show", "--frame-id", frame_id],
            ),
            (
                "lineage-show",
                ["lineage-show", "--workspace", str(workspace), "--scope", SCOPE],
            ),
            (
                "self-project",
                ["self-project", "--workspace", str(workspace), "--scope", SCOPE],
            ),
            (
                "trace-check",
                [
                    "trace-check",
                    "--workspace", str(workspace),
                    "--scope", SCOPE,
                    "--text", "collapsed with no trace after",
                ],
            ),
        ]

        for name, data in shapes.items():
            mutated = list(events)
            mutated[-1] = {**terminal, "data": data}
            write_events(path, mutated)
            case = {}
            for reader_name, argv in readers:
                result = run(argv, env)
                payload = load_json(result)
                if not isinstance(payload, dict):
                    payload = {}
                blob = result.stdout + result.stderr
                case[reader_name] = {
                    "returncode": result.returncode,
                    "valid": (payload or {}).get("valid"),
                    "errors": (payload or {}).get("errors"),
                    "markers": (payload or {}).get("markers"),
                    "mentions_marker_text": (
                        "unmet_obligations" in blob or "obligations_basis" in blob
                    ),
                }
            case["gates_relaxed_collapse_without_trace"] = (
                case["validate"]["returncode"] == 0
            )
            findings["cases"][name] = case

        # Which surfaces can ever emit `markers`? Static count of callers.
        source = SCRIPT.read_text(encoding="utf-8")
        findings["frame_validation_markers_call_sites"] = source.count(
            "frame_validation_markers("
        ) - 1  # minus the def
        findings["validate_events_call_sites"] = source.count(
            "validate_events("
        ) - 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(json.dumps(findings, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
