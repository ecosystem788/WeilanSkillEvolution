"""Read-only independent review of Codex's 2026-08-01T19:13:58+09:00 proposal.

Checks, without writing to any governed file:
  1. enforcement census for proposal.budgets.max_deployments across the tool plane
  2. whether SHADOW_RESULT binds proposal content at all (it must not, for A to be safe)
  3. proposal.target_metrics vs SHADOW_RESULT.checks[].metric identity (the drift nobody guards)
  4. simulated 0 -> 2 edit: leaf-level diff must be exactly one item
  5. rollback_triggers: count + canonical digest, so two decisions can bind them verbatim
  6. one decision cannot bind two targets: resolve() of a joined string equals neither target
  7. both install points still equal the frozen baseline

Writes only its own .out.json next to itself.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))

from evolution_core import canonical_json, sha256_text, tree_hash  # noqa: E402

PROPOSAL = HERE / "proposal.json"
SHADOW = HERE / "SHADOW_RESULT.json"
TARGETS = [
    r"D:\CodexData\skills\solve-with-weilan",
    r"C:\Users\zy\.claude\skills\solve-with-weilan",
]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def leaves(value, prefix=""):
    out = {}
    if isinstance(value, dict):
        for key, item in value.items():
            out.update(leaves(item, f"{prefix}.{key}" if prefix else key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            out.update(leaves(item, f"{prefix}[{index}]"))
    else:
        out[prefix] = value
    return out


def census_max_deployments():
    hits = []
    for path in sorted((REPO / "tools").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "max_deployments" in line:
                hits.append(
                    {
                        "file": str(path.relative_to(REPO)).replace("\\", "/"),
                        "line": number,
                        "text": line.strip(),
                    }
                )
    return hits


def main():
    proposal = read_json(PROPOSAL)
    shadow = read_json(SHADOW)

    hits = census_max_deployments()
    reads_proposal_budget = [
        hit for hit in hits if "proposal" in hit["text"] or "proposal" in hit["file"]
    ]

    shadow_keys = sorted(shadow.keys())
    binds_proposal_content = [
        key for key in shadow_keys if "proposal" in key and key != "proposal_id"
    ]

    declared = list(proposal.get("target_metrics", []))
    measured = [check.get("metric") for check in shadow.get("checks", [])]
    metrics_identical = declared == measured

    before = leaves(proposal)
    edited = json.loads(json.dumps(proposal))
    edited["budgets"]["max_deployments"] = 2
    after = leaves(edited)
    diff = sorted(
        key
        for key in set(before) | set(after)
        if before.get(key, "\0absent") != after.get(key, "\0absent")
    )

    triggers = proposal.get("rollback_triggers", [])

    joined = ";".join(TARGETS)
    joined_resolved = str(Path(joined).resolve())
    joined_matches = [t for t in TARGETS if str(Path(t).resolve()) == joined_resolved]

    baseline_hash = shadow.get("baseline_artifact_hash")
    installed = {}
    for target in TARGETS:
        path = Path(target)
        installed[target] = {
            "exists": path.exists(),
            "tree_hash": tree_hash(path) if path.exists() else None,
            "equals_frozen_baseline": bool(path.exists() and tree_hash(path) == baseline_hash),
        }

    out = {
        "probe": "claude independent review of codex 2026-08-01T19:13:58+09:00 proposal",
        "authority": "review_evidence_only_never_adopts_or_deploys",
        "reviewed_commit_note": "run against the working tree; no governed file is written",
        "check_1_max_deployments_enforcement": {
            "tool_plane_hits": hits,
            "hits_reading_a_proposal_budget": reads_proposal_budget,
            "verdict": "proposal.budgets.max_deployments is enforced by no gate"
            if not reads_proposal_budget
            else "some gate reads the proposal budget",
        },
        "check_2_shadow_binds_proposal_content": {
            "shadow_top_level_keys": shadow_keys,
            "proposal_binding_keys_beyond_id": binds_proposal_content,
            "verdict": "shadow binds proposal by id only, not by content hash"
            if not binds_proposal_content
            else "shadow binds proposal content",
        },
        "check_3_target_metric_identity": {
            "declared_count": len(declared),
            "measured_count": len(measured),
            "identical_and_ordered": metrics_identical,
            "declared_not_measured": [m for m in declared if m not in measured],
            "measured_not_declared": [m for m in measured if m not in declared],
        },
        "check_4_simulated_budget_edit": {
            "before": proposal["budgets"]["max_deployments"],
            "after": edited["budgets"]["max_deployments"],
            "leaf_diff": diff,
            "leaf_diff_count": len(diff),
            "is_exactly_the_budget_leaf": diff == ["budgets.max_deployments"],
        },
        "check_5_rollback_triggers": {
            "count": len(triggers),
            "canonical_digest": sha256_text(canonical_json(triggers)),
            "triggers": triggers,
        },
        "check_6_one_decision_cannot_bind_two_targets": {
            "joined_string": joined,
            "resolved": joined_resolved,
            "matches_a_real_target": joined_matches,
            "verdict": "a joined deployment_target resolves to neither install point, so deploy_candidate's equality check rejects both deploys"
            if not joined_matches
            else "joined string unexpectedly matches a target",
        },
        "check_7_install_points_still_baseline": {
            "frozen_baseline": baseline_hash,
            "installed": installed,
            "both_equal_baseline": all(v["equals_frozen_baseline"] for v in installed.values()),
        },
    }
    Path(str(Path(__file__).with_suffix("")) + ".out.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(
        {
            key: value
            for key, value in out.items()
            if key.startswith("check_")
        },
        ensure_ascii=False,
        indent=1,
    )[:4000])


if __name__ == "__main__":
    main()
