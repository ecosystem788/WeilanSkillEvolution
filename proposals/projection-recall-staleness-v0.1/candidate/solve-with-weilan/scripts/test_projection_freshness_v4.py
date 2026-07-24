"""Axis-1 v4 regression arms for semantic freshness and branch preflight.

These tests anchor the current stateless recomputation behavior. If a later,
separately authorized proposal introduces forced rebuild, the no-write arm is
expected to fail deliberately until that contract is revised.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("weilan_trace.py")
SCOPE = "memory-system"


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


def control(workspace, environment):
    return run(
        [
            "memory-control", "--workspace", workspace, "--scope", SCOPE,
            "--state", "active", "--directive", "axis-1 fixture",
        ],
        environment,
    )


def update(workspace, environment, source=None):
    arguments = [
        "memory-update", "--workspace", workspace, "--scope", SCOPE,
        "--focus", "axis-1", "--status", "active", "--next", "verify",
    ]
    if source is not None:
        arguments.extend(["--source", str(source)])
    return run(arguments, environment)


def recall(workspace, environment):
    return run(
        ["memory-recall", "--workspace", workspace, "--scope", SCOPE],
        environment,
    )


def consolidate(workspace, source, summary, environment, conflicts_with=None):
    arguments = [
        "memory-consolidate", "--workspace", workspace, "--scope", SCOPE,
        "--kind", "decision", "--summary", summary, "--source", str(source),
    ]
    if conflicts_with:
        arguments.extend(["--conflicts-with", conflicts_with])
    return run(arguments, environment)


def component(result, name, current=False):
    freshness = result["freshness"]
    key = (
        "current_semantic_dependency_vector"
        if current
        else "semantic_dependency_vector"
    )
    owner = freshness if current else result["projection"]
    return owner[key]["components"][name]


def assert_semantic_stale(result):
    if result["activation"]["state"] != "STALE":
        raise AssertionError(f"expected STALE, got {result['activation']}")
    if result["freshness"]["freshness"] != "stale":
        raise AssertionError("new freshness enum did not report stale")
    if "semantic-stale" not in result["freshness"]["reason_codes"]:
        raise AssertionError("semantic-stale reason was not surfaced")


def assert_schema(result):
    freshness = result["freshness"]
    required = {
        "fresh",
        "freshness",
        "adjudication",
        "branch_selection_needed",
        "reason_codes",
    }
    if not required.issubset(freshness):
        raise AssertionError(f"freshness schema keys missing: {required - set(freshness)}")
    if freshness["freshness"] not in {"fresh", "stale"}:
        raise AssertionError("freshness enum is incompatible")
    if freshness["adjudication"] not in {"clean", "contested"}:
        raise AssertionError("adjudication enum is incompatible")


def arm_d0(root, environment):
    workspace = str(root / "d0")
    Path(workspace).mkdir()
    source = root / "d0-source.txt"
    source.write_text("stable source", encoding="utf-8")
    before_source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    control(workspace, environment)
    update(workspace, environment)
    baseline = recall(workspace, environment)
    assert_schema(baseline)
    old_component = baseline["projection"]["semantic_dependency_vector"]["components"][
        "active_semantic_entries"
    ]
    consolidate(workspace, source, "new active semantic entry", environment)
    stale = recall(workspace, environment)
    assert_semantic_stale(stale)
    new_component = component(stale, "active_semantic_entries", current=True)
    if old_component == new_component:
        raise AssertionError("D0 did not flip the active semantic-entry component")
    if before_source_hash != hashlib.sha256(source.read_bytes()).hexdigest():
        raise AssertionError("D0 changed an existing source byte")


def arm_d1(root, environment):
    source = root / "d1-source.txt"
    source.write_text("stable source", encoding="utf-8")
    for state in ("dormant", "retired"):
        workspace = str(root / f"d1-{state}")
        Path(workspace).mkdir()
        control(workspace, environment)
        memory = consolidate(
            workspace, source, f"{state} disposition dependency", environment
        )
        update(workspace, environment)
        baseline = recall(workspace, environment)
        old_component = baseline["projection"]["semantic_dependency_vector"]["components"][
            "semantic_dispositions"
        ]
        run(
            [
                "memory-disposition", "--workspace", workspace, "--scope", SCOPE,
                "--memory-id", memory["memory_id"], "--state", state,
                "--reason", f"D1 {state} fixture",
            ],
            environment,
        )
        stale = recall(workspace, environment)
        assert_semantic_stale(stale)
        if old_component == component(stale, "semantic_dispositions", current=True):
            raise AssertionError(f"D1 {state} did not flip the disposition component")


def arm_d2(root, environment):
    for state in ("withdrawn", "expired", "superseded"):
        workspace = str(root / f"d2-{state}")
        Path(workspace).mkdir()
        control(workspace, environment)
        evidence = run(
            [
                "evidence-capture", "--workspace", workspace, "--scope", SCOPE,
                "--signal", "architectural_decision",
                "--claim", f"{state} evidence lifecycle dependency",
                "--source", f"conversation:axis1-test#d2-{state}",
            ],
            environment,
        )
        run(
            [
                "evidence-promote", "--workspace", workspace, "--scope", SCOPE,
                "--evidence-id", evidence["evidence_id"], "--kind", "decision",
                "--summary", f"{state} evidence lifecycle dependency",
                "--stable", "--reusable", "--privacy-reviewed",
            ],
            environment,
        )
        update(workspace, environment)
        baseline = recall(workspace, environment)
        old_component = baseline["projection"]["semantic_dependency_vector"]["components"][
            "evidence_dependencies"
        ]

        unrelated = run(
            [
                "evidence-capture", "--workspace", workspace, "--scope", SCOPE,
                "--signal", "architectural_decision",
                "--claim", f"{state} unrelated evidence",
                "--source", f"conversation:axis1-test#unrelated-{state}",
            ],
            environment,
        )
        run(
            [
                "evidence-disposition", "--workspace", workspace, "--scope", SCOPE,
                "--evidence-id", unrelated["evidence_id"], "--state", "withdrawn",
                "--reason", "unrelated D2 negative control",
            ],
            environment,
        )
        unrelated_recall = recall(workspace, environment)
        if unrelated_recall["activation"]["state"] != "ACTIVE":
            raise AssertionError("unrelated evidence lifecycle manufactured staleness")
        if old_component != component(
            unrelated_recall, "evidence_dependencies", current=True
        ):
            raise AssertionError("unrelated evidence leaked into the dependency set")

        disposition_arguments = [
            "evidence-disposition", "--workspace", workspace, "--scope", SCOPE,
            "--evidence-id", evidence["evidence_id"], "--state", state,
            "--reason", f"D2 {state} fixture",
        ]
        if state == "superseded":
            replacement = run(
                [
                    "evidence-capture", "--workspace", workspace, "--scope", SCOPE,
                    "--signal", "architectural_decision",
                    "--claim", "replacement evidence lifecycle dependency",
                    "--source", "conversation:axis1-test#replacement",
                ],
                environment,
            )
            disposition_arguments.extend(
                ["--replacement-evidence-id", replacement["evidence_id"]]
            )
        run(disposition_arguments, environment)
        stale = recall(workspace, environment)
        assert_semantic_stale(stale)
        if old_component == component(stale, "evidence_dependencies", current=True):
            raise AssertionError(
                f"D2 {state} did not flip the relevant evidence component"
            )


def arm_d3(root, environment):
    workspace = str(root / "d3")
    Path(workspace).mkdir()
    control(workspace, environment)
    update(workspace, environment)
    baseline = recall(workspace, environment)
    old_vector = baseline["projection"]["semantic_dependency_vector"]["hash"]
    run(
        [
            "memory-budget-set", "--workspace", workspace, "--scope", SCOPE,
            "--max-active", "101", "--reason", "D3 negative control",
        ],
        environment,
    )
    current = recall(workspace, environment)
    if current["activation"]["state"] != "ACTIVE":
        raise AssertionError("budget-only change manufactured staleness")
    if old_vector != current["freshness"]["current_semantic_dependency_vector"]["hash"]:
        raise AssertionError("budget head leaked into the dependency vector")


def arms_abc_and_contested(root, environment):
    workspace = str(root / "abc")
    Path(workspace).mkdir()
    source = root / "abc-source.txt"
    source.write_text("v1", encoding="utf-8")
    control(workspace, environment)
    update(workspace, environment, source)
    arm_a = recall(workspace, environment)
    if arm_a["activation"]["state"] != "ACTIVE":
        raise AssertionError("arm A baseline was not fresh")
    source.write_text("v2", encoding="utf-8")
    arm_b = recall(workspace, environment)
    if "source_changed" not in arm_b["freshness"]["reason_codes"]:
        raise AssertionError("arm B did not surface source_changed")
    source.write_text("v1", encoding="utf-8")
    arm_c = recall(workspace, environment)
    if arm_c["activation"]["state"] != "ACTIVE":
        raise AssertionError("arm C did not return to fresh after byte restoration")

    first = consolidate(workspace, source, "contested alpha", environment)
    consolidate(
        workspace, source, "contested beta", environment,
        conflicts_with=first["memory_id"],
    )
    update(workspace, environment, source)
    contested = recall(workspace, environment)
    freshness = contested["freshness"]
    if freshness["fresh"] is not True or freshness["freshness"] != "fresh":
        raise AssertionError("contested state polluted the freshness axis")
    if freshness["adjudication"] != "contested":
        raise AssertionError("contested adjudication was not surfaced")
    if "contested" not in freshness["reason_codes"]:
        raise AssertionError("contested reason was not surfaced")
    if contested["activation"]["state"] != "ACTIVE":
        raise AssertionError("contested state changed activation authority")


def close_lineaged(frame_id, environment):
    run(
        [
            "persistence-audit", "--frame-id", frame_id, "--trigger", "round_end",
            "--decision", "not_persisted", "--reason", "branch fixture only",
        ],
        environment,
    )
    run(
        [
            "close", "--frame-id", frame_id, "--outcome", "success",
            "--verdict", "branch fixture closed",
        ],
        environment,
    )


def branch_preflight_arm(root, environment):
    workspace = str(root / "branches")
    Path(workspace).mkdir()
    control(workspace, environment)
    legacy = run(
        [
            "open", "--level", "L2", "--workspace", workspace,
            "--problem", "legacy branch anchor", "--success", "closed",
        ],
        environment,
    )["frame_id"]
    run(
        [
            "close", "--frame-id", legacy, "--outcome", "success",
            "--verdict", "legacy anchor closed",
        ],
        environment,
    )
    main_frame = run(
        [
            "open", "--level", "L2", "--workspace", workspace, "--scope", SCOPE,
            "--branch", "main", "--relation", "continue", "--parent", legacy,
            "--problem", "main branch", "--success", "closed",
        ],
        environment,
    )["frame_id"]
    close_lineaged(main_frame, environment)
    peer_frame = run(
        [
            "open", "--level", "L2", "--workspace", workspace, "--scope", SCOPE,
            "--branch", "peer", "--relation", "fork", "--parent", main_frame,
            "--problem", "peer branch", "--success", "closed",
        ],
        environment,
    )["frame_id"]
    close_lineaged(peer_frame, environment)
    rebuilt = run(
        [
            "projection-rebuild", "--workspace", workspace, "--scope", SCOPE,
            "--branch", "main",
        ],
        environment,
    )
    projection_path = Path(rebuilt["path"])
    before = projection_path.read_bytes()
    recalled = recall(workspace, environment)
    after = projection_path.read_bytes()
    freshness = recalled["freshness"]
    if freshness["branch_selection_needed"] is not True:
        raise AssertionError("multiple active branches did not request selection")
    if "operational-stale-branch-needed" not in freshness["reason_codes"]:
        raise AssertionError("operational branch reason was not surfaced")
    if before != after:
        raise AssertionError("read-only branch preflight wrote the projection")
    if recalled["activation"]["state"] != "ACTIVE":
        raise AssertionError("branch preflight changed activation.state")
    if freshness["fresh"] is not True:
        raise AssertionError("branch preflight changed legacy fresh")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temp-parent")
    args = parser.parse_args()
    parent = Path(args.temp_parent).resolve() if args.temp_parent else Path.home()
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="axis1-v4-", dir=str(parent)) as temporary:
        root = Path(temporary)
        environment = os.environ.copy()
        environment["WEILAN_METHOD_HOME"] = str(root / "method-state")
        environment["WEILAN_ALLOW_UNRESOLVED_CONVERSATION"] = "1"
        environment["WEILAN_CODEX_SESSIONS_HOME"] = str(root / "sessions")
        arm_d0(root, environment)
        arm_d1(root, environment)
        arm_d2(root, environment)
        arm_d3(root, environment)
        arms_abc_and_contested(root, environment)
        branch_preflight_arm(root, environment)
    print(
        json.dumps(
            {
                "valid": True,
                "arms": ["D0", "D1", "D2", "D3", "A", "B", "C"],
                "branch_selection_needed": "read_only",
                "schema_compatibility": True,
                "forced_rebuild_contract": "deliberately_not_authorized",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
