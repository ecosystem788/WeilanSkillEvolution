"""Read-only probe: how many commits in recent history are tree-identical to
their (first) parent, i.e. assert work in the message that git cannot corroborate?

No writes. Prints JSON to a file given as argv[1].
"""
import json
import subprocess
import sys

REPO = r"D:\WeilanSkillEvolution"
N = 400


def git(*args):
    out = subprocess.run(
        ["git", "-C", REPO, *args],
        capture_output=True,
    )
    if out.returncode != 0:
        raise SystemExit(f"git {args} rc={out.returncode}: {out.stderr[:400]!r}")
    return out.stdout.decode("utf-8", errors="strict")


def main() -> int:
    # oid<TAB>parentcount<TAB>subject   (subject last: may contain tabs? use \x1f)
    raw = git(
        "log",
        f"-{N}",
        "--pretty=format:%H\x1f%P\x1f%s",
    )
    rows = [r for r in raw.split("\n") if r.strip()]
    empties = []
    total_single_parent = 0
    for r in rows:
        oid, parents, subject = r.split("\x1f", 2)
        plist = parents.split()
        if len(plist) != 1:
            continue  # skip merges / root
        total_single_parent += 1
        t_self = git("rev-parse", f"{oid}^{{tree}}").strip()
        t_par = git("rev-parse", f"{plist[0]}^{{tree}}").strip()
        if t_self == t_par:
            empties.append({"oid": oid[:7], "subject": subject})

    result = {
        "commits_examined": len(rows),
        "single_parent_commits": total_single_parent,
        "empty_tree_commits": len(empties),
        "rate": round(len(empties) / total_single_parent, 4) if total_single_parent else None,
        "items": empties,
    }
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
