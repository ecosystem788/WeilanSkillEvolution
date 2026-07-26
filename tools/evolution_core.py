"""External proposal, artifact, evaluation, and method-impact authority."""

import hashlib
import json
import math
import os
import shutil
import uuid
from pathlib import Path


PROPOSAL_SCHEMA_VERSION = "weilan_skill_change_proposal_v0.5"
EVAL_SCHEMA_VERSION = "weilan_skill_eval_manifest_v0.5"
TRIAL_SCHEMA_VERSION = "weilan_skill_trial_receipt_v0.5"
METHOD_IMPACT_SCHEMA_VERSION = "weilan_method_impact_v0.5"
AGGREGATION_VERSION = "equal-case-mean-v0.1"

FORBIDDEN_CANDIDATE_PATHS = (
    "ROADMAP.md",
    "ARCHITECTURE.md",
    "EVALUATION_POLICY.md",
    "CAPABILITY_MAP.md",
    "AGENTS.md",
    "baseline/",
    "packages/",
    "evals/",
    "deployments/",
    "tools/",
)


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_sha256(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_manifest(root):
    root = Path(root).resolve()
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or ".pytest_cache" in path.parts or path.suffix == ".pyc":
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    return rows


def tree_hash(root):
    return sha256_text(canonical_json(tree_manifest(root)))


def changed_files(base, candidate):
    base_rows = {item["path"]: item for item in tree_manifest(base)}
    candidate_rows = {item["path"]: item for item in tree_manifest(candidate)}
    return sorted(
        path
        for path in set(base_rows) | set(candidate_rows)
        if base_rows.get(path) != candidate_rows.get(path)
    )


def path_is_forbidden(path):
    normalized = path.replace("\\", "/").lstrip("./")
    return any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in FORBIDDEN_CANDIDATE_PATHS
    )


def validate_proposal(proposal):
    issues = []
    if proposal.get("schema_version") != PROPOSAL_SCHEMA_VERSION:
        issues.append("unsupported proposal schema")
    for field in ("proposal_id", "rationale", "base_artifact_hash", "candidate_artifact_hash"):
        if not proposal.get(field):
            issues.append(f"missing {field}")
    changed = proposal.get("changed_paths")
    budgets = proposal.get("budgets")
    if not isinstance(changed, list) or not changed:
        issues.append("changed_paths must be a non-empty list")
        changed = []
    forbidden = sorted(path for path in changed if path_is_forbidden(path))
    if forbidden:
        issues.append("candidate touches external authority: " + ", ".join(forbidden))
    if not isinstance(budgets, dict):
        issues.append("missing proposal budgets")
        budgets = {}
    max_files = budgets.get("max_changed_files")
    if not isinstance(max_files, int) or max_files < 1:
        issues.append("max_changed_files must be a positive integer")
    elif len(changed) > max_files:
        issues.append("changed file budget exceeded")
    if not proposal.get("target_metrics"):
        issues.append("proposal requires target_metrics")
    if not proposal.get("rollback_triggers"):
        issues.append("proposal requires rollback_triggers")
    return {"valid": not issues, "issues": issues, "changed_path_count": len(changed)}


