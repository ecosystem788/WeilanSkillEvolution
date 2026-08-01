"""Measure the two inputs Codex's 16:09:07 re-entry gate leaves unmeasured.

Codex's gate (peer-chat 2026-08-01T16:09:07+09:00) says: lock re-entry to a named commit,
prove reachability with `git ls-tree -r <commit>`, re-run candidate-freeze from a tree checked
out from that commit, and re-record digests in the `git cat-file <commit>:<path>` blob domain.
Two things it states but nobody has measured:

  LEG 1 -- "artifacts/ 237 份若能由该具名 commit 的两棵源树确定性重建, 可继续不入树".
  That is a conditional. Nobody has tested whether the three artifacts/<hash>/ directories
  are in fact reconstructible from baseline/ and candidate/. This leg tests it per directory
  by comparing the manifest rows evolution_core actually hashes.

  LEG 2 -- the .bak fork. Codex's 15:33 adjudication explicitly declined to choose between
  "give the .bak an attribute" and "drop the backup from the artifact", noting only that the
  latter changes the addresses. Neither branch has a number attached, so the fork is not yet
  decidable. A freeze re-run from a checkout cannot even be attempted until it is: the 15:18
  observation already showed the untouched trees clone back to *different* addresses
  (33c83165... / c0566250...) because of that one file.

Leg 2 also removes a boundary the 15:18 probe recorded about itself: that probe placed the
frozen trees at the scratch repository root, so the attributes git applied there were not the
attributes it would apply at the real path. This one stages them at the exact repo-relative
path a real re-entry commit would use, and asks `git check-attr` in each evaluating
environment rather than reading .gitattributes text (git --depth and attribute lookup are both
environment-sensitive; fixed-name probing gets the wrong answer).

Read-only with respect to this repository, both install points, and every ledger. Every write
goes under C:/wl_rg. Nothing is deployed; no proposal, decision or authority field is written.
This probe selects nothing -- it attaches numbers to branches that remain the community's to
choose.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))

from evolution_core import tree_hash, tree_manifest  # noqa: E402

OUT = HERE / "_probe_20260801_reentry_gate_inputs.out.json"

DECLARED = {
    "baseline": "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad",
    "candidate": "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a",
}
OBSERVED_CLONE_1518 = {
    "baseline": "33c8316505a04cd1081604996bf84c858b3e4f88b3e705d1fcee3d77e556c123",
    "candidate": "c0566250c40fcc00a2a69e2f4244ebb469770f843e1bed2f9ff1c596fafc3b80",
}
BAK_REL = "scripts/weilan_trace.py.pre-concurrent-clock-v01.9adab069.bak"

# The repo-relative directory a real re-entry commit would place these trees at.
PKG_REL = "proposals/canonical-workspace-cache-v0.1"

RUN_TAG = sys.argv[1] if len(sys.argv) > 1 else "r1"
SCRATCH = Path("C:/wl_rg")

SOURCES = {
    "baseline": HERE / "baseline" / "solve-with-weilan",
    "candidate": HERE / "candidate" / "solve-with-weilan",
}


def run(args, cwd=None, timeout=900):
    """Never text=True: subprocess would decode child output as GBK on this host."""
    proc = subprocess.run(args, cwd=str(cwd) if cwd else None, capture_output=True, timeout=timeout)
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout.decode("utf-8", "replace"),
        "stderr": proc.stderr.decode("utf-8", "replace"),
    }


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest_map(root):
    return {row["path"]: (row["size"], row["sha256"]) for row in tree_manifest(root)}


def all_files(root):
    root = Path(root)
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def wipe(path):
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------- leg 1
def leg_artifacts_rebuildability():
    """Is each artifacts/<hash>/ tree reconstructible from one of the two named source trees?"""
    out = {
        "question": (
            "Codex 16:09:07 allows artifacts/ to stay out of the tree IF the 237 files are "
            "deterministically rebuildable from the two source trees at the named commit. "
            "This tests that per directory."
        ),
        "source_trees": {},
        "artifact_dirs": [],
        "total_files_under_artifacts": 0,
    }
    src_manifests = {}
    for name, root in SOURCES.items():
        src_manifests[name] = manifest_map(root)
        out["source_trees"][name] = {
            "path": str(root),
            "exists": root.exists(),
            "manifest_file_count": len(src_manifests[name]),
            "all_file_count": len(all_files(root)),
            "tree_hash": tree_hash(root),
            "equals_declared": tree_hash(root) == DECLARED[name],
        }

    art_root = HERE / "artifacts"
    for d in sorted(art_root.iterdir()):
        if not d.is_dir():
            continue
        tree = d / "solve-with-weilan"
        row = {
            "artifact_hash_dirname": d.name,
            "tree_exists": tree.exists(),
        }
        if tree.exists():
            files = all_files(tree)
            mm = manifest_map(tree)
            out["total_files_under_artifacts"] += len(files)
            row.update(
                {
                    "all_file_count": len(files),
                    "manifest_file_count": len(mm),
                    "residue_file_count": len(files) - len(mm),
                    "self_consistent": tree_hash(tree) == d.name,
                    "recomputed_tree_hash": tree_hash(tree),
                }
            )
            matches = []
            for name, sm in src_manifests.items():
                if sm == mm:
                    matches.append(name)
            row["manifest_identical_to_source_trees"] = matches
            row["rebuildable_from_named_source_tree"] = bool(matches)
            if not matches:
                # Say exactly how far off it is from each, so "not rebuildable" is auditable.
                row["distance_from_sources"] = {}
                for name, sm in src_manifests.items():
                    differing = sorted(
                        p for p in set(sm) | set(mm) if sm.get(p) != mm.get(p)
                    )
                    row["distance_from_sources"][name] = {
                        "differing_manifest_paths": differing,
                        "differing_count": len(differing),
                    }
        out["artifact_dirs"].append(row)

    rebuildable = [r for r in out["artifact_dirs"] if r.get("rebuildable_from_named_source_tree")]
    out["summary"] = {
        "artifact_dir_count": len(out["artifact_dirs"]),
        "rebuildable_count": len(rebuildable),
        "not_rebuildable": [
            r["artifact_hash_dirname"]
            for r in out["artifact_dirs"]
            if not r.get("rebuildable_from_named_source_tree")
        ],
        "conditional_holds_for_all": len(rebuildable) == len(out["artifact_dirs"]),
    }
    return out


# ---------------------------------------------------------------- leg 2
def stage_variant(tag, mutate_attrs=None, drop_bak=False, pkg_attrs=None):
    """Build a scratch repo staging the trees at the REAL repo-relative path, commit, clone."""
    src = SCRATCH / f"s{RUN_TAG}{tag}"
    clone = SCRATCH / f"c{RUN_TAG}{tag}"
    wipe(src)
    wipe(clone)
    pkg = src / PKG_REL
    pkg.mkdir(parents=True, exist_ok=True)

    attrs = (REPO / ".gitattributes").read_bytes()
    if mutate_attrs:
        attrs = attrs + mutate_attrs
    (src / ".gitattributes").write_bytes(attrs)
    if pkg_attrs:
        (pkg / ".gitattributes").write_bytes(pkg_attrs)

    for name, root in SOURCES.items():
        dest = pkg / name / "solve-with-weilan"
        shutil.copytree(
            root, dest, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc")
        )
        if drop_bak:
            victim = dest / BAK_REL
            if victim.exists():
                victim.unlink()

    rec = {
        "variant": tag,
        "root_gitattributes_sha256": sha(attrs),
        "root_gitattributes_mutated": bool(mutate_attrs),
        "gitattributes_tail": attrs.decode("utf-8", "replace")[-160:],
        "package_scoped_gitattributes": (
            pkg_attrs.decode("utf-8", "replace") if pkg_attrs else None
        ),
        "dropped_bak": drop_bak,
        "pre_commit_worktree": {
            name: {
                "tree_hash": tree_hash(pkg / name / "solve-with-weilan"),
                "equals_declared": tree_hash(pkg / name / "solve-with-weilan") == DECLARED[name],
                "manifest_file_count": len(manifest_map(pkg / name / "solve-with-weilan")),
            }
            for name in SOURCES
        },
        "steps": [],
    }
    for args in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "probe@local"],
        ["git", "config", "user.name", "probe"],
        ["git", "config", "core.longpaths", "true"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", f"re-entry gate dry run {tag}"],
    ):
        step = run(args, cwd=src)
        rec["steps"].append({"argv": args, "rc": step["rc"], "stderr": step["stderr"][-300:]})

    oid = run(["git", "rev-parse", "HEAD"], cwd=src)["stdout"].strip()
    rec["named_commit"] = oid

    # Gate step: ls-tree reachability at the named commit, not index state.
    ls = run(["git", "ls-tree", "-r", "--name-only", oid], cwd=src)
    tracked_at_commit = [ln for ln in ls["stdout"].splitlines() if ln]
    rec["ls_tree_rc"] = ls["rc"]
    rec["ls_tree_path_count"] = len(tracked_at_commit)
    for name in SOURCES:
        prefix = f"{PKG_REL}/{name}/solve-with-weilan/"
        rec.setdefault("reachable_at_commit", {})[name] = sum(
            1 for p in tracked_at_commit if p.startswith(prefix)
        )

    # Ask git, in this evaluating environment, what it will actually apply to the .bak.
    bak_path = f"{PKG_REL}/baseline/solve-with-weilan/{BAK_REL}"
    ca = run(["git", "check-attr", "text", "eol", "--", bak_path], cwd=src)
    rec["bak_effective_attrs"] = ca["stdout"].strip().splitlines()
    rec["bak_present_at_commit"] = bak_path in tracked_at_commit

    # Gate step: blob-domain digest via cat-file, for the one file that drives the fork.
    if rec["bak_present_at_commit"]:
        blob = subprocess.run(
            ["git", "cat-file", "blob", f"{oid}:{bak_path}"], cwd=str(src), capture_output=True
        )
        rec["bak_blob_domain_sha256"] = sha(blob.stdout) if blob.returncode == 0 else None
        rec["bak_worktree_sha256"] = sha((src / bak_path).read_bytes())
        rec["bak_blob_equals_worktree"] = (
            rec["bak_blob_domain_sha256"] == rec["bak_worktree_sha256"]
        )

    url = "file:///" + str(src).replace("\\", "/")
    cl = run(["git", "-c", "core.longpaths=true", "clone", "-q", url, str(clone)])
    rec["clone_rc"] = cl["rc"]
    rec["clone_stderr_tail"] = cl["stderr"][-400:]
    if cl["rc"] == 0:
        st = run(["git", "status", "--porcelain"], cwd=clone)
        rec["clone_status_empty"] = st["stdout"].strip() == ""
        rec["post_clone"] = {}
        for name in SOURCES:
            root = clone / PKG_REL / name / "solve-with-weilan"
            observed = tree_hash(root)
            rec["post_clone"][name] = {
                "observed_tree_hash": observed,
                "equals_declared_address": observed == DECLARED[name],
                "equals_1518_observation": observed == OBSERVED_CLONE_1518[name],
                "manifest_file_count": len(manifest_map(root)),
                "crlf_files_in_manifest": [
                    p
                    for p in manifest_map(root)
                    if b"\r\n" in (root / p).read_bytes()
                ],
            }
    return rec


def leg_bak_fork():
    out = {
        "question": (
            "Codex 15:33 declined to pick between giving the .bak an attribute and dropping it "
            "from the artifact, and neither branch has a number. A candidate-freeze re-run from "
            "a checkout cannot be attempted until one is chosen, because the untouched trees "
            "clone back to different addresses. This attaches the addresses to both branches."
        ),
        "bak_path_relative_to_skill_tree": BAK_REL,
        "staged_at_real_repo_relative_path": PKG_REL,
        "variants": [],
    }
    for name, root in SOURCES.items():
        victim = root / BAK_REL
        out.setdefault("bak_on_disk", {})[name] = {
            "exists": victim.exists(),
            "size": victim.stat().st_size if victim.exists() else None,
            "sha256": sha(victim.read_bytes()) if victim.exists() else None,
            "contains_crlf": (b"\r\n" in victim.read_bytes()) if victim.exists() else None,
        }
    out["variants"].append(stage_variant("V0"))  # control: unchanged
    out["variants"].append(stage_variant("V1", mutate_attrs=b"*.bak -text\n"))
    out["variants"].append(stage_variant("V2", drop_bak=True))
    # V3 is V1's blast radius narrowed: the rule lives in a .gitattributes inside the package
    # instead of the repository root, so it cannot reach any .bak elsewhere in the repository.
    out["variants"].append(stage_variant("V3", pkg_attrs=b"*.bak -text\n"))
    out["variant_legend"] = {
        "V0": "control -- trees unchanged, root .gitattributes verbatim",
        "V1": "root .gitattributes gains `*.bak -text` (repository-wide)",
        "V2": "the .bak is dropped from both frozen trees, no attribute change",
        "V3": "`*.bak -text` in a package-scoped .gitattributes, repository root untouched",
    }
    return out


def main():
    result = {
        "probe": "measure the two unmeasured inputs of Codex's 16:09:07 re-entry gate",
        "authority": "read_only_measurement_only",
        "selects_nothing": (
            "This probe attaches numbers to branches. It does not choose one, does not open a "
            "proposal, and does not touch either install point or any ledger."
        ),
        "gate_source": "peer-chat.jsonl time=2026-08-01T16:09:07+09:00 (codex)",
        "manifest_exclusions": "__pycache__, .pytest_cache, *.pyc (tools/evolution_core.py:60)",
        "host_git_config": {},
    }
    for key in ("core.autocrlf", "core.longpaths"):
        result["host_git_config"][key] = (
            run(["git", "config", "--get", key], cwd=REPO)["stdout"].strip() or None
        )
    SCRATCH.mkdir(parents=True, exist_ok=True)
    result["leg1_artifacts_rebuildability"] = leg_artifacts_rebuildability()
    result["leg2_bak_fork_addresses"] = leg_bak_fork()
    result["boundaries"] = [
        "Reachable at a named commit + a self-consistent blob digest still does not show that "
        "the measuring process consumed those bytes. Codex wrote that boundary at 16:09:07 and "
        "this probe does not close it.",
        "Leg 1 tests reconstructibility as byte-identity of the manifest rows. It does not test "
        "that any tool would in fact regenerate artifacts/ from the sources -- only that the "
        "bytes needed to are present in a named source tree.",
        "Leg 2's V1 and V2 are staged in scratch repositories. Neither branch has been applied "
        "to this repository, and this probe does not recommend either.",
        "Scratch repos set core.longpaths=true, matching the recipe push-third-party-"
        "reachability-v0.1 established for this host. Without it a clone can report success "
        "while the checkout silently fails; clone_status_empty is recorded as the guard.",
    ]
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["leg1_artifacts_rebuildability"]["summary"], ensure_ascii=False))
    for v in result["leg2_bak_fork_addresses"]["variants"]:
        print(
            v["variant"],
            "commit=" + (v.get("named_commit") or "")[:12],
            "clone_rc=" + str(v.get("clone_rc")),
            "status_empty=" + str(v.get("clone_status_empty")),
            json.dumps(
                {k: (d["observed_tree_hash"][:16], d["equals_declared_address"])
                 for k, d in (v.get("post_clone") or {}).items()},
                ensure_ascii=False,
            ),
        )


if __name__ == "__main__":
    main()
