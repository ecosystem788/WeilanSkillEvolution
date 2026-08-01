"""Assemble the missing Release Plane input for canonical-workspace-cache-v0.1.

Both members already agreed the candidate itself is clean and that it cannot be adopted
without a frozen, equal-budget shadow result bound to the exact revised content address.
This script builds that shadow result. It is evidence only: it never adopts, deploys, or
writes to any installed tree.

Discipline it enforces on itself:

* Every artifact hash is recomputed here from bytes with `tools/evolution_core.tree_hash`.
  No hash string is copied out of the package.
* Every target metric must be backed by a receipt whose own declared
  `candidate_artifact_hash` is the revised address. A receipt naming the prior candidate
  counts as UNBOUND, not as verified -- that is the exact substitution this line has been
  refusing all day.
* `adoption_eligible` is false unless every metric is verified and no rollback trigger
  fires. A metric that merely documents behaviour without discriminating between a real
  and a cache-free implementation is recorded as verified with that limit stated, because
  the metric text is what it must satisfy.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from evolution_core import canonical_json, file_sha256, sha256_text, tree_hash, changed_files  # noqa: E402

HERE = Path(__file__).resolve().parent
BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"
PRIOR = "ec236760072cf20d3a65df3eebd4c4075e86f79e64971b59375e4937fb3d956f"
INSTALL_POINTS = [
    r"C:\Users\zy\.claude\skills\solve-with-weilan",
    r"D:\CodexData\skills\solve-with-weilan",
]
OUT = HERE / "SHADOW_RESULT.json"


def load(name):
    path = HERE / name
    return json.loads(path.read_text(encoding="utf-8")), {
        "ref": f"proposals/canonical-workspace-cache-v0.1/{name}",
        "sha256": file_sha256(path),
    }


def bound_to_revised(receipt):
    """A receipt counts only if it names the revised candidate itself."""
    for key in ("candidate_artifact_hash", "candidate_artifact_hash_revised"):
        if receipt.get(key) == CAND:
            return True
    arms = receipt.get("arms")
    if isinstance(arms, dict) and arms.get("revised_candidate") == CAND:
        return True
    return False


def main():
    proposal = json.loads((HERE / "proposal.json").read_text(encoding="utf-8"))
    metrics = proposal["target_metrics"]
    triggers = proposal["rollback_triggers"]

    recomputed = {
        "tracked_baseline_tree": tree_hash(HERE / "baseline" / "solve-with-weilan"),
        "tracked_candidate_tree": tree_hash(HERE / "candidate" / "solve-with-weilan"),
        "frozen_baseline_artifact": tree_hash(HERE / "artifacts" / BASE / "solve-with-weilan"),
        "frozen_candidate_artifact": tree_hash(HERE / "artifacts" / CAND / "solve-with-weilan"),
    }
    declared_paths_match = changed_files(
        HERE / "artifacts" / BASE / "solve-with-weilan",
        HERE / "artifacts" / CAND / "solve-with-weilan",
    )
    install_state = {
        point: {"tree_hash": tree_hash(point), "equals_frozen_baseline": tree_hash(point) == BASE}
        for point in INSTALL_POINTS
        if Path(point).is_dir()
    }

    diff, diff_ref = load("_probe_candidate_tree_diff.out.json")
    contract, contract_ref = load("_probe_contract_discrimination.out.json")
    sham, sham_ref = load("_review2_20260801_claude_sham_candidate.out.json")
    suite, suite_ref = load("_review2_20260801_claude_independent_suite.out.json")
    cli, cli_ref = load("_shadow_20260801_claude_cli_equivalence_revised.out.json")
    latency, latency_ref = load("_shadow_20260801_claude_revised_latency.out.json")

    declared = [
        "proposals/canonical-workspace-cache-v0.1/candidate/solve-with-weilan/scripts/runtime_core.py",
        "proposals/canonical-workspace-cache-v0.1/candidate/solve-with-weilan/scripts/test_canonical_workspace_cache.py",
    ]
    two_paths_ok = (
        sorted(declared_paths_match)
        == ["scripts/runtime_core.py", "scripts/test_canonical_workspace_cache.py"]
        and sorted(proposal["changed_paths"]) == sorted(declared)
        and recomputed["frozen_candidate_artifact"] == CAND
        and recomputed["frozen_baseline_artifact"] == BASE
    )

    checks = [
        {
            "metric": metrics[0],
            "verified": bool(two_paths_ok),
            "provenance": "recomputed_now_from_bytes",
            "evidence": [diff_ref],
            "observed": {"changed_paths_between_frozen_trees": sorted(declared_paths_match)},
            # bound by construction: the tree compared here is artifacts/<revised hash>,
            # and its recomputed tree_hash is asserted to equal that hash in two_paths_ok
            "bound_to_revised_candidate": recomputed["frozen_candidate_artifact"] == CAND,
        },
        {
            "metric": metrics[1],
            "verified": bool(
                contract.get("baseline_failed_by_assertion_not_attribute_error")
                and contract.get("candidate_passed")
                and sham.get("conclusion", {}).get("sham_is_rejected")
                and sham.get("conclusion", {}).get("sham_rejected_by_assertion_not_attribute_error")
            ),
            "provenance": "archived_receipt_bound_to_revised_candidate",
            "evidence": [contract_ref, sham_ref],
            "observed": {
                "baseline_fails_by_assertion_without_attribute_error":
                    contract.get("baseline_failed_by_assertion_not_attribute_error"),
                "candidate_passes": contract.get("candidate_passed"),
                "cache_free_sham_with_full_api_is_rejected": sham.get("conclusion"),
            },
            "bound_to_revised_candidate": bound_to_revised(contract),
        },
        {
            "metric": metrics[2],
            "verified": bool(contract.get("candidate_passed")),
            "provenance": "archived_receipt_bound_to_revised_candidate",
            "evidence": [contract_ref, sham_ref],
            "observed": {"discriminating": True,
                         "note": "this is the half a cache-free sham fails"},
            "bound_to_revised_candidate": bound_to_revised(contract),
        },
        {
            "metric": metrics[3],
            "verified": bool(contract.get("candidate_passed")),
            "provenance": "archived_receipt_bound_to_revised_candidate",
            "evidence": [contract_ref, sham_ref],
            "observed": {
                "discriminating": False,
                "disclosure": (
                    "the cache-free sham also passes this half, so it documents the "
                    "contract rather than discriminating cached from uncached; it is "
                    "still a true assertion about the candidate, which is what the "
                    "metric text asks for"
                ),
            },
            "bound_to_revised_candidate": bound_to_revised(contract),
        },
        {
            "metric": metrics[4],
            "verified": bool(cli.get("baseline_and_revised_candidate_byte_identical")),
            "provenance": "rerun_now_bound_to_revised_candidate",
            "evidence": [cli_ref],
            "observed": {
                "commands": sorted(cli.get("commands", {})),
                "prior_and_revised_candidate_byte_identical":
                    cli.get("prior_and_revised_candidate_byte_identical"),
            },
            "bound_to_revised_candidate": bound_to_revised(cli),
        },
        {
            "metric": metrics[5],
            "verified": bool(
                suite.get("candidate_only_failures") == []
                and suite.get("shared_nodes_with_changed_verdict") == {}
            ),
            "provenance": "archived_receipt_bound_to_revised_candidate",
            "evidence": [suite_ref],
            "observed": {
                "candidate_only_failures": suite.get("candidate_only_failures"),
                "baseline_only_nodes": suite.get("baseline_only_nodes"),
                "shared_nodes_with_changed_verdict": suite.get("shared_nodes_with_changed_verdict"),
                "disclosure": (
                    "the suite is not all green on either arm; one pre-existing failure, "
                    "test_slow_loop.py::test_promotion_gate_rejects_on_full_budget, fails "
                    "on baseline and candidate alike and predates this line"
                ),
            },
            "bound_to_revised_candidate": bound_to_revised(suite),
        },
        {
            "metric": metrics[6],
            "verified": bool(
                latency.get("baseline", {}).get("n", 0) >= 3
                and latency.get("candidate", {}).get("n", 0) >= 3
                and latency.get("baseline", {}).get("n") == latency.get("candidate", {}).get("n")
                and latency.get("all_runs_returned_open_frames")
            ),
            "provenance": "rerun_now_bound_to_revised_candidate",
            "evidence": [latency_ref],
            "observed": {
                "samples_per_arm": [latency.get("baseline", {}).get("n"),
                                    latency.get("candidate", {}).get("n")],
                "run_order": latency.get("run_order"),
                "all_runs_returned_open_frames": latency.get("all_runs_returned_open_frames"),
            },
            "bound_to_revised_candidate": bound_to_revised(latency),
        },
        {
            "metric": metrics[7],
            "verified": bool(latency.get("candidate_median_lower")),
            "provenance": "rerun_now_bound_to_revised_candidate",
            "evidence": [latency_ref],
            "observed": {
                "baseline_median_s": latency.get("baseline", {}).get("median_s"),
                "candidate_median_s": latency.get("candidate", {}).get("median_s"),
                "median_speedup_x": latency.get("median_speedup_x"),
                "arms_have_disjoint_ranges": latency.get("arms_have_disjoint_ranges"),
                "worst_cross_arm_ratio_x": latency.get("worst_cross_arm_ratio_x"),
                "disclosure": (
                    "host load is uncontrolled and three samples per arm bound an "
                    "observation on one copied ledger; this is not a latency floor and "
                    "no lower bound is claimed"
                ),
            },
            "bound_to_revised_candidate": bound_to_revised(latency),
        },
    ]

    gate_failures = []
    if not two_paths_ok:
        gate_failures.append(f"rollback trigger fired: {triggers[0]}")
    if not (contract.get("baseline_failed_by_assertion_not_attribute_error")):
        gate_failures.append(f"rollback trigger fired: {triggers[1]}")
    if not contract.get("candidate_passed"):
        gate_failures.append(f"rollback trigger fired: {triggers[2]}")
    if not cli.get("baseline_and_revised_candidate_byte_identical"):
        gate_failures.append(f"rollback trigger fired: {triggers[3]}")
    if suite.get("candidate_only_failures") != []:
        gate_failures.append(f"rollback trigger fired: {triggers[4]}")
    if not latency.get("candidate_median_lower"):
        gate_failures.append(f"rollback trigger fired: {triggers[5]}")
    if not all(row["equals_frozen_baseline"] for row in install_state.values()):
        gate_failures.append(f"rollback trigger fired: {triggers[6]}")

    unbound = [row["metric"] for row in checks if not row["bound_to_revised_candidate"]]
    for metric in unbound:
        gate_failures.append(f"evidence for a target metric is not bound to the revised candidate: {metric}")
    unverified = [row["metric"] for row in checks if not row["verified"]]
    for metric in unverified:
        gate_failures.append(f"target metric not verified: {metric}")

    body = {
        "schema_version": "weilan_skill_shadow_result_v0.6",
        "shadow_id": "canonical-workspace-cache-v0.1-revised-targeted-20260801",
        "evidence_kind": "targeted_executable_verification",
        "proposal_id": "canonical-workspace-cache-v0.1",
        "baseline_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "prior_candidate_artifact_hash": PRIOR,
        "recomputed_tree_hashes": recomputed,
        "installed_tree_state": install_state,
        "produced_by": "claude",
        "author_of_candidate": "codex",
        "independence": (
            "the member assembling this evidence is not the candidate author; assembling "
            "shadow evidence confers no adoption or deployment authority on either member"
        ),
        "comparison_count": len(checks),
        "checks": checks,
        "metrics_verified": len(checks) - len(unverified),
        "metrics_total": len(checks),
        "unbound_metrics": unbound,
        "unverified_metrics": unverified,
        "gate_failures": gate_failures,
        "adoption_eligible": not gate_failures,
        "boundary": (
            "Byte identity on one ledger, a passing contract test, a rejected cache-free "
            "sham, one full-suite comparison and three timed opens per arm are what was "
            "measured. None of it proves semantic equivalence over all inputs, and "
            "process-local resolution stability is not filesystem stability."
        ),
        "authority": "targeted_shadow_evidence_only_never_adopts_or_deploys",
    }
    result = {**body, "result_hash": sha256_text(canonical_json(body))}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(
        {k: v for k, v in result.items() if k != "checks"}, ensure_ascii=False, indent=2))
    print("\nresult_hash:", result["result_hash"])
    return 0 if result["adoption_eligible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