def freeze_candidate(source, artifact_root):
    source = Path(source).resolve()
    artifact_root = Path(artifact_root).resolve()
    digest = tree_hash(source)
    target = artifact_root / digest / "solve-with-weilan"
    if target.exists():
        if tree_hash(target) != digest:
            raise ValueError("existing content-addressed artifact does not match its address")
        return {"created": False, "artifact_hash": digest, "path": str(target)}
    stage = artifact_root / f".stage-{uuid.uuid4().hex}"
    stage.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(source, stage)
        if tree_hash(stage) != digest:
            raise ValueError("staged candidate hash mismatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage, target)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {"created": True, "artifact_hash": digest, "path": str(target)}


def validate_method_impact(record):
    issues = []
    if record.get("schema_version") != METHOD_IMPACT_SCHEMA_VERSION:
        issues.append("unsupported method-impact schema")
    for field in ("gate", "observable_effect", "source"):
        if not record.get(field):
            issues.append(f"missing method-impact {field}")
    if not isinstance(record.get("changed_action"), bool):
        issues.append("changed_action must be boolean")
    cost = record.get("cost")
    if not isinstance(cost, dict):
        issues.append("method-impact cost is required")
    else:
        for field in ("tool_calls", "elapsed_ms", "context_tokens"):
            value = cost.get(field)
            if not isinstance(value, int) or value < 0:
                issues.append(f"cost.{field} must be a non-negative integer")
    return issues


def validate_case_set(case_set):
    issues = []
    if case_set.get("schema_version") != "weilan_skill_eval_case_set_v0.1":
        issues.append("unsupported evaluation case-set schema")
    if case_set.get("status") != "approved_frozen" or not case_set.get("frozen"):
        issues.append("evaluation case set is not explicitly approved and frozen")
    if not case_set.get("approval_source"):
        issues.append("evaluation case set lacks external approval source")
    cases = case_set.get("cases")
    if not isinstance(cases, list) or not cases:
        issues.append("evaluation case set has no cases")
        cases = []
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != len(cases) or len(case_ids) != len(set(case_ids)) or any(not item for item in case_ids):
        issues.append("case-set ids must be present and unique")
    for case in cases:
        if not case.get("task") or not case.get("success") or not case.get("guardrails"):
            issues.append(f"case lacks task, success, or guardrails: {case.get('case_id')}")
    return {"valid": not issues, "issues": issues, "case_count": len(cases)}


def validate_eval_manifest(manifest, require_approved=True, case_set=None):
    issues = []
    if manifest.get("schema_version") != EVAL_SCHEMA_VERSION:
        issues.append("unsupported evaluation manifest schema")
    if require_approved and (
        manifest.get("status") != "approved" or not manifest.get("frozen")
    ):
        issues.append("evaluation manifest is not explicitly approved and frozen")
    if require_approved and not manifest.get("approval_source"):
        issues.append("evaluation manifest lacks external approval source")
    if not manifest.get("scoring_version"):
        issues.append("evaluation manifest lacks scoring version")
    if not manifest.get("case_spec"):
        issues.append("evaluation manifest lacks case_spec")
    case_spec_hash = manifest.get("case_spec_hash")
    if not isinstance(case_spec_hash, str) or len(case_spec_hash) != 64:
        issues.append("evaluation manifest lacks a valid case_spec_hash")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        issues.append("evaluation manifest has no cases")
        cases = []
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(case_ids) != len(cases) or len(case_ids) != len(set(case_ids)) or any(not item for item in case_ids):
        issues.append("case ids must be present and unique")
    for case in cases:
        if not isinstance(case.get("trial_count"), int) or case["trial_count"] < 1:
            issues.append(f"invalid trial_count for {case.get('case_id')}")
        if not case.get("budget") or not case.get("metrics"):
            issues.append(f"case lacks budget or metrics: {case.get('case_id')}")
        elif abs(sum(float(weight) for weight in case["metrics"].values()) - 1.0) > 1e-9:
            issues.append(f"metric weights must sum to one: {case.get('case_id')}")
        budget = case.get("budget", {})
        if not isinstance(budget, dict) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in budget.values()
        ):
            issues.append(f"case budget values must be non-negative integers: {case.get('case_id')}")
    if case_set is not None:
        case_validation = validate_case_set(case_set)
        issues.extend(case_validation["issues"])
        if case_set.get("suite_id") != manifest.get("suite_id"):
            issues.append("manifest and case-set suite ids differ")
        case_set_ids = [case.get("case_id") for case in case_set.get("cases", [])]
        if case_set_ids != case_ids:
            issues.append("manifest and case-set case order differs")
        if sha256_text(canonical_json(case_set)) != case_spec_hash:
            issues.append("evaluation case set does not match frozen hash")
    return {"valid": not issues, "issues": issues, "case_count": len(cases)}


