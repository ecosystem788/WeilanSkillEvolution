"""Finite foreground SE-0.7 evolution manifest runner."""

import json
import os
import uuid
from pathlib import Path

from evolution_core import (
    canonical_json,
    freeze_candidate,
    sha256_text,
    validate_proposal,
)
from release_core import (
    compare_shadow,
    deploy_candidate,
    evaluate_canary,
    rollback_deployment,
    validate_decision,
)


EVOLUTION_MANIFEST_SCHEMA_VERSION = "weilan_skill_evolution_manifest_v0.7"
EVOLUTION_RUN_SCHEMA_VERSION = "weilan_skill_evolution_run_v0.7"
ALLOWED_STEPS = {
    "proposal_validate",
    "candidate_freeze",
    "shadow_compare",
    "decision_validate",
    "deploy",
    "canary",
    "rollback",
    "complete",
}


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_name(f".{path.name}.stage-{uuid.uuid4().hex}")
    stage.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(stage, path)


def validate_evolution_manifest(manifest):
    issues = []
    if manifest.get("schema_version") != EVOLUTION_MANIFEST_SCHEMA_VERSION:
        issues.append("unsupported evolution-manifest schema")
    if not manifest.get("run_id"):
        issues.append("evolution manifest lacks run_id")
    max_steps = manifest.get("max_steps")
    steps = manifest.get("steps")
    if not isinstance(max_steps, int) or max_steps < 1:
        issues.append("max_steps must be a positive integer")
    if not isinstance(steps, list) or not steps:
        issues.append("evolution manifest requires finite non-empty steps")
        steps = []
    elif isinstance(max_steps, int) and len(steps) > max_steps:
        issues.append("evolution step budget exceeded")
    ids = [step.get("step_id") for step in steps if isinstance(step, dict)]
    if len(ids) != len(steps) or len(ids) != len(set(ids)) or any(not item for item in ids):
        issues.append("evolution step ids must be present and unique")
    for step in steps:
        if step.get("kind") not in ALLOWED_STEPS:
            issues.append(f"unsupported evolution step: {step.get('kind')}")
        if not isinstance(step.get("inputs", {}), dict):
            issues.append(f"step inputs must be an object: {step.get('step_id')}")
    budgets = manifest.get("budgets")
    if not isinstance(budgets, dict):
        issues.append("evolution manifest lacks budgets")
        budgets = {}
    counters = {
        "max_proposals": sum(step.get("kind") == "proposal_validate" for step in steps),
        "max_candidate_generations": sum(step.get("kind") == "candidate_freeze" for step in steps),
        "max_shadow_comparisons": sum(step.get("kind") == "shadow_compare" for step in steps),
        "max_deployments": sum(step.get("kind") == "deploy" for step in steps),
    }
    for budget, count in counters.items():
        limit = budgets.get(budget)
        if not isinstance(limit, int) or limit < 0:
            issues.append(f"missing non-negative budget: {budget}")
        elif count > limit:
            issues.append(f"evolution budget exceeded: {budget}")
    max_receipts = budgets.get("max_evaluation_receipts")
    if not isinstance(max_receipts, int) or max_receipts < 0:
        issues.append("missing non-negative budget: max_evaluation_receipts")
    authority_roots = manifest.get("authority_roots")
    if not isinstance(authority_roots, list) or not authority_roots:
        issues.append("evolution manifest requires external authority_roots")
    return {"valid": not issues, "issues": issues, "step_count": len(steps)}


def _resolve(root, value):
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def _inside(path, roots):
    path = Path(path).resolve()
    for root in roots:
        try:
            path.relative_to(Path(root).resolve())
            return True
        except ValueError:
            continue
    return False


def _workspace_path(root, value):
    path = _resolve(root, value)
    if not _inside(path, [root]):
        raise ValueError("evolution manifest path escapes its workspace root")
    return path


def _step_result(results, step, key):
    reference = step.get("inputs", {}).get(key)
    if not reference or reference not in results:
        raise ValueError(f"missing prior step result: {key}")
    return results[reference]


