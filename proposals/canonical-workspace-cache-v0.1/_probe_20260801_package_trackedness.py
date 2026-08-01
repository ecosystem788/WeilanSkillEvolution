"""Read-only probe: is the canonical-workspace-cache-v0.1 package itself in the repo?

SHADOW_RESULT.json's headline numbers are tree hashes over baseline/ and candidate/.
This probe asks the prior question nobody had measured: can a third party who clones
this repository obtain those trees at all, and the proposal.json that declares them.

Measured per proposal directory:
  tracked / untracked / ignored-but-present file counts
  presence of the load-bearing package members (proposal.json, baseline/, candidate/)
  whether each declared changed path exists at ANY tracked path in the repo

find-frame-index-v0.1 is measured alongside as a control: it is a comparable
baseline+candidate proposal in the same tree, so it shows whether an untracked package
is this repo's norm or this package's exception.

Mutates nothing. Uses git plumbing only; no clone, no checkout, no writes outside the
same-named .out.json.
"""

import json
import os
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
OUT = os.path.splitext(os.path.abspath(__file__))[0] + ".out.json"

SUBJECT = "proposals/canonical-workspace-cache-v0.1"
CONTROL = "proposals/find-frame-index-v0.1"

# The two paths SHADOW_RESULT.json declares as the candidate's difference.
DECLARED_CHANGED = [
    "scripts/runtime_core.py",
    "scripts/test_canonical_workspace_cache.py",
]


def git(args):
    p = subprocess.run(
        ["git"] + args, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return p.stdout.decode("utf-8", "replace").splitlines(), p.returncode


def census(prefix, exclude=()):
    tracked, _ = git(["ls-files", "--", prefix])
    untracked, _ = git(["ls-files", "--others", "--exclude-standard", "--", prefix])
    ignored, _ = git(["ls-files", "--others", "--ignored", "--exclude-standard", "--", prefix])
    excl = set(exclude)
    tracked = [p for p in tracked if p not in excl]
    untracked = [p for p in untracked if p not in excl]
    ignored = [p for p in ignored if p not in excl]

    def under(paths, sub):
        return sum(1 for p in paths if p.startswith(prefix + "/" + sub))

    return {
        "prefix": prefix,
        "self_excluded_paths": sorted(excl),
        "tracked_count": len(tracked),
        "untracked_count": len(untracked),
        "ignored_present_count": len(ignored),
        "baseline": {
            "tracked": under(tracked, "baseline/"),
            "untracked": under(untracked, "baseline/"),
        },
        "candidate": {
            "tracked": under(tracked, "candidate/"),
            "untracked": under(untracked, "candidate/"),
        },
        "proposal_json_tracked": (prefix + "/proposal.json") in tracked,
        "proposal_json_untracked": (prefix + "/proposal.json") in untracked,
    }


def main():
    head, rc = git(["rev-parse", "HEAD"])
    if rc != 0:
        raise SystemExit("git rev-parse HEAD failed")
    head = head[0]

    all_tracked, _ = git(["ls-files"])
    tracked_set = set(all_tracked)

    changed_path_reachability = []
    for rel in DECLARED_CHANGED:
        basename = rel.rsplit("/", 1)[-1]
        # Exact-suffix match, case-sensitive: does this file exist at any tracked path?
        hits = [p for p in tracked_set if p.endswith("/" + basename) or p == rel]
        in_subject_candidate = [p for p in hits if p.startswith(SUBJECT + "/candidate/")]
        changed_path_reachability.append(
            {
                "declared_path": rel,
                "tracked_paths_anywhere_in_repo": len(hits),
                "tracked_inside_subject_candidate_tree": len(in_subject_candidate),
                "exists_at_any_tracked_path": bool(hits),
            }
        )

    # This probe's own two files are not part of the package under audit, and counting
    # them would make the census depend on whether the probe had already been run once.
    stem = SUBJECT + "/" + os.path.splitext(os.path.basename(__file__))[0]
    self_files = (stem + ".py", stem + ".out.json")

    subject = census(SUBJECT, exclude=self_files)
    control = census(CONTROL)

    gitignore_rel = SUBJECT + "/.gitignore"
    gitignore_tracked = gitignore_rel in tracked_set
    gi_path = os.path.join(REPO, gitignore_rel.replace("/", os.sep))
    gitignore_body = None
    if os.path.isfile(gi_path):
        with open(gi_path, "r", encoding="utf-8", errors="replace") as fh:
            gitignore_body = [ln.strip() for ln in fh if ln.strip()]

    out = {
        "probe": os.path.basename(__file__),
        "authority": "read_only_observation; no adoption or deployment authority",
        "head": head,
        "subject": subject,
        "control": control,
        "declared_changed_path_reachability": changed_path_reachability,
        "subject_gitignore": {
            "path": gitignore_rel,
            "present_on_disk": gitignore_body is not None,
            "tracked": gitignore_tracked,
            "rules": gitignore_body,
            "note": (
                "An untracked .gitignore does not travel to a clone; it explains why these "
                "paths were never committed here, not what a third party would see."
            ),
        },
        "boundary": (
            "Trackedness is not authenticity: a committed tree is not proof that those bytes "
            "are what any measurement consumed. Suffix matching for the declared paths could "
            "in principle collide with an unrelated file of the same basename; the counts are "
            "reported so a reader can check rather than trust. One control proposal is not a "
            "survey of repo norms."
        ),
    }

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    json.dump(
        {
            "subject": {
                k: subject[k]
                for k in ("tracked_count", "untracked_count", "ignored_present_count")
            },
            "subject_candidate": subject["candidate"],
            "control_candidate": control["candidate"],
            "declared_changed": changed_path_reachability,
        },
        sys.stdout,
        ensure_ascii=False,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
