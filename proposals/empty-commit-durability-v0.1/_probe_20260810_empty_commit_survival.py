"""Read-only-on-the-real-repo probe: does the empty commit e1a43d3 survive
routine history operations, given that its message body is the sole record of
the 28-file deletion?

All mutation happens inside a throwaway clone under %TEMP%. The real repository
is only ever read (clone source).

Control: bcb3de0 is a NON-empty commit from the same cleanup line, replayed in
the same range. If the control also vanishes, the run is broken, not the finding.

Prints JSON to argv[1].
"""
import json
import os
import shutil
import subprocess
import sys

SRC = r"D:\WeilanSkillEvolution"
BRANCH = "codex/se-0.4-0.7-program"
EMPTY_SUBJ_KEY = "移除仓根 28 个未跟踪"
CTRL_SUBJ_KEY = "移除 eb15727 冒烟测试残留"


def run(cwd, *args, env=None, check=True):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run(list(args), cwd=cwd, capture_output=True, env=e)
    if check and p.returncode != 0:
        raise SystemExit(
            f"cmd {args} rc={p.returncode}\nSTDOUT {p.stdout[:600]!r}\nSTDERR {p.stderr[:600]!r}"
        )
    return p.returncode, p.stdout.decode("utf-8", errors="replace")


def subjects(cwd, rng):
    _, out = run(cwd, "git", "log", "--format=%s", rng)
    return [s for s in out.split("\n") if s.strip()]


def present(subs, key):
    return sum(1 for s in subs if key in s)


def fresh_clone(dst):
    # Short destination root + core.longpaths: this repo has paths that blow
    # past MAX_PATH when cloned under %TEMP%.
    if os.path.exists(dst):
        run(None, "cmd", "/c", "rmdir", "/s", "/q", dst, check=False)
        shutil.rmtree(dst, ignore_errors=True)
    run(
        None,
        "git",
        "-c",
        "core.longpaths=true",
        "clone",
        "--quiet",
        "--branch",
        BRANCH,
        SRC,
        dst,
    )
    run(dst, "git", "config", "core.longpaths", "true")
    return dst


def main() -> int:
    tmp = r"D:\_p"
    os.makedirs(tmp, exist_ok=True)
    results = {}

    # Resolve the two commits and a base that precedes both, in a scratch clone.
    probe0 = fresh_clone(os.path.join(tmp, "e1a-probe-0"))
    _, empty_oid = run(probe0, "git", "rev-parse", "e1a43d3")
    _, ctrl_oid = run(probe0, "git", "rev-parse", "bcb3de0")
    _, base = run(probe0, "git", "rev-parse", "bcb3de0^")
    empty_oid, ctrl_oid, base = empty_oid.strip(), ctrl_oid.strip(), base.strip()

    baseline = subjects(probe0, f"{base}..HEAD")
    results["setup"] = {
        "base": base[:7],
        "empty_commit": empty_oid[:7],
        "control_commit": ctrl_oid[:7],
        "commits_in_replay_range": len(baseline),
        "empty_present_before": present(baseline, EMPTY_SUBJ_KEY),
        "control_present_before": present(baseline, CTRL_SUBJ_KEY),
    }

    cases = [
        (
            "rebase_noninteractive_forced",
            ["git", "rebase", "--force-rebase", base],
            {},
        ),
        (
            "rebase_interactive_autoaccept",
            ["git", "rebase", "-i", base],
            {"GIT_SEQUENCE_EDITOR": "true", "GIT_EDITOR": "true"},
        ),
    ]

    for name, cmd, env in cases:
        wd = fresh_clone(os.path.join(tmp, f"e1a-probe-{name}"))
        rc, out = run(wd, *cmd, env=env, check=False)
        after = subjects(wd, f"{base}..HEAD")
        results[name] = {
            "cmd": " ".join(cmd),
            "env": env,
            "rc": rc,
            "commits_after": len(after),
            "empty_survived": present(after, EMPTY_SUBJ_KEY) > 0,
            "control_survived": present(after, CTRL_SUBJ_KEY) > 0,
            "stdout_tail": out[-300:],
        }

    # cherry-pick the empty commit onto its own parent in a detached head
    wd = fresh_clone(os.path.join(tmp, "e1a-probe-cherry"))
    run(wd, "git", "checkout", "--quiet", "--detach", f"{empty_oid}^")
    rc, out = run(wd, "git", "cherry-pick", empty_oid, check=False)
    _, head_subj = run(wd, "git", "log", "-1", "--format=%s")
    results["cherry_pick_empty"] = {
        "rc": rc,
        "head_subject_after": head_subj.strip(),
        "empty_survived": EMPTY_SUBJ_KEY in head_subj,
        "stderr_or_out_tail": out[-300:],
    }

    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
