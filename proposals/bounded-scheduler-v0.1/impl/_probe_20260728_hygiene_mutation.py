"""Mutation checks for signing conditions 1 and 2 of 甲₂ (peer-chat 06:36:19).

Condition 1: put any literal back into a source file -> the source-hygiene case
             must turn red, and must kill only that one case.
Condition 2: the fail-closed case must be red when missing/unreadable input is
             swallowed instead of raised.

All mutations happen in a throwaway copy under TEMP. The repo is never touched.
Every synthetic secret shape is assembled at runtime, so this probe itself scans
to zero hits under the scanner's own PATTERNS.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(r"D:\WeilanSkillEvolution\proposals\charter-daily-push-v0.1")
SCANNER = "scan_push_manifest.py"
TEST = "test_scan_push_manifest.py"


def stage():
    work = pathlib.Path(tempfile.mkdtemp(prefix="wl_mut_"))
    for name in (SCANNER, TEST):
        shutil.copy2(SRC / name, work / name)
    return work


def run(work):
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", TEST, "--tb=no"],
        cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = [line for line in proc.stdout.splitlines() if line.strip()][-1:]
    passed = int(next(iter(re.findall(r"(\d+) passed", proc.stdout)), 0))
    failed = int(next(iter(re.findall(r"(\d+) failed", proc.stdout)), 0))
    # only the part after "::" is the case name; the part before it is the module
    red = re.findall(r"^FAILED \S+?::(\w+)", proc.stdout, re.M)
    return passed, failed, red, tail


def report(label, expect_failed, expect_red, result):
    """expect_red is the exact set of case names that must be the only reds."""
    passed, failed, red, tail = result
    ok = failed == expect_failed and (expect_red is None or set(red) == expect_red)
    print(f"[{label}] passed={passed} failed={failed} red={red} -> "
          f"{'OK' if ok else 'UNEXPECTED'}  ({tail})")
    return ok


def baseline():
    work = stage()
    return report("baseline (no mutation)", 0, None, run(work))


def literal_into(target_name, label):
    """Condition 1: reinsert a literal secret shape into one source file."""
    work = stage()
    path = work / target_name
    literal = "AK" + "IA" + "Q" * 16          # assembled at runtime, not stored
    text = path.read_text(encoding="utf-8")
    path.write_text(text + f'\n# planted literal: {literal}\n', encoding="utf-8")
    result = run(work)
    return report(label, 1, {"test_scanner_sources_have_no_literal_pattern_hits"}, result)


def swallow_missing():
    """Condition 2: make source_pattern_hits silently skip unreadable input."""
    work = stage()
    path = work / TEST
    text = path.read_text(encoding="utf-8")
    before = "        payload = path.read_bytes()"
    after = ("        try:\n"
             "            payload = path.read_bytes()\n"
             "        except OSError:\n"
             "            continue")
    assert before in text, "mutation anchor drifted; hand-check before trusting"
    path.write_text(text.replace(before, after, 1), encoding="utf-8")
    return report("swallow missing/unreadable input", 1, {"test_source_hygiene_fails_closed_on_missing_or_unreadable_source"}, run(work))


if __name__ == "__main__":
    results = [
        baseline(),
        literal_into(TEST, "literal back into test source"),
        literal_into(SCANNER, "literal back into scanner source"),
        swallow_missing(),
    ]
    print("ALL EXPECTED" if all(results) else "SOME UNEXPECTED - read above")
    sys.exit(0 if all(results) else 1)
