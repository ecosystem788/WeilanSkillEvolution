"""External SE-0.6 shadow comparison, deployment, canary, and rollback authority."""

import json
import os
import shutil
import uuid
from pathlib import Path

from evolution_core import canonical_json, compare_trials, sha256_text, tree_hash


SHADOW_SCHEMA_VERSION = "weilan_skill_shadow_plan_v0.6"
DECISION_SCHEMA_VERSION = "weilan_skill_adoption_decision_v0.6"
DEPLOYMENT_SCHEMA_VERSION = "weilan_skill_deployment_receipt_v0.6"
ROLLBACK_SCHEMA_VERSION = "weilan_skill_rollback_receipt_v0.6"
CANARY_SCHEMA_VERSION = "weilan_skill_canary_result_v0.6"


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_name(f".{path.name}.stage-{uuid.uuid4().hex}")
    stage.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(stage, path)


def _manifest_hash(manifest):
    return sha256_text(canonical_json(manifest))


def validate_shadow_plan(plan, eval_manifest):
    issues = []
    if plan.get("schema_version") != SHADOW_SCHEMA_VERSION:
        issues.append("unsupported shadow-plan schema")
    for field in (
        "shadow_id",
        "baseline_artifact_hash",
        "candidate_artifact_hash",
        "configuration_hash",
        "evaluation_manifest_hash",
        "case_spec_hash",
    ):
        if not plan.get(field):
            issues.append(f"missing shadow-plan {field}")
    if plan.get("baseline_artifact_hash") == plan.get("candidate_artifact_hash"):
        issues.append("shadow plan requires distinct baseline and candidate artifacts")
    if plan.get("evaluation_manifest_hash") != _manifest_hash(eval_manifest):
        issues.append("shadow plan evaluation manifest hash mismatch")
    if plan.get("case_spec_hash") != eval_manifest.get("case_spec_hash"):
        issues.append("shadow plan case-set hash mismatch")
    expected_receipts = 2 * sum(case.get("trial_count", 0) for case in eval_manifest.get("cases", []))
    max_receipts = plan.get("max_receipts")
    if not isinstance(max_receipts, int) or max_receipts < expected_receipts:
        issues.append("shadow plan receipt budget cannot cover the frozen evaluation suite")
    gate = plan.get("gate")
    if not isinstance(gate, dict):
        issues.append("shadow plan lacks an external adoption gate")
        gate = {}
    if not isinstance(gate.get("min_mean_delta"), (int, float)):
        issues.append("shadow gate lacks min_mean_delta")
    required_case_deltas = gate.get("required_case_deltas", {})
    if not isinstance(required_case_deltas, dict):
        issues.append("required_case_deltas must be an object")
    elif any(case_id not in {case.get("case_id") for case in eval_manifest.get("cases", [])} for case_id in required_case_deltas):
        issues.append("shadow gate references an unknown case")
    return {
        "valid": not issues,
        "issues": issues,
        "expected_receipt_count": expected_receipts,
    }


def compare_shadow(plan, eval_manifest, receipts):
    validation = validate_shadow_plan(plan, eval_manifest)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["issues"]))
    if len(receipts) > plan["max_receipts"]:
        raise ValueError("shadow receipt budget exceeded")
    for receipt in receipts:
        variant = receipt.get("variant")
        expected_artifact = (
            plan["baseline_artifact_hash"]
            if variant == "baseline"
            else plan["candidate_artifact_hash"]
            if variant == "candidate"
            else None
        )
        if receipt.get("artifact_hash") != expected_artifact:
            raise ValueError("shadow receipt artifact hash mismatch")
        if receipt.get("configuration_hash") != plan["configuration_hash"]:
            raise ValueError("shadow receipt configuration mismatch")
        if receipt.get("evaluation_manifest_hash") != plan["evaluation_manifest_hash"]:
            raise ValueError("shadow receipt evaluation manifest hash mismatch")
        if receipt.get("case_spec_hash") != plan["case_spec_hash"]:
            raise ValueError("shadow receipt case-set hash mismatch")
    comparison = compare_trials(eval_manifest, receipts)
    by_case = {}
    for item in comparison["comparisons"]:
        by_case.setdefault(item["case_id"], []).append(item["delta"])
    case_deltas = {
        case_id: sum(values) / len(values)
        for case_id, values in sorted(by_case.items())
    }
    gate = plan["gate"]
    gate_failures = []
    if comparison["mean_delta"] < float(gate["min_mean_delta"]):
        gate_failures.append("mean delta below external gate")
    for case_id, minimum in gate.get("required_case_deltas", {}).items():
        if case_deltas.get(case_id, float("-inf")) < float(minimum):
            gate_failures.append(f"required case delta missed: {case_id}")
    if comparison["guardrail_failures"]:
        gate_failures.append("candidate guardrail failure")
    body = {
        "schema_version": "weilan_skill_shadow_result_v0.6",
        "shadow_id": plan["shadow_id"],
        "baseline_artifact_hash": plan["baseline_artifact_hash"],
        "candidate_artifact_hash": plan["candidate_artifact_hash"],
        "evaluation_manifest_hash": plan["evaluation_manifest_hash"],
        "case_spec_hash": plan["case_spec_hash"],
        "configuration_hash": plan["configuration_hash"],
        "comparison_count": comparison["comparison_count"],
        "mean_delta": comparison["mean_delta"],
        "case_deltas": case_deltas,
        "guardrail_failures": comparison["guardrail_failures"],
        "gate_failures": gate_failures,
        "adoption_eligible": comparison["adoption_eligible"] and not gate_failures,
        "comparisons": comparison["comparisons"],
        "authority": "shadow_evidence_only_never_adopts_or_deploys",
    }
    return {**body, "result_hash": sha256_text(canonical_json(body))}


