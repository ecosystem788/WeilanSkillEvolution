"""Read-only: Claude's INDEPENDENT acceptance + discrimination check of the
revised candidate fb16689a...

Two questions, both of which the receipt asserts and neither of which a reviewer
should take on the implementer's word:

  A. Suite acceptance. pytest over the frozen baseline and the frozen revised
     candidate under identical conditions. Acceptance is (returncode, collected
     node count, per-node verdict) -- never the phrase "all green", because
     pytest prints "no tests collected" under rc 0, 2 and 5 alike. The claim
     under test: baseline 92 pass + 1 shared fail, candidate 103 pass + the same
     shared fail, exactly +11 nodes, zero candidate-only failures.

  B. Discrimination. A regression test that passes against an implementation
     without the guard proves nothing. So the new test file is also run against
     a tree that is the revised candidate with scripts/weilan_trace.py swapped
     back to the SUPERSEDED unguarded candidate (794022d9...). T2
     (test_foreign_second_file_rebuilds_after_observable_mtime_change) must fail
     there. If it passes, the guard is not what makes it green and the test is
     decorative.

     The same-tick residual test is expected to error rather than fail in arm B:
     it reaches for weilan_trace._FRAME_INDEX_DIR_MTIMES, which the unguarded
     version does not define. That is recorded, not scored as discrimination.

Arm B stages into a temp directory; the frozen trees are never written to.
Emits JSON to stdout.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "fb16689a63538f39d35374a123c860c0bfbfddeca900fd10027483c865830996"
UNGUARDED = "794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b"
HERE = os.path.dirname(os.path.abspath(__file__))
NODE_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)")
T2_NODE = ("test_find_frame_index.py::"
           "test_foreign_second_file_rebuilds_after_observable_mtime_change")
RESIDUAL_NODE = ("test_find_frame_index.py::"
                 "test_same_mtime_tick_residual_is_pinned_not_hidden")


def scripts_of(digest):
    return os.path.join(HERE, "artifacts", digest, "solve-with-weilan", "scripts")


def pytest_run(scripts_dir, target, timeout):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", target, "-v", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=scripts_dir, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
    )
    nodes = {}
    for line in proc.stdout.splitlines():
        match = NODE_RE.match(line.strip())
        if match:
            nodes[match.group(1)] = match.group(2)
    verdicts = {}
    for verdict in nodes.values():
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
    return {
        "returncode": proc.returncode,
        "collected_node_count": len(nodes),
        "verdict_counts": verdicts,
        "non_passing_nodes": sorted(
            node for node, verdict in nodes.items()
            if verdict not in ("PASSED", "SKIPPED", "XFAIL")
        ),
        "nodes": {node: nodes[node] for node in sorted(nodes)},
        "summary_line": (proc.stdout.strip().splitlines() or [""])[-1],
    }


def main():
    timeout = int(os.environ.get("WEILAN_PROBE_TIMEOUT", "1800"))
    result = {"probe": "claude_revision_acceptance",
              "checked_by": "claude (reviewer, not implementer)",
              "base_artifact_hash": BASE, "candidate_artifact_hash": CAND}

    arm_a = {}
    for label, digest in (("baseline", BASE), ("candidate", CAND)):
        arm_a[label] = pytest_run(scripts_of(digest), ".", timeout)
    base_nodes = set(arm_a["baseline"]["nodes"])
    cand_nodes = set(arm_a["candidate"]["nodes"])
    base_bad = set(arm_a["baseline"]["non_passing_nodes"])
    cand_bad = set(arm_a["candidate"]["non_passing_nodes"])
    arm_a["delta"] = {
        "new_nodes": sorted(cand_nodes - base_nodes),
        "new_node_count": len(cand_nodes - base_nodes),
        "removed_nodes": sorted(base_nodes - cand_nodes),
        "candidate_only_failures": sorted(cand_bad - base_bad),
        "shared_failures": sorted(cand_bad & base_bad),
        "baseline_only_failures": sorted(base_bad - cand_bad),
    }
    result["arm_a_suite"] = arm_a

    staged = tempfile.mkdtemp(prefix="wl-unguarded-")
    try:
        shutil.copytree(scripts_of(CAND), os.path.join(staged, "scripts"))
        shutil.copyfile(
            os.path.join(scripts_of(UNGUARDED), "weilan_trace.py"),
            os.path.join(staged, "scripts", "weilan_trace.py"),
        )
        arm_b = pytest_run(os.path.join(staged, "scripts"),
                           "test_find_frame_index.py", timeout)
    finally:
        shutil.rmtree(staged, ignore_errors=True)

    arm_c = pytest_run(scripts_of(CAND), "test_find_frame_index.py", timeout)

    result["arm_b_new_tests_against_unguarded_implementation"] = {
        "swapped_weilan_trace_from": UNGUARDED,
        "run": arm_b,
        "t2_verdict": arm_b["nodes"].get(T2_NODE),
        "t2_discriminates": arm_b["nodes"].get(T2_NODE) in ("FAILED", "ERROR"),
        "residual_test_verdict": arm_b["nodes"].get(RESIDUAL_NODE),
    }
    result["arm_c_new_tests_against_revised_candidate"] = {
        "run": arm_c,
        "t2_verdict": arm_c["nodes"].get(T2_NODE),
        "residual_test_verdict": arm_c["nodes"].get(RESIDUAL_NODE),
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
