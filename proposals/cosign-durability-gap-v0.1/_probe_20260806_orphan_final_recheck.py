"""Read-only: is the ORPHANED signed final of 2026-07-28 still there?

Rechecks proposals/cosign-durability-gap-v0.1/FINDING.md:143-161 (section 7.2)
at 2026-08-06.

Recorded state on 07-28:
  signed final sha256 = ce41975991c7...  (wake_prompt_codex.md line 3 co-sign)
  present as LOOSE blob ff3d72e4486e88e697d7de76e7fd0388740ec076
  `git rev-list --objects --all --reflog` -> 0 hits (unreachable, even via reflog)
  gc.pruneExpire unset -> git default 2 weeks grace from 07-28 (~08-11)

Question this probe answers, keeping the three predicates the FINDING itself
insists on separating (FINDING.md:163-177):
  (P1) do the bytes still EXIST as an object?
  (P2) are they REACHABLE from any ref/reflog?
  (P3) did those exact bytes ever land in a committed version of the path?
"present" != "reachable" != "in history".

Writes only its own .out.json. Re-run:
  python _probe_20260806_orphan_final_recheck.py
"""
import hashlib
import json
import os
import subprocess

REPO = r"D:\WeilanSkillEvolution"
SIGNED_FINAL = "ce41975991c77c930cbf85fef7953b31860c7b7f297346e3613f9ef88613daec"
LOOSE_OID = "ff3d72e4486e88e697d7de76e7fd0388740ec076"
PATH = "proposals/bounded-scheduler-v0.1/impl/wake_prompt_codex.md"


def git(*args, text=True):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    out = p.stdout.decode("utf-8", "replace") if text else p.stdout
    return p.returncode, out, p.stderr.decode("utf-8", "replace")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    res = {"signed_final_sha256": SIGNED_FINAL, "loose_oid": LOOSE_OID, "path": PATH}

    # --- P1: does the object still exist at all?
    rc, _, _ = git("cat-file", "-e", LOOSE_OID)
    exists = rc == 0
    res["P1_object_exists"] = exists

    if exists:
        rc, raw, _ = git("cat-file", "blob", LOOSE_OID, text=False)
        res["P1_bytes_match_signed_final"] = sha(raw) == SIGNED_FINAL
        res["P1_size"] = len(raw)
        # loose or packed?
        loose_path = os.path.join(REPO, ".git", "objects", LOOSE_OID[:2], LOOSE_OID[2:])
        res["P1_still_loose_on_disk"] = os.path.exists(loose_path)
    else:
        res["P1_bytes_match_signed_final"] = None
        res["P1_size"] = None
        res["P1_still_loose_on_disk"] = False

    # --- P2: reachable from any ref, including reflog?
    rc, out, err = git("rev-list", "--objects", "--all", "--reflog")
    hit = False
    for line in out.splitlines():
        if line.split(" ")[0] == LOOSE_OID:
            hit = True
            break
    res["P2_reachable_from_ref_or_reflog"] = hit
    res["P2_scan_rc"] = rc

    # --- P3: did these exact bytes ever land in a committed version of the path?
    rc, out, _ = git("rev-list", "--all", "--", PATH)
    commits = out.split()
    matches = []
    for c in commits:
        rc2, blob, _ = git("show", f"{c}:{PATH}", text=False)
        if rc2 == 0 and sha(blob) == SIGNED_FINAL:
            matches.append(c)
    res["P3_commits_touching_path"] = len(commits)
    res["P3_commits_with_exact_signed_final"] = matches
    res["P3_signed_final_ever_in_history"] = bool(matches)

    # --- prune exposure
    rc, out, _ = git("config", "--get", "gc.pruneExpire")
    res["gc_pruneExpire"] = out.strip() or "(unset -> git default: 2.weeks.ago)"

    # --- verdict, using the FINDING's own vocabulary
    if res["P3_signed_final_ever_in_history"]:
        verdict = "DURABLE_reached_history"
    elif not exists:
        verdict = "GONE_object_no_longer_present"
    elif hit:
        verdict = "REACHABLE_but_not_on_this_path"
    else:
        verdict = "STILL_ORPHANED_present_but_unreachable"
    res["verdict"] = verdict
    res["limitation"] = (
        "P3 covers committed versions of THIS path only. If the same bytes were "
        "committed under a different path they would not be counted here. P2 is a "
        "point-in-time answer: an unreachable object can be pruned at any later gc."
    )

    outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_probe_20260806_orphan_final_recheck.out.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("wrote", outp)


if __name__ == "__main__":
    main()
