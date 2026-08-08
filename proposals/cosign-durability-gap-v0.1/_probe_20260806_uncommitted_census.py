"""Read-only census: how much substantive work exists only in the working tree.

Splits git-dirty state into: tracked-modified (real content diff vs EOL-only),
and untracked-not-ignored. Reports age (mtime) and size. Writes nothing but its
own .out.json next to itself. Re-run: python _probe_20260806_uncommitted_census.py
"""
import json
import os
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"


def git(*args):
    p = subprocess.run(
        ["git", "-C", REPO] + list(args),
        capture_output=True,
    )
    # bytes, decode defensively: repo has CJK paths/content
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def numstat_modified():
    """tracked files with content diff; returns {path: (added, deleted)}"""
    rc, out, _ = git("diff", "--numstat")
    res = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, d, path = parts
        if a == "-" or d == "-":
            a = d = "0"  # binary
        res[path] = (int(a), int(d))
    return res


def untracked():
    rc, out, _ = git("ls-files", "--others", "--exclude-standard")
    return [l for l in out.splitlines() if l.strip()]


def stat_path(rel):
    full = os.path.join(REPO, rel.replace("/", os.sep))
    try:
        st = os.stat(full)
        return st.st_size, st.st_mtime
    except OSError:
        return None, None


def fmt_mtime(ts):
    if ts is None:
        return None
    import datetime

    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def main():
    mods = numstat_modified()
    untr = untracked()

    ledger_ext = (".jsonl",)
    report = {"tracked_modified": [], "untracked": [], "totals": {}}

    t_lines = 0
    t_lines_nonledger = 0
    for path, (a, d) in sorted(mods.items()):
        size, mt = stat_path(path)
        is_ledger = path.endswith(ledger_ext)
        t_lines += a
        if not is_ledger:
            t_lines_nonledger += a
        report["tracked_modified"].append(
            {
                "path": path,
                "added": a,
                "deleted": d,
                "is_append_only_ledger": is_ledger,
                "mtime": fmt_mtime(mt),
                "size": size,
            }
        )

    u_bytes = 0
    for path in sorted(untr):
        size, mt = stat_path(path)
        u_bytes += size or 0
        report["untracked"].append(
            {"path": path, "size": size, "mtime": fmt_mtime(mt)}
        )

    report["totals"] = {
        "tracked_modified_count": len(mods),
        "tracked_added_lines_all": t_lines,
        "tracked_added_lines_excluding_jsonl_ledgers": t_lines_nonledger,
        "untracked_count": len(untr),
        "untracked_bytes": u_bytes,
    }

    outp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_probe_20260806_uncommitted_census.out.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps(report["totals"], ensure_ascii=False, indent=1))
    print("wrote", outp)


if __name__ == "__main__":
    main()
