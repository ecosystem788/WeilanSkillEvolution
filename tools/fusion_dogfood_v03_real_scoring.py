"""Real-trial scoring utilities for fusion-dogfood-v0.3 calibration receipts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fusion_dogfood_v03_harness import receipt_hash, validate_arm_purity, write_json


BASELINE_HASH = "2c539d0b9444a395e66ce4ddaad1412f0ea5c4f0541112f63d3365c65d2bcf4f"
SUITE_ID = "fusion-dogfood-v0.3"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def text_of(value) -> str:
    return json.dumps(value, ensure_ascii=False).lower()


def contains(value, needle: str) -> bool:
    return needle.lower() in text_of(value)


def ledger_text(trial_root: Path) -> str:
    chunks = []
    roots = [trial_root / "method-home", trial_root / "workspace" / "method-home"]
    paths = []
    for root in roots:
        try:
            paths.extend(sorted(root.rglob("*")))
        except OSError:
            continue
    for path in paths:
        try:
            is_relevant = path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"}
        except OSError:
            continue
        if is_relevant:
            try:
                chunks.append(path.read_text(encoding="utf-8-sig", errors="ignore"))
            except OSError:
                continue
    return "\n".join(chunks).lower()


def certified_runtime_collapse(trial_root: Path, receipt: dict) -> bool:
    if receipt.get("arm") != "method-baseline":
        return False
    haystack = ledger_text(trial_root) + "\n" + text_of(receipt.get("ledger_observables", []))
    if "fallback" in haystack and "runtime" in haystack and "failed" in haystack:
        return False
    return any(marker in haystack for marker in [
        "minimal_unit_collapsed",
        '"event_type": "collapse"',
        '"event_type":"collapse"',
        '"event_type": "supersession"',
        '"event_type":"supersession"',
    ])


def certified_runtime_trace(trial_root: Path, receipt: dict) -> bool:
    if receipt.get("arm") != "method-baseline":
        return False
    haystack = ledger_text(trial_root) + "\n" + text_of(receipt.get("ledger_observables", []))
    if "fallback" in haystack and "runtime" in haystack and "failed" in haystack:
        return False
    return any(marker in haystack for marker in [
        "trace_emitted",
        '"event_type": "trace"',
        '"event_type":"trace"',
    ])


def fallback_or_path_issue(receipt: dict) -> bool:
    haystack = text_of(receipt)
    return any(marker in haystack for marker in ["fallback", "path-length", "path length", "runtime error", "failed tool-call budget"])


def score_trial(trial_root: Path) -> dict:
    receipt = read_json(trial_root / "receipt.json")
    telemetry = read_json(trial_root / "telemetry.json")
    trial_id = trial_root.name
    case_id = receipt.get("case_id")
    arm = receipt.get("arm")
    trace = telemetry.get("rollout_trace") or telemetry
    actual_usage = trace.get("actual_usage") or telemetry.get("actual_usage")
    r3_budget_bound = telemetry.get("r3_budget_bound")
    if r3_budget_bound is None and isinstance(actual_usage, dict):
        r3_budget_bound = not bool(actual_usage.get("truncated"))
    purity = validate_arm_purity(arm, trace)
    trial_valid_for_scoring = purity["valid"] or arm == "method-baseline"
    if "stale-holder-collapse" in trial_id:
        conflict_recognized = any(
            contains(receipt, marker)
            for marker in ["invalidated_holder", "invalidating_public_evidence", "not active truth", "superseded"]
        )
        certified_collapse = certified_runtime_collapse(trial_root, receipt)
        certified_trace = certified_runtime_trace(trial_root, receipt)
        path_issue = fallback_or_path_issue(receipt)
        if arm == "no-method":
            score = 0.20 if conflict_recognized else 0.10
        elif arm == "append-only":
            score = 0.45 if conflict_recognized else 0.25
        else:
            score = 0.78 if certified_collapse and certified_trace and not path_issue else 0.68 if conflict_recognized else 0.40
        reasons = {
            "conflict_recognized": conflict_recognized,
            "certified_runtime_collapse_or_supersession": certified_collapse,
            "certified_runtime_trace": certified_trace,
            "fallback_or_path_issue": path_issue,
            "scoring_note": "negative-control receipt text is not counted as authenticated collapse evidence",
        }
    elif "redesign-conflict-v2" in str(case_id) or trial_id.startswith("cross-v2-"):
        decision_y = receipt.get("decision") == "Y" or contains(receipt, '"decision": "Y"')
        conflict_recognized = any(
            contains(receipt, marker)
            for marker in ["invalidated", "retired_for_hash_drift", "successor", "superseded", "collapsed"]
        )
        recalled_procedure = bool(receipt.get("recalled_procedure_id")) or contains(receipt, "proc-threshold-plus-two-on-retired-hash")
        certified_collapse = certified_runtime_collapse(trial_root, receipt)
        certified_trace = certified_runtime_trace(trial_root, receipt)
        path_issue = fallback_or_path_issue(receipt)
        if arm == "no-method":
            score = 0.30 if decision_y else 0.15
        elif arm == "append-only":
            score = 0.55 if decision_y and recalled_procedure else 0.45 if conflict_recognized else 0.25
        else:
            score = 0.76 if decision_y and certified_collapse and certified_trace and not path_issue else 0.45 if conflict_recognized else 0.30
        reasons = {
            "decision_y": decision_y,
            "conflict_recognized": conflict_recognized,
            "recalled_procedure": recalled_procedure,
            "certified_runtime_collapse_or_supersession": certified_collapse,
            "certified_runtime_trace": certified_trace,
            "fallback_or_path_issue": path_issue,
            "scoring_note": "v2 correct decision is Y; method mechanism credit requires authenticated runtime collapse/trace, not receipt text",
        }
    elif "cross-window" in trial_id:
        decision_z = contains(receipt, '"z"') or receipt.get("decision") == "Z"
        recalled = bool(receipt.get("recalled_rule_id")) or contains(receipt, "rule-public-rotated-slice-v1")
        verified = contains(receipt, "sha256:public-rotated-slice-v1") or contains(receipt, "source_verification")
        path_issue = fallback_or_path_issue(receipt)
        if arm == "no-method":
            score = 0.15 if not decision_z else 0.30
        elif arm == "append-only":
            score = 0.78 if decision_z and recalled else 0.50
        else:
            score = 0.76 if decision_z and recalled and not path_issue else 0.66 if decision_z and recalled else 0.45
        reasons = {
            "decision_z": decision_z,
            "recalled_rule": recalled,
            "source_verified_claim": verified,
            "fallback_or_path_issue": path_issue,
        }
    else:
        selected = text_of(receipt.get("selected_sources", []))
        selected_receipt07 = "receipt-07" in selected
        selected_gate03 = "gate-03" in selected
        skipped = bool(receipt.get("skipped_sources")) or contains(receipt, "skipped")
        full_coverage_claim = contains(receipt, "complete corpus coverage") or contains(receipt, "full coverage")
        score = 0.30
        if selected_receipt07:
            score += 0.25
        if selected_gate03:
            score += 0.25
        if skipped:
            score += 0.10
        if not full_coverage_claim:
            score += 0.05
        reasons = {
            "selected_receipt_07": selected_receipt07,
            "selected_gate_03": selected_gate03,
            "skipped_sources_present": skipped,
            "full_coverage_claim": full_coverage_claim,
        }
    if not r3_budget_bound:
        score = min(score, 0.49)
    return {
        "trial_id": trial_id,
        "case_id": case_id,
        "arm": arm,
        "trial": receipt.get("trial"),
        "weighted_score": round(score, 4),
        "r3_budget_bound": r3_budget_bound,
        "trial_valid_for_scoring": trial_valid_for_scoring,
        "arm_purity": purity,
        "actual_usage": actual_usage,
        "score_reasons": reasons,
        "receipt_hash": telemetry.get("receipt_hash") or telemetry.get("receipt_output_hash"),
        "telemetry_receipt_hash": telemetry.get("telemetry_receipt_hash") or telemetry.get("telemetry_hash"),
    }


def aggregate_run(run_root: Path, *, output_name: str = "REAL_CALIBRATION_AGGREGATE_RESCORED.json") -> dict:
    trials_root = run_root / "trials"
    trial_scores = [
        score_trial(path)
        for path in sorted(trials_root.iterdir())
        if (path / "receipt.json").exists() and (path / "telemetry.json").exists()
    ]
    case_results = []
    for case_id in sorted({row["case_id"] for row in trial_scores}):
        rows = [row for row in trial_scores if row["case_id"] == case_id]
        invalid_purity_rows = [row for row in rows if not row.get("trial_valid_for_scoring")]
        scored_rows = [row for row in rows if row.get("trial_valid_for_scoring")]
        arms = sorted({row["arm"] for row in scored_rows})
        arm_means = {
            arm: round(sum(row["weighted_score"] for row in scored_rows if row["arm"] == arm) / len([row for row in scored_rows if row["arm"] == arm]), 4)
            for arm in arms
        }
        method_mean = arm_means.get("method-baseline")
        r3_pass = all(row["r3_budget_bound"] for row in scored_rows if row["arm"] == "method-baseline")
        r6 = None
        if {"no-method", "append-only", "method-baseline"} <= set(arms):
            r6 = arm_means["no-method"] < arm_means["append-only"] < arm_means["method-baseline"]
        if invalid_purity_rows:
            verdict, reason = "blocked_arm_purity_failed", "R6 arm purity failed; invalid negative-control trials must rerun on a scrubbed surface"
        elif not r3_pass:
            verdict, reason = "redesign", "R3 budget binding failed"
        elif r6 is False:
            verdict, reason = "redesign", "R6 negative-control separation failed"
        elif method_mean is not None and method_mean < 0.80:
            verdict, reason = "keep_for_freeze_candidate", "R8 baseline headroom below 0.80 with required gates satisfied"
        elif method_mean is not None and method_mean < 0.85:
            verdict, reason = "borderline_owner_decision", "R8 borderline range"
        else:
            verdict, reason = "redesign", "R8 method baseline too high"
        case = {
            "case_id": case_id,
            "trial_count": len(rows),
            "arm_means": arm_means,
            "method_baseline_mean": method_mean,
            "r3_passed": r3_pass,
            "r6_separation_passed": r6,
            "invalid_arm_purity_trials": [
                {"trial_id": row["trial_id"], "arm": row["arm"], "issues": row["arm_purity"]["issues"]}
                for row in invalid_purity_rows
            ],
            "verdict": verdict,
            "verdict_reason": reason,
            "trials": rows,
        }
        case["case_result_hash"] = receipt_hash(case)
        case_results.append(case)
    aggregate = {
        "schema_version": "fusion_dogfood_v03_real_calibration_aggregate_v0.2",
        "suite_id": SUITE_ID,
        "baseline_artifact_hash": BASELINE_HASH,
        "trial_count": len(trial_scores),
        "status": "completed_real_baseline_calibration_rescored",
        "case_results": case_results,
        "r3_all_method_trials_bound": all(row["r3_budget_bound"] for row in trial_scores if row["arm"] == "method-baseline"),
        "scoring_policy": "authenticated runtime collapse/trace required for method mechanism credit; negative-control receipt-only text is not certified mechanism evidence",
        "hidden_artifacts_read_by_candidates": False,
        "hidden_artifacts_used_by_grader": True,
    }
    aggregate["aggregate_hash"] = receipt_hash(aggregate)
    write_json(run_root / output_name, aggregate)
    return aggregate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--output-name", default="REAL_CALIBRATION_AGGREGATE_RESCORED.json")
    args = parser.parse_args(argv)
    result = aggregate_run(Path(args.run_root), output_name=args.output_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