def _validate_trial_receipt(receipt, case, manifest_hash, case_spec_hash):
    identity = f"{receipt.get('case_id')}/{receipt.get('variant')}/{receipt.get('trial')}"
    issues = []
    if receipt.get("evaluation_manifest_hash") != manifest_hash:
        issues.append(f"{identity}: evaluation manifest hash mismatch")
    if receipt.get("case_spec_hash") != case_spec_hash:
        issues.append(f"{identity}: case-set hash mismatch")
    for field in ("fixture_manifest_hash", "configuration_hash", "raw_output_hash"):
        if not is_sha256(receipt.get(field)):
            issues.append(f"{identity}: {field} must be a lowercase SHA-256 hash")
    if not receipt.get("environment_id"):
        issues.append(f"{identity}: environment_id is required")
    if receipt.get("scoring_version") is None:
        issues.append(f"{identity}: scoring_version is required")
    if receipt.get("termination_status") not in {
        "completed",
        "budget_exhausted",
        "blocked",
        "failed",
    }:
        issues.append(f"{identity}: invalid termination_status")
    if not receipt.get("grader_id"):
        issues.append(f"{identity}: grader_id is required")
    provenance = receipt.get("grader_provenance")
    if not isinstance(provenance, dict):
        issues.append(f"{identity}: grader_provenance is required")
    else:
        if not provenance.get("authority_source"):
            issues.append(f"{identity}: grader provenance authority_source is required")
        for field in ("evaluator_artifact_hash", "evidence_hash"):
            if not is_sha256(provenance.get(field)):
                issues.append(f"{identity}: grader provenance {field} must be a lowercase SHA-256 hash")
    metrics = receipt.get("metrics")
    expected_metrics = set(case["metrics"])
    if not isinstance(metrics, dict) or set(metrics) != expected_metrics:
        issues.append(f"{identity}: metrics must exactly match the declared metric set")
    else:
        for name, value in metrics.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 1
            ):
                issues.append(f"{identity}: metric {name} must be finite and within [0,1]")
    failures = receipt.get("guardrail_failures")
    if not isinstance(failures, list) or any(not isinstance(item, str) or not item for item in failures):
        issues.append(f"{identity}: guardrail_failures must be a list of non-empty strings")
    usage = receipt.get("actual_usage")
    budget = case["budget"]
    if not isinstance(usage, dict) or set(usage) != set(budget):
        issues.append(f"{identity}: actual_usage must exactly match declared budget dimensions")
    else:
        for name, value in usage.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                issues.append(f"{identity}: actual_usage.{name} must be a non-negative integer")
            elif value > budget[name]:
                issues.append(f"{identity}: actual_usage.{name} exceeds declared budget")
    return issues


