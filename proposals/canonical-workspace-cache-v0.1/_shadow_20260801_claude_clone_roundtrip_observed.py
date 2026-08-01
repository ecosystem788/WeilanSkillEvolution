"""Observe -- not predict -- what a clean clone recomputes for this line's byte bindings.

My peer-chat message of 2026-08-01T14:40:52+09:00 said the LF tree hashes 7744d858... /
efca4a1f... were arithmetic, not observation: "我没有真跑一次克隆". Codex's 14:59:05 cosign
adopted that boundary verbatim into a signed statement. This probe runs the clone.

It also corrects the root the 14:40 arithmetic was computed over. `evolution_core.tree_manifest`
(tools/evolution_core.py:56-69) skips `__pycache__`, `.pytest_cache` and every `.pyc`. The
14:40 census counted all files under the artifact directories, so its "37 CRLF / 52 LF" and
its LF-normalised hashes covered ~40 build-residue files that never enter the hash at all --
including compiled bytecode, which LF-normalising is meaningless for. This probe measures the
manifest file set, i.e. the bytes the declared addresses are actually computed from.

Arms:

  A -- real shallow clone of this repository via file:// URL with the core.longpaths recipe
  that push-third-party-reachability-v0.1 established as necessary on this host. Recompute
  the sha256 of each tracked evidence artifact as a cloner finds it, and compare against the
  digest SHADOW_RESULT.json records for it.

  B -- the frozen trees are untracked (baseline/, candidate/) or gitignored (artifacts/), so
  they cannot be cloned from here. Instead: build a scratch repository carrying this
  repository's real .gitattributes verbatim, commit both trees, clone via file:// URL, and
  run the same evolution_core.tree_hash over the cloned checkout.

  C -- census of the manifest file set: line endings, extension-to-attribute coverage, and
  whether the declared address agrees across all three independent materialisations that
  exist on this host today (the baseline/ directory, the artifacts/<hash>/ directory, and
  the live install point).

Read-only with respect to this repository and both install points: arm A clones, arm B writes
only under a scratch directory outside the repository. Nothing is deployed, no proposal or
decision field is written.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from evolution_core import tree_hash, tree_manifest  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "_shadow_20260801_claude_clone_roundtrip_observed.out.json"

DECLARED = {
    "baseline": "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad",
    "candidate": "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a",
}
PREDICTED_LF_1440 = {
    "baseline": "7744d85887d8d8f3061304ef7aeef4bfd60be367dc463a7061d6621c22630940",
    "candidate": "efca4a1f4663ef499c1d422171bd590aec0b9253df64294b7289f240b4fb45fb",
}
INSTALL_POINTS = {
    "claude": Path(r"C:\Users\zy\.claude\skills\solve-with-weilan"),
    "codex": Path(r"D:\CodexData\skills\solve-with-weilan"),
}

# Run tag keeps each invocation's scratch directories distinct: git clone refuses a
# non-empty destination, and a previous run's .git can resist rmtree while in use.
RUN_TAG = sys.argv[1] if len(sys.argv) > 1 else "r1"
SCRATCH = Path("C:/wl_eolrt")
SRC = SCRATCH / f"s{RUN_TAG}"
CLONE_A = SCRATCH / f"a{RUN_TAG}"
CLONE_B = SCRATCH / f"b{RUN_TAG}"


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


def manifest_paths(root):
    return [row["path"] for row in tree_manifest(root)]


def manifest_eol_census(root):
    root = Path(root)
    crlf, lf, none = [], 0, 0
    for rel in manifest_paths(root):
        data = (root / rel).read_bytes()
        if b"\r\n" in data:
            crlf.append(rel)
        elif b"\n" in data:
            lf += 1
        else:
            none += 1
    return {"crlf_files": crlf, "crlf_count": len(crlf), "lf_only_count": lf, "no_newline_count": none}


def wipe(path):
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def main():
    result = {
        "probe": "does a real clean clone reproduce this line's declared byte addresses",
        "authority": "read_only_measurement_only",
        "corrects": (
            "peer-chat 2026-08-01T14:40:52+09:00 -- that message's EOL census and LF hashes "
            "were computed over every file under artifacts/<hash>/, but tree_manifest skips "
            "__pycache__/.pytest_cache/*.pyc, so ~40 of the counted files never enter the hash"
        ),
        "manifest_exclusions": "__pycache__, .pytest_cache, *.pyc (tools/evolution_core.py:60)",
        "host_git_config": {},
        "arm_c_manifest_census": {},
        "arm_a_tracked_evidence": {},
        "arm_b_frozen_trees": {},
        "boundaries": [],
    }

    for key in ("core.autocrlf", "core.longpaths", "core.symlinks"):
        result["host_git_config"][key] = (
            run(["git", "config", "--get", key], cwd=REPO)["stdout"].strip() or None
        )

    # ---------------- Arm C: what the declared address is actually computed over -------
    arm_c = {"trees": {}, "materialisation_agreement": {}}
    roots = {
        "baseline": HERE / "baseline" / "solve-with-weilan",
        "candidate": HERE / "candidate" / "solve-with-weilan",
    }
    for name, root in roots.items():
        paths = manifest_paths(root)
        arm_c["trees"][name] = {
            "manifest_file_count": len(paths),
            "raw_file_count": sum(1 for p in root.rglob("*") if p.is_file()),
            "extension_histogram": dict(Counter(Path(p).suffix or "<none>" for p in paths)),
            "eol_census_over_manifest": manifest_eol_census(root),
            "tree_hash": tree_hash(root),
            "equals_declared": tree_hash(root) == DECLARED[name],
        }
    # Does the same declared address fall out of every materialisation on this host?
    arm_c["materialisation_agreement"]["baseline"] = {
        "baseline_dir": tree_hash(roots["baseline"]),
        "artifacts_dir": tree_hash(HERE / "artifacts" / DECLARED["baseline"] / "solve-with-weilan"),
        "install_claude": tree_hash(INSTALL_POINTS["claude"]),
        "install_codex": tree_hash(INSTALL_POINTS["codex"]),
    }
    arm_c["materialisation_agreement"]["candidate"] = {
        "candidate_dir": tree_hash(roots["candidate"]),
        "artifacts_dir": tree_hash(HERE / "artifacts" / DECLARED["candidate"] / "solve-with-weilan"),
    }
    for name, mapping in arm_c["materialisation_agreement"].items():
        mapping["all_equal_declared"] = all(v == DECLARED[name] for v in mapping.values())
    result["arm_c_manifest_census"] = arm_c

    # ---------------- Arm A: real shallow clone of this repository --------------------
    wipe(CLONE_A)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO)["stdout"].strip()
    url = "file:///" + str(REPO).replace("\\", "/")
    clone = run(
        ["git", "-c", "core.longpaths=true", "clone", "--depth", "1", "--branch", branch,
         url, str(CLONE_A)]
    )
    arm_a = {
        "source_head": run(["git", "rev-parse", "HEAD"], cwd=REPO)["stdout"].strip(),
        "clone_url": url,
        "clone_rc": clone["rc"],
        "clone_stderr_tail": clone["stderr"][-1200:],
        "recorded_digest_recompute": {},
    }
    rel_dir = "proposals/canonical-workspace-cache-v0.1"
    if clone["rc"] == 0:
        arm_a["clone_head"] = run(["git", "rev-parse", "HEAD"], cwd=CLONE_A)["stdout"].strip()
        arm_a["clone_index_entry_count"] = len(
            run(["git", "ls-files"], cwd=CLONE_A)["stdout"].splitlines()
        )
        # SHADOW_RESULT.json records evidence digests inside its `checks` rows.
        doc = json.loads((HERE / "SHADOW_RESULT.json").read_text(encoding="utf-8"))
        recorded = {}

        def harvest(node):
            if isinstance(node, dict):
                name = node.get("ref") or node.get("evidence_file") or node.get("path")
                digest = node.get("sha256") or node.get("file_sha256")
                if isinstance(name, str) and isinstance(digest, str) and len(digest) == 64:
                    recorded[Path(name).name] = digest
                for value in node.values():
                    harvest(value)
            elif isinstance(node, list):
                for value in node:
                    harvest(value)

        harvest(doc)
        for fname, digest in sorted(recorded.items()):
            worktree = HERE / fname
            cloned = CLONE_A / rel_dir / fname
            row = {
                "recorded_sha256": digest,
                "tracked_in_source": run(
                    ["git", "ls-files", "--error-unmatch", "--", f"{rel_dir}/{fname}"], cwd=REPO
                )["rc"] == 0,
                "present_in_clone": cloned.is_file(),
            }
            if worktree.is_file():
                data = worktree.read_bytes()
                row["worktree_sha256"] = sha(data)
                row["worktree_matches_record"] = row["worktree_sha256"] == digest
                row["worktree_has_crlf"] = b"\r\n" in data
            if cloned.is_file():
                cdata = cloned.read_bytes()
                row["clone_sha256"] = sha(cdata)
                row["clone_has_crlf"] = b"\r\n" in cdata
                row["recomputes_in_clone"] = row["clone_sha256"] == digest
            arm_a["recorded_digest_recompute"][fname] = row
        rows = arm_a["recorded_digest_recompute"].values()
        arm_a["summary"] = {
            "recorded_evidence_count": len(rows),
            "matches_in_worktree": sum(1 for r in rows if r.get("worktree_matches_record")),
            "present_in_clone": sum(1 for r in rows if r.get("present_in_clone")),
            "recomputes_in_clone": sum(1 for r in rows if r.get("recomputes_in_clone")),
        }
    result["arm_a_tracked_evidence"] = arm_a

    # ---------------- Arm B: scratch round trip of the frozen trees --------------------
    wipe(SRC)
    wipe(CLONE_B)
    SRC.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / ".gitattributes", SRC / ".gitattributes")
    for name, root in roots.items():
        shutil.copytree(root, SRC / name, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    arm_b = {
        "gitattributes_sha256": sha((REPO / ".gitattributes").read_bytes()),
        "pre_commit_scratch_worktree": {
            name: {
                "tree_hash": tree_hash(SRC / name),
                "equals_declared": tree_hash(SRC / name) == DECLARED[name],
            }
            for name in roots
        },
        "steps": [],
        "post_clone": {},
    }
    for args in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "probe@local"],
        ["git", "config", "user.name", "probe"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "frozen trees for round trip observation"],
    ):
        step = run(args, cwd=SRC)
        arm_b["steps"].append({"argv": args, "rc": step["rc"], "stderr": step["stderr"][-400:]})

    # Ask git, in the evaluating environment, for the attributes it will actually apply.
    probe_paths = sorted({f"baseline/{p}" for p in manifest_paths(roots["baseline"])})
    attrs = run(["git", "check-attr", "text", "eol", "--"] + probe_paths, cwd=SRC)["stdout"]
    eol_by_path = {}
    for line in attrs.splitlines():
        if ": eol: " in line:
            path, _, value = line.rpartition(": eol: ")
            eol_by_path[path.rsplit(": ", 1)[0] if path.endswith(":") else path] = value
    arm_b["effective_eol_attr_histogram"] = dict(Counter(eol_by_path.values()))
    arm_b["paths_without_explicit_eol_lf"] = sorted(
        p for p, v in eol_by_path.items() if v != "lf"
    )
    arm_b["scratch_effective_autocrlf"] = (
        run(["git", "config", "--get", "core.autocrlf"], cwd=SRC)["stdout"].strip() or None
    )

    src_url = "file:///" + str(SRC).replace("\\", "/")
    cl = run(["git", "clone", "-q", src_url, str(CLONE_B)])
    arm_b["clone_rc"] = cl["rc"]
    arm_b["clone_stderr_tail"] = cl["stderr"][-800:]
    if cl["rc"] == 0:
        for name in roots:
            observed = tree_hash(CLONE_B / name)
            arm_b["post_clone"][name] = {
                "observed_tree_hash": observed,
                "equals_declared_address": observed == DECLARED[name],
                "equals_1440_lf_prediction": observed == PREDICTED_LF_1440[name],
                "declared_address": DECLARED[name],
                "prediction_made_at_1440": PREDICTED_LF_1440[name],
                "eol_census_over_manifest": manifest_eol_census(CLONE_B / name),
                "manifest_file_count": len(manifest_paths(CLONE_B / name)),
            }
    result["arm_b_frozen_trees"] = arm_b

    result["boundaries"] = [
        "Arm B places the trees at the scratch repository root rather than under "
        "proposals/canonical-workspace-cache-v0.1/. The effective attributes git applied are "
        "recorded above from check-attr in that environment, not assumed from the file text.",
        "Arm A observes one clone on this host with this host's global git config. It does not "
        "establish what another host computes.",
        "A digest that recomputes after a clone shows the bytes are reachable and recomputable. "
        "It does not show they are the bytes the measurement actually ran against; nothing binds "
        "an archived .out.json to the process that produced it.",
        "Arm A is --depth 1. History reachability is untested and not claimed.",
        "artifacts/ is gitignored and baseline/ and candidate/ are untracked as of this run, so "
        "arm B measures what a round trip would do to these bytes, not a round trip that has "
        "happened.",
    ]

    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "out": str(OUT),
        "arm_c_declared_reproduced_from_every_materialisation": {
            k: v["all_equal_declared"] for k, v in arm_c["materialisation_agreement"].items()
        },
        "arm_c_crlf_in_manifest": {
            k: v["eol_census_over_manifest"]["crlf_count"] for k, v in arm_c["trees"].items()
        },
        "arm_a": arm_a.get("summary"),
        "arm_b_clone_rc": arm_b.get("clone_rc"),
        "arm_b_eol_attr_histogram": arm_b.get("effective_eol_attr_histogram"),
        "arm_b_post_clone": {
            k: {
                "observed": v["observed_tree_hash"],
                "eq_declared": v["equals_declared_address"],
                "eq_1440_prediction": v["equals_1440_lf_prediction"],
            }
            for k, v in arm_b.get("post_clone", {}).items()
        },
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
