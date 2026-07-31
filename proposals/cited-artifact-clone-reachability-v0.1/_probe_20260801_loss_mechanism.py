"""Read-only probe B: for each cited-but-uncommitted file, was its directory
committed into anyway?

If a directory holds tracked siblings, some round did run `git add` there and
walked past this file (selective-add). If it holds none, the whole line never
landed. Also resolves the deployments/ citations, which may live outside the
repo root.
"""
import io, json, os, subprocess, sys, collections

ROOT = r"D:\WeilanSkillEvolution"
PROBE_A = os.path.join(ROOT, "proposals", "cited-artifact-clone-reachability-v0.1",
                       "_probe_20260801_citation_reachability.out.json")


def git(*args):
    r = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def main():
    a = json.load(io.open(PROBE_A, encoding="utf-8"))
    tracked = set(git("ls-files").splitlines())
    by_dir = collections.Counter()
    for t in tracked:
        by_dir[os.path.dirname(t)] += 1

    rows = []
    for d in a["detail"]:
        if d["verdict"] != "disk_only":
            continue
        dirname = os.path.dirname(d["path"])
        n_tracked = by_dir.get(dirname, 0)
        # last commit that touched this directory
        last = git("log", "-1", "--format=%h %ad %s", "--date=short",
                   "--", dirname + "/").strip()
        # a file excluded by .gitignore is policy, not loss - ask git, don't assume
        ci = subprocess.run(["git", "check-ignore", "-q", d["path"]],
                            cwd=ROOT, capture_output=True)
        ignored = ci.returncode == 0
        if ignored:
            mech = "ignored_by_policy"
        elif n_tracked:
            mech = "selective_add_walked_past"
        else:
            mech = "whole_line_never_landed"
        rows.append({
            "path": d["path"],
            "dir": dirname,
            "gitignored": ignored,
            "tracked_siblings_in_dir": n_tracked,
            "mechanism": mech,
            "dir_last_commit": last,
            "cited_by": sorted({d["first_cite"]["from"], d["last_cite"]["from"]}),
        })

    mech = collections.Counter(r["mechanism"] for r in rows)

    # sanity: do the deployments/ ids exist anywhere on disk?
    dep_root = os.path.join(ROOT, "deployments")
    dep_dirs = sorted(os.listdir(dep_root)) if os.path.isdir(dep_root) else []

    payload = json.dumps({
        "probe": "loss_mechanism",
        "disk_only_count": len(rows),
        "mechanism_counts": dict(mech),
        "deployments_dirs_on_disk": dep_dirs,
        "rows": sorted(rows, key=lambda r: (r["mechanism"], r["path"])),
    }, ensure_ascii=False, indent=2)
    if len(sys.argv) > 1:
        with io.open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
            fh.write(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
