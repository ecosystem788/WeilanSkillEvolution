"""Read-only independent review of commit e15b002 (adoption authority shape, A/B/C/D).

Written from zero by Claude 2026-08-01, does not import or reuse Codex's review probes.
It only reads: git objects, the landed JSON files, the two installed Skill trees, and the
deploy/rollback source. It writes nothing outside its own .out.json (written by the caller
via redirection) and never touches an install tree.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(r"D:\WeilanSkillEvolution")
PKG = REPO / "proposals" / "canonical-workspace-cache-v0.1"
COMMIT = "e15b0024b56c26c023c809af4d4bb70f4dfd94d6"
sys.path.insert(0, str(REPO / "tools"))
from evolution_core import canonical_json, sha256_text, tree_hash  # noqa: E402

CLAIMED = {
    "baseline": "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad",
    "candidate": "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a",
    "shadow_result_hash": "70ea86b2c2b042c3c4c8d76f103a861d014ba7e834e3ea7d99ada9bf125f7b9c",
    "rollback_digest": "c68ff934198d0b64523b5a6db908761bd416f22a26001c2f83f386385f2b96d7",
}
INSTALLS = {
    "codexdata": Path(r"D:\CodexData\skills\solve-with-weilan"),
    "claude_home": Path(r"C:\Users\zy\.claude\skills\solve-with-weilan"),
}


def git(*args):
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, check=True
    ).stdout.decode("utf-8", "replace")


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


def blob_json(rev, path):
    raw = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{rev}:{path}"], capture_output=True, check=True
    ).stdout
    return json.loads(raw.decode("utf-8"))


report = {"commit": COMMIT, "checks": [], "notes": []}


def check(name, ok, detail):
    report["checks"].append({"check": name, "ok": bool(ok), "detail": detail})


# 1. commit scope: exactly the three declared paths, two added one modified.
name_status = [
    line.split("\t") for line in git("show", "--name-status", "--format=", COMMIT).splitlines() if line
]
check(
    "commit_touches_exactly_the_declared_three_paths",
    sorted(name_status)
    == sorted(
        [
            ["A", "proposals/canonical-workspace-cache-v0.1/adoption/ADOPTION_DECISION_CLAUDE_HOME.json"],
            ["A", "proposals/canonical-workspace-cache-v0.1/adoption/ADOPTION_DECISION_CODEXDATA.json"],
            ["M", "proposals/canonical-workspace-cache-v0.1/proposal.json"],
        ]
    ),
    name_status,
)

# 2. proposal leaf diff is exactly budgets.max_deployments 0 -> 2.
rel_proposal = "proposals/canonical-workspace-cache-v0.1/proposal.json"
before = leaves(blob_json(f"{COMMIT}~1", rel_proposal))
after = leaves(blob_json(COMMIT, rel_proposal))
diff = {
    key: [before.get(key, "<absent>"), after.get(key, "<absent>")]
    for key in set(before) | set(after)
    if before.get(key, "<absent>") != after.get(key, "<absent>")
}
check(
    "proposal_leaf_diff_is_exactly_max_deployments_0_to_2",
    diff == {"budgets.max_deployments": [0, 2]},
    diff,
)

# 3. decision-validate on both, run as a subprocess against the real CLI.
shadow_path = PKG / "SHADOW_RESULT.json"
for key, rel in (
    ("codexdata", "adoption/ADOPTION_DECISION_CODEXDATA.json"),
    ("claude_home", "adoption/ADOPTION_DECISION_CLAUDE_HOME.json"),
):
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools" / "evolution_cli.py"),
            "decision-validate",
            "--decision",
            str(PKG / rel),
            "--shadow-result",
            str(shadow_path),
        ],
        capture_output=True,
    )
    payload = json.loads(proc.stdout.decode("utf-8"))
    check(f"decision_validate_valid_{key}", payload.get("valid") is True, payload)

# 4. rollback_triggers identity across proposal + both decisions, and the claimed digest.
proposal = json.loads((PKG / "proposal.json").read_text(encoding="utf-8"))
decisions = {
    key: json.loads((PKG / rel).read_text(encoding="utf-8"))
    for key, rel in (
        ("codexdata", "adoption/ADOPTION_DECISION_CODEXDATA.json"),
        ("claude_home", "adoption/ADOPTION_DECISION_CLAUDE_HOME.json"),
    )
}
triggers = proposal["rollback_triggers"]
check(
    "rollback_triggers_verbatim_and_in_order_across_all_three",
    all(d["rollback_triggers"] == triggers for d in decisions.values()) and len(triggers) == 7,
    {"count": len(triggers)},
)
check(
    "rollback_triggers_canonical_digest_matches_claim",
    sha256_text(canonical_json(triggers)) == CLAIMED["rollback_digest"],
    sha256_text(canonical_json(triggers)),
)

# 5. target_metrics vs SHADOW_RESULT checks[].metric, verbatim and same order.
shadow = json.loads(shadow_path.read_text(encoding="utf-8"))
metrics = [c["metric"] for c in shadow.get("checks", [])]
check(
    "target_metrics_match_shadow_checks_verbatim_same_order",
    metrics == proposal["target_metrics"] and len(metrics) == 8,
    {"n_shadow": len(metrics), "n_target": len(proposal["target_metrics"])},
)

# 6. shadow result_hash recomputes from its own body.
body = {k: v for k, v in shadow.items() if k != "result_hash"}
check(
    "shadow_result_hash_recomputes_from_body",
    sha256_text(canonical_json(body)) == shadow.get("result_hash") == CLAIMED["shadow_result_hash"],
    {"recomputed": sha256_text(canonical_json(body)), "recorded": shadow.get("result_hash")},
)

# 7. frozen candidate tree still hashes to the authorized candidate hash.
check(
    "frozen_candidate_tree_hash_unchanged",
    tree_hash(PKG / "candidate" / "solve-with-weilan") == CLAIMED["candidate"],
    tree_hash(PKG / "candidate" / "solve-with-weilan"),
)

# 8. both install trees are still the declared baseline: zero bytes deployed.
for key, path in INSTALLS.items():
    observed = tree_hash(path) if path.exists() else None
    check(
        f"install_tree_still_baseline_{key}",
        observed == CLAIMED["baseline"],
        {"target": str(path), "observed": observed},
    )

# 9. NEW DIFFERENCE (static): does the deploy path bind the predecessor?
release_src = (REPO / "tools" / "release_core.py").read_text(encoding="utf-8")
deploy_src = release_src.split("def deploy_candidate", 1)[1].split("\ndef ", 1)[0]
report["notes"].append(
    {
        "note": "deploy_candidate never compares the current target tree against "
        "decision.baseline_artifact_hash; it records whatever is on disk as "
        "before_artifact_hash and installs.",
        "baseline_artifact_hash_mentioned_in_deploy_body": "baseline_artifact_hash" in deploy_src,
        "validate_decision_compares_baseline_to": "shadow_result.baseline_artifact_hash only",
        "consequence": "reversibility is snapshot-bound and holds; authorization is not "
        "predecessor-bound, so deploying onto a drifted target would succeed silently.",
    }
)

# 10. NEW DIFFERENCE: the two decisions produce distinct deployment_ids (no receipt collision).
ids = {}
for key, decision in decisions.items():
    decision_hash = sha256_text(canonical_json(decision))
    target = str(Path(decision["deployment_target"]).resolve())
    ids[key] = sha256_text(canonical_json({"decision_hash": decision_hash, "target": target}))[:24]
check("two_decisions_yield_distinct_deployment_ids", len(set(ids.values())) == 2, ids)

report["ok"] = all(c["ok"] for c in report["checks"])
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(0 if report["ok"] else 1)
