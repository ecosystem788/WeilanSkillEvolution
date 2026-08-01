"""Compare complete frozen-tree regression outcomes, including script-style tests."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"
OUT = HERE / "_probe_suite_acceptance.out.json"
NODE_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)")


def pytest_run(scripts_dir, timeout):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", ".", "-v", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=scripts_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    nodes = {}
    for line in proc.stdout.splitlines():
        match = NODE_RE.match(line.strip())
        if match:
            nodes[match.group(1)] = match.group(2)
    return {
        "returncode": proc.returncode,
        "collected_node_count": len(nodes),
        "nodes": nodes,
        "non_passing_nodes": sorted(
            node for node, verdict in nodes.items()
            if verdict not in ("PASSED", "SKIPPED", "XFAIL")
        ),
        "summary_line": (proc.stdout.strip().splitlines() or [""])[-1],
    }


def main_style_files(scripts_dir):
    found = []
    for path in sorted(scripts_dir.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        if "\ndef main(" in text and "__main__" in text:
            found.append(path.name)
    return found


def script_runs(scripts_dir, names, timeout):
    results = {}
    for name in names:
        try:
            proc = subprocess.run(
                [sys.executable, "-X", "utf8", name],
                cwd=scripts_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
            results[name] = {
                "returncode": proc.returncode,
                "stderr_tail": proc.stderr.strip()[-300:] if proc.returncode else "",
            }
        except subprocess.TimeoutExpired:
            results[name] = {"returncode": None, "stderr_tail": "TIMEOUT"}
    return results


def main():
    timeout = int(os.environ.get("WEILAN_PROBE_TIMEOUT", "1800"))
    trees = {}
    for label, digest in (("baseline", BASE), ("candidate", CAND)):
        scripts_dir = HERE / "artifacts" / digest / "solve-with-weilan" / "scripts"
        names = main_style_files(scripts_dir)
        pytest = pytest_run(scripts_dir, timeout)
        scripts = script_runs(scripts_dir, names, timeout)
        trees[label] = {
            "pytest": pytest,
            "main_style_file_count": len(names),
            "main_style_runs": scripts,
            "main_style_nonzero": sorted(
                name for name, row in scripts.items() if row["returncode"] != 0
            ),
        }
    baseline_nodes = trees["baseline"]["pytest"]["nodes"]
    candidate_nodes = trees["candidate"]["pytest"]["nodes"]
    candidate_only_failures = sorted(
        node for node, verdict in candidate_nodes.items()
        if verdict in ("FAILED", "ERROR", "XPASS")
        and baseline_nodes.get(node) not in ("FAILED", "ERROR", "XPASS")
    )
    result = {
        "base_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "trees": trees,
        "candidate_only_nodes": sorted(set(candidate_nodes) - set(baseline_nodes)),
        "baseline_only_nodes": sorted(set(baseline_nodes) - set(candidate_nodes)),
        "candidate_only_failures": candidate_only_failures,
        "main_style_nonzero_equal": (
            trees["baseline"]["main_style_nonzero"]
            == trees["candidate"]["main_style_nonzero"]
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    passed = (
        not result["baseline_only_nodes"]
        and result["candidate_only_nodes"] == [
            "test_canonical_workspace_cache.py::test_resolution_is_fixed_in_process_and_repeated_in_a_new_process"
        ]
        and not candidate_only_failures
        and result["main_style_nonzero_equal"]
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