def run_evolution_manifest(manifest, root, receipt_path, allow_deployment=False):
    validation = validate_evolution_manifest(manifest)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["issues"]))
    root = Path(root).resolve()
    receipt_path = Path(receipt_path).resolve()
    if not _inside(receipt_path, [root]):
        raise ValueError("evolution receipt path escapes its workspace root")
    manifest_hash = sha256_text(canonical_json(manifest))
    if receipt_path.exists():
        receipt = _load_json(receipt_path)
        if receipt.get("manifest_hash") != manifest_hash:
            raise ValueError("existing evolution receipt belongs to another manifest")
        return receipt
    authority_roots = [_workspace_path(root, item) for item in manifest["authority_roots"]]
    results = {}
    completed = []
    stop_reason = "COMPLETED"
    evaluation_receipts = 0
    pending_rollback = False

    for index, step in enumerate(manifest["steps"]):
        step_id = step["step_id"]
        kind = step["kind"]
        inputs = step.get("inputs", {})
        try:
            if pending_rollback and kind != "rollback":
                stop_reason = "ROLLBACK_REQUIRED"
                break
            if kind == "proposal_validate":
                proposal_path = _workspace_path(root, inputs["proposal"])
                proposal = _load_json(proposal_path)
                result = validate_proposal(proposal)
                if not result["valid"]:
                    stop_reason = "INVALID_PROPOSAL"
                    results[step_id] = result
                    break
            elif kind == "candidate_freeze":
                result = freeze_candidate(
                    _workspace_path(root, inputs["source"]),
                    _workspace_path(root, inputs["artifact_root"]),
                )
            elif kind == "shadow_compare":
                plan = _load_json(_workspace_path(root, inputs["plan"]))
                eval_manifest = _load_json(_workspace_path(root, inputs["evaluation_manifest"]))
                receipts = _load_jsonl(_workspace_path(root, inputs["receipts"]))
                evaluation_receipts += len(receipts)
                if evaluation_receipts > manifest["budgets"]["max_evaluation_receipts"]:
                    stop_reason = "EVALUATION_BUDGET_EXHAUSTED"
                    break
                result = compare_shadow(plan, eval_manifest, receipts)
                output = inputs.get("output")
                if output:
                    _write_json(_workspace_path(root, output), result)
                if not result["adoption_eligible"]:
                    stop_reason = "REGRESSION_OR_GATE_FAILURE"
                    results[step_id] = result
                    break
            elif kind == "decision_validate":
                decision_path = _workspace_path(root, inputs["decision"])
                if not _inside(decision_path, authority_roots):
                    stop_reason = "MISSING_OR_INVALID_AUTHORITY"
                    break
                decision = _load_json(decision_path)
                shadow = _step_result(results, step, "shadow_result_step")
                result = validate_decision(decision, shadow)
                if not result["valid"]:
                    stop_reason = "MISSING_OR_INVALID_AUTHORITY"
                    results[step_id] = result
                    break
                result = {**result, "decision": decision}
                if decision["decision"] == "reject":
                    stop_reason = "REJECTED"
                    results[step_id] = result
                    completed.append(step_id)
                    break
            elif kind == "deploy":
                if not allow_deployment:
                    stop_reason = "DEPLOYMENT_AUTHORITY_REQUIRED"
                    break
                decision_result = _step_result(results, step, "decision_step")
                shadow = _step_result(results, step, "shadow_result_step")
                result = deploy_candidate(
                    _workspace_path(root, inputs["candidate"]),
                    _resolve(root, inputs["target"]),
                    decision_result["decision"],
                    shadow,
                    _workspace_path(root, inputs["receipt_root"]),
                )
            elif kind == "canary":
                deployment = _step_result(results, step, "deployment_step")
                observations = _load_json(_workspace_path(root, inputs["observations"]))
                result = evaluate_canary(deployment, observations)
                if not result["valid"]:
                    stop_reason = "INVALID_CANARY_EVIDENCE"
                    results[step_id] = result
                    break
                pending_rollback = result["rollback_required"]
            elif kind == "rollback":
                if not pending_rollback:
                    result = {"skipped": True, "reason": "no predeclared canary trigger fired"}
                    results[step_id] = result
                    completed.append(step_id)
                    continue
                deployment = _step_result(results, step, "deployment_step")
                authority_source = inputs.get("authority_source")
                authority_file = _workspace_path(root, inputs["authority_file"])
                if not authority_source or not _inside(authority_file, authority_roots) or not authority_file.exists():
                    stop_reason = "ROLLBACK_AUTHORITY_REQUIRED"
                    break
                deployment_path = (
                    _workspace_path(root, inputs["receipt_root"])
                    / deployment["deployment_id"]
                    / "DEPLOYMENT_RECEIPT.json"
                )
                result = rollback_deployment(deployment_path, authority_source)
                pending_rollback = False
            elif kind == "complete":
                if index != len(manifest["steps"]) - 1:
                    raise ValueError("complete must be the final manifest step")
                result = {"complete": True}
            else:
                raise ValueError(f"unsupported evolution step: {kind}")
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            result = {"error": str(exc)}
            results[step_id] = result
            stop_reason = "INVALID_OR_CONFLICTING_EVENT"
            break
        results[step_id] = result
        completed.append(step_id)

    if pending_rollback and stop_reason == "COMPLETED":
        stop_reason = "ROLLBACK_REQUIRED"
    body = {
        "schema_version": EVOLUTION_RUN_SCHEMA_VERSION,
        "run_id": manifest["run_id"],
        "manifest_hash": manifest_hash,
        "step_budget": manifest["max_steps"],
        "completed_steps": completed,
        "step_count": len(completed),
        "evaluation_receipt_count": evaluation_receipts,
        "stop_reason": stop_reason,
        "results": results,
        "authority": "finite_foreground_run_never_creates_evaluation_or_deployment_authority",
    }
    receipt = {**body, "receipt_hash": sha256_text(canonical_json(body))}
    _write_json(receipt_path, receipt)
    return receipt
