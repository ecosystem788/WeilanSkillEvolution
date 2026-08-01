"""Independent review of Codex's 2026-08-01T20:47:41+09:00 deployment/rollback receipt,
plus a live sandbox probe of whether release_core.deploy_candidate fails closed on
two adoption targets that are path aliases of one physical tree.

Read-only with respect to the repository and to both real install points.
The sandbox half creates and destroys its own temporary directories only.

Run:  python _review_20260801_claude_alias_target_and_rollback_state.py
Writes: _review_20260801_claude_alias_target_and_rollback_state.out.json
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROP = Path(__file__).resolve().parent
TOOLS = REPO / "tools"

BASELINE_EXPECT = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CANDIDATE_EXPECT = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"
DEPLOY_ID = "56bc789721f37b7e5055d37a"
ROLLBACK_ID = "a59bd56fb0043866eded33a5"
T1 = r"D:\CodexData\skills\solve-with-weilan"
T2 = r"C:\Users\zy\.claude\skills\solve-with-weilan"


# --- my own reimplementation of the tool's tree hash spec (not imported) -------
def _canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def my_tree_hash(root):
    root = Path(root).resolve()
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or ".pytest_cache" in path.parts or path.suffix == ".pyc":
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return hashlib.sha256(_canon(rows).encode("utf-8")).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


results = {}


# === PART A: verify the receipt Codex published ================================
def part_a():
    out = {}
    dep = load(PROP / "deployments" / DEPLOY_ID / "DEPLOYMENT_RECEIPT.json")
    rbk = load(PROP / "deployments" / DEPLOY_ID / f"ROLLBACK_RECEIPT-{ROLLBACK_ID}.json")
    proposal = load(PROP / "proposal.json")
    dec_t1 = load(PROP / "adoption" / "ADOPTION_DECISION_CODEXDATA.json")
    dec_t2 = load(PROP / "adoption" / "ADOPTION_DECISION_CLAUDE_HOME.json")

    # A1 junction topology: do the two authorized targets name one physical tree?
    skill_md_1 = Path(T1) / "SKILL.md"
    skill_md_2 = Path(T2) / "SKILL.md"
    st1, st2 = os.stat(skill_md_1), os.stat(skill_md_2)
    out["a1_alias"] = {
        "t1_resolved": str(Path(T1).resolve()),
        "t2_resolved": str(Path(T2).resolve()),
        "resolve_collides": str(Path(T1).resolve()) == str(Path(T2).resolve()),
        "t1_file_id": [st1.st_dev, st1.st_ino],
        "t2_file_id": [st2.st_dev, st2.st_ino],
        "file_id_identical": (st1.st_dev, st1.st_ino) == (st2.st_dev, st2.st_ino),
        "claude_skills_is_reparse_point": bool(
            os.lstat(r"C:\Users\zy\.claude\skills").st_file_attributes & 0x400
        ),
    }

    # A2 current state of both names, and of the rollback snapshot
    h1 = my_tree_hash(T1)
    h2 = my_tree_hash(T2)
    snap = my_tree_hash(PROP / "deployments" / DEPLOY_ID / "rollback" / "solve-with-weilan")
    out["a2_current_state"] = {
        "t1_tree_hash": h1,
        "t2_tree_hash": h2,
        "rollback_snapshot_tree_hash": snap,
        "t1_is_baseline": h1 == BASELINE_EXPECT,
        "t2_is_baseline": h2 == BASELINE_EXPECT,
        "snapshot_is_baseline": snap == BASELINE_EXPECT,
        "any_is_candidate": CANDIDATE_EXPECT in {h1, h2, snap},
    }

    # A3 frozen package trees still match the signed hashes
    out["a3_package"] = {
        "baseline_tree_hash": my_tree_hash(PROP / "baseline" / "solve-with-weilan"),
        "candidate_tree_hash": my_tree_hash(PROP / "candidate" / "solve-with-weilan"),
        "baseline_matches": my_tree_hash(PROP / "baseline" / "solve-with-weilan") == BASELINE_EXPECT,
        "candidate_matches": my_tree_hash(PROP / "candidate" / "solve-with-weilan") == CANDIDATE_EXPECT,
    }

    # A4 receipt internals recomputed from the decision, not copied from the receipt
    def decision_hash(dec):
        return hashlib.sha256(_canon(dec).encode("utf-8")).hexdigest()

    def deployment_id(dec, target):
        body = {"decision_hash": decision_hash(dec), "target": str(Path(target).resolve())}
        return hashlib.sha256(_canon(body).encode("utf-8")).hexdigest()[:24]

    out["a4_receipt_math"] = {
        "t1_decision_hash": decision_hash(dec_t1),
        "receipt_decision_hash": dep["decision_hash"],
        "decision_hash_matches": decision_hash(dec_t1) == dep["decision_hash"],
        "t1_deployment_id_recomputed": deployment_id(dec_t1, T1),
        "deployment_id_matches": deployment_id(dec_t1, T1) == dep["deployment_id"],
        "t2_deployment_id_would_have_been": deployment_id(dec_t2, T2),
        "t2_id_differs_from_t1": deployment_id(dec_t2, T2) != dep["deployment_id"],
        "receipt_before": dep["before_artifact_hash"],
        "receipt_after": dep["after_artifact_hash"],
        "before_is_baseline": dep["before_artifact_hash"] == BASELINE_EXPECT,
        "after_is_candidate": dep["after_artifact_hash"] == CANDIDATE_EXPECT,
        "rollback_restored": rbk["restored_artifact_hash"],
        "rollback_replaced": rbk["replaced_artifact_hash"],
        "rollback_restored_is_baseline": rbk["restored_artifact_hash"] == BASELINE_EXPECT,
    }

    # A5 budget accounting from disk, not from the narrative
    dep_dirs = sorted(
        p.name for p in (PROP / "deployments").iterdir() if p.is_dir()
    ) if (PROP / "deployments").is_dir() else []
    receipts = sorted(str(p.relative_to(PROP)) for p in (PROP / "deployments").rglob("DEPLOYMENT_RECEIPT.json"))
    intents = sorted(str(p.relative_to(PROP)) for p in (PROP / "deployments").rglob("DEPLOYMENT_INTENT.json"))
    out["a5_budget"] = {
        "max_deployments": proposal["budgets"]["max_deployments"],
        "deployment_dirs": dep_dirs,
        "deployment_receipts": receipts,
        "deployment_intents": intents,
        "consumed": len(receipts),
        "within_budget": len(receipts) <= proposal["budgets"]["max_deployments"],
    }
    return out


# === PART B: does the tool itself fail closed on aliased targets? ==============
def part_b():
    sys.path.insert(0, str(TOOLS))
    import release_core  # noqa: E402
    import evolution_core  # noqa: E402

    root = Path(tempfile.mkdtemp(prefix="wl_alias_")).resolve()
    out = {"sandbox_root": str(root)}
    try:
        real = root / "realskills"
        (real / "solve-with-weilan" / "scripts").mkdir(parents=True)
        (real / "solve-with-weilan" / "SKILL.md").write_text("baseline\n", encoding="utf-8")
        (real / "solve-with-weilan" / "scripts" / "runtime_core.py").write_text("BASE = 1\n", encoding="utf-8")

        cand = root / "cand" / "solve-with-weilan"
        (cand / "scripts").mkdir(parents=True)
        (cand / "SKILL.md").write_text("baseline\n", encoding="utf-8")
        (cand / "scripts" / "runtime_core.py").write_text("BASE = 2  # candidate\n", encoding="utf-8")

        alias = root / "aliasskills"
        mk = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(real)],
            capture_output=True, text=True,
        )
        out["mklink_rc"] = mk.returncode
        if mk.returncode != 0:
            out["skipped"] = "junction creation failed: " + (mk.stderr or mk.stdout).strip()
            return out

        target1 = real / "solve-with-weilan"
        target2 = alias / "solve-with-weilan"
        base_h = evolution_core.tree_hash(target1)
        cand_h = evolution_core.tree_hash(cand)
        out["sandbox_hashes"] = {"baseline": base_h, "candidate": cand_h, "distinct": base_h != cand_h}
        out["alias_resolves_same"] = str(target1.resolve()) == str(target2.resolve())

        shadow = {
            "result_hash": "s" * 64,
            "baseline_artifact_hash": base_h,
            "candidate_artifact_hash": cand_h,
            "adoption_eligible": True,
        }

        def decision(target):
            return {
                "schema_version": release_core.DECISION_SCHEMA_VERSION,
                "decision": "adopt",
                "authority_source": "sandbox-only synthetic authority",
                "shadow_result_hash": shadow["result_hash"],
                "baseline_artifact_hash": base_h,
                "candidate_artifact_hash": cand_h,
                "deployment_target": str(target),
                "rollback_triggers": ["sandbox trigger"],
            }

        receipt_root = root / "receipts"
        r1 = release_core.deploy_candidate(cand, target1, decision(target1), shadow, receipt_root)
        out["t1"] = {
            "deployment_id": r1["deployment_id"],
            "before": r1["before_artifact_hash"],
            "after": r1["after_artifact_hash"],
            "reversible": r1["reversible"],
            "before_is_baseline": r1["before_artifact_hash"] == base_h,
        }

        # Second deploy through the *other name* for the same physical tree.
        try:
            r2 = release_core.deploy_candidate(cand, target2, decision(target2), shadow, receipt_root)
            snap2 = evolution_core.tree_hash(Path(r2["rollback_artifact"])) if r2["rollback_artifact"] else None
            out["t2"] = {
                "raised": None,
                "deployment_id": r2["deployment_id"],
                "distinct_deployment_id": r2["deployment_id"] != r1["deployment_id"],
                "target_recorded": r2["target"],
                "before": r2["before_artifact_hash"],
                "after": r2["after_artifact_hash"],
                "reversible": r2["reversible"],
                "rollback_snapshot_tree_hash": snap2,
                "rollback_snapshot_is_candidate_not_baseline": snap2 == cand_h,
            }
        except Exception as exc:  # tool refused -> it fails closed
            out["t2"] = {"raised": f"{type(exc).__name__}: {exc}"}

        out["verdict"] = {
            "tool_fails_closed_on_alias": out["t2"].get("raised") is not None,
            "second_receipt_written_with_candidate_rollback_domain": (
                out["t2"].get("raised") is None
                and out["t2"].get("rollback_snapshot_is_candidate_not_baseline") is True
            ),
        }
        return out
    finally:
        shutil.rmtree(root, ignore_errors=True)


# === PART C: after a precise rollback, can the SAME decision redeploy? =========
def part_c():
    sys.path.insert(0, str(TOOLS))
    import release_core  # noqa: E402
    import evolution_core  # noqa: E402

    root = Path(tempfile.mkdtemp(prefix="wl_redeploy_")).resolve()
    out = {"sandbox_root": str(root)}
    try:
        target = root / "skills" / "solve-with-weilan"
        (target / "scripts").mkdir(parents=True)
        (target / "SKILL.md").write_text("baseline\n", encoding="utf-8")
        (target / "scripts" / "runtime_core.py").write_text("BASE = 1\n", encoding="utf-8")

        cand = root / "cand" / "solve-with-weilan"
        (cand / "scripts").mkdir(parents=True)
        (cand / "SKILL.md").write_text("baseline\n", encoding="utf-8")
        (cand / "scripts" / "runtime_core.py").write_text("BASE = 2  # candidate\n", encoding="utf-8")

        base_h = evolution_core.tree_hash(target)
        cand_h = evolution_core.tree_hash(cand)
        shadow = {
            "result_hash": "s" * 64,
            "baseline_artifact_hash": base_h,
            "candidate_artifact_hash": cand_h,
            "adoption_eligible": True,
        }

        def decision(authority):
            return {
                "schema_version": release_core.DECISION_SCHEMA_VERSION,
                "decision": "adopt",
                "authority_source": authority,
                "shadow_result_hash": shadow["result_hash"],
                "baseline_artifact_hash": base_h,
                "candidate_artifact_hash": cand_h,
                "deployment_target": str(target),
                "rollback_triggers": ["sandbox trigger"],
            }

        receipt_root = root / "receipts"
        dec1 = decision("sandbox authority round 1")
        r1 = release_core.deploy_candidate(cand, target, dec1, shadow, receipt_root)
        out["deploy1"] = {"id": r1["deployment_id"], "after_state": evolution_core.tree_hash(target)}

        rb = release_core.rollback_deployment(
            Path(receipt_root) / r1["deployment_id"] / "DEPLOYMENT_RECEIPT.json",
            "sandbox rollback authority",
        )
        out["rollback"] = {
            "id": rb["rollback_id"],
            "restored": rb["restored_artifact_hash"],
            "state_now_is_baseline": evolution_core.tree_hash(target) == base_h,
        }

        # C1: same decision again (identical bytes -> identical deployment_id)
        try:
            release_core.deploy_candidate(cand, target, dec1, shadow, receipt_root)
            out["redeploy_same_decision"] = {"raised": None, "state": evolution_core.tree_hash(target)}
        except Exception as exc:
            out["redeploy_same_decision"] = {"raised": f"{type(exc).__name__}: {exc}"}

        # C2: a fresh decision (new authority_source -> new decision_hash -> new id)
        dec2 = decision("sandbox authority round 2 (fresh cosign)")
        try:
            r2 = release_core.deploy_candidate(cand, target, dec2, shadow, receipt_root)
            out["redeploy_fresh_decision"] = {
                "raised": None,
                "id": r2["deployment_id"],
                "distinct_id": r2["deployment_id"] != r1["deployment_id"],
                "before": r2["before_artifact_hash"],
                "before_is_baseline": r2["before_artifact_hash"] == base_h,
                "state_now_is_candidate": evolution_core.tree_hash(target) == cand_h,
            }
        except Exception as exc:
            out["redeploy_fresh_decision"] = {"raised": f"{type(exc).__name__}: {exc}"}

        out["verdict"] = {
            "same_decision_blocked": out["redeploy_same_decision"].get("raised") is not None,
            "fresh_decision_required_for_reentry": (
                out["redeploy_same_decision"].get("raised") is not None
                and out["redeploy_fresh_decision"].get("raised") is None
            ),
        }
        return out
    finally:
        shutil.rmtree(root, ignore_errors=True)


results["part_a_receipt_verification"] = part_a()
results["part_b_alias_guard_probe"] = part_b()
results["part_c_redeploy_after_rollback"] = part_c()

a = results["part_a_receipt_verification"]
results["summary"] = {
    "codex_receipt_claims_confirmed": all(
        [
            a["a1_alias"]["file_id_identical"],
            a["a1_alias"]["resolve_collides"],
            a["a2_current_state"]["t1_is_baseline"],
            a["a2_current_state"]["t2_is_baseline"],
            a["a2_current_state"]["snapshot_is_baseline"],
            not a["a2_current_state"]["any_is_candidate"],
            a["a3_package"]["baseline_matches"],
            a["a3_package"]["candidate_matches"],
            a["a4_receipt_math"]["decision_hash_matches"],
            a["a4_receipt_math"]["deployment_id_matches"],
            a["a4_receipt_math"]["before_is_baseline"],
            a["a4_receipt_math"]["after_is_candidate"],
            a["a4_receipt_math"]["rollback_restored_is_baseline"],
            a["a5_budget"]["within_budget"],
        ]
    ),
    "deployments_consumed": a["a5_budget"]["consumed"],
    "currently_deployed": a["a2_current_state"]["any_is_candidate"],
}

text = json.dumps(results, ensure_ascii=False, indent=2)
Path(str(Path(__file__).with_suffix("")) + ".out.json").write_text(text + "\n", encoding="utf-8")
sys.stdout.buffer.write((text + "\n").encode("utf-8"))