def validate_decision(decision, shadow_result):
    issues = []
    if decision.get("schema_version") != DECISION_SCHEMA_VERSION:
        issues.append("unsupported adoption-decision schema")
    if decision.get("decision") not in {"adopt", "reject"}:
        issues.append("decision must be adopt or reject")
    if not decision.get("authority_source"):
        issues.append("adoption decision lacks independent authority source")
    if decision.get("shadow_result_hash") != shadow_result.get("result_hash"):
        issues.append("adoption decision shadow-result hash mismatch")
    for field in ("baseline_artifact_hash", "candidate_artifact_hash"):
        if decision.get(field) != shadow_result.get(field):
            issues.append(f"adoption decision {field} mismatch")
    if decision.get("decision") == "adopt" and not shadow_result.get("adoption_eligible"):
        issues.append("ineligible shadow result cannot be adopted")
    if decision.get("decision") == "adopt":
        if not decision.get("deployment_target"):
            issues.append("adoption decision lacks deployment target")
        triggers = decision.get("rollback_triggers")
        if not isinstance(triggers, list) or not triggers or any(not item for item in triggers):
            issues.append("adoption decision requires predeclared rollback triggers")
    return {"valid": not issues, "issues": issues}


def _atomic_install(source, target):
    source = Path(source).resolve()
    target = Path(target).resolve()
    stage = target.parent / f".{target.name}.stage-{uuid.uuid4().hex}"
    old = target.parent / f".{target.name}.old-{uuid.uuid4().hex}"
    shutil.copytree(source, stage)
    moved_old = False
    try:
        if target.exists():
            os.replace(target, old)
            moved_old = True
        os.replace(stage, target)
    except Exception:
        if target.exists() and not moved_old:
            shutil.rmtree(target)
        if moved_old and old.exists() and not target.exists():
            os.replace(old, target)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if old.exists():
            shutil.rmtree(old)


def deploy_candidate(candidate, target, decision, shadow_result, receipt_root):
    validation = validate_decision(decision, shadow_result)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["issues"]))
    if decision["decision"] != "adopt":
        raise ValueError("only an explicit adopt decision can deploy")
    candidate = Path(candidate).resolve()
    target = Path(target).resolve()
    if str(target) != str(Path(decision["deployment_target"]).resolve()):
        raise ValueError("deployment target differs from authorized target")
    candidate_hash = tree_hash(candidate)
    if candidate_hash != decision["candidate_artifact_hash"]:
        raise ValueError("candidate artifact no longer matches adoption decision")
    decision_hash = sha256_text(canonical_json(decision))
    deployment_id = sha256_text(canonical_json({"decision_hash": decision_hash, "target": str(target)}))[:24]
    receipt_root = Path(receipt_root).resolve() / deployment_id
    receipt_path = receipt_root / "DEPLOYMENT_RECEIPT.json"
    intent_path = receipt_root / "DEPLOYMENT_INTENT.json"
    if receipt_path.exists():
        receipt = _read_json(receipt_path)
        if receipt.get("decision_hash") != decision_hash or tree_hash(target) != receipt.get("after_artifact_hash"):
            raise ValueError("existing deployment receipt does not match current state")
        return receipt
    rollback_path = receipt_root / "rollback" / "solve-with-weilan"
    if intent_path.exists():
        receipt = _read_json(intent_path)
        if receipt.get("decision_hash") != decision_hash or receipt.get("after_artifact_hash") != candidate_hash:
            raise ValueError("existing deployment intent conflicts with requested deployment")
        current_hash = tree_hash(target) if target.exists() else None
        if current_hash == candidate_hash:
            if receipt.get("before_artifact_hash") and tree_hash(rollback_path) != receipt["before_artifact_hash"]:
                raise ValueError("deployment recovery rollback snapshot mismatch")
            _write_json(receipt_path, receipt)
            return receipt
        if current_hash != receipt.get("before_artifact_hash"):
            raise ValueError("deployment intent cannot reconcile current target")
    else:
        before_hash = tree_hash(target) if target.exists() else None
        if target.exists():
            rollback_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(target, rollback_path)
            if tree_hash(rollback_path) != before_hash:
                raise ValueError("rollback snapshot hash mismatch")
        receipt = {
            "schema_version": DEPLOYMENT_SCHEMA_VERSION,
            "deployment_id": deployment_id,
            "decision_hash": decision_hash,
            "authority_source": decision["authority_source"],
            "target": str(target),
            "before_artifact_hash": before_hash,
            "after_artifact_hash": candidate_hash,
            "rollback_artifact": str(rollback_path) if before_hash else None,
            "rollback_triggers": decision["rollback_triggers"],
            "reversible": before_hash is not None,
        }
        _write_json(intent_path, receipt)
    _atomic_install(candidate, target)
    if tree_hash(target) != candidate_hash:
        raise ValueError("deployed artifact verification failed")
    _write_json(receipt_path, receipt)
    return receipt


