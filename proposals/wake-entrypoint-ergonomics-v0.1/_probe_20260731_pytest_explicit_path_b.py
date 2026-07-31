"""Round 2: replicate the LANDED directory shape, then re-ask the same question.

Round 1 (_probe_20260731_pytest_explicit_path.py) got "no tests collected" for the
explicit-path case -- but with rc=2 and "1 error during collection", because the
harness does module-level _load() of two sibling files that did not exist in the
bare tempdir.  That is a masked import error, not pytest declining to collect.

Here the full landing shape is reconstructed (wake_brief.py present at the impl
path, wake_brief.proposed-final.py present beside the harness), which is what
Codex reports having done.  Throwaway tempdir; no live state touched.
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
        "collected_lines": [ln for ln in lines if "collected" in ln or "error" in ln.lower()][-4:],
        "test_nodes": [ln for ln in lines if "::" in ln][:12],
        "tail": lines[-3:],
    }


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    harness_raw = HARNESS.read_bytes()
    wb_raw = WB_PROPOSED.read_bytes()
    result = {
        "pytest_version": subprocess.run(
            [sys.executable, "-m", "pytest", "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.decode("utf-8", "replace").strip(),
        "harness_sha256": sha(harness_raw),
        "wake_brief_proposed_sha256": sha(wb_raw),
        "cases": {},
    }

    tmp = Path(tempfile.mkdtemp(prefix="wl_pytest_probe_b_"))
    try:
        pkg = tmp / "proposals" / "wake-entrypoint-ergonomics-v0.1"
        impl = tmp / "proposals" / "bounded-scheduler-v0.1" / "impl"
        pkg.mkdir(parents=True)
        impl.mkdir(parents=True)
        # landed state: wake_brief.py == proposed bytes
        (impl / "wake_brief.py").write_bytes(wb_raw)
        (pkg / "wake_brief.proposed-final.py").write_bytes(wb_raw)
        target = pkg / LANDED_NAME
        target.write_bytes(harness_raw)

        rc, out = run(["--collect-only", "-q", str(target)], tmp)
        result["cases"]["A_explicit_file_path"] = {"rc": rc, **summarize(out)}

        rc, out = run(["--collect-only", "-q", str(pkg)], tmp)
        result["cases"]["B_directory_discovery"] = {"rc": rc, **summarize(out)}

        rc, out = run(["--collect-only", "-q"], tmp)
        result["cases"]["C_rootdir_discovery"] = {"rc": rc, **summarize(out)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    a = result["cases"]["A_explicit_file_path"]
    result["verdict"] = {
        "explicit_path_collects_tests": (not a["no_tests_collected"]) and a["rc"] == 0,
        "explicit_path_rc": a["rc"],
        "directory_discovery_rc": result["cases"]["B_directory_discovery"]["rc"],
        "revision2_bearing_sentence_holds": a["no_tests_collected"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    Path(__file__).with_suffix(".out.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
