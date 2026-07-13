"""Harness for the conservation boundary-settlement probe.

The probe compares two isolated arms with the same budget-denied pending entry.
Only the experimental arm enables release->consumer settlement when a semantic
slot is released. The success signal is a downstream recall decision, not the
mechanical presence of the pending entry.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


SCRIPT = Path(__file__).with_name("weilan_trace.py")
SCOPE = "conservation-probe"
PENDING_ID = str(uuid.UUID("11111111-2222-4333-8444-555555555555"))
W_SUMMARY = "probe W downstream conclusion becomes available after settlement"
K_SUMMARY = "anchor K remains clean unless W is admitted as a conflict"


def run(arguments, environment):
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    return json.loads(completed.stdout)


def projection_snapshot(workspace, environment, scope=SCOPE):
    run(["projection-rebuild", "--workspace", workspace, "--scope", scope], environment)
    recall = run(["memory-recall", "--workspace", workspace, "--scope", scope], environment)
    return recall["projection"]


def clean_decisions(workspace, environment, scope=SCOPE):
    return projection_snapshot(workspace, environment, scope).get("decisions", [])


def contains_summary(decisions, summary):
    return any(summary in decision for decision in decisions)


def setup_arm(root, arm, settle_pending):
    environment = os.environ.copy()
    environment["WEILAN_METHOD_HOME"] = str(root / f"method-state-{arm}")
    workspace_path = root / f"workspace-{arm}"
    workspace_path.mkdir()
    workspace = str(workspace_path)
    source = root / f"source-{arm}.txt"
    source.write_text("conservation probe fixture\n", encoding="utf-8")

    run(
        [
            "memory-control",
            "--workspace",
            workspace,
            "--scope",
            SCOPE,
            "--state",
            "active",
            "--directive",
            "exercise conservation boundary-settlement probe",
        ],
        environment,
    )
    run(
        [
            "memory-budget-set",
            "--workspace",
            workspace,
            "--scope",
            SCOPE,
            "--max-active",
            "2",
            "--reason",
            "fixed active-slot budget for conservation probe",
        ],
        environment,
    )
    release_source = run(
        [
            "memory-consolidate",
            "--workspace",
            workspace,
            "--scope",
            SCOPE,
            "--kind",
            "decision",
            "--summary",
            "release source H occupies one semantic slot",
            "--source",
            str(source),
        ],
        environment,
    )
    anchor = run(
        [
            "memory-consolidate",
            "--workspace",
            workspace,
            "--scope",
            SCOPE,
            "--kind",
            "decision",
            "--summary",
            K_SUMMARY,
            "--source",
            str(source),
        ],
        environment,
    )

    pending = run(
        [
            "memory-pending-capture",
            "--workspace",
            workspace,
            "--scope",
            SCOPE,
            "--kind",
            "decision",
            "--summary",
            W_SUMMARY,
            "--source",
            str(source),
            "--pending-id",
            PENDING_ID,
            "--conflicts-with",
            anchor["memory_id"],
        ],
        environment,
    )
    if not pending["captured"] or pending["recall_visible"] or pending["active_visible"]:
        raise AssertionError(f"{arm}: pending entry crossed its visibility boundary")

    before_decisions = clean_decisions(workspace, environment)
    if contains_summary(before_decisions, W_SUMMARY):
        raise AssertionError(f"{arm}: pending W leaked into recall before release")
    if not contains_summary(before_decisions, K_SUMMARY):
        raise AssertionError(f"{arm}: clean anchor K was absent before settlement")

    disposition_args = [
        "memory-disposition",
        "--workspace",
        workspace,
        "--scope",
        SCOPE,
        "--memory-id",
        release_source["memory_id"],
        "--state",
        "retired",
        "--reason",
        "probe releases one active semantic slot",
        "--source",
        str(source),
    ]
    if settle_pending:
        disposition_args.append("--settle-pending")
    disposition = run(disposition_args, environment)

    after_projection = projection_snapshot(workspace, environment)
    after_decisions = after_projection.get("decisions", [])
    pending_show = run(
        ["memory-pending-show", "--workspace", workspace, "--scope", SCOPE],
        environment,
    )
    search = run(
        ["memory-search", "--workspace", workspace, "--scope", SCOPE, "--query", "downstream"],
        environment,
    )

    return {
        "arm": arm,
        "workspace": workspace,
        "release_source_id": release_source["memory_id"],
        "anchor_id": anchor["memory_id"],
        "pending_id": pending["pending_id"],
        "settle_pending": settle_pending,
        "disposition": disposition,
        "before_decisions": before_decisions,
        "after_decisions": after_decisions,
        "after_projection": after_projection,
        "pending_show": pending_show,
        "search_matched": search["matched"],
        "search_result_ids": [item["memory_id"] for item in search["results"]],
    }


def setup_basic_scope(root, name, scope, max_active):
    environment = os.environ.copy()
    environment["WEILAN_METHOD_HOME"] = str(root / f"method-state-{name}")
    workspace_path = root / f"workspace-{name}"
    workspace_path.mkdir()
    workspace = str(workspace_path)
    source = root / f"source-{name}.txt"
    source.write_text("conservation probe fixture\n", encoding="utf-8")

    run(
        [
            "memory-control",
            "--workspace",
            workspace,
            "--scope",
            scope,
            "--state",
            "active",
            "--directive",
            "exercise conservation boundary-settlement probe",
        ],
        environment,
    )
    run(
        [
            "memory-budget-set",
            "--workspace",
            workspace,
            "--scope",
            scope,
            "--max-active",
            str(max_active),
            "--reason",
            "fixed active-slot budget for conservation probe",
        ],
        environment,
    )
    release_source = run(
        [
            "memory-consolidate",
            "--workspace",
            workspace,
            "--scope",
            scope,
            "--kind",
            "decision",
            "--summary",
            f"release source for {name}",
            "--source",
            str(source),
        ],
        environment,
    )
    return environment, workspace, source, release_source


def exercise_empty_queue(root):
    scope = f"{SCOPE}-empty-queue"
    environment, workspace, source, release_source = setup_basic_scope(root, "empty", scope, 1)
    disposition = run(
        [
            "memory-disposition",
            "--workspace",
            workspace,
            "--scope",
            scope,
            "--memory-id",
            release_source["memory_id"],
            "--state",
            "retired",
            "--reason",
            "probe releases one active semantic slot",
            "--source",
            str(source),
            "--settle-pending",
        ],
        environment,
    )
    settlement = disposition.get("pending_settlement", {})
    if settlement.get("settled") or settlement.get("reason") != "no_pending_consumer":
        raise AssertionError("empty queue settlement did not return the released slot")
    return {
        "empty_queue_returned": True,
        "active_count_after_release": disposition["active_entry_count"],
        "settlement": settlement,
    }


def exercise_two_pending_fifo(root):
    scope = f"{SCOPE}-fifo"
    environment, workspace, source, release_source = setup_basic_scope(root, "fifo", scope, 1)
    first_pending = str(uuid.UUID("22222222-2222-4333-8444-555555555555"))
    second_pending = str(uuid.UUID("33333333-2222-4333-8444-555555555555"))
    for pending_id, summary in [
        (first_pending, "first queued pending W"),
        (second_pending, "second queued pending W"),
    ]:
        pending = run(
            [
                "memory-pending-capture",
                "--workspace",
                workspace,
                "--scope",
                scope,
                "--kind",
                "decision",
                "--summary",
                summary,
                "--source",
                str(source),
                "--pending-id",
                pending_id,
            ],
            environment,
        )
        if not pending["captured"]:
            raise AssertionError(f"pending capture failed for {pending_id}")

    disposition = run(
        [
            "memory-disposition",
            "--workspace",
            workspace,
            "--scope",
            scope,
            "--memory-id",
            release_source["memory_id"],
            "--state",
            "retired",
            "--reason",
            "probe releases one active semantic slot",
            "--source",
            str(source),
            "--settle-pending",
        ],
        environment,
    )
    settlement = disposition.get("pending_settlement", {})
    pending_show = run(["memory-pending-show", "--workspace", workspace, "--scope", scope], environment)
    if settlement.get("pending_id") != first_pending:
        raise AssertionError("settlement did not consume the first queued pending entry")
    if pending_show["queued_count"] != 1 or pending_show["admitted_count"] != 1:
        raise AssertionError("two-pending settlement did not leave exactly one queued and one admitted")
    if pending_show["queued"][0]["pending_id"] != second_pending:
        raise AssertionError("settlement did not preserve the second pending entry")
    return {
        "two_pending_fifo": True,
        "admitted_pending_id": settlement["pending_id"],
        "remaining_pending_id": pending_show["queued"][0]["pending_id"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-parent")
    args = parser.parse_args()

    temp_parent = Path(args.temp_parent).resolve() if args.temp_parent else Path.home()
    temp_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="weilan-conservation-probe-", dir=str(temp_parent)) as temporary:
        root = Path(temporary)
        control = setup_arm(root, "control", settle_pending=False)
        experiment = setup_arm(root, "experiment", settle_pending=True)
        empty_queue = exercise_empty_queue(root)
        two_pending_fifo = exercise_two_pending_fifo(root)

        control_k_clean = contains_summary(control["after_decisions"], K_SUMMARY)
        experiment_k_clean = contains_summary(experiment["after_decisions"], K_SUMMARY)
        experiment_w_clean = contains_summary(experiment["after_decisions"], W_SUMMARY)
        experiment_contested = {
            item["summary"]: item
            for item in experiment["after_projection"].get("contested_semantic_entries", [])
        }
        downstream_changed = control_k_clean and not experiment_k_clean
        if control["pending_show"]["queued_count"] != 1 or control["pending_show"]["admitted_count"] != 0:
            raise AssertionError("control arm did not retain the same pending W without settlement")
        if experiment["pending_show"]["queued_count"] != 0 or experiment["pending_show"]["admitted_count"] != 1:
            raise AssertionError("experimental arm did not consume exactly one pending W")
        if not control_k_clean:
            raise AssertionError("control arm lost clean third-party K without release settlement")
        if experiment_k_clean:
            raise AssertionError("experimental arm did not demote third-party K after W settlement")
        if experiment_w_clean:
            raise AssertionError("mechanically admitted W leaked into clean decisions")
        if K_SUMMARY not in experiment_contested or W_SUMMARY not in experiment_contested:
            raise AssertionError("experimental arm did not preserve W/K as contested downstream evidence")
        if control["disposition"]["active_entry_count"] > 2:
            raise AssertionError("control arm exceeded max_active")
        if experiment["disposition"]["active_entry_count"] > 2:
            raise AssertionError("experimental arm exceeded max_active")
        if control["pending_id"] != experiment["pending_id"]:
            raise AssertionError("probe arms did not capture the same pending id")

        print(json.dumps({
            "conservation_boundary_settlement_probe": True,
            "same_pending_id": PENDING_ID,
            "control_k_clean": control_k_clean,
            "experiment_k_clean": experiment_k_clean,
            "experiment_downstream_changed": downstream_changed,
            "control_active_count_after_release": control["disposition"]["active_entry_count"],
            "experiment_active_count_after_release": experiment["disposition"]["active_entry_count"],
            "experiment_contested_summaries": sorted(experiment_contested),
            "control_pending": control["pending_show"],
            "experiment_pending": experiment["pending_show"],
            "empty_queue": empty_queue,
            "two_pending_fifo": two_pending_fifo,
        }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