def evaluate_canary(deployment_receipt, observations):
    triggers = set(deployment_receipt.get("rollback_triggers", []))
    issues = []
    fired = []
    for item in observations:
        if not isinstance(item, dict) or not item.get("trigger") or not item.get("source"):
            issues.append("invalid canary observation")
            continue
        if item["trigger"] not in triggers:
            issues.append(f"undeclared canary trigger: {item['trigger']}")
            continue
        if not isinstance(item.get("failed"), bool):
            issues.append("canary failed flag must be boolean")
        elif item["failed"]:
            fired.append({"trigger": item["trigger"], "source": item["source"]})
    body = {
        "schema_version": CANARY_SCHEMA_VERSION,
        "deployment_id": deployment_receipt.get("deployment_id"),
        "valid": not issues,
        "issues": issues,
        "fired_triggers": fired,
        "rollback_required": bool(fired) and not issues,
        "authority": "canary_evidence_never_self_authorizes_rollback",
    }
    return {**body, "result_hash": sha256_text(canonical_json(body))}


def rollback_deployment(deployment_receipt_path, authority_source):
    if not authority_source:
        raise ValueError("rollback requires independent authority source")
    deployment_receipt_path = Path(deployment_receipt_path).resolve()
    deployment = _read_json(deployment_receipt_path)
    if deployment.get("schema_version") != DEPLOYMENT_SCHEMA_VERSION:
        raise ValueError("unsupported deployment receipt")
    if not deployment.get("reversible") or not deployment.get("rollback_artifact"):
        raise ValueError("deployment has no rollback artifact")
    target = Path(deployment["target"]).resolve()
    rollback_artifact = Path(deployment["rollback_artifact"]).resolve()
    if tree_hash(rollback_artifact) != deployment.get("before_artifact_hash"):
        raise ValueError("rollback artifact integrity failure")
    rollback_id = sha256_text(canonical_json({
        "deployment_id": deployment["deployment_id"],
        "authority_source": authority_source,
    }))[:24]
    receipt_path = deployment_receipt_path.parent / f"ROLLBACK_RECEIPT-{rollback_id}.json"
    intent_path = deployment_receipt_path.parent / f"ROLLBACK_INTENT-{rollback_id}.json"
    if receipt_path.exists():
        receipt = _read_json(receipt_path)
        if tree_hash(target) != receipt.get("restored_artifact_hash"):
            raise ValueError("existing rollback receipt does not match current state")
        return receipt
    current_hash = tree_hash(target)
    if intent_path.exists():
        receipt = _read_json(intent_path)
        if receipt.get("deployment_id") != deployment["deployment_id"] or receipt.get("authority_source") != authority_source:
            raise ValueError("existing rollback intent conflicts with requested rollback")
        if current_hash == receipt.get("restored_artifact_hash"):
            _write_json(receipt_path, receipt)
            return receipt
        if current_hash != receipt.get("replaced_artifact_hash"):
            raise ValueError("rollback intent cannot reconcile current target")
    else:
        if current_hash != deployment.get("after_artifact_hash"):
            raise ValueError("deployed target changed before rollback")
        receipt = {
            "schema_version": ROLLBACK_SCHEMA_VERSION,
            "rollback_id": rollback_id,
            "deployment_id": deployment["deployment_id"],
            "authority_source": authority_source,
            "target": str(target),
            "replaced_artifact_hash": current_hash,
            "restored_artifact_hash": deployment["before_artifact_hash"],
        }
        _write_json(intent_path, receipt)
    _atomic_install(rollback_artifact, target)
    restored_hash = tree_hash(target)
    if restored_hash != deployment.get("before_artifact_hash"):
        raise ValueError("rollback failed to restore exact predecessor")
    _write_json(receipt_path, receipt)
    return receipt
