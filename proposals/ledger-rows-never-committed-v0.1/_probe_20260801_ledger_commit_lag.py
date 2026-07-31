# -*- coding: utf-8 -*-
"""Read-only probe: which append-only ledger rows exist on disk but in no commit?

Subject: every *.jsonl under proposals/bounded-scheduler-v0.1/impl/ that git tracks.
Method (read-only; no index writes, no checkout, no network):
  * working-tree line count  vs  `git show HEAD:<path>` line count
  * for each working-tree line absent from HEAD, ask whether that exact line ever
    appeared in ANY commit reachable from any ref:  git log --all -p is too coarse,
    so we walk `git rev-list --all -- <path>` and read each blob.
  * commit-lag: how many commits have landed on HEAD since the last commit that
    touched the file at all.
Output: _probe_20260801_ledger_commit_lag.out.json (deterministic, sorted).
"""
import json
import os
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
IMPL = "proposals/bounded-scheduler-v0.1/impl"
OUT = os.path.join(REPO, "proposals", "ledger-rows-never-committed-v0.1",
                   "_probe_20260801_ledger_commit_lag.out.json")


def git(*args, binary=False):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if r.returncode != 0:
        return None if binary else None
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def lines_of(blob_bytes):
    if blob_bytes is None:
        return None
    return [ln for ln in blob_bytes.decode("utf-8", "replace").replace("\r\n", "\n").split("\n") if ln.strip()]


def main():
    head = git("rev-parse", "HEAD").strip()
    tracked = [p for p in git("ls-files", IMPL).splitlines() if p.endswith(".jsonl")]
    total_commits = len(git("rev-list", "HEAD").splitlines())

    report = []
    for path in sorted(tracked):
        disk_path = os.path.join(REPO, path.replace("/", os.sep))
        with open(disk_path, "rb") as fh:
            disk_lines = lines_of(fh.read())
        head_lines = lines_of(git("show", "%s:%s" % (head, path), binary=True))
        if head_lines is None:
            head_lines = []

        disk_set_missing = [ln for ln in disk_lines if ln not in set(head_lines)]

        # commits that ever touched this path, newest first
        touching = git("rev-list", "--all", "--", path).splitlines()
        last_touch = touching[0] if touching else None
        # how many HEAD-reachable commits since the last one that touched this file
        lag = None
        if last_touch:
            since = git("rev-list", "%s..HEAD" % last_touch)
            lag = len(since.splitlines()) if since is not None else None

        # for rows absent from HEAD: did they ever exist in ANY commit's version?
        never_anywhere = []
        if disk_set_missing:
            seen = set()
            for c in touching:
                b = git("show", "%s:%s" % (c, path), binary=True)
                if b is None:
                    continue
                seen.update(lines_of(b))
            never_anywhere = [ln for ln in disk_set_missing if ln not in seen]

        report.append({
            "path": path,
            "disk_rows": len(disk_lines),
            "head_rows": len(head_lines),
            "rows_absent_from_head": len(disk_set_missing),
            "rows_in_no_commit_at_all": len(never_anywhere),
            "last_commit_touching": last_touch[:12] if last_touch else None,
            "commits_on_head_since_last_touch": lag,
            "sample_never_committed": [json.loads(x) if x.lstrip().startswith("{") else x
                                       for x in never_anywhere[:3]],
        })

    out = {
        "probe": "ledger_commit_lag",
        "read_only": True,
        "head": head,
        "head_commit_count": total_commits,
        "impl_dir": IMPL,
        "tracked_jsonl_count": len(tracked),
        "ledgers": report,
        "totals": {
            "ledgers_with_uncommitted_rows": sum(1 for r in report if r["rows_in_no_commit_at_all"] > 0),
            "rows_in_no_commit_at_all": sum(r["rows_in_no_commit_at_all"] for r in report),
        },
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(out["totals"], ensure_ascii=False))
    for r in report:
        if r["rows_in_no_commit_at_all"] or r["rows_absent_from_head"]:
            print(r["path"], "disk", r["disk_rows"], "head", r["head_rows"],
                  "never-committed", r["rows_in_no_commit_at_all"],
                  "lag", r["commits_on_head_since_last_touch"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
