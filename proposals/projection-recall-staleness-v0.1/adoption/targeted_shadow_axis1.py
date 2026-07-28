"""Bounded targeted shadow for the double-signed axis-1 frozen candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


BASELINE_HASH = "9872361cd77d4a3efaa23b2f00560288301d9ce921425c762687b2c58f551d9e"
CANDIDATE_HASH = "03194f11a78bb5cf96dc49c90e08d7f62b216fa4a21d53d09428ad8e23432750"
DRIVERS = (
    ("test_projection_freshness_v4.py", "test_projection_freshness_v4.py:7/7_pass"),
    ("test_semantic_memory.py", "test_semantic_memory.py:pass"),
    ("test_false_zero_guard.py", "test_false_zero_guard.py:pass"),
    ("test_frame_lineage.py", "test_frame_lineage.py:pass"),
    ("test_evidence_lifecycle.py", "test_evidence_lifecycle.py:pass"),
    ("test_episode_memory.py", "test_episode_memory.py:pass"),
)
TIMEOUT_SECONDS = 120
COMPARISON_COUNT = 7


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_evolution_core(workspace_root):
    sys.path.insert(0, str(workspace_root / "tools"))
    from evolution_core import tree_hash

    return tree_hash


def ephemera(root):
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.name in {"__pycache__", ".pytest_cache"} or path.suffix == ".pyc"
    )


def run_json(script, arguments, environment):
    completed = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", str(script), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        timeout=TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{script.name} exited {completed.returncode}: "
            f"{completed.stderr[-2000:]}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{script.name} did not emit JSON: {error}") from error


def build_d0_fixture(candidate_script, root, environment):
    workspace = root / "d0-workspace"
    workspace.mkdir()
    source = root / "d0-source.txt"
    source.write_text("stable source", encoding="utf-8")
    common = ["--workspace", str(workspace), "--scope", "memory-system"]
    run_json(
        candidate_script,
        [
            "memory-control",
            *common,
            "--state",
            "active",
            "--directive",
            "axis-1 targeted shadow fixture",
        ],
        environment,
    )
    run_json(
        candidate_script,
        [
            "memory-update",
            *common,
            "--focus",
            "axis-1",
            "--status",
            "active",
            "--next",
            "compare deployed and frozen candidate",
        ],
        environment,
    )
    run_json(
        candidate_script,
        [
            "memory-consolidate",
            *common,
            "--kind",
            "decision",
            "--summary",
            "post projection new active entry",
            "--source",
            str(source),
        ],
        environment,
    )
    return [
        "memory-recall",
        "--workspace",
        str(workspace),
        "--scope",
        "memory-system",
    ]


def run_driver(script, environment):
    completed = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        timeout=TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{script.name} exited {completed.returncode}: "
            f"{completed.stderr[-2000:]}"
        )


def write_result(path, result):
    body = dict(result)
    body["result_hash"] = hashlib.sha256(
        canonical_json(result).encode("utf-8")
    ).hexdigest()
    path.write_text(
        json.dumps(body, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployed", required=True)
    parser.add_argument("--frozen-candidate", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--freeze-created", choices=("true", "false"), required=True)
    args = parser.parse_args()

    harness_path = Path(__file__).resolve()
    workspace_root = harness_path.parents[3]
    deployed = Path(args.deployed).resolve()
    frozen = Path(args.frozen_candidate).resolve()
    output = Path(args.output).resolve()
    tree_hash = load_evolution_core(workspace_root)
    freeze_created = args.freeze_created == "true"
    gate_failures = []
    baseline_checks = []
    candidate_checks = []

    pre_deployed_hash = tree_hash(deployed)
    pre_candidate_hash = tree_hash(frozen)
    physical_ephemera = ephemera(frozen)
    if pre_deployed_hash != BASELINE_HASH:
        gate_failures.append("baseline_pre_run_artifact_drift")
    if pre_candidate_hash != CANDIDATE_HASH:
        gate_failures.append("candidate_pre_run_artifact_drift")
    if physical_ephemera:
        gate_failures.append("frozen_candidate_contains_ephemera")

    if not gate_failures:
        with tempfile.TemporaryDirectory(prefix="axis1-shadow-") as temporary:
            temporary_root = Path(temporary)
            environment = os.environ.copy()
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["WEILAN_METHOD_HOME"] = str(temporary_root / "method-state")
            environment["WEILAN_ALLOW_UNRESOLVED_CONVERSATION"] = "1"
            environment["WEILAN_CODEX_SESSIONS_HOME"] = str(
                temporary_root / "sessions"
            )
            candidate_script = frozen / "scripts" / "weilan_trace.py"
            deployed_script = deployed / "scripts" / "weilan_trace.py"
            recall_arguments = build_d0_fixture(
                candidate_script, temporary_root, environment
            )
            deployed_recall = run_json(
                deployed_script, recall_arguments, environment
            )
            candidate_recall = run_json(
                candidate_script, recall_arguments, environment
            )

            deployed_bug = deployed_recall["freshness"]["fresh"] is True
            candidate_fix = (
                candidate_recall["freshness"]["freshness"] == "stale"
                and "semantic-stale"
                in candidate_recall["freshness"]["reason_codes"]
            )
            if deployed_bug:
                baseline_checks.append(
                    "memory-recall-D0-diff:not-stale(live-bug-reproduced)"
                )
            else:
                gate_failures.append("deployed_D0_live_bug_not_reproduced")
            if candidate_fix:
                candidate_checks.append(
                    "memory-recall-D0-diff:stale+semantic-stale(fix)"
                )
            else:
                gate_failures.append("candidate_D0_fix_not_reproduced")

            for filename, receipt in DRIVERS:
                try:
                    run_driver(frozen / "scripts" / filename, environment)
                    candidate_checks.append(receipt)
                except (RuntimeError, subprocess.TimeoutExpired) as error:
                    gate_failures.append(f"{filename}:{error}")

    post_deployed_hash = tree_hash(deployed)
    post_candidate_hash = tree_hash(frozen)
    if post_deployed_hash != pre_deployed_hash or post_deployed_hash != BASELINE_HASH:
        gate_failures.append("baseline_post_run_artifact_drift")
    if post_candidate_hash != pre_candidate_hash or post_candidate_hash != CANDIDATE_HASH:
        gate_failures.append("candidate_post_run_artifact_drift")
    post_ephemera = ephemera(frozen)
    if post_ephemera:
        gate_failures.append("frozen_candidate_post_run_ephemera")

    targeted_verification_passed = (
        not gate_failures
        and len(baseline_checks) == 1
        and len(candidate_checks) == COMPARISON_COUNT
    )
    result = {
        "schema_version": "weilan_skill_shadow_result_v0.6",
        "shadow_id": "projection-recall-staleness-v0.1-axis1-v4-targeted-20260724",
        "evidence_kind": "targeted_executable_verification",
        "baseline_artifact_hash": BASELINE_HASH,
        "candidate_artifact_hash": CANDIDATE_HASH,
        "harness_sha256": file_sha256(harness_path),
        "comparison_count": COMPARISON_COUNT,
        "baseline_checks": baseline_checks,
        "candidate_checks": candidate_checks,
        "gate_failures": gate_failures,
        "freeze_created": freeze_created,
        "reused_existing_artifact": not freeze_created,
        "targeted_verification_passed": targeted_verification_passed,
        "adoption_eligible": False,
        "full_suite_shadow_required_for_method_behavior": True,
        "source_refs": [
            "proposal:proposals/projection-recall-staleness-v0.1/adoption/proposal.json",
            "inbox:0da36421af5d",
            "peer-chat:2026-07-24 12:03:03",
            "peer-chat:2026-07-24 12:22:02",
        ],
        "authority": (
            "targeted_executable_verification_evidence_only__"
            "not_an_adoption_gate__method_change_requires_approved_"
            "harder_suite_full_shadow"
        ),
    }
    body = write_result(output, result)
    print(json.dumps(body, ensure_ascii=False, indent=2))
    return 0 if targeted_verification_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
