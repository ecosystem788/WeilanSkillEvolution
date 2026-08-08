"""Read-only: where do the bytes of the co-signed final c485e953... live today?

Re-verifies the central STRANDED@base example of
proposals/cosign-durability-gap-v0.1/FINDING.md:30-45 at 2026-08-06.

At FINDING time (~07-29): worktree bytes == signed final; HEAD held the signed base.
This probe asks whether that is still true, or whether the worktree has drifted
past the signed final (in which case the signed final is in NO location).

Writes only its own .out.json. Re-run: python _probe_20260806_stranded_final_recheck.py
"""
import hashlib
import json
import os
import subprocess

REPO = r"D:\WeilanSkillEvolution"
TARGET = "proposals/bounded-scheduler-v0.1/impl/run_wake_cron.ps1"
SIGNED_FINAL = "c485e953814a43ec7894afbacdf1de9f084f780d938adc89417245c4b60fc49d"
SIGNED_BASE_PREFIX = "eb552cc6"


def git_bytes(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    return p.returncode, p.stdout, p.stderr.decode("utf-8", "replace")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    res = {"target": TARGET, "signed_final": SIGNED_FINAL}

    # 1. worktree raw bytes (no EOL translation)
    full = os.path.join(REPO, TARGET.replace("/", os.sep))
    with open(full, "rb") as f:
        wt = f.read()
    res["worktree"] = {"sha256": sha(wt), "bytes": len(wt),
                       "equals_signed_final": sha(wt) == SIGNED_FINAL}

    # 2. HEAD blob raw bytes
    rc, head_b, err = git_bytes("show", f"HEAD:{TARGET}")
    res["head_blob"] = {
        "rc": rc,
        "sha256": sha(head_b) if rc == 0 else None,
        "bytes": len(head_b) if rc == 0 else None,
        "equals_signed_final": (sha(head_b) == SIGNED_FINAL) if rc == 0 else None,
        "stderr": err.strip() or None,
    }

    # 3. Does the signed final exist in ANY version of this path in history?
    #    Walk every commit that touched it, hash each blob.
    rc, out, _ = git_bytes("rev-list", "--all", "--", TARGET)
    commits = out.decode("utf-8", "replace").split()
    hits = []
    seen = {}
    for c in commits:
        rc2, blob, _ = git_bytes("show", f"{c}:{TARGET}")
        if rc2 != 0:
            continue
        h = sha(blob)
        seen[h] = seen.get(h, 0) + 1
        if h == SIGNED_FINAL:
            hits.append(c)
    res["history_scan"] = {
        "commits_touching_path": len(commits),
        "distinct_blob_sha256_count": len(seen),
        "commits_whose_blob_equals_signed_final": hits,
        "signed_final_ever_committed_on_this_path": bool(hits),
    }

    # 4. Is a loose/packed object with those bytes reachable anywhere at all?
    #    (git object ids are sha1 of a header+content, not sha256 of content,
    #     so we cannot look it up directly -- record that limitation honestly.)
    res["limitation"] = (
        "git object ids are sha1(header+content); the signed final is a sha256 of "
        "raw content, so no direct object-db lookup is possible. history_scan "
        "covers every committed version of THIS path only -- the bytes could in "
        "principle exist under a different path."
    )

    # 5. verdict
    wt_is_final = res["worktree"]["equals_signed_final"]
    head_is_final = res["head_blob"]["equals_signed_final"]
    committed = res["history_scan"]["signed_final_ever_committed_on_this_path"]
    if head_is_final or committed:
        verdict = "REPAIRED_signed_final_reached_git"
    elif wt_is_final:
        verdict = "STILL_STRANDED_worktree_only"
    else:
        verdict = "DRIFTED_signed_final_in_no_location_on_this_path"
    res["verdict"] = verdict

    outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_probe_20260806_stranded_final_recheck.out.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("wrote", outp)


if __name__ == "__main__":
    main()
