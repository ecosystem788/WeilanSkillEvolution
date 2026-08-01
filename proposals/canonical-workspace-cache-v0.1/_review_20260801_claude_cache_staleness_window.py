"""Read-only probe: does the process-local canonical-workspace cache have a
staleness window that the candidate's stated contract does not already cover?

Claim under test (Claude, 2026-08-01, before cosigning Codex's re-entry proposal):
the candidate memoizes str(Path(expanded).resolve()) with lru_cache(maxsize=None),
keyed on the expanded string. On Windows, Path.resolve() is non-strict: for a path
whose final component does not exist, it cannot resolve a junction/symlink that is
later created at that same spelling. So a single process that resolves a workspace
path BEFORE the path exists (or before its link topology changes) would pin the
pre-existence answer for the rest of the process.

This probe never touches the installed skill tree. It imports the candidate module
out of the proposal package by file path, and works inside a fresh temp sandbox.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATE_RC = HERE / "candidate" / "solve-with-weilan" / "scripts" / "runtime_core.py"
BASELINE_RC = HERE / "baseline" / "solve-with-weilan" / "scripts" / "runtime_core.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    out = {}
    cand = load(CANDIDATE_RC, "cand_runtime_core")
    base = load(BASELINE_RC, "base_runtime_core")

    out["candidate_exports_clear"] = hasattr(cand, "clear_canonical_workspace_cache")
    out["candidate_contract"] = getattr(cand, "CANONICAL_WORKSPACE_CACHE_CONTRACT", None)

    sandbox = Path(tempfile.mkdtemp(prefix="wl_cachewin_"))
    out["sandbox_root"] = str(sandbox)

    real = sandbox / "real_ws"
    real.mkdir()
    link = sandbox / "linked_ws"  # does not exist yet

    # --- window 1: resolve before the junction exists, then create it -------
    before_cand = cand.canonical_workspace(str(link))
    before_base = base.canonical_workspace(str(link))
    rc = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(real)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out["mklink_rc"] = rc.returncode
    after_cand = cand.canonical_workspace(str(link))
    after_base = base.canonical_workspace(str(link))

    out["window_1_create_junction_after_first_resolve"] = {
        "candidate_before": before_cand,
        "candidate_after": after_cand,
        "baseline_before": before_base,
        "baseline_after": after_base,
        "baseline_changed_after_creation": before_base != after_base,
        "candidate_changed_after_creation": before_cand != after_cand,
        "candidate_diverges_from_baseline": after_cand != after_base,
        "real_target": str(real),
    }

    # --- does the documented escape hatch actually recover it? --------------
    cand.clear_canonical_workspace_cache()
    out["window_1_after_documented_clear"] = {
        "candidate": cand.canonical_workspace(str(link)),
        "baseline": base.canonical_workspace(str(link)),
        "recovers": cand.canonical_workspace(str(link)) == base.canonical_workspace(str(link)),
    }

    # --- window 2: retarget an existing junction in-process -----------------
    real2 = sandbox / "real_ws_2"
    real2.mkdir()
    link2 = sandbox / "retargeted_ws"
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link2), str(real)],
                   capture_output=True, text=True)
    w2_before_cand = cand.canonical_workspace(str(link2))
    w2_before_base = base.canonical_workspace(str(link2))
    os.rmdir(link2)
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link2), str(real2)],
                   capture_output=True, text=True)
    w2_after_cand = cand.canonical_workspace(str(link2))
    w2_after_base = base.canonical_workspace(str(link2))
    out["window_2_retarget_existing_junction"] = {
        "candidate_before": w2_before_cand,
        "candidate_after": w2_after_cand,
        "baseline_before": w2_before_base,
        "baseline_after": w2_after_base,
        "baseline_changed": w2_before_base != w2_after_base,
        "candidate_changed": w2_before_cand != w2_after_cand,
        "candidate_diverges_from_baseline": w2_after_cand != w2_after_base,
    }

    # --- is the divergence reachable from a real long-lived caller? ---------
    # The only long-lived callers of canonical_workspace in the shipped tree are
    # the pytest suite (one process, many tests) and wake_brief.py. Count how many
    # shipped test files build a workspace path and then mkdir/mklink it.
    scripts = HERE / "candidate" / "solve-with-weilan" / "scripts"
    callers = []
    for py in sorted(scripts.glob("*.py")):
        text = py.read_text(encoding="utf-8", errors="replace")
        if "canonical_workspace" in text:
            callers.append({
                "file": py.name,
                "is_test": py.name.startswith("test_"),
                "calls": text.count("canonical_workspace("),
            })
    out["in_tree_callers"] = callers
    out["clear_called_anywhere_in_tree"] = sum(
        p.read_text(encoding="utf-8", errors="replace").count(
            "clear_canonical_workspace_cache()")
        for p in scripts.glob("*.py")
    )

    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
