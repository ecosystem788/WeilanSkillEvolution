"""Round 3: does Codex's proposed REPLACEMENT acceptance command actually hold?

Codex (2026-07-31T22:32:43+09:00) proposes swapping the acceptance to directory
discovery with rc=5 / zero target nodes, and cites having run it with
`--ignore='*proposed-final.py'`.  Two things need machine-checking before I can
sign that into revision 3:

  1. The real landing shape puts `test_wake_brief.proposed-final.py` in the SAME
     directory.  That name matches pytest's default `test_*.py` glob and is not a
     legal module name -> ModuleNotFoundError -> collection error.  So plain
     directory discovery there may give rc=2, not rc=5.
  2. `--ignore` takes a PATH, not a glob; the glob form is `--ignore-glob`.  If
     `--ignore='*proposed-final.py'` is a no-op, the cited rc=5 came from the
     absence of that file, not from the ignore.

Throwaway tempdir; no live state touched.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROP = Path(r"D:\WeilanSkillEvolution\proposals\wake-entrypoint-ergonomics-v0.1")
HARNESS = PROP / "_probe_20260731_wake_peek_prelanding_harness.proposed-final.py"
WB_PROPOSED = PROP / "wake_brief.proposed-final.py"
TEST_PROPOSED = PROP / "test_wake_brief.proposed-final.py"
LANDED_NAME = "_probe_20260731_wake_peek_prelanding_harness.py"


def run(args, cwd):
    p = subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    return p.returncode, p.stdout.decode("utf-8", "replace")


def summarize(out):
    lines = [ln for ln in out.splitlines() if ln.strip()]
    return {
        "no_tests_collected": "no tests collected" in out,
        "harness_nodes": [ln for ln in lines if LANDED_NAME in ln and "::" in ln],
        "errors": [ln for ln in lines if ln.startswith("ERROR")],
        "tail": lines[-2:],
    }


def sha(b):
    return hashlib.sha256(b).hexdigest()


def build(tmp, include_test_proposed):
    pkg = tmp / "proposals" / "wake-entrypoint-ergonomics-v0.1"
    impl = tmp / "proposals" / "bounded-scheduler-v0.1" / "impl"
    pkg.mkdir(parents=True, exist_ok=True)
    impl.mkdir(parents=True, exist_ok=True)
    wb = WB_PROPOSED.read_bytes()
    (impl / "wake_brief.py").write_bytes(wb)
    (pkg / "wake_brief.proposed-final.py").write_bytes(wb)
    (pkg / LANDED_NAME).write_bytes(HARNESS.read_bytes())
    if include_test_proposed:
        (pkg / "test_wake_brief.proposed-final.py").write_bytes(TEST_PROPOSED.read_bytes())
    return pkg


def main():
    result = {
        "pytest_version": subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.decode("utf-8", "replace").strip(),
        "harness_sha256": sha(HARNESS.read_bytes()),
        "test_proposed_sha256": sha(TEST_PROSPOSED_BYTES := TEST_PROPOSED.read_bytes()),
        "test_proposed_bytes": len(TEST_PROSPOSED_BYTES),
        "cases": {},
    }

    tmp = Path(tempfile.mkdtemp(prefix="wl_pytest_probe_c_"))
    try:
        # Shape 1: landing WITHOUT the test_*.proposed-final.py evidence copy
        pkg = build(tmp, include_test_proposed=False)
        rc, out = run(["--collect-only", "-q", str(pkg)], tmp)
        result["cases"]["S1_dir_no_test_proposed"] = {"rc": rc, **summarize(out)}

        shutil.rmtree(tmp, ignore_errors=True)
        tmp = Path(tempfile.mkdtemp(prefix="wl_pytest_probe_c_"))

        # Shape 2: landing WITH it (the shape revision 2 actually produces)
        pkg = build(tmp, include_test_proposed=True)
        rc, out = run(["--collect-only", "-q", str(pkg)], tmp)
        result["cases"]["S2_dir_with_test_proposed"] = {"rc": rc, **summarize(out)}

        rc, out = run(
            ["--collect-only", "-q", str(pkg), "--ignore=*proposed-final.py"], tmp)
        result["cases"]["S2_dir_ignore_glob_as_path"] = {"rc": rc, **summarize(out)}

        rc, out = run(
            ["--collect-only", "-q", str(pkg), "--ignore-glob=*proposed-final.py"], tmp)
        result["cases"]["S2_dir_ignore_glob_proper"] = {"rc": rc, **summarize(out)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    c = result["cases"]
    result["verdict"] = {
        "plain_dir_discovery_rc5_in_real_landing_shape":
            c["S2_dir_with_test_proposed"]["rc"] == 5,
        "ignore_as_path_form_works": c["S2_dir_ignore_glob_as_path"]["rc"] == 5,
        "ignore_glob_form_works": c["S2_dir_ignore_glob_proper"]["rc"] == 5,
        "harness_nodes_ever_collected_by_dir_discovery": any(
            v["harness_nodes"] for v in c.values()
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    Path(__file__).with_suffix(".out.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
