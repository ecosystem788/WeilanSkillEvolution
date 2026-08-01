"""Show that the cache contract test fails on baseline and passes on candidate."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"
TEST = "test_canonical_workspace_cache.py"
OUT = HERE / "_probe_contract_discrimination.out.json"
NODE_RE = re.compile(r"^(\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)")


def run_test(scripts_dir):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", TEST, "-v", "--no-header",
         "-p", "no:cacheprovider", "--tb=short"],
        cwd=scripts_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    nodes = {}
    for line in proc.stdout.splitlines():
        match = NODE_RE.match(line.strip())
        if match:
            nodes[match.group(1)] = match.group(2)
    combined = proc.stdout + "\n" + proc.stderr
    return {
        "returncode": proc.returncode,
        "nodes": nodes,
        "summary_line": (proc.stdout.strip().splitlines() or [""])[-1],
        "has_assertion_error": "AssertionError" in combined,
        "has_attribute_error": "AttributeError" in combined,
    }


def main():
    base_scripts = HERE / "artifacts" / BASE / "solve-with-weilan" / "scripts"
    cand_scripts = HERE / "artifacts" / CAND / "solve-with-weilan" / "scripts"
    candidate = run_test(cand_scripts)
    with tempfile.TemporaryDirectory(prefix="wl-cache-contract-") as temp:
        scratch = Path(temp) / "scripts"
        shutil.copytree(base_scripts, scratch)
        shutil.copy2(cand_scripts / TEST, scratch / TEST)
        baseline = run_test(scratch)
    result = {
        "base_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "test_file": TEST,
        "baseline_with_candidate_test_grafted": baseline,
        "candidate": candidate,
        "baseline_failed_by_assertion_not_attribute_error": (
            baseline["returncode"] == 1
            and sorted(baseline["nodes"].values()) == ["FAILED", "SKIPPED"]
            and baseline["has_assertion_error"]
            and not baseline["has_attribute_error"]
        ),
        "candidate_passed": (
            candidate["returncode"] == 0
            and list(candidate["nodes"].values()) == ["PASSED", "PASSED"]
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["baseline_failed_by_assertion_not_attribute_error"] and result["candidate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
