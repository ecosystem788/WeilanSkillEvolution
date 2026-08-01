"""Claude's independent full-suite comparison for the REVISED candidate.

Written from scratch (not a copy of _probe_suite_acceptance.py) because that
probe's on-disk .out.json is contested by its own author's receipt, which states
no revised full-suite result was written. Read-only with respect to the two real
install points and the repository ledgers: it only runs pytest inside the two
frozen artifact trees.
"""

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"
OUT = HERE / "_review2_20260801_claude_independent_suite.out.json"

# pytest -v prints "<nodeid> <VERDICT>"; also accept the "<VERDICT> <nodeid>" order
# some plugins emit, so a formatting difference cannot silently zero the census.
FORWARD = re.compile(r"^(\S+\.py::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b")
REVERSE = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S+\.py::\S+)")


def tree_scripts(digest):
    return HERE / "artifacts" / digest / "solve-with-weilan" / "scripts"


def contract_test_sha256(digest):
    p = tree_scripts(digest) / "test_canonical_workspace_cache.py"
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def runtime_core_sha256(digest):
    p = tree_scripts(digest) / "runtime_core.py"
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_arm(label, digest, timeout):
    scripts = tree_scripts(digest)
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", ".", "-v", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=str(scripts),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    nodes = {}
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        m = FORWARD.match(line)
        if m:
            nodes[m.group(1)] = m.group(2)
            continue
        m = REVERSE.match(line)
        if m:
            nodes[m.group(2)] = m.group(1)
    return {
        "label": label,
        "artifact_hash": digest,
        "scripts_dir": str(scripts),
        "returncode": proc.returncode,
        "wall_seconds": round(time.time() - started, 3),
        "node_count": len(nodes),
        "nodes": nodes,
        "failing_nodes": sorted(n for n, v in nodes.items() if v in ("FAILED", "ERROR")),
        "skipped_nodes": sorted(n for n, v in nodes.items() if v == "SKIPPED"),
        "summary_line": (proc.stdout.strip().splitlines() or [""])[-1],
        "runtime_core_sha256": runtime_core_sha256(digest),
        "contract_test_sha256": contract_test_sha256(digest),
    }


def main():
    result = {
        "author": "claude",
        "purpose": "independent revised-candidate full-suite comparison",
        "base_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "boundary": (
            "Arms run sequentially on this host with no load control. Verdict sets, "
            "not wall time, are the load-bearing output; the wall_seconds field is "
            "recorded only so a future reader can see the arms were comparable in cost."
        ),
        "arms": {},
    }
    for label, digest in (("baseline", BASE), ("candidate", CAND)):
        try:
            result["arms"][label] = run_arm(label, digest, timeout=1500)
        except subprocess.TimeoutExpired:
            result["arms"][label] = {
                "label": label, "artifact_hash": digest, "returncode": None,
                "error": "TIMEOUT_1500s", "node_count": 0, "nodes": {},
            }
    base_nodes = result["arms"]["baseline"].get("nodes", {})
    cand_nodes = result["arms"]["candidate"].get("nodes", {})
    result["candidate_only_nodes"] = sorted(set(cand_nodes) - set(base_nodes))
    result["baseline_only_nodes"] = sorted(set(base_nodes) - set(cand_nodes))
    result["candidate_only_failures"] = sorted(
        n for n in cand_nodes
        if cand_nodes[n] in ("FAILED", "ERROR")
        and base_nodes.get(n) not in ("FAILED", "ERROR")
    )
    result["shared_nodes_with_changed_verdict"] = {
        n: {"baseline": base_nodes[n], "candidate": cand_nodes[n]}
        for n in sorted(set(base_nodes) & set(cand_nodes))
        if base_nodes[n] != cand_nodes[n]
    }
    result["runtime_core_identical_across_arms"] = (
        result["arms"]["baseline"].get("runtime_core_sha256")
        == result["arms"]["candidate"].get("runtime_core_sha256")
    )
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "candidate_only_failures": result["candidate_only_failures"],
        "candidate_only_nodes": result["candidate_only_nodes"],
        "baseline_only_nodes": result["baseline_only_nodes"],
        "changed_verdicts": result["shared_nodes_with_changed_verdict"],
        "baseline_rc": result["arms"]["baseline"].get("returncode"),
        "candidate_rc": result["arms"]["candidate"].get("returncode"),
        "baseline_nodes": result["arms"]["baseline"].get("node_count"),
        "candidate_nodes": result["arms"]["candidate"].get("node_count"),
    }, indent=2))


if __name__ == "__main__":
    main()
