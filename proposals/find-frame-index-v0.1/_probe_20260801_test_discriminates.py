"""Run the new regression file against the FROZEN BASELINE tree as well as the
candidate, and report honestly what that comparison does and does not show.

NEGATIVE RESULT, stated up front: this probe does NOT establish behavioural
discrimination. The test file calls invalidate_frame_index(), which does not
exist on the baseline, so on the baseline every test ERRORs at fixture setup.
An all-ERROR run proves the API is absent, not that any behaviour differs --
reading it as "10 behaviours differ" would be the zero-hit-read-as-zero-input
error this line has hit before. Behavioural equivalence is established instead
by _probe_20260801_find_frame_equivalence.py, which drives identical scenarios
through both implementations.

What this probe is still good for: it pins the candidate-side acceptance run
(rc + node list, not the word "green"), and it records the setup-error fact so
nobody re-derives it. It copies only the test file into a scratch copy of the
baseline scripts dir -- the frozen artifacts are never modified.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b"
HERE = os.path.dirname(os.path.abspath(__file__))
TEST = "test_find_frame_index.py"


def run_pytest(scripts_dir):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", TEST, "-v", "--no-header", "-p",
         "no:cacheprovider"],
        cwd=scripts_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    nodes = {}
    for line in proc.stdout.splitlines():
        if "::" in line and ("PASSED" in line or "FAILED" in line or "ERROR" in line):
            node = line.split(" ")[0]
            verdict = (
                "PASSED" if "PASSED" in line
                else "FAILED" if "FAILED" in line
                else "ERROR"
            )
            nodes[node] = verdict
    return {
        "returncode": proc.returncode,
        "collected_node_count": len(nodes),
        "nodes": nodes,
        "passed": sum(1 for v in nodes.values() if v == "PASSED"),
        "failed": sum(1 for v in nodes.values() if v != "PASSED"),
        "tail": proc.stdout.strip().splitlines()[-1:] or [""],
    }


def main():
    cand_scripts = os.path.join(HERE, "artifacts", CAND, "solve-with-weilan", "scripts")
    candidate = run_pytest(cand_scripts)

    base_scripts = os.path.join(HERE, "artifacts", BASE, "solve-with-weilan", "scripts")
    with tempfile.TemporaryDirectory(prefix="ffi-baseline-") as tmp:
        scratch = os.path.join(tmp, "scripts")
        shutil.copytree(base_scripts, scratch)
        shutil.copy2(os.path.join(cand_scripts, TEST), os.path.join(scratch, TEST))
        baseline = run_pytest(scratch)

    real_nodes = {k: v for k, v in baseline["nodes"].items() if "::" in k}
    all_error_at_setup = bool(real_nodes) and all(
        v == "ERROR" for v in real_nodes.values()
    )
    result = {
        "test_file": TEST,
        "candidate": candidate,
        "baseline_with_test_file_grafted": baseline,
        "baseline_nodes_all_error_at_setup": all_error_at_setup,
        "baseline_error_cause": (
            "weilan_trace.invalidate_frame_index does not exist on the baseline, so the "
            "fixture raises AttributeError before any assertion runs"
        ),
        "behavioural_discrimination_established_here": False,
        "behavioural_discrimination_evidence_lives_in":
            "_probe_20260801_find_frame_equivalence.py",
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
