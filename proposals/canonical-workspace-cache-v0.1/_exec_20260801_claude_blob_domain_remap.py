"""Executor-side independent recomputation for the cosigned digest remap.

Read-only with respect to the repository: it never writes into the worktree.
It recomputes, from Git object bytes at two named commits, the sha256 of every
file cited by SHADOW_RESULT.json's checks[].evidence[], and reports whether the
recorded digests match the worktree bytes, the blob bytes, or neither.

It writes exactly one file, its own <same-name>.out.json, in UTF-8 without BOM
(shell redirection on this host prepends a BOM, which would make the artifact
unreadable to json.load).

Usage:  python _exec_20260801_claude_blob_domain_remap.py
"""
import hashlib
import io
import json
import os
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
SR = os.path.join(REPO, "proposals", "canonical-workspace-cache-v0.1", "SHADOW_RESULT.json")
COMMITS = ["e516aca", "HEAD"]


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)


def blob_bytes(commit, path):
    r = git("show", "%s:%s" % (commit, path))
    if r.returncode != 0:
        return None
    return r.stdout


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def main():
    doc = json.load(io.open(SR, encoding="utf-8"))
    occurrences = []
    for ci, check in enumerate(doc.get("checks", [])):
        for ei, ev in enumerate(check.get("evidence", [])):
            if isinstance(ev, dict) and "sha256" in ev:
                occurrences.append(
                    {
                        "check_index": ci,
                        "evidence_index": ei,
                        "path": ev.get("ref"),
                        "recorded_sha256": ev["sha256"],
                    }
                )

    head_oid = git("rev-parse", "HEAD").stdout.decode("ascii").strip()
    paths = sorted({o["path"] for o in occurrences})
    per_file = {}
    for p in paths:
        entry = {"path": p, "blob_sha256_by_commit": {}, "worktree_sha256": None}
        for c in COMMITS:
            b = blob_bytes(c, p)
            entry["blob_sha256_by_commit"][c] = None if b is None else sha256_bytes(b)
        disk = os.path.join(REPO, p.replace("/", os.sep))
        if os.path.exists(disk):
            with open(disk, "rb") as fh:
                entry["worktree_sha256"] = sha256_bytes(fh.read())
        vals = [v for v in entry["blob_sha256_by_commit"].values() if v]
        entry["blob_stable_across_commits"] = len(set(vals)) == 1 and len(vals) == len(COMMITS)
        entry["blob_sha256"] = vals[0] if entry["blob_stable_across_commits"] else None
        per_file[p] = entry

    for o in occurrences:
        f = per_file[o["path"]]
        o["blob_sha256"] = f["blob_sha256"]
        o["worktree_sha256"] = f["worktree_sha256"]
        o["recorded_equals_blob"] = o["recorded_sha256"] == f["blob_sha256"]
        o["recorded_equals_worktree"] = o["recorded_sha256"] == f["worktree_sha256"]

    out = {
        "probe": "_exec_20260801_claude_blob_domain_remap",
        "repo": REPO,
        "head_oid": head_oid,
        "commits_compared": COMMITS,
        "occurrence_count": len(occurrences),
        "unique_file_count": len(paths),
        "recorded_equals_blob_count": sum(1 for o in occurrences if o["recorded_equals_blob"]),
        "recorded_equals_worktree_count": sum(1 for o in occurrences if o["recorded_equals_worktree"]),
        "blob_stable_across_commits_count": sum(1 for p in paths if per_file[p]["blob_stable_across_commits"]),
        "proposed_mapping": {p: per_file[p]["blob_sha256"] for p in paths},
        "per_file": [per_file[p] for p in paths],
        "occurrences": occurrences,
        "boundary": "blob recomputability is not evidence that the measuring process consumed these bytes",
    }
    text = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    dest = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    sys.stdout.write(dest + "\n")


if __name__ == "__main__":
    main()
