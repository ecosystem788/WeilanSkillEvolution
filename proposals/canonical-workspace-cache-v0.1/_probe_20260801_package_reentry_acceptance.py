"""Read-only acceptance for the package re-entry commit.

Answers, from a real clone rather than from the working copy:
  1. are baseline/, candidate/, proposal.json reachable at the named commit
  2. does a clean clone of that commit check out with an empty status
  3. do the two frozen trees, recomputed from the CLONE, equal the declared
     addresses ae0537da... / 8602bb0f...
  4. does proposal-validate pass against the cloned package
  5. for every evidence file SHADOW_RESULT.json cites by sha256: does the
     recorded digest match the clone bytes, or only the LF-normalised bytes

Writes only under a scratch root. Never touches the live repo, the ledgers or
either install point.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
PKG = "proposals/canonical-workspace-cache-v0.1"
SCRATCH = r"C:\wl_reentry"
DECLARED = {
    "baseline": "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad",
    "candidate": "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a",
}


def run(args, cwd):
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "rc": p.returncode,
        "out": p.stdout.decode("utf-8", "replace"),
        "err": p.stderr.decode("utf-8", "replace"),
    }


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def main():
    commit = run(["git", "rev-parse", "HEAD"], REPO)["out"].strip()
    out = {"named_commit": commit, "package": PKG}

    # 1. reachability at the named commit -- index-independent
    ls = run(["git", "ls-tree", "-r", "--name-only", commit, "--", PKG], REPO)
    paths = [p for p in ls["out"].splitlines() if p]
    out["ls_tree"] = {
        "rc": ls["rc"],
        "package_path_count": len(paths),
        "baseline_tree_files": len([p for p in paths if p.startswith(PKG + "/baseline/")]),
        "candidate_tree_files": len([p for p in paths if p.startswith(PKG + "/candidate/")]),
        "proposal_json_reachable": (PKG + "/proposal.json") in paths,
        "shadow_result_reachable": (PKG + "/SHADOW_RESULT.json") in paths,
        "artifacts_in_tree": len([p for p in paths if p.startswith(PKG + "/artifacts/")]),
    }

    # 2. a real clone of that commit
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(SCRATCH, exist_ok=True)
    clone = os.path.join(SCRATCH, "clone")
    url = "file:///" + REPO.replace("\\", "/")
    c = run(["git", "-c", "core.longpaths=true", "clone", "--no-local", "-q", url, clone], SCRATCH)
    out["clone"] = {"rc": c["rc"], "stderr_tail": c["err"][-400:]}
    if c["rc"] != 0:
        out["verdict"] = "clone_failed"
        emit(out)
        return 1
    co = run(["git", "-c", "core.longpaths=true", "checkout", "-q", commit], clone)
    st = run(["git", "status", "--porcelain"], clone)
    out["clone"]["checkout_rc"] = co["rc"]
    out["clone"]["status_empty"] = (st["out"].strip() == "")
    out["clone"]["status_tail"] = st["out"][-400:]
    if co["rc"] != 0 or not out["clone"]["status_empty"]:
        out["verdict"] = "clone_not_faithful"
        emit(out)
        return 1

    # 3. recompute both frozen tree addresses FROM THE CLONE
    sys.path.insert(0, os.path.join(REPO, "tools"))
    import evolution_core

    out["recomputed_from_clone"] = {}
    ok_addr = True
    for arm, declared in DECLARED.items():
        root = os.path.join(clone, PKG.replace("/", os.sep), arm, "solve-with-weilan")
        exists = os.path.isdir(root)
        h = evolution_core.tree_hash(root) if exists else None
        n = len(evolution_core.tree_manifest(root)) if exists else 0
        ok_addr = ok_addr and (h == declared)
        out["recomputed_from_clone"][arm] = {
            "exists": exists,
            "manifest_file_count": n,
            "tree_hash": h,
            "declared": declared,
            "equals_declared_address": h == declared,
        }
    out["both_addresses_reproduce_from_clone"] = ok_addr

    # 4. proposal-validate against the cloned package
    pv = run(
        [sys.executable, os.path.join(REPO, "tools", "evolution_cli.py"),
         "proposal-validate", "--proposal",
         os.path.join(clone, PKG.replace("/", os.sep), "proposal.json")],
        clone,
    )
    try:
        pv_json = json.loads(pv["out"])
    except Exception:
        pv_json = {"unparsed": pv["out"][-400:], "stderr": pv["err"][-400:]}
    out["proposal_validate_from_clone"] = {"rc": pv["rc"], "result": pv_json}

    # 5. cited-evidence digest domain: recorded digest vs clone bytes
    shadow_path = os.path.join(clone, PKG.replace("/", os.sep), "SHADOW_RESULT.json")
    with open(shadow_path, "rb") as fh:
        shadow = json.loads(fh.read().decode("utf-8-sig"))
    rows = []
    for check in shadow.get("checks", []):
        for ev in check.get("evidence", []) or []:
            ref, recorded = ev.get("ref"), ev.get("sha256")
            if not ref or not recorded:
                continue
            cloned = os.path.join(clone, ref.replace("/", os.sep))
            live = os.path.join(REPO, ref.replace("/", os.sep))
            row = {"ref": ref, "recorded_sha256": recorded,
                   "present_in_clone": os.path.isfile(cloned)}
            if row["present_in_clone"]:
                b = open(cloned, "rb").read()
                row["clone_bytes_sha256"] = sha256_bytes(b)
                row["clone_bytes_match_recorded"] = row["clone_bytes_sha256"] == recorded
                row["clone_has_crlf"] = b.count(b"\r\n") > 0
            if os.path.isfile(live):
                lb = open(live, "rb").read()
                row["live_disk_sha256"] = sha256_bytes(lb)
                row["live_disk_match_recorded"] = row["live_disk_sha256"] == recorded
                row["live_lf_normalised_sha256"] = sha256_bytes(lb.replace(b"\r\n", b"\n"))
                row["recorded_domain"] = (
                    "clone_and_disk_agree" if row.get("clone_bytes_match_recorded") and row.get("live_disk_match_recorded")
                    else "worktree_crlf_only" if row.get("live_disk_match_recorded")
                    else "clone_lf_only" if row.get("clone_bytes_match_recorded")
                    else "neither"
                )
            rows.append(row)
    out["cited_evidence"] = {
        "total": len(rows),
        "present_in_clone": sum(1 for r in rows if r.get("present_in_clone")),
        "recomputable_from_clone": sum(1 for r in rows if r.get("clone_bytes_match_recorded")),
        "recorded_in_worktree_crlf_domain_only": sum(
            1 for r in rows if r.get("recorded_domain") == "worktree_crlf_only"),
        "rows": rows,
    }

    out["verdict"] = "trees_reachable_and_addresses_reproduce" if ok_addr else "addresses_do_not_reproduce"
    out["boundary"] = (
        "This measures reachability and address reproduction from a clone. It does "
        "not adopt, does not deploy, does not re-record any digest, and does not "
        "show that the archived measurements consumed these exact bytes."
    )
    emit(out)
    return 0


def emit(out):
    dst = os.path.join(REPO, PKG.replace("/", os.sep),
                       "_probe_20260801_package_reentry_acceptance.out.json")
    with open(dst, "wb") as fh:
        fh.write(json.dumps(out, indent=2, sort_keys=True).encode("utf-8"))
    sys.stdout.write(json.dumps(
        {k: v for k, v in out.items() if k != "cited_evidence"}, indent=2)[:2000] + "\n")


if __name__ == "__main__":
    sys.exit(main())
