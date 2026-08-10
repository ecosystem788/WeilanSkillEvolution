"""Close the gap left by the survival probe: did `git rebase --force-rebase`
actually REPLAY the range (new commit OIDs), or no-op? If it no-ops, "the empty
commit survived" is a vacuous claim.

Operates only inside throwaway clones under D:\\_p. Prints JSON to argv[1].
"""
import json
import os
import subprocess
import sys

SRC = r"D:\WeilanSkillEvolution"
BRANCH = "codex/se-0.4-0.7-program"
EMPTY_KEY = "移除仓根 28 个未跟踪"


def run(cwd, *args, env=None, check=True):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(list(args), cwd=cwd, capture_output=True, env=e)
    if check and p.returncode != 0:
        raise SystemExit(f"cmd {args} rc={p.returncode}\n{p.stderr[:600]!r}")
    return p.returncode, p.stdout.decode("utf-8", errors="replace")


def clone(dst):
    if os.path.exists(dst):
        run(None, "cmd", "/c", "rmdir", "/s", "/q", dst, check=False)
    run(None, "git", "-c", "core.longpaths=true", "clone", "--quiet",
        "--branch", BRANCH, SRC, dst)
    run(dst, "git", "config", "core.longpaths", "true")
    return dst


def oids(cwd, rng):
    _, out = run(cwd, "git", "log", "--format=%H %s", rng)
    return [l for l in out.split("\n") if l.strip()]


def main() -> int:
    os.makedirs(r"D:\_p", exist_ok=True)
    out = {}

    for name, cmd, env in [
        ("noninteractive_forced", ["git", "rebase", "--force-rebase"], {}),
        ("interactive_autoaccept", ["git", "rebase", "-i"],
         {"GIT_SEQUENCE_EDITOR": "true", "GIT_EDITOR": "true"}),
    ]:
        wd = clone(rf"D:\_p\oid-{name}")
        _, base = run(wd, "git", "rev-parse", "bcb3de0^")
        base = base.strip()
        before = oids(wd, f"{base}..HEAD")
        rc, so = run(wd, *cmd, base, env=env, check=False)
        after = oids(wd, f"{base}..HEAD")

        before_oids = {l.split(" ", 1)[0] for l in before}
        after_oids = {l.split(" ", 1)[0] for l in after}
        empty_before = [l for l in before if EMPTY_KEY in l]
        empty_after = [l for l in after if EMPTY_KEY in l]

        out[name] = {
            "rc": rc,
            "stdout": so.strip()[-200:],
            "n_before": len(before),
            "n_after": len(after),
            "oids_all_identical": before_oids == after_oids,
            "n_oids_changed": len(after_oids - before_oids),
            "replay_actually_happened": before_oids != after_oids,
            "empty_oid_before": empty_before[0].split(" ", 1)[0][:7] if empty_before else None,
            "empty_oid_after": empty_after[0].split(" ", 1)[0][:7] if empty_after else None,
            "empty_rewritten_to_new_oid": bool(
                empty_before and empty_after
                and empty_before[0].split(" ", 1)[0] != empty_after[0].split(" ", 1)[0]
            ),
            "empty_still_tree_identical_to_parent": None,
        }

        if empty_after:
            new_oid = empty_after[0].split(" ", 1)[0]
            _, t_self = run(wd, "git", "rev-parse", f"{new_oid}^{{tree}}")
            _, t_par = run(wd, "git", "rev-parse", f"{new_oid}^^{{tree}}")
            out[name]["empty_still_tree_identical_to_parent"] = (
                t_self.strip() == t_par.strip()
            )

    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