def compare_trials(manifest, receipts):
    validation = validate_eval_manifest(manifest, require_approved=True)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["issues"]))
    cases = {case["case_id"]: case for case in manifest["cases"]}
    manifest_hash = sha256_text(canonical_json(manifest))
    grouped = {}
    issues = []
    for receipt in receipts:
        if receipt.get("schema_version") != TRIAL_SCHEMA_VERSION:
            issues.append("unsupported trial receipt schema")
            continue
        case_id = receipt.get("case_id")
        variant = receipt.get("variant")
        trial = receipt.get("trial")
        if case_id not in cases or variant not in {"baseline", "candidate"} or not isinstance(trial, int):
            issues.append("invalid trial identity")
            continue
        if trial < 1 or trial > cases[case_id]["trial_count"]:
            issues.append(f"invalid trial identity: {case_id}/{variant}/{trial}")
            continue
        identity = (case_id, variant, trial)
        if identity in grouped:
            issues.append(f"duplicate trial identity: {case_id}/{variant}/{trial}")
            continue
        issues.extend(
            _validate_trial_receipt(
                receipt,
                cases[case_id],
                manifest_hash,
                manifest["case_spec_hash"],
            )
        )
        impact_issues = [
            issue
            for record in receipt.get("method_impacts", [])
            for issue in validate_method_impact(record)
        ]
        if impact_issues:
            issues.extend(f"{case_id}/{variant}/{trial}: {item}" for item in impact_issues)
        grouped[identity] = receipt
    comparisons = []
    for case_id, case in cases.items():
        for trial in range(1, case["trial_count"] + 1):
            baseline = grouped.get((case_id, "baseline", trial))
            candidate = grouped.get((case_id, "candidate", trial))
            if baseline is None or candidate is None:
                issues.append(f"missing equivalent pair: {case_id}/{trial}")
                continue
            if baseline.get("configuration_hash") != candidate.get("configuration_hash"):
                issues.append(f"configuration mismatch: {case_id}/{trial}")
            if baseline.get("fixture_manifest_hash") != candidate.get("fixture_manifest_hash"):
                issues.append(f"fixture mismatch: {case_id}/{trial}")
            if baseline.get("environment_id") != candidate.get("environment_id"):
                issues.append(f"environment mismatch: {case_id}/{trial}")
            if baseline.get("scoring_version") != candidate.get("scoring_version"):
                issues.append(f"scoring mismatch: {case_id}/{trial}")
            if candidate.get("scoring_version") != manifest["scoring_version"]:
                issues.append(f"undeclared scoring version: {case_id}/{trial}")
            if baseline.get("budget") != candidate.get("budget") or candidate.get("budget") != case["budget"]:
                issues.append(f"budget mismatch: {case_id}/{trial}")
            metrics = case["metrics"]
            baseline_score = sum(
                float(baseline.get("metrics", {}).get(name, 0)) * float(weight)
                for name, weight in metrics.items()
            )
            candidate_score = sum(
                float(candidate.get("metrics", {}).get(name, 0)) * float(weight)
                for name, weight in metrics.items()
            )
            comparisons.append(
                {
                    "case_id": case_id,
                    "trial": trial,
                    "baseline_score": baseline_score,
                    "candidate_score": candidate_score,
                    "delta": candidate_score - baseline_score,
                    "baseline_guardrail_failures": baseline.get("guardrail_failures", []),
                    "candidate_guardrail_failures": candidate.get("guardrail_failures", []),
                    "method_impact_count": len(candidate.get("method_impacts", [])),
                }
            )
    if issues:
        raise ValueError("; ".join(issues))
    by_case = {}
    for item in comparisons:
        by_case.setdefault(item["case_id"], []).append(item["delta"])
    case_deltas = {
        case_id: sum(values) / len(values)
        for case_id, values in sorted(by_case.items())
    }
    baseline_guardrail_failures = [
        failure
        for item in comparisons
        for failure in item["baseline_guardrail_failures"]
    ]
    candidate_guardrail_failures = [
        failure
        for item in comparisons
        for failure in item["candidate_guardrail_failures"]
    ]
    mean_delta = sum(case_deltas.values()) / len(case_deltas) if case_deltas else 0.0
    return {
        "manifest_hash": manifest_hash,
        "comparison_count": len(comparisons),
        "aggregation_version": AGGREGATION_VERSION,
        "case_deltas": case_deltas,
        "mean_delta": mean_delta,
        "baseline_guardrail_failures": baseline_guardrail_failures,
        "candidate_guardrail_failures": candidate_guardrail_failures,
        "guardrail_failures": candidate_guardrail_failures,
        "adoption_eligible": bool(comparisons) and not candidate_guardrail_failures and mean_delta >= 0,
        "comparisons": comparisons,
        "authority": "evaluation_evidence_only_never_deploys_or_adopts",
    }
