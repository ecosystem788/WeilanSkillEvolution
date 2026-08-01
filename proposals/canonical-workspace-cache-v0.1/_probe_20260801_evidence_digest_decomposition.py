"""Read-only probe: decompose "a third party cannot recompute the recorded digest of
SHADOW_RESULT.json's evidence" into its distinguishable causes, per evidence file.

For each distinct evidence ref, four byte domains are hashed independently:
  worktree      - bytes on disk right now in D:\\WeilanSkillEvolution
  worktree_lf   - the same bytes with CRLF collapsed to LF
  head_blob     - bytes of the blob at the current branch HEAD (git cat-file blob)
  clone_ckout   - bytes of the file as checked out by a fresh clone of that same HEAD
and compared against the sha256 written into SHADOW_RESULT.json.

Three causes present identically as "the recorded digest does not recompute", and only
the extra domains tell them apart:
  A. not tracked at HEAD                     -> a clone cannot obtain the file at all
  B. tracked content differs from HEAD       -> digest recorded over uncommitted content
  D. content is committed and identical, but the digest was taken over the CRLF
     worktree bytes while the archived byte domain is LF (worktree_lf == head_blob)
  C. clone checkout bytes != HEAD blob bytes -> genuine clone-fidelity problem

Two measurement traps this probe is built to avoid, both previously observed here:
  - `git diff HEAD` reports CLEAN for a CRLF worktree file against an LF blob when the
    path has `text` set, because the comparison normalizes. Cleanliness therefore does
    NOT imply byte identity, and cannot be used to rule out cause D.
  - a whole-repo clone of this repository fails checkout with "Filename too long"
    unless core.longpaths is set on the clone, which silently voids the clone leg.
    --depth is also ignored for local-path clones, hence the file:// URL.

Writes a same-named .out.json. Mutates nothing in the repo; the clone goes to a temp
directory and is removed.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = r"D:\WeilanSkillEvolution"
SHADOW = os.path.join(
    REPO, "proposals", "canonical-workspace-cache-v0.1", "SHADOW_RESULT.json"
)
OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"


def run(args, cwd=REPO, binary=False):
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = p.stdout if binary else p.stdout.decode("utf-8", "replace").strip()
    return out, p.returncode, p.stderr.decode("utf-8", "replace").strip()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_bytes(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def main():
    with open(SHADOW, "rb") as fh:
        shadow_raw = fh.read()
    shadow = json.loads(shadow_raw.decode("utf-8-sig"))

    recorded = {}
    for check in shadow["checks"]:
        for ev in check.get("evidence", []):
            recorded.setdefault(ev["ref"], set()).add(ev["sha256"])
    refs = sorted(recorded)

    head, rc, err = run(["git", "rev-parse", "HEAD"])
    if rc != 0:
        raise SystemExit("git rev-parse HEAD failed: %s" % err)
    branch, _, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    # Ask git for the values in effect in the evaluating environment, not fixed guesses.
    eff = {}
    for key in ("core.autocrlf", "core.eol", "core.safecrlf", "core.longpaths"):
        val, rc_cfg, _ = run(["git", "config", "--get", key])
        eff[key] = val if rc_cfg == 0 else None

    tmp = tempfile.mkdtemp(prefix="wl_evidence_decomp_")
    clone_dir = os.path.join(tmp, "clone")
    clone_err = None
    url = "file:///" + REPO.replace("\\", "/")
    _, rc, err = run(
        ["git", "-c", "core.longpaths=true", "clone", "--no-local", "--quiet", url, clone_dir],
        cwd=tmp,
    )
    if rc != 0:
        clone_err = "clone failed: %s" % err
    else:
        _, rc, err = run(
            ["git", "-c", "core.longpaths=true", "checkout", "--quiet", "--detach", head],
            cwd=clone_dir,
        )
        if rc != 0:
            clone_err = "checkout %s failed: %s" % (head, err)
        else:
            # A partially-failed checkout still exits 0 in some git versions; require the
            # clone worktree to be reported clean before trusting any absence as evidence.
            st, rc_st, _ = run(
                ["git", "-c", "core.longpaths=true", "status", "--porcelain"], cwd=clone_dir
            )
            if rc_st != 0 or st:
                clone_err = "clone worktree not clean after checkout: %s" % (st or "rc=%d" % rc_st)

    rows = []
    try:
        for ref in refs:
            rec = sorted(recorded[ref])
            wt = read_bytes(os.path.join(REPO, ref.replace("/", os.sep)))
            wt_sha = sha256_bytes(wt) if wt is not None else None
            wt_lf = sha256_bytes(wt.replace(b"\r\n", b"\n")) if wt is not None else None
            crlf_count = wt.count(b"\r\n") if wt is not None else None
            lone_lf = (wt.count(b"\n") - wt.count(b"\r\n")) if wt is not None else None

            blob, rc_b, _ = run(["git", "cat-file", "blob", "%s:%s" % (head, ref)], binary=True)
            head_blob = sha256_bytes(blob) if rc_b == 0 else None

            # rc 0 == git considers the path unchanged, AFTER eol normalization.
            _, rc_diff, _ = run(["git", "diff", "--quiet", "HEAD", "--", ref])
            attrs, _, _ = run(["git", "check-attr", "text", "eol", "--", ref])

            clone_sha = None
            if clone_err is None:
                cb = read_bytes(os.path.join(clone_dir, ref.replace("/", os.sep)))
                clone_sha = sha256_bytes(cb) if cb is not None else None

            rows.append(
                {
                    "ref": ref,
                    "recorded_sha256": rec[0] if len(rec) == 1 else rec,
                    "worktree_sha256": wt_sha,
                    "worktree_lf_normalized_sha256": wt_lf,
                    "head_blob_sha256": head_blob,
                    "clone_checkout_sha256": clone_sha,
                    "worktree_crlf_count": crlf_count,
                    "worktree_lone_lf_count": lone_lf,
                    "git_reports_path_unchanged_vs_head": rc_diff == 0,
                    "check_attr": attrs,
                    "tracked_at_head": head_blob is not None,
                    "worktree_matches_recorded": wt_sha is not None and wt_sha in rec,
                    "head_blob_matches_recorded": head_blob is not None and head_blob in rec,
                    "clone_matches_recorded": clone_sha is not None and clone_sha in rec,
                    "worktree_lf_equals_head_blob": (
                        None if (wt_lf is None or head_blob is None) else wt_lf == head_blob
                    ),
                    "clone_reproduces_head_blob": (
                        None if (clone_sha is None or head_blob is None) else clone_sha == head_blob
                    ),
                }
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    def diagnose(r):
        if not r["tracked_at_head"]:
            return "A_not_tracked_at_head"
        if r["clone_matches_recorded"]:
            return "ok_clone_recomputes_recorded"
        if r["clone_reproduces_head_blob"] is False:
            return "C_checkout_mutates_bytes"
        if r["worktree_lf_equals_head_blob"] and not r["head_blob_matches_recorded"]:
            return "D_recorded_over_crlf_worktree_bytes_archived_domain_is_lf"
        if not r["git_reports_path_unchanged_vs_head"]:
            return "B_content_differs_from_head"
        return "unclassified"

    for r in rows:
        r["diagnosis"] = diagnose(r)

    tally = {}
    for r in rows:
        tally[r["diagnosis"]] = tally.get(r["diagnosis"], 0) + 1

    tracked = [r for r in rows if r["tracked_at_head"]]
    out = {
        "probe": os.path.basename(__file__),
        "authority": "read_only_observation; no adoption or deployment authority",
        "repo": REPO,
        "head": head,
        "branch": branch,
        "effective_git_config": eff,
        "clone_error": clone_err,
        "clone_leg_valid": clone_err is None,
        "shadow_result_sha256": sha256_bytes(shadow_raw),
        "evidence_count": len(rows),
        "rows": rows,
        "tally_by_diagnosis": tally,
        "summary": {
            "worktree_matches_recorded": sum(1 for r in rows if r["worktree_matches_recorded"]),
            "tracked_at_head": len(tracked),
            "clone_matches_recorded": sum(1 for r in rows if r["clone_matches_recorded"]),
            "clone_reproduces_head_blob_among_tracked": sum(
                1 for r in tracked if r["clone_reproduces_head_blob"] is True
            ),
            "tracked_reported_unchanged_by_git_yet_bytes_differ": sum(
                1
                for r in tracked
                if r["git_reports_path_unchanged_vs_head"]
                and r["worktree_sha256"] != r["head_blob_sha256"]
            ),
        },
        "boundary": (
            "This measures byte reachability of the cited evidence files only. It does not "
            "check that those bytes are what the measuring process consumed, it does not "
            "cover any other file in the proposal, and it says nothing about whether the "
            "proposal should be adopted."
        ),
    }

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    json.dump(out["summary"], sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    json.dump(out["tally_by_diagnosis"], sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.write("clone_leg_valid=%s\n" % out["clone_leg_valid"])


if __name__ == "__main__":
    main()
