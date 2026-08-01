"""Does the assembled SHADOW_RESULT.json actually satisfy the Release Plane contract?

Read-only. Writes no adoption decision, no deployment, touches no installed tree. It only
answers a question neither member has measured: `tools/release_core.validate_decision` is
the gate every adopt path runs through -- what does it actually check about the shadow
result it is handed?

Three arms, all in memory:

  A. a hypothetical adopt decision bound to the real assembled result
  B. the same decision bound to a fabricated shadow result that has the four fields
     validate_decision reads and nothing else -- no evidence, no checks, no probes
  C. the canonical producer path: can `run_shadow` even be reached for this proposal?

If B validates as readily as A, the contract binds field equality, not provenance, and the
question "may targeted evidence sit in the shadow-result slot" is a community judgment the
tooling will not make for us.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import release_core  # noqa: E402
from evolution_core import canonical_json, sha256_text  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "_shadow_20260801_claude_decision_contract_probe.out.json"
BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"


def hypothetical_decision(result_hash):
    """NOT an adoption decision. An in-memory shape used to interrogate the validator."""
    return {
        "schema_version": release_core.DECISION_SCHEMA_VERSION,
        "decision": "adopt",
        "authority_source": "PROBE ONLY -- no member has signed anything",
        "shadow_result_hash": result_hash,
        "baseline_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "deployment_target": r"C:\Users\zy\.claude\skills\solve-with-weilan",
        "rollback_triggers": ["probe placeholder trigger"],
    }


def main():
    real = json.loads((HERE / "SHADOW_RESULT.json").read_text(encoding="utf-8"))

    # Arm A: the evidence we actually assembled this turn.
    arm_a = release_core.validate_decision(hypothetical_decision(real["result_hash"]), real)

    # Arm B: a shadow result with no evidence behind it at all.
    hollow_body = {
        "baseline_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "adoption_eligible": True,
        "note": "fabricated for this probe; no comparison, no checks, no measurement",
    }
    hollow = {**hollow_body, "result_hash": sha256_text(canonical_json(hollow_body))}
    arm_b = release_core.validate_decision(hypothetical_decision(hollow["result_hash"]), hollow)

    # Arm C: what the canonical producer would demand instead.
    plan_fields = release_core.validate_shadow_plan({}, {}, None)["issues"]

    result = {
        "probe": "what validate_decision actually binds",
        "authority": "read_only_probe_never_a_decision_never_a_deployment",
        "arm_a_real_assembled_shadow_result": {
            "result_hash": real["result_hash"],
            "adoption_eligible": real["adoption_eligible"],
            "metrics_verified": f'{real["metrics_verified"]}/{real["metrics_total"]}',
            "decision_would_validate": arm_a["valid"],
            "issues": arm_a["issues"],
        },
        "arm_b_hollow_fabricated_shadow_result": {
            "fields_present": sorted(hollow),
            "decision_would_validate": arm_b["valid"],
            "issues": arm_b["issues"],
        },
        "arm_c_canonical_producer_requirements": {
            "empty_plan_issue_count": len(plan_fields),
            "empty_plan_issues": plan_fields,
        },
        "finding": (
            "validate_decision binds the decision to a result_hash and two artifact hashes "
            "and reads adoption_eligible. It does not read schema_version, evidence_kind, "
            "checks, gate_failures, or any provenance field of the shadow result, and it "
            "does not require that the result came from run_shadow. Whether targeted "
            "executable verification may occupy the shadow-result slot is therefore a "
            "governance judgment; the tooling will accept either and cannot make it for us."
        ),
        "boundary": (
            "This measures the validator, not the candidate. It says nothing about whether "
            "the canonical-workspace-cache candidate is correct, and it is not an argument "
            "that the assembled evidence is weak -- arm A carries eight verified metrics "
            "that arm B does not. It only shows the validator cannot tell them apart."
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
