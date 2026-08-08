#!/usr/bin/env python3
"""Read-only: run the co-signed hard-acceptance test (B, untracked since 08-01)
against the HEAD version of the checker (A, still uncommitted), in a temp copy.

Nothing in the repo working tree is modified.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import pathlib

REPO = pathlib.Path(
    subprocess.run(["git", "rev-parse", "--show-toplevel"],
                   cwd=str(pathlib.Path(__file__).resolve().parent),
                   capture_output=True, check=True)
    .stdout.decode("utf-8").strip()
)


CHECKER_REL = "proposals/bounded-scheduler-v0.1/impl/cited_artifact_receipt_check.py"


def _materialize_head_checker() -> pathlib.Path:
    """Write HEAD's version of the checker to a temp file (never touches the tree)."""
    blob = subprocess.run(
        ["git", "show", f"HEAD:{CHECKER_REL}"],
        cwd=str(REPO), capture_output=True, check=True,
    ).stdout
    fd, name = tempfile.mkstemp(prefix="cited_HEAD_", suffix=".py")
    with os.fdopen(fd, "wb") as fh:
        fh.write(blob)
    return pathlib.Path(name)

IMPL = REPO / "proposals/bounded-scheduler-v0.1/impl"
TEST_B = IMPL / "test_cited_artifact_receipt_check.py"
HEAD_A = None  # materialized from HEAD at runtime
WORK_A = IMPL / "cited_artifact_receipt_check.py"  # worktree version


HEAD_A = _materialize_head_checker()


def run_case(label: str, checker_src: Path, tmpdir: Path) -> dict:
    case = tmpdir / label
    case.mkdir()
    shutil.copy2(TEST_B, case / "test_cited_artifact_receipt_check.py")
    shutil.copy2(checker_src, case / "cited_artifact_receipt_check.py")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(case / "test_cited_artifact_receipt_check.py"),
         "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=str(case),
        capture_output=True,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    tail = [ln for ln in out.splitlines() if ln.strip()][-6:]
    return {
        "checker_version": label,
        "checker_src": str(checker_src),
        "rc": proc.returncode,
        "tail": tail,
        "stderr_tail": proc.stderr.decode("utf-8", errors="replace").splitlines()[-3:],
    }


with tempfile.TemporaryDirectory(prefix="wsl_drift_") as td:
    tmp = Path(td)
    results = [
        run_case("head_version", HEAD_A, tmp),
        run_case("worktree_version", WORK_A, tmp),
    ]

print(json.dumps({
    "test_file": str(TEST_B),
    "test_file_tracked": False,
    "results": results,
}, ensure_ascii=False, indent=1))
