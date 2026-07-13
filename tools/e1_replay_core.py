"""Helpers for E1 correction and fixed-suite seed replay binding."""

from pathlib import Path

from evolution_core import file_sha256


SCORE_EPSILON = 1e-9


def _case_scores(shadow_result, case_id):
    return [
        item
        for item in shadow_result.get("comparisons", [])
        if item.get("case_id") == case_id
    ]


def case_level_non_saturated_delta(shadow_result, case_ids, saturation_threshold=0.95):
    """Return case-level E1-S components under the preregistered saturation rule."""
    components = []
    for case_id in case_ids:
        rows = _case_scores(shadow_result, case_id)
        if not rows:
            continue
        baseline_mean = sum(float(item["baseline_score"]) for item in rows) / len(rows)
        delta_mean = sum(float(item["delta"]) for item in rows) / len(rows)
        if baseline_mean + SCORE_EPSILON < saturation_threshold:
            components.append(
                {
                    "case_id": case_id,
                    "baseline_mean": baseline_mean,
                    "delta_mean": delta_mean,
                    "trial_count": len(rows),
                }
            )
    mean_delta = (
        sum(item["delta_mean"] for item in components) / len(components)
        if components
        else 0.0
    )
    return {
        "non_saturated_case_ids": [item["case_id"] for item in components],
        "non_saturated_hard_case_mean_delta": mean_delta,
        "non_saturated_comparison_count": len(components),
        "components": components,
    }


def validate_fixed_suite_baseline_binding(
    observed_baseline_artifact,
    *,
    current_deployed_artifact,
    direct_predecessor_artifact,
):
    """Validate that a guardrail baseline binds to current deployed lineage."""
    allowed = {current_deployed_artifact, direct_predecessor_artifact}
    if observed_baseline_artifact not in allowed:
        raise ValueError(f"stale_baseline_binding: {observed_baseline_artifact}")
    return {
        "valid": True,
        "baseline_artifact_hash": observed_baseline_artifact,
        "binding": (
            "current_deployed"
            if observed_baseline_artifact == current_deployed_artifact
            else "direct_predecessor"
        ),
    }


def deployment_lineage_from_receipts(current_receipt, predecessor_receipt):
    """Build the minimal lineage document required by the replay spec."""
    current_after = current_receipt.get("after_artifact_hash")
    current_before = current_receipt.get("before_artifact_hash")
    predecessor_after = predecessor_receipt.get("after_artifact_hash")
    if not current_after or not current_before or not predecessor_after:
        raise ValueError("ambiguous_deployment_lineage")
    if current_before != predecessor_after:
        raise ValueError("ambiguous_deployment_lineage")
    return {
        "current_deployed_artifact": current_after,
        "direct_predecessor_artifact": current_before,
    }


def replay_preflight(
    *,
    manifest_hash,
    case_spec_hash,
    configuration_hash,
    fixture_manifest_hashes,
    evaluator_artifact_hashes,
    current_deployed_artifact,
    candidate_artifact_hash,
    spec_paths,
):
    """Create a bounded hash preflight body before seed baseline replay."""
    return {
        "schema_version": "seed_replay_preflight_v0.1",
        "manifest_hash": manifest_hash,
        "case_spec_hash": case_spec_hash,
        "configuration_hash": configuration_hash,
        "fixture_manifest_hashes": dict(sorted(fixture_manifest_hashes.items())),
        "evaluator_artifact_hashes": dict(sorted(evaluator_artifact_hashes.items())),
        "current_deployed_artifact": current_deployed_artifact,
        "candidate_artifact_hash": candidate_artifact_hash,
        "spec_hashes": {
            str(path).replace("\\", "/"): file_sha256(Path(path))
            for path in spec_paths
        },
    }
