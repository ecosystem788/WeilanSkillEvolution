"""Adversarial integrity tests for evaluator-owned trial evidence."""

import copy
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from evolution_core import (
    AGGREGATION_VERSION,
    EVAL_SCHEMA_VERSION,
    TRIAL_SCHEMA_VERSION,
    canonical_json,
    compare_trials,
    sha256_text,
)
from release_core import SHADOW_SCHEMA_VERSION, compare_shadow, validate_shadow_plan


def expect_rejected(call, text):
    try:
        call()
    except ValueError as error:
        if text not in str(error):
            raise AssertionError(f"expected {text!r}, got {error!r}") from error
    else:
        raise AssertionError(f"invalid evaluation evidence was accepted: {text}")


def main():
    cases = [
        {
            "case_id": "repeated",
            "trial_count": 2,
            "budget": {"tool_calls": 4, "context_tokens": 1000},
            "metrics": {"outcome": 1.0},
        },
        {
            "case_id": "single",
            "trial_count": 1,
            "budget": {"tool_calls": 4, "context_tokens": 1000},
            "metrics": {"outcome": 1.0},
        },
    ]
    case_set = {
        "schema_version": "weilan_skill_eval_case_set_v0.1",
        "suite_id": "integrity-v0.1",
        "status": "approved_frozen",
        "frozen": True,
        "approval_source": "external:integrity-test",
        "cases": [
            {
                "case_id": case["case_id"],
                "task": f"execute {case['case_id']}",
                "success": ["evidence scored"],
                "guardrails": ["authority preserved"],
            }
            for case in cases
        ],
    }
    case_hash = sha256_text(canonical_json(case_set))
    manifest = {
        "schema_version": EVAL_SCHEMA_VERSION,
        "suite_id": case_set["suite_id"],
        "status": "approved",
        "frozen": True,
        "approval_source": case_set["approval_source"],
        "scoring_version": "integrity-score-v0.1",
        "case_spec": "evals/cases/integrity.json",
        "case_spec_hash": case_hash,
        "cases": cases,
    }
    manifest_hash = sha256_text(canonical_json(manifest))
    plan = {
        "schema_version": SHADOW_SCHEMA_VERSION,
        "shadow_id": "integrity-shadow",
        "baseline_artifact_hash": "a" * 64,
        "candidate_artifact_hash": "b" * 64,
        "configuration_hash": "c" * 64,
        "environment_id": "isolated-integrity-environment",
        "evaluation_manifest_hash": manifest_hash,
        "case_spec_hash": case_hash,
        "fixture_manifest_hashes": {"repeated": "d" * 64, "single": "e" * 64},
        "aggregation_version": AGGREGATION_VERSION,
        "max_receipts": 6,
        "gate": {"min_mean_delta": 0.0, "required_case_deltas": {}},
    }
    validation = validate_shadow_plan(plan, manifest, case_set)
    if not validation["valid"]:
        raise AssertionError(validation["issues"])

    def receipt(case_id, trial, variant, score):
        case = next(item for item in cases if item["case_id"] == case_id)
        return {
            "schema_version": TRIAL_SCHEMA_VERSION,
            "case_id": case_id,
            "trial": trial,
            "variant": variant,
            "artifact_hash": plan[f"{variant}_artifact_hash"],
            "evaluation_manifest_hash": manifest_hash,
            "case_spec_hash": case_hash,
            "fixture_manifest_hash": plan["fixture_manifest_hashes"][case_id],
            "configuration_hash": plan["configuration_hash"],
            "environment_id": plan["environment_id"],
            "scoring_version": manifest["scoring_version"],
            "budget": case["budget"],
            "actual_usage": {"tool_calls": 2, "context_tokens": 500},
            "termination_status": "completed",
            "raw_output_hash": "f" * 64,
            "grader_id": "independent-grader",
            "grader_provenance": {
                "authority_source": "external:grader",
                "evaluator_artifact_hash": "1" * 64,
                "evidence_hash": "2" * 64,
            },
            "metrics": {"outcome": score},
            "guardrail_failures": ["baseline-observed"]
            if case_id == "repeated" and trial == 1 and variant == "baseline"
            else [],
            "method_impacts": [],
        }

    receipts = []
    for trial in (1, 2):
        receipts.extend([
            receipt("repeated", trial, "baseline", 0.0),
            receipt("repeated", trial, "candidate", 1.0),
        ])
    receipts.extend([
        receipt("single", 1, "baseline", 1.0),
        receipt("single", 1, "candidate", 0.0),
    ])

    result = compare_shadow(plan, manifest, receipts, case_set=case_set)
    if result["mean_delta"] != 0.0 or result["case_deltas"] != {"repeated": 1.0, "single": -1.0}:
        raise AssertionError("repeated trials were not reduced to equal-weight case means")
    if result["baseline_guardrail_failures"] != ["baseline-observed"]:
        raise AssertionError("baseline guardrail evidence was not preserved symmetrically")
    if result["candidate_guardrail_failures"]:
        raise AssertionError("candidate guardrail evidence changed unexpectedly")

    duplicate = receipts + [copy.deepcopy(receipts[0])]
    expect_rejected(lambda: compare_trials(manifest, duplicate), "duplicate trial identity")

    for label, mutate, expected in (
        ("missing metric", lambda item: item["metrics"].clear(), "metrics must exactly match"),
        ("NaN metric", lambda item: item["metrics"].update(outcome=math.nan), "must be finite"),
        ("range metric", lambda item: item["metrics"].update(outcome=1.1), "must be finite"),
        ("budget overrun", lambda item: item["actual_usage"].update(tool_calls=5), "exceeds declared budget"),
        ("missing grader", lambda item: item.pop("grader_id"), "grader_id is required"),
        ("bad raw hash", lambda item: item.update(raw_output_hash="not-a-hash"), "raw_output_hash"),
        ("wrong manifest", lambda item: item.update(evaluation_manifest_hash="0" * 64), "manifest hash mismatch"),
    ):
        changed = copy.deepcopy(receipts)
        mutate(changed[0])
        expect_rejected(lambda changed=changed: compare_trials(manifest, changed), expected)

    tampered_case_set = copy.deepcopy(case_set)
    tampered_case_set["cases"][0]["task"] = "tampered"
    expect_rejected(
        lambda: compare_shadow(plan, manifest, receipts, case_set=tampered_case_set),
        "loaded case-set content hash mismatch",
    )
    expect_rejected(
        lambda: compare_shadow(plan, manifest, receipts),
        "requires the loaded frozen case set",
    )

    print(json.dumps({
        "valid": True,
        "duplicates_rejected": True,
        "metrics_strict": True,
        "provenance_required": True,
        "budget_usage_enforced": True,
        "case_set_content_bound": True,
        "guardrails_symmetric": True,
        "equal_case_aggregation": True,
    }, indent=2))


if __name__ == "__main__":
    main()
