"""Read-only POST-check of Codex's executed cosign e830a26 (UTF-16 end-to-end pinning).

Why a second script instead of re-running _probe_20260728_utf16_e2e_pinning.py:
that probe encoded "pre" as `explicit=False` == "the repo file as it lies on disk".
After e830a26 landed, the on-disk file IS post, so its cells 1/2 silently re-measured
post under pre labels and cells 3/4 died on a now-non-unique anchor. Labels that drift
with the repo are not evidence. Here PRE is derived by reverse-applying the landed edit,
and the direction is asserted, so the script cannot quietly measure the wrong thing.

Same two traps as the original probe, deliberately kept:
  * full directory layout is reproduced (peer_health_wake resolves wake_brief via
    Path(__file__).parents[1]; a two-file copy yields ImportError, indistinguishable
    from "mutation caught" by exit code alone);
  * verdicts compare SETS OF FAILING TEST NAMES against a per-cell baseline, never
    counts (the baseline is not green: test_real_current_log_tail_... reads the real
    repo and fails in any copy).

The repo is never modified.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(r"D:\WeilanSkillEvolution")
MUTUAL = REPO / "proposals" / "mutual-aid-v0.1"
IMPL = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl"
TEST_NAME = "test_peer_health_wake.py"
TARGET = "test_authentic_run_younger_than_threshold_does_not_raise"

# What e830a26 landed, stated in the reverse direction (post -> pre).
POST_CALL = '    codex_runs(tmp_path, "2026-07-12 06:18:00", encoding="utf-16")\n    codex_runs(tmp_path, "2026-07-12 10:55:00", executed=False)'
PRE_CALL = '    codex_runs(tmp_path, "2026-07-12 06:18:00")\n    codex_runs(tmp_path, "2026-07-12 10:55:00", executed=False)'

DRIFT_BEFORE = 'encoding: str = "utf-16"'
DRIFT_AFTER = 'encoding: str = "utf-8"'

MUTATE_BEFORE = '    if raw.startswith(b"\\xff\\xfe"):\n        encoding = "utf-16"'
MUTATE_AFTER = '    if raw.startswith(b"\\xff\\xfe"):\n        encoding = "utf-8"'

FAIL_LINE = re.compile(r"^(?:FAILED|ERROR) ([^\s:]+::[^\s]+)", re.M)


def build(tmp: Path, *, post: bool, drift: bool, mutate: bool) -> Path:
    mut = tmp / "proposals" / "mutual-aid-v0.1"
    impl = tmp / "proposals" / "bounded-scheduler-v0.1" / "impl"
    mut.mkdir(parents=True)
    impl.mkdir(parents=True)
    for src in MUTUAL.glob("*.py"):
        shutil.copy2(src, mut / src.name)
    for src in IMPL.glob("*.py"):
        shutil.copy2(src, impl / src.name)

    test_path = mut / TEST_NAME
    text = test_path.read_text(encoding="utf-8")
    # Direction assertion: on-disk must already be post, else this script is lying.
    assert text.count(POST_CALL) == 1, "on-disk file is not the post state; abort"
    if not post:
        text = text.replace(POST_CALL, PRE_CALL)
    if drift:
        assert text.count(DRIFT_BEFORE) == 1, "helper default anchor not unique"
        text = text.replace(DRIFT_BEFORE, DRIFT_AFTER)
    test_path.write_text(text, encoding="utf-8")

    if mutate:
        prod = mut / "peer_health_wake.py"
        ptext = prod.read_text(encoding="utf-8")
        assert ptext.count(MUTATE_BEFORE) == 1, "decoder anchor not unique"
        prod.write_text(ptext.replace(MUTATE_BEFORE, MUTATE_AFTER), encoding="utf-8")
    return test_path


def failures(*, post: bool, drift: bool, mutate: bool) -> set[str]:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        test_path = build(tmp, post=post, drift=drift, mutate=mutate)
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-q", "--tb=no", "-p", "no:cacheprovider"],
            capture_output=True,
            text=True,
            cwd=str(tmp),
        )
        if "passed" not in proc.stdout and "failed" not in proc.stdout:
            raise SystemExit(f"harness error, not a verdict:\n{proc.stdout[-3000:]}\n{proc.stderr[-2000:]}")
        return {m.rsplit("::", 1)[-1] for m in FAIL_LINE.findall(proc.stdout)}


def cell(label: str, *, post: bool, drift: bool) -> set[str]:
    base = failures(post=post, drift=drift, mutate=False)
    mutated = failures(post=post, drift=drift, mutate=True)
    caught = mutated - base
    print(f"{label}: baseline={sorted(base)}")
    print(f"{label}: caught={sorted(caught)} -> target_in_caught={TARGET in caught}")
    return caught


def main() -> None:
    c1 = cell("1 pre  + default", post=False, drift=False)
    c2 = cell("2 pre  + drifted", post=False, drift=True)
    c3 = cell("3 post + drifted", post=True, drift=True)
    c4 = cell("4 post + default", post=True, drift=False)

    print()
    print(f"c2 -> c3 delta (what e830a26 buys): {sorted(c3 - c2)}")
    print(f"c1 -> c4 regression check (lost coverage): {sorted(c1 - c4)}")

    base_pre = failures(post=False, drift=False, mutate=False)
    drift_pre = failures(post=False, drift=True, mutate=False)
    drift_post = failures(post=True, drift=True, mutate=False)
    print()
    print(f"drift alone, pre : new_failures={sorted(drift_pre - base_pre)}")
    print(f"drift alone, post: new_failures={sorted(drift_post - base_pre)}")

    ok = (TARGET not in c2) and (TARGET in c3) and (TARGET in c4) and not (c1 - c4)
    print()
    print(f"VERDICT: {'claims hold' if ok else 'CLAIMS DO NOT HOLD'}")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
