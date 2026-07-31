"""Only-read probe: does `pytest --collect-only <explicit file path>` honour python_files?

Adjudicates Codex's 2026-07-31T22:32:43+09:00 counter-claim against my revision-2
bearing sentence ("explicit path -> no tests collected").

Runs entirely inside a throwaway tempdir. Touches no ledger, no repo state.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(
    r"D:\WeilanSkillEvolution\proposals\wake-entrypoint-ergonomics-v0.1"
    r"\_probe_20260731_wake_peek_prelanding_harness.proposed-final.py"
)
LANDED_NAME = "_probe_20260731_wake_peek_prelanding_harness.py"


def run(args, cwd):
    p = subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return p.returncode, p.stdout.decode("utf-8", "replace")


def summarize(out):
    tail = [ln for ln in out.splitlines() if ln.strip()][-4:]
    return {
        "no_tests_collected": "no tests collected" in out,
        "tests_collected_line": [ln for ln in out.splitlines() if "collected" in ln][-3:],
        "tail": tail,
    }


def main():
    raw = SRC.read_bytes()
    result = {
        "source": str(SRC),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_bytes": len(raw),
        "pytest_version": subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.decode("utf-8", "replace").strip(),
        "python": sys.version.split()[0],
        "cases": {},
    }

    tmp = Path(tempfile.mkdtemp(prefix="wl_pytest_probe_"))
    try:
        pkg = tmp / "proposals" / "wake-entrypoint-ergonomics-v0.1"
        pkg.mkdir(parents=True)
        target = pkg / LANDED_NAME
        target.write_bytes(raw)

        # A: explicit file path (the exact command my revision-2 signed into acceptance)
        rc, out = run(["--collect-only", "-q", str(target)], tmp)
        result["cases"]["A_explicit_file_path"] = {"rc": rc, **summarize(out)}

        # B: directory discovery (Codex's proposed replacement)
        rc, out = run(["--collect-only", "-q", str(pkg)], tmp)
        result["cases"]["B_directory_discovery"] = {"rc": rc, **summarize(out)}

        # C: rootdir discovery from the tmp root
        rc, out = run(["--collect-only", "-q"], tmp)
        result["cases"]["C_rootdir_discovery"] = {"rc": rc, **summarize(out)}

        # D: control -- explicit path to a file with no test_* functions at all
        plain = pkg / "_probe_plain_control.py"
        plain.write_text("def helper():\n    return 1\n", encoding="utf-8")
        rc, out = run(["--collect-only", "-q", str(plain)], tmp)
        result["cases"]["D_control_explicit_no_test_funcs"] = {"rc": rc, **summarize(out)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    result["verdict"] = {
        "claim_explicit_path_yields_no_tests_collected":
            result["cases"]["A_explicit_file_path"]["no_tests_collected"],
        "claim_directory_discovery_yields_no_tests_collected":
            result["cases"]["B_directory_discovery"]["no_tests_collected"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    out_path = Path(__file__).with_suffix(".out.json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
