"""SE-0.7 acceptance tests for one finite foreground evolution manifest."""

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from evolution_core import (
    EVAL_SCHEMA_VERSION,
    PROPOSAL_SCHEMA_VERSION,
    TRIAL_SCHEMA_VERSION,
    canonical_json,
    freeze_candidate,
    sha256_text,
    tree_hash,
)
from evolution_runner import (
    EVOLUTION_MANIFEST_SCHEMA_VERSION,
    run_evolution_manifest,
    validate_evolution_manifest,
)
from release_core import (
    DECISION_SCHEMA_VERSION,
    SHADOW_SCHEMA_VERSION,
    compare_shadow,
)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item) + "\n" for item in values), encoding="utf-8")


def write_skill(path, marker):
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: fixture\ndescription: {marker}\n---\n",
        encoding="utf-8",
    )


def main():
    with tempfile.TemporaryDirectory(prefix="weilan-bounded-evolution-") as temporary:
        root = Path(temporary)
        baseline = root / "baseline"
        candidate = root / "candidate"
        target = root / "deployed"
        write_skill(baseline, "baseline")
        write_skill(candidate, "candidate")
        write_skill(target, "baseline")
        baseline_hash = tree_hash(baseline)
        candidate_hash = tree_hash(candidate)
        frozen = freeze_candidate(candidate, root / "artifacts")
        proposal = {
            "schema_version": PROPOSAL_SCHEMA_VERSION,
            "proposal_id": "fixture-proposal",
            "rationale": "exercise one bounded externally governed evolution run",
            "base_artifact_hash": baseline_hash,
            "candidate_artifact_hash": candidate_hash,
            "changed_paths": ["proposals/fixture/candidate/solve-with-weilan/SKILL.md"],
            "budgets": {"max_changed_files": 1},
            "target_metrics": ["outcome"],
            "rollback_triggers": ["verification regression"],
        }
        write_json(root / "proposal.json", proposal)
        case = {
            "case_id": "fixture-case",
            "trial_count": 1,
            "budget": {"tool_calls": 2, "context_tokens": 500},
            "metrics": {"outcome": 1.0},
        }
        case_set = {
            "schema_version": "weilan_skill_eval_case_set_v0.1",
            "suite_id": "fixture-v0.1",
            "status": "approved_frozen",
            "frozen": True,
            "approval_source": "authority:fixture",
            "cases": [{
                "case_id": "fixture-case",
                "task": "evaluate fixture",
                "success": ["scored"],
                "guardrails": ["authority preserved"],
            }],
        }
        case_set_hash = sha256_text(canonical_json(case_set))
        write_json(root / "case-set.json", case_set)
        eval_manifest = {
            "schema_version": EVAL_SCHEMA_VERSION,
            "suite_id": "fixture-v0.1",
            "status": "approved",
            "frozen": True,
            "approval_source": "authority:fixture",
            "scoring_version": "fixture-v0.1",
            "case_spec": "evals/cases/fixture.json",
            "case_spec_hash": case_set_hash,
            "cases": [case],
        }
        write_json(root / "eval-manifest.json", eval_manifest)
        eval_hash = sha256_text(canonical_json(eval_manifest))
        shadow_plan = {
            "schema_version": SHADOW_SCHEMA_VERSION,
            "shadow_id": "fixture-shadow",
            "baseline_artifact_hash": baseline_hash,
            "candidate_artifact_hash": candidate_hash,
            "configuration_hash": "1" * 64,
            "environment_id": "fixture-environment",
            "fixture_manifest_hashes": {"fixture-case": "2" * 64},
            "aggregation_version": "equal-case-mean-v0.1",
            "evaluation_manifest_hash": eval_hash,
            "case_spec_hash": eval_manifest["case_spec_hash"],
            "max_receipts": 2,
            "gate": {"min_mean_delta": 0.1, "required_case_deltas": {"fixture-case": 0.1}},
        }
        write_json(root / "shadow-plan.json", shadow_plan)
        common = {
            "schema_version": TRIAL_SCHEMA_VERSION,
            "case_id": "fixture-case",
            "trial": 1,
            "configuration_hash": shadow_plan["configuration_hash"],
            "evaluation_manifest_hash": eval_hash,
            "case_spec_hash": eval_manifest["case_spec_hash"],
            "fixture_manifest_hash": shadow_plan["fixture_manifest_hashes"]["fixture-case"],
            "environment_id": shadow_plan["environment_id"],
            "scoring_version": eval_manifest["scoring_version"],
            "budget": case["budget"],
            "actual_usage": {"tool_calls": 1, "context_tokens": 100},
            "termination_status": "completed",
            "raw_output_hash": "3" * 64,
            "grader_id": "external-grader",
            "grader_provenance": {
                "authority_source": "authority:fixture-grader",
                "evaluator_artifact_hash": "4" * 64,
                "evidence_hash": "5" * 64,
            },
            "guardrail_failures": [],
            "method_impacts": [],
        }
        receipts = [
            {**common, "variant": "baseline", "artifact_hash": baseline_hash, "metrics": {"outcome": 0.4}},
            {**common, "variant": "candidate", "artifact_hash": candidate_hash, "metrics": {"outcome": 0.8}},
        ]
        write_jsonl(root / "trial-receipts.jsonl", receipts)
        shadow_result = compare_shadow(shadow_plan, eval_manifest, receipts, case_set=case_set)
        authority = root / "authority"
        decision = {
            "schema_version": DECISION_SCHEMA_VERSION,
            "decision": "adopt",
            "authority_source": "authority:fixture-adopt",
            "shadow_result_hash": shadow_result["result_hash"],
            "baseline_artifact_hash": baseline_hash,
            "candidate_artifact_hash": candidate_hash,
            "deployment_target": str(target.resolve()),
            "rollback_triggers": ["verification regression"],
        }
        write_json(authority / "decision.json", decision)
        write_json(authority / "rollback.json", {"authorized": True})
        write_json(root / "canary.json", [{
            "trigger": "verification regression",
            "failed": True,
            "source": "fixture:canary",
        }])
        manifest = {
            "schema_version": EVOLUTION_MANIFEST_SCHEMA_VERSION,
            "run_id": "fixture-full-cycle",
            "max_steps": 8,
            "budgets": {
                "max_proposals": 1,
                "max_candidate_generations": 1,
                "max_shadow_comparisons": 1,
                "max_evaluation_receipts": 2,
                "max_deployments": 1,
            },
            "authority_roots": ["authority"],
            "steps": [
                {"step_id": "proposal", "kind": "proposal_validate", "inputs": {"proposal": "proposal.json"}},
                {"step_id": "freeze", "kind": "candidate_freeze", "inputs": {"source": "candidate", "artifact_root": "artifacts"}},
                {"step_id": "shadow", "kind": "shadow_compare", "inputs": {"plan": "shadow-plan.json", "evaluation_manifest": "eval-manifest.json", "case_set": "case-set.json", "receipts": "trial-receipts.jsonl", "output": "shadow-result.json"}},
                {"step_id": "decision", "kind": "decision_validate", "inputs": {"decision": "authority/decision.json", "shadow_result_step": "shadow"}},
                {"step_id": "deploy", "kind": "deploy", "inputs": {"candidate": str(Path(frozen["path"]).relative_to(root)), "target": "deployed", "receipt_root": "deployment-receipts", "decision_step": "decision", "shadow_result_step": "shadow"}},
                {"step_id": "canary", "kind": "canary", "inputs": {"deployment_step": "deploy", "observations": "canary.json"}},
                {"step_id": "rollback", "kind": "rollback", "inputs": {"deployment_step": "deploy", "receipt_root": "deployment-receipts", "authority_file": "authority/rollback.json", "authority_source": "authority:fixture-rollback"}},
                {"step_id": "complete", "kind": "complete", "inputs": {}},
            ],
        }
        if not validate_evolution_manifest(manifest)["valid"]:
            raise AssertionError("valid finite evolution manifest was rejected")
        no_deploy_manifest = json.loads(json.dumps(manifest))
        no_deploy_manifest["run_id"] = "fixture-no-deploy-authority"
        blocked = run_evolution_manifest(
            no_deploy_manifest,
            root,
            root / "blocked-run.json",
            allow_deployment=False,
        )
        if blocked["stop_reason"] != "DEPLOYMENT_AUTHORITY_REQUIRED" or tree_hash(target) != baseline_hash:
            raise AssertionError("runner did not stop safely before unauthorized deployment")
        receipt = run_evolution_manifest(
            manifest,
            root,
            root / "full-run.json",
            allow_deployment=True,
        )
        if receipt["stop_reason"] != "COMPLETED" or receipt["step_count"] != 8:
            raise AssertionError("finite authorized evolution manifest did not complete")
        if tree_hash(target) != baseline_hash:
            raise AssertionError("canary rollback did not restore baseline")
        replay = run_evolution_manifest(manifest, root, root / "full-run.json", allow_deployment=True)
        if replay != receipt:
            raise AssertionError("evolution run receipt replay changed")
        over_budget = json.loads(json.dumps(manifest))
        over_budget["budgets"]["max_deployments"] = 0
        if validate_evolution_manifest(over_budget)["valid"]:
            raise AssertionError("over-budget evolution manifest was accepted")
        escaping = json.loads(json.dumps(manifest))
        escaping["run_id"] = "fixture-path-escape"
        escaping["steps"] = [
            {"step_id": "escape", "kind": "proposal_validate", "inputs": {"proposal": "../outside.json"}}
        ]
        escaping["max_steps"] = 1
        escaping["budgets"]["max_candidate_generations"] = 0
        escaping["budgets"]["max_shadow_comparisons"] = 0
        escaping["budgets"]["max_deployments"] = 0
        escaped = run_evolution_manifest(escaping, root, root / "escape-run.json")
        if escaped["stop_reason"] != "INVALID_OR_CONFLICTING_EVENT":
            raise AssertionError("workspace path escape was not rejected")
        print(json.dumps({
            "valid": True,
            "finite_manifest": True,
            "hard_budgets": True,
            "external_authority_roots": True,
            "unauthorized_deployment_stopped": True,
            "canary_rollback_cycle": True,
            "idempotent_run_receipt": True,
            "no_background_loop": True,
            "workspace_path_escape_rejected": True,
        }, indent=2))


if __name__ == "__main__":
    main()
