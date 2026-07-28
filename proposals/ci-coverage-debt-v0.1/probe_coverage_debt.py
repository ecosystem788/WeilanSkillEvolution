"""Reproduce the CI coverage-debt measurements for the Windows regression job.

Codex named the minimal discriminator on 2026-07-27T14:34:01+09:00:
"同形回归是否能逃过现有 job" — can an isomorphic regression escape the existing job?
This script answers that by measurement, not by reading the workflow.

It never touches the repository working tree: every arm runs against a copy of the
impl scripts placed under --workdir, and each mutation is applied to that copy.

    python proposals/ci-coverage-debt-v0.1/probe_coverage_debt.py

Exit code is 0 when every arm produced its expected verdict, 1 otherwise, so this
doubles as a regression check on the finding itself.
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IMPL = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl"
WORKFLOW = REPO / ".github" / "workflows" / "scheduler-windows-regressions.yml"

CRON_TEST = "test_cron_wrapper_survives_cjk_report_on_any_console_codepage"
AGENT_TEST = "test_wake_agent_capture_is_utf8_on_any_console_codepage"

# The cmd-owned redirection in run_wake_cron.ps1 that the 2026-07-14T14:00:58
# incident produced. Replacing it with PowerShell-owned redirection reintroduces
# that incident verbatim.
REDIRECTION_PRESENT = (
    '    & cmd /c "python `"$WakeScript`" --commit '
    '1>`"$stdoutPath`" 2>`"$stderrPath`""'
)
REDIRECTION_MUTANT = '    & python "$WakeScript" --commit 1> $stdoutPath 2> $stderrPath'

# The line that pins the python child's stdout encoding independently of host locale.
PIN_PRESENT = '$env:PYTHONIOENCODING = "utf-8"'
PIN_MUTANT = "# pin removed (mutation probe)"

# The wrapper's hardcoded checkout path, and a hosted-runner-shaped path that does
# not exist on the authoring machine.
REPO_PRESENT = '$repo = "D:\\WeilanSkillEvolution"'
REPO_MUTANT = '$repo = "D:\\a\\WeilanSkillEvolution\\WeilanSkillEvolution"'


def stage(workdir):
    impl = workdir / "impl"
    if impl.exists():
        shutil.rmtree(impl)
    impl.mkdir(parents=True)
    for pattern in ("*.py", "*.ps1"):
        for src in IMPL.glob(pattern):
            shutil.copy2(src, impl / src.name)
    return impl


def patch(impl, before, after):
    """Rewrite run_wake_cron.ps1 in the staged copy, preserving its byte prelude."""
    path = impl / "run_wake_cron.ps1"
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    if text.count(before) != 1:
        raise SystemExit(
            f"expected exactly one occurrence of {before!r}, found {text.count(before)}"
        )
    out = text.replace(before, after)
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    path.write_bytes(out.encode(encoding))


def run(impl, test, io_encoding=None):
    env = dict(os.environ)
    env.pop("PYTHONIOENCODING", None)
    if io_encoding:
        env["PYTHONIOENCODING"] = io_encoding
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", f"test_wake_sentinel.py::{test}", "-q"],
        cwd=str(impl), env=env, capture_output=True, timeout=600,
    )
    return "pass" if proc.returncode == 0 else "fail"


def collected(impl):
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "test_wake_sentinel.py", "--collect-only", "-q"],
        cwd=str(impl), capture_output=True, timeout=600,
    )
    tail = proc.stdout.decode("utf-8", errors="replace").strip().splitlines()[-1]
    return tail.strip()


def workflow_facts():
    text = io.open(WORKFLOW, encoding="utf-8").read()
    return {
        "names_agent_test": AGENT_TEST in text,
        "names_cron_test": CRON_TEST in text,
        "triggers_on_cron_wrapper": "impl/run_wake_cron.ps1" in text,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=r"D:\WeilanExec\coverage-debt-probe")
    args = ap.parse_args()
    workdir = Path(args.workdir)

    facts = workflow_facts()
    print("== workflow, read as source ==")
    for key, value in facts.items():
        print(f"  {key}: {value}")

    impl = stage(workdir)
    print(f"\n== staged copy: {impl} ==")
    print(f"  {collected(impl)}")

    results = []

    def arm(name, verdict, expected):
        ok = verdict == expected
        results.append(ok)
        print(f"  [{'ok ' if ok else 'BAD'}] {name}: {verdict} (expected {expected})")

    print("\n== A. baseline, unmutated copy ==")
    arm("cron test", run(impl, CRON_TEST), "pass")
    arm("wake-agent test (the one CI names)", run(impl, AGENT_TEST), "pass")

    print("\n== B. discriminator: 2026-07-14 redirection incident reintroduced ==")
    patch(impl, REDIRECTION_PRESENT, REDIRECTION_MUTANT)
    arm("wake-agent test (what CI would report)", run(impl, AGENT_TEST), "pass")
    arm("cron test (what CI never runs)", run(impl, CRON_TEST), "fail")
    patch(impl, REDIRECTION_MUTANT, REDIRECTION_PRESENT)

    print("\n== C. is the cron test locale-fragile like the wake-agent stand-in was? ==")
    arm("cron test @ PYTHONIOENCODING=cp1252", run(impl, CRON_TEST, "cp1252"), "pass")
    arm("cron test @ unset (host ACP)", run(impl, CRON_TEST), "pass")
    arm("cron test @ PYTHONIOENCODING=utf-8", run(impl, CRON_TEST, "utf-8"), "pass")

    print("\n== D. why it is immune: run_wake_cron.ps1 pins the child's encoding ==")
    patch(impl, PIN_PRESENT, PIN_MUTANT)
    arm("cron test, pin removed @ cp1252", run(impl, CRON_TEST, "cp1252"), "fail")
    arm("cron test, pin removed @ unset", run(impl, CRON_TEST), "fail")
    patch(impl, PIN_MUTANT, PIN_PRESENT)

    print("\n== E. would naming the cron test in CI actually work there? ==")
    patch(impl, REPO_PRESENT, REPO_MUTANT)
    arm("cron test @ hosted-runner-shaped checkout path", run(impl, CRON_TEST), "fail")
    patch(impl, REPO_MUTANT, REPO_PRESENT)

    print(f"\n{sum(results)}/{len(results)} arms produced the expected verdict")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
