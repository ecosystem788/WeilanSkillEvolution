"""Acceptance tests for the external SE-0.5 evolution authority."""

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from evolution_core import (
    EVAL_SCHEMA_VERSION,
    METHOD_IMPACT_SCHEMA_VERSION,
    PROPOSAL_SCHEMA_VERSION,
    TRIAL_SCHEMA_VERSION,
    compare_trials,
    freeze_candidate,
    validate_eval_manifest,
    validate_proposal,
)


def main():
    with tempfile.TemporaryDirectory(prefix="weilan-evolution-plane-") as temporary:
        root = Path(temporary)
        source = root / "candidate"
        source.mkdir()
        (source / "SKILL.md").write_text("---\nname: fixture\ndescription: fixture\n---\n", encoding="utf-8")
        artifacts = root / "artifacts"
        first = freeze_candidate(source, artifacts)
        second = freeze_candidate(source, artifacts)
        if not first["created"] or second["created"] or first["artifact_hash"] != second["artifact_hash"]:
            raise AssertionError("content-addressed candidate freeze is not idempotent")
        frozen_file = Path(first["path"]) / "SKILL.md"
        frozen_file.write_text("tampered", encoding="utf-8")
        try:
            freeze_candidate(source, artifacts)
        except ValueError as exc:
            if "does not match" not in str(exc):
                raise
        else:
            raise AssertionError("tampered immutable artifact was accepted")

        valid_proposal = {
            "schema_version": PROPOSAL_SCHEMA_VERSION,
            "proposal_id": "fixture",
            "rationale": "test bounded proposal",
            "base_artifact_hash": "base",
            "candidate_artifact_hash": "candidate",
            "changed_paths": ["proposals/fixture/candidate/solve-with-weilan/SKILL.md"],
            "budgets": {"max_changed_files": 2},
            "target_metrics": ["verification_quality"],
            "rollback_triggers": ["guardrail regression"],
        }
        if not validate_proposal(valid_proposal)["valid"]:
            raise AssertionError("bounded proposal was rejected")
        invalid_proposal = dict(valid_proposal)
        invalid_proposal["changed_paths"] = ["ROADMAP.md"]
        if validate_proposal(invalid_proposal)["valid"]:
            raise AssertionError("candidate was allowed to edit roadmap authority")

        case = {
            "case_id": "external-fixture",
            "trial_count": 1,
            "budget": {"tool_calls": 5, "context_tokens": 1000},
            "metrics": {"outcome": 0.7, "verification": 0.3},
        }
        manifest = {
            "schema_version": EVAL_SCHEMA_VERSION,
            "suite_id": "approved-fixture",
            "status": "approved",
            "frozen": True,
            "approval_source": "external:test",
            "cases": [case],
        }
        if not validate_eval_manifest(manifest)["valid"]:
            raise AssertionError("approved fixed manifest was rejected")
        impact = {
            "schema_version": METHOD_IMPACT_SCHEMA_VERSION,
            "gate": "collapse_review",
            "changed_action": True,
            "observable_effect": "stopped repeating a falsified route",
            "source": "frame:fixture",
            "cost": {"tool_calls": 1, "elapsed_ms": 20, "context_tokens": 40},
        }
        common = {
            "schema_version": TRIAL_SCHEMA_VERSION,
            "case_id": "external-fixture",
            "trial": 1,
            "configuration_hash": "same-model-tools",
            "budget": case["budget"],
            "guardrail_failures": [],
        }
        receipts = [
            {**common, "variant": "baseline", "artifact_hash": "base", "metrics": {"outcome": 0.6, "verification": 0.7}, "method_impacts": []},
            {**common, "variant": "candidate", "artifact_hash": "candidate", "metrics": {"outcome": 0.8, "verification": 0.9}, "method_impacts": [impact]},
        ]
        comparison = compare_trials(manifest, receipts)
        if not comparison["adoption_eligible"] or comparison["mean_delta"] <= 0:
            raise AssertionError("equivalent improved candidate pair was not evaluable")
        mismatched = [dict(receipts[0]), dict(receipts[1])]
        mismatched[1]["configuration_hash"] = "different"
        try:
            compare_trials(manifest, mismatched)
        except ValueError as exc:
            if "configuration mismatch" not in str(exc):
                raise
        else:
            raise AssertionError("unequal baseline/candidate configuration was accepted")

        deployed = ROOT / "DONT_CREATE_DEPLOYMENT"
        if deployed.exists():
            raise AssertionError("evaluation unexpectedly changed deployment state")

        print(json.dumps({
            "valid": True,
            "bounded_proposal": True,
            "external_authority_protected": True,
            "content_addressed_candidate": True,
            "tamper_detected": True,
            "equivalent_trial_pairing": True,
            "method_impact_validated": True,
            "evaluation_does_not_deploy": True,
        }, indent=2))


if __name__ == "__main__":
    main()
