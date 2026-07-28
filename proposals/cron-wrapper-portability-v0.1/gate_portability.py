"""Codex's death-gate for the cron-wrapper portability case (route 甲).

Codex, 2026-07-27T14:59:01+09:00:

    下一案的最小死闸应是仓外后像同时让当前 clone 与 runner 形状 clone 的
    cron focused test 两参数全绿，并显式验证派生根含预期仓标记，否则拒签。

This script is that gate, run against the *out-of-tree* post-image only.  It
never writes inside the repository working tree: both clones live under
--workdir, and every wrapper variant is installed into those clones.

    python proposals/cron-wrapper-portability-v0.1/gate_portability.py

Exit 0 iff every arm produced its expected verdict.

Arms
----
1. derivation identity, current clone .... the post-image's own function, invoked
   with $here = the live impl directory, must return exactly the path the
   pre-image hardcoded.  This is what says the live heartbeat's cwd is unchanged.
2. marker validation ..................... the derivation must throw on a
   marker-less directory, and on a directory carrying CHARTER.md alone.
3. current-clone-shaped clone ............ cron focused test, both codepage
   params, pre-image and post-image, both green (portability must not cost the
   shape that works today).
4. runner-shaped clone (a/<repo>/<repo>) . cron focused test, both params,
   post-image GREEN.
4b. what the hardcoded root actually does in another clone.  Measured, not
   assumed — and it corrected this author: on *this* machine the pre-image is
   green in the runner-shaped clone, because D:\WeilanSkillEvolution happens to
   exist here.  It is green while running the heartbeat from a different
   checkout than the one it was launched from.  Two distinct failure modes:
     - hardcoded root ABSENT (the hosted runner) -> Set-Location throws, red;
     - hardcoded root PRESENT but foreign (any second local clone) -> silently
       green from the wrong checkout, which no test was watching.
5. mutation .............................. with the marker checks stripped, arm 2
   must stop failing — i.e. arm 2's assertions are load-bearing, not decorative.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
IMPL_REL = Path("proposals") / "bounded-scheduler-v0.1" / "impl"
LIVE_IMPL = REPO / IMPL_REL
PRE_IMAGE = LIVE_IMPL / "run_wake_cron.ps1"
POST_IMAGE = HERE / "run_wake_cron.proposed-final.ps1"
TEST_FILE = LIVE_IMPL / "test_wake_sentinel.py"

CRON_TEST = "test_cron_wrapper_survives_cjk_report_on_any_console_codepage"
HARDCODED_ROOT = r"D:\WeilanSkillEvolution"

results = []


def arm(name, verdict, expected):
    ok = verdict == expected
    results.append((name, ok))
    print(f"  [{'ok ' if ok else 'BAD'}] {name}: {verdict} (expected {expected})")


def rmtree_force(path):
    """Remove a staged clone.

    Two Windows facts, both hit while writing this gate: git's object files are
    read-only (plain rmtree leaves a partial tree, and the next clone then fails
    into a non-empty directory), and this repository carries paths that exceed
    MAX_PATH once re-rooted under a longer prefix — git handles that with
    core.longpaths, Python's os calls need the \\\\?\\ extended prefix.
    """
    path = Path(path)
    if not path.exists():
        return
    ext = "\\\\?\\" + str(path.resolve())

    def chmod_retry(func, target, _exc):
        os.chmod(target, 0o700)
        func(target)

    shutil.rmtree(ext, onerror=chmod_retry)


def clone(dest, longpaths=True):
    """A real clone of this repository at an arbitrary path."""
    rmtree_force(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git"]
    if longpaths:
        cmd += ["-c", "core.longpaths=true"]
    cmd += ["clone", "--quiet", "--local", "--single-branch", str(REPO), str(dest)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=900)
    # A clone checks out through the smudge filter (core.autocrlf=true here), so
    # install the exact working-tree bytes of the two files under test.
    for src in (TEST_FILE,):
        (dest / IMPL_REL / src.name).write_bytes(src.read_bytes())
    return dest


def install(clone_root, wrapper_bytes):
    (clone_root / IMPL_REL / "run_wake_cron.ps1").write_bytes(wrapper_bytes)


def focused(clone_root, codepage):
    impl = clone_root / IMPL_REL
    env = dict(os.environ)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         f"test_wake_sentinel.py::{CRON_TEST}[{codepage}]"],
        cwd=str(impl), env=env, capture_output=True, timeout=900,
    )
    return "pass" if proc.returncode == 0 else "fail"


def cwd_of(clone_root, wrapper_bytes, workdir, tag):
    """Which checkout does the wrapper actually run the wake from?

    The wrapper logs the child's stop_reason verbatim, so a fake wake whose
    stop_reason is its own cwd turns the log line into the answer.
    """
    install(clone_root, wrapper_bytes)
    scratch = workdir / f"cwd-{tag}"
    rmtree_force(scratch)
    scratch.mkdir(parents=True)
    fake = scratch / "fake_wake.py"
    fake.write_text(
        "import json, os, sys\n"
        "sys.stdout.buffer.write(json.dumps({\n"
        "    'committed_frame': 'wf-cwd-probe',\n"
        "    'receipt': {'crossed_irreversible_gate': False,\n"
        "                'stop_reason': os.getcwd()},\n"
        "}).encode('utf-8'))\n",
        encoding="utf-8",
    )
    log = scratch / "cron.log"
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(clone_root / IMPL_REL / "run_wake_cron.ps1"),
         "-WakeScript", str(fake), "-LogPath", str(log), "-NoEscalate"],
        capture_output=True, timeout=300,
    )
    if not log.exists():
        return f"NOLOG rc={proc.returncode}"
    text = log.read_text(encoding="utf-8-sig")
    for line in text.splitlines():
        if " wake ok " in line:
            return line.split("stop=", 1)[1].split("  frame=")[0]
    return f"NOWAKE rc={proc.returncode}: {text.strip()[:200]}"


def derive(wrapper_bytes, script_dir, workdir):
    """Invoke the post-image's own Resolve-CheckoutRoot with a chosen $here.

    The function body is taken verbatim out of the wrapper bytes, so this arm
    measures the proposed file rather than a paraphrase of it.
    """
    text = wrapper_bytes.decode("utf-8")
    start = text.index("function Resolve-CheckoutRoot")
    end = text.index("\n$repo = Resolve-CheckoutRoot")
    body = text[start:end]
    driver = workdir / "derive.ps1"
    driver.write_text(
        body
        + '\ntry { Write-Output ("OK=" + (Resolve-CheckoutRoot $args[0])) }\n'
          'catch { Write-Output ("THROW=" + $_.Exception.Message) }\n',
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(driver), str(script_dir)],
        capture_output=True, timeout=120,
    )
    out = proc.stdout.decode("utf-8", errors="replace").strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=r"D:\WeilanExec\cron-portability-gate")
    args = ap.parse_args()
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    pre = PRE_IMAGE.read_bytes()
    post = POST_IMAGE.read_bytes()

    print("== arm 1: derivation identity on the live clone ==")
    got = derive(post, LIVE_IMPL, workdir)
    print(f"       derived: {got}")
    arm("post-image derives the live checkout root",
        got, f"OK={HARDCODED_ROOT}")
    arm("...and it equals the value the pre-image hardcoded",
        str(HARDCODED_ROOT in pre.decode("utf-8")), "True")

    print("\n== arm 2: marker validation is explicit ==")
    bare = workdir / "bare-dir"
    bare.mkdir(parents=True, exist_ok=True)
    arm("marker-less directory throws",
        derive(post, bare, workdir).split("=")[0], "THROW")
    charter_only = workdir / "charter-only"
    charter_only.mkdir(parents=True, exist_ok=True)
    (charter_only / "CHARTER.md").write_text("decoy\n", encoding="utf-8")
    arm("CHARTER.md alone is not enough",
        derive(post, charter_only, workdir).split("=")[0], "THROW")

    print("\n== arm 5: those two assertions are load-bearing (mutation) ==")
    sys.path.insert(0, str(HERE))
    import build_proposed  # noqa: E402  (deliberately late; needs HERE on path)
    mutant = build_proposed.build(pre, "no-marker-check")
    arm("marker checks stripped -> marker-less directory no longer throws",
        derive(mutant, bare, workdir).split("=")[0], "OK")
    charter_mutant = build_proposed.build(pre, "charter-only")
    arm("impl check stripped -> CHARTER.md alone is accepted",
        derive(charter_mutant, charter_only, workdir).split("=")[0], "OK")

    print("\n== arm 3: current-clone-shaped clone ==")
    plain = clone(workdir / "plain" / "WeilanSkillEvolution")
    print(f"       {plain}")
    for image, label, expected in ((pre, "pre-image", "pass"), (post, "post-image", "pass")):
        install(plain, image)
        for codepage in (65001, 936):
            arm(f"{label} @ chcp {codepage}", focused(plain, codepage), expected)

    print("\n== arm 4: runner-shaped clone (a/<repo>/<repo>) ==")
    runner = clone(workdir / "a" / "WeilanSkillEvolution" / "WeilanSkillEvolution")
    print(f"       {runner}")
    install(runner, post)
    arm("post-image derives the runner-shaped root",
        derive(post, runner / IMPL_REL, workdir), f"OK={runner}")
    for codepage in (65001, 936):
        arm(f"post-image @ chcp {codepage}", focused(runner, codepage), "pass")

    print("\n== arm 4b: which checkout does each image actually wake from? ==")
    arm("post-image wakes from the clone it was launched from",
        cwd_of(runner, post, workdir, "post"), str(runner))
    pre_cwd = cwd_of(runner, pre, workdir, "pre")
    print(f"       pre-image, launched from {runner}")
    print(f"       ...actually woke from   {pre_cwd}")
    arm("pre-image silently wakes from the OTHER checkout",
        pre_cwd, HARDCODED_ROOT)

    print("\n== arm 4c: hosted-runner condition (hardcoded root absent) ==")
    absent = pre.decode("utf-8").replace(
        '$repo = "D:\\WeilanSkillEvolution"',
        '$repo = "D:\\a\\WeilanSkillEvolution\\WeilanSkillEvolution"',
    ).encode("utf-8")
    if absent == pre:
        raise SystemExit("arm 4c: hardcoded-root anchor not found in the pre-image")
    install(runner, absent)
    for codepage in (65001, 936):
        arm(f"pre-image, root absent @ chcp {codepage}", focused(runner, codepage), "fail")
    install(runner, post)

    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} arms produced the expected verdict")
    if passed != len(results):
        print(json.dumps([n for n, ok in results if not ok], ensure_ascii=False, indent=1))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
