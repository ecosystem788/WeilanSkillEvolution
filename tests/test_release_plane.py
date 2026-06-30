"""SE-0.6 acceptance tests for shadow comparison, deployment, canary, and rollback."""

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from evolution_core import (
    EVAL_SCHEMA_VERSION,
    METHOD_IMPACT_SCHEMA_VERSION,
    TRIAL_SCHEMA_VERSION,
    canonical_json,
    sha256_text,
    tree_hash,
)
import release_core
from release_core import (
    DECISION_SCHEMA_VERSION,
    SHADOW_SCHEMA_VERSION,
    compare_shadow,
    deploy_candidate,
    evaluate_canary,
    rollback_deployment,
    validate_decision,
    validate_shadow_plan,
)


def write_skill(path, marker):
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: fixture\ndescription: {marker}\n---\n",
        encoding="utf-8",
    )


def main():
    with tempfile.TemporaryDirectory(prefix="weilan-release-plane-") as temporary:
        root = Path(temporary)
        baseline = root / "baseline"
        candidate = root / "candidate"
        target = root / "deployed"
        write_skill(baseline, "baseline")
        write_skill(candidate, "candidate")
        write_skill(target, "baseline")
        baseline_hash = tree_hash(baseline)
        candidate_hash = tree_hash(candidate)
        case_set_hash = "c" * 64
        case = {
            "case_id": "fixture-case",
            "trial_count": 2,
            "budget": {"tool_calls": 5, "context_tokens": 1000},
            "metrics": {"outcome": 0.7, "verification": 0.3},
        }
        manifest = {
            "schema_version": EVAL_SCHEMA_VERSION,
            "suite_id": "fixture-v0.1",
            "status": "approved",
            "frozen": True,
            "approval_source": "external:test",
            "scoring_version": "fixture-v0.1",
            "case_spec": "evals/cases/fixture.json",
            "case_spec_hash": case_set_hash,
            "cases": [case],
        }
        manifest_hash = sha256_text(canonical_json(manifest))
        plan = {
            "schema_version": SHADOW_SCHEMA_VERSION,
            "shadow_id": "fixture-shadow",
            "baseline_artifact_hash": baseline_hash,
            "candidate_artifact_hash": candidate_hash,
            "configuration_hash": "same-model-tools",
            "evaluation_manifest_hash": manifest_hash,
            "case_spec_hash": case_set_hash,
            "max_receipts": 4,
            "gate": {
                "min_mean_delta": 0.05,
                "required_case_deltas": {"fixture-case": 0.05},
            },
        }
        if not validate_shadow_plan(plan, manifest)["valid"]:
            raise AssertionError("valid bounded shadow plan was rejected")
        impact = {
            "schema_version": METHOD_IMPACT_SCHEMA_VERSION,
            "gate": "verification_gate",
            "changed_action": True,
            "observable_effect": "caught the prepared regression",
            "source": "fixture:test",
            "cost": {"tool_calls": 1, "elapsed_ms": 2, "context_tokens": 20},
        }
        receipts = []
        for trial in (1, 2):
            common = {
                "schema_version": TRIAL_SCHEMA_VERSION,
                "case_id": "fixture-case",
                "trial": trial,
                "configuration_hash": plan["configuration_hash"],
                "evaluation_manifest_hash": manifest_hash,
                "case_spec_hash": case_set_hash,
                "budget": case["budget"],
                "guardrail_failures": [],
            }
            receipts.extend([
                {
                    **common,
                    "variant": "baseline",
                    "artifact_hash": baseline_hash,
                    "metrics": {"outcome": 0.5, "verification": 0.6},
                    "method_impacts": [],
                },
                {
                    **common,
                    "variant": "candidate",
                    "artifact_hash": candidate_hash,
                    "metrics": {"outcome": 0.8, "verification": 0.9},
                    "method_impacts": [impact],
                },
            ])
        shadow = compare_shadow(plan, manifest, receipts)
        if not shadow["adoption_eligible"] or shadow["mean_delta"] <= 0:
            raise AssertionError("improved equivalent shadow candidate was not eligible")
        decision = {
            "schema_version": DECISION_SCHEMA_VERSION,
            "decision": "adopt",
            "authority_source": "external:test-authority",
            "shadow_result_hash": shadow["result_hash"],
            "baseline_artifact_hash": baseline_hash,
            "candidate_artifact_hash": candidate_hash,
            "deployment_target": str(target.resolve()),
            "rollback_triggers": ["verification regression", "activation leakage"],
        }
        if not validate_decision(decision, shadow)["valid"]:
            raise AssertionError("eligible externally authorized decision was rejected")
        self_decision = dict(decision)
        self_decision["authority_source"] = ""
        if validate_decision(self_decision, shadow)["valid"]:
            raise AssertionError("candidate was allowed to authorize its own adoption")
        deployment = deploy_candidate(candidate, target, decision, shadow, root / "receipts")
        if tree_hash(target) != candidate_hash or not deployment["reversible"]:
            raise AssertionError("candidate deployment was not verified and reversible")
        replay = deploy_candidate(candidate, target, decision, shadow, root / "receipts")
        if replay != deployment:
            raise AssertionError("deployment idempotency receipt changed")
        canary = evaluate_canary(deployment, [{
            "trigger": "verification regression",
            "failed": True,
            "source": "fixture:canary",
        }])
        if not canary["rollback_required"]:
            raise AssertionError("predeclared canary failure did not require rollback")
        deployment_path = root / "receipts" / deployment["deployment_id"] / "DEPLOYMENT_RECEIPT.json"
        rollback = rollback_deployment(deployment_path, "external:test-rollback")
        if tree_hash(target) != baseline_hash or rollback["restored_artifact_hash"] != baseline_hash:
            raise AssertionError("rollback did not restore exact verified predecessor")
        rollback_replay = rollback_deployment(deployment_path, "external:test-rollback")
        if rollback_replay != rollback:
            raise AssertionError("rollback idempotency receipt changed")

        crash_target = root / "crash-deployed"
        write_skill(crash_target, "baseline")
        crash_decision = dict(decision)
        crash_decision["deployment_target"] = str(crash_target.resolve())
        original_write = release_core._write_json

        def fail_deployment_receipt(path, value):
            if Path(path).name == "DEPLOYMENT_RECEIPT.json":
                raise OSError("simulated receipt-write crash")
            return original_write(path, value)

        release_core._write_json = fail_deployment_receipt
        try:
            try:
                deploy_candidate(candidate, crash_target, crash_decision, shadow, root / "crash-receipts")
            except OSError:
                pass
            else:
                raise AssertionError("simulated deployment receipt crash did not occur")
        finally:
            release_core._write_json = original_write
        recovered_deployment = deploy_candidate(
            candidate,
            crash_target,
            crash_decision,
            shadow,
            root / "crash-receipts",
        )
        if recovered_deployment["before_artifact_hash"] != baseline_hash:
            raise AssertionError("deployment recovery lost the original rollback predecessor")
        recovered_path = (
            root
            / "crash-receipts"
            / recovered_deployment["deployment_id"]
            / "DEPLOYMENT_RECEIPT.json"
        )

        def fail_rollback_receipt(path, value):
            if Path(path).name.startswith("ROLLBACK_RECEIPT-"):
                raise OSError("simulated rollback receipt-write crash")
            return original_write(path, value)

        release_core._write_json = fail_rollback_receipt
        try:
            try:
                rollback_deployment(recovered_path, "external:crash-rollback")
            except OSError:
                pass
            else:
                raise AssertionError("simulated rollback receipt crash did not occur")
        finally:
            release_core._write_json = original_write
        recovered_rollback = rollback_deployment(recovered_path, "external:crash-rollback")
        if recovered_rollback["restored_artifact_hash"] != baseline_hash or tree_hash(crash_target) != baseline_hash:
            raise AssertionError("rollback recovery did not preserve exact predecessor")
        print(json.dumps({
            "valid": True,
            "equivalent_shadow_comparison": True,
            "external_adoption_authority": True,
            "content_addressed_deployment": True,
            "deterministic_receipt_replay": True,
            "predeclared_canary_trigger": True,
            "exact_rollback": True,
            "post_install_receipt_recovery": True,
            "post_rollback_receipt_recovery": True,
        }, indent=2))


if __name__ == "__main__":
    main()
