"""Regression tests for the episode-receipt subcommand (receipt-subcommand-v0.1).

Pins the dual-signed spec (peer-chat 2026-08-04T03:38:51 + codex agreement
2026-08-04T03:52:46): fail-closed-before-write validation, automatic scope-head
parent resolution, atomic frame_opened -> persistence_audit -> frame_closed, and
machine-readable output of frame_id / event ids / parent / prior head.  The
boundaries pinned here: no fork/join shapes, promoted requires --evidence-id,
verdict non-empty, decision/outcome combination legality, and zero writes before
every validation passes (no half-chain in any ledger).
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("weilan_trace.py")
SCOPE = "episode-receipt-test"


def completed(arguments, environment):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def run(arguments, environment):
    result = completed(arguments, environment)
    if result.returncode:
        raise AssertionError(f"command failed: {result.stderr}")
    return json.loads(result.stdout)


@pytest.fixture()
def fixture(tmp_path):
    method_state = tmp_path / "method-state"
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()
    environment = os.environ.copy()
    environment["WEILAN_METHOD_HOME"] = str(method_state)
    return {
        "method_state": method_state,
        "workspace": str(workspace_path),
        "environment": environment,
    }


def open_frame(fixture, *, branch="main", relation="root", parents=()):
    arguments = [
        "open",
        "--level", "L2",
        "--workspace", fixture["workspace"],
        "--problem", "episode receipt regression",
        "--success", "receipt stays bounded",
        "--scope", SCOPE,
        "--branch", branch,
        "--relation", relation,
    ]
    for parent in parents:
        arguments.extend(["--parent", parent])
    return run(arguments, fixture["environment"])


def close_frame(fixture, frame_id):
    run(
        [
            "persistence-audit",
            "--frame-id", frame_id,
            "--trigger", "round_end",
            "--decision", "not_persisted",
            "--reason", "episode receipt fixture has no durable conclusion",
        ],
        fixture["environment"],
    )
    run(
        [
            "close",
            "--frame-id", frame_id,
            "--outcome", "success",
            "--verdict", "fixture frame closed",
        ],
        fixture["environment"],
    )


def lineage(fixture):
    return run(
        ["lineage-show", "--workspace", fixture["workspace"], "--scope", SCOPE],
        fixture["environment"],
    )


def receipt(fixture, **overrides):
    arguments = [
        "episode-receipt",
        "--workspace", fixture["workspace"],
        "--scope", SCOPE,
        "--level", "L2",
        "--problem", "episode receipt fixture",
        "--success", "receipt written and closed",
        "--outcome", "success",
        "--verdict", "fixture receipt verdict",
        "--decision", "not_persisted",
        "--reason", "fixture receipt reason",
    ]
    aliases = {
        "level": "--level",
        "problem": "--problem",
        "success": "--success",
        "outcome": "--outcome",
        "verdict": "--verdict",
        "decision": "--decision",
        "evidence_id": "--evidence-id",
        "reason": "--reason",
        "trigger": "--trigger",
        "branch_id": "--branch-id",
    }
    for key, value in overrides.items():
        flag = aliases.get(key)
        if flag is None:
            raise AssertionError(f"unknown override: {key}")
        if value is None:
            continue
        if flag in arguments:
            arguments[arguments.index(flag) + 1] = str(value)
        else:
            arguments.extend([flag, str(value)])
    return completed(arguments, fixture["environment"])


def frame_paths(fixture):
    return list(fixture["method_state"].glob("frames/*/*.jsonl"))


def lineage_records(fixture):
    records = []
    for path in fixture["method_state"].glob("memory/lineage/**/*.jsonl"):
        records.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return records


def audit_records(fixture, frame_id=None):
    records = []
    for path in fixture["method_state"].glob("memory/audits/persistence/**/*.jsonl"):
        records.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    if frame_id is not None:
        return [record for record in records if record["frame_id"] == frame_id]
    return records


def read_frame_events(fixture, frame_id):
    matches = list(fixture["method_state"].glob(f"frames/*/{frame_id}.jsonl"))
    if len(matches) != 1:
        raise AssertionError(f"expected one frame path for {frame_id}: {matches}")
    return [
        json.loads(line)
        for line in matches[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def age_frame(fixture, frame_id, *, seconds=10800):
    path = list(fixture["method_state"].glob(f"frames/*/{frame_id}.jsonl"))
    if len(path) != 1:
        raise AssertionError(f"expected one frame path for {frame_id}: {path}")
    events = [
        json.loads(line)
        for line in path[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    events[-1]["timestamp_utc"] = (
        datetime.now(timezone.utc) - timedelta(seconds=seconds)
    ).replace(microsecond=0).isoformat()
    path[0].write_text(
        "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            for event in events
        ),
        encoding="utf-8",
    )


def test_receipt_parent_matches_lineage_head(fixture):
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    head = lineage(fixture)["branches"]["main"]["head_frame_id"]
    result = receipt(fixture)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["parent_frame_id"] == head
    assert output["prior_head_frame_id"] == head
    assert output["relation"] == "continue"
    assert output["frame_id"] != head


def test_receipt_three_event_shape_passes_validate_and_lineage(fixture):
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    result = receipt(fixture)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    frame_id = output["frame_id"]

    events = read_frame_events(fixture, frame_id)
    assert [event["event_type"] for event in events] == [
        "frame_opened",
        "frame_closed",
    ]
    assert output["frame_opened_event_id"] == events[0]["event_id"]
    assert output["frame_closed_event_id"] == events[1]["event_id"]

    validate = run(
        ["validate", "--frame-id", frame_id, "--require-closed"],
        fixture["environment"],
    )
    assert validate["valid"] is True
    assert validate["event_count"] == 2

    shown = lineage(fixture)
    assert shown["valid"] is True
    assert shown["record_count"] == 2
    assert shown["branches"]["main"]["head_frame_id"] == frame_id

    audits = audit_records(fixture, frame_id=frame_id)
    assert len(audits) == 1
    assert audits[0]["decision"] == "NOT_PERSISTED"
    assert audits[0]["trigger"] == "round_end"
    assert audits[0]["audit_id"] == output["persistence_audit_id"]


def test_receipt_rejects_unclosed_head_without_fork(fixture):
    root = open_frame(fixture)["frame_id"]
    before_frames = len(frame_paths(fixture))
    before_lineage = len(lineage_records(fixture))
    result = receipt(fixture)
    assert result.returncode != 0
    assert "terminal" in result.stderr
    assert len(frame_paths(fixture)) == before_frames
    assert len(lineage_records(fixture)) == before_lineage
    assert len(audit_records(fixture)) == 0


def test_receipt_rejects_missing_head(fixture):
    result = receipt(fixture)
    assert result.returncode != 0
    assert "no frames are recorded" in result.stderr
    assert len(frame_paths(fixture)) == 0
    assert len(lineage_records(fixture)) == 0
    assert len(audit_records(fixture)) == 0


def test_receipt_promoted_without_evidence_id_rejected_before_write(fixture):
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    audits_before = len(audit_records(fixture))
    result = receipt(fixture, decision="promoted")
    assert result.returncode != 0
    assert "--evidence-id" in result.stderr
    assert len(frame_paths(fixture)) == 1
    assert len(lineage_records(fixture)) == 1
    assert len(audit_records(fixture)) == audits_before


def test_receipt_promoted_writes_promoted_audit_record(fixture):
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    result = receipt(fixture, decision="promoted", evidence_id="ev-smoke")
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["decision"] == "PROMOTED"
    assert output["evidence_id"] == "ev-smoke"
    audits = audit_records(fixture, frame_id=output["frame_id"])
    assert len(audits) == 1
    assert audits[0]["decision"] == "PROMOTED"
    assert audits[0]["evidence_id"] == "ev-smoke"


def test_receipt_decision_outcome_combination_legality(fixture):
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    promoted_failed = receipt(
        fixture, decision="promoted", evidence_id="ev-1", outcome="failed"
    )
    assert promoted_failed.returncode != 0
    assert "outcome success or partial" in promoted_failed.stderr

    not_persisted_with_evidence = receipt(
        fixture, decision="not_persisted", evidence_id="ev-1"
    )
    assert not_persisted_with_evidence.returncode != 0
    assert "must not provide" in not_persisted_with_evidence.stderr

    promoted_partial = receipt(
        fixture, decision="promoted", evidence_id="ev-2", outcome="partial"
    )
    assert promoted_partial.returncode == 0, promoted_partial.stderr
    assert len(frame_paths(fixture)) == 2


def test_receipt_verdict_must_be_nonempty(fixture):
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    audits_before = len(audit_records(fixture))
    result = receipt(fixture, verdict="   ")
    assert result.returncode != 0
    assert "--verdict" in result.stderr
    assert len(frame_paths(fixture)) == 1
    assert len(lineage_records(fixture)) == 1
    assert len(audit_records(fixture)) == audits_before


def test_receipt_rejects_multiple_active_branches(fixture):
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    open_frame(fixture, branch="alt", relation="fork", parents=[root])
    result = receipt(fixture)
    assert result.returncode != 0
    assert "exactly one active branch" in result.stderr
    assert len(frame_paths(fixture)) == 2
    assert len(audit_records(fixture)) == 1


def test_receipt_branch_id_picks_target_branch_in_multi_branch_fixture(fixture):
    # multi-branch synthetic lineage: main + closed alt — both leaves must be
    # exactly equal to those branches' current heads when --branch-id picks.
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    alt = open_frame(fixture, branch="alt", relation="fork", parents=[root])["frame_id"]
    close_frame(fixture, alt)

    shown = lineage(fixture)
    main_head = shown["branches"]["main"]["head_frame_id"]
    alt_head = shown["branches"]["alt"]["head_frame_id"]

    main_result = receipt(fixture, branch_id="main")
    assert main_result.returncode == 0, main_result.stderr
    main_output = json.loads(main_result.stdout)
    assert main_output["branch_id"] == "main"
    assert main_output["parent_frame_id"] == main_head

    alt_result = receipt(fixture, branch_id="alt")
    assert alt_result.returncode == 0, alt_result.stderr
    alt_output = json.loads(alt_result.stdout)
    assert alt_output["branch_id"] == "alt"
    assert alt_output["parent_frame_id"] == alt_head


def test_receipt_branch_id_rejects_unknown_branch_id(fixture):
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    open_frame(fixture, branch="alt", relation="fork", parents=[root])
    before_frames = len(frame_paths(fixture))
    before_audits = len(audit_records(fixture))
    result = receipt(fixture, branch_id="does-not-exist")
    assert result.returncode != 0
    assert "unknown branch" in result.stderr
    assert len(frame_paths(fixture)) == before_frames
    assert len(audit_records(fixture)) == before_audits


def test_receipt_branch_id_works_in_single_branch_fixture(fixture):
    # Codex 3645 §3: single active branch + --branch-id must also succeed.
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    head = lineage(fixture)["branches"]["main"]["head_frame_id"]
    result = receipt(fixture, branch_id="main")
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["branch_id"] == "main"
    assert output["parent_frame_id"] == head


def test_receipt_branch_id_rejects_open_headed_active_branch_before_write(fixture):
    # Codex 3645 §2: open-headed active branch is rejected by assert_closed_parent
    # (NOT by --branch-id surface); the rejection happens before any write.
    root = open_frame(fixture)["frame_id"]
    close_frame(fixture, root)
    open_frame(fixture, branch="alt", relation="fork", parents=[root])  # alt open-headed
    before_frames = len(frame_paths(fixture))
    before_audits = len(audit_records(fixture))
    result = receipt(fixture, branch_id="alt")
    assert result.returncode != 0
    assert "terminal" in result.stderr or "open" in result.stderr or "abandoned" in result.stderr
    assert len(frame_paths(fixture)) == before_frames
    assert len(audit_records(fixture)) == before_audits


def test_receipt_continues_after_abandoned_head(fixture):
    root = open_frame(fixture)["frame_id"]
    age_frame(fixture, root)
    abandon = subprocess.run(
        [
            sys.executable, "-X", "utf8", str(SCRIPT),
            "frame-abandon",
            "--frame-id", root,
            "--silence-threshold-seconds", "7200",
            "--evidence", json.dumps({
                "alert_id": "fixture-alert",
                "consecutive_count": 1,
                "source_ref": "fixture:episode-receipt",
            }),
            "--reason", "episode receipt fixture abandons stale head",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=fixture["environment"],
    )
    assert abandon.returncode == 0, abandon.stderr
    result = receipt(fixture)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["parent_frame_id"] == root
