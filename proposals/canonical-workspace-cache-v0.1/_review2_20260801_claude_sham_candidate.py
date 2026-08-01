"""Does the revised contract test discriminate BEHAVIOUR, or only API presence?

My 12:45:34 objection was that the previous test died on its first line with
AttributeError, so it would have shown identical discriminating power against a
sham candidate that adds `clear_canonical_workspace_cache` and the contract
constant while caching nothing. Codex's revision claims to fix that. Reasoning
about the source is not proof, so this probe builds exactly that sham candidate
and runs the revised test against it.

Read-only with respect to the repository and both install points: the sham tree
is built in a temp directory from a copy of the frozen baseline and deleted.
"""

import hashlib
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
CONTRACT = "test_canonical_workspace_cache.py"
OUT = HERE / "_review2_20260801_claude_sham_candidate.out.json"

# The sham: every symbol the test can name, none of the behaviour it asserts.
SHAM_APPENDIX = '''

CANONICAL_WORKSPACE_CACHE_CACHE = {}

CANONICAL_WORKSPACE_CACHE_CONTRACT = (
    "The same expanded workspace path is resolved once per process. "
    "A new process resolves it again. Long-lived callers must clear explicitly."
)


def clear_canonical_workspace_cache():
    """Sham: advertises the cache-control boundary and caches nothing."""
    CANONICAL_WORKSPACE_CACHE_CACHE.clear()
'''


def art(digest):
    return HERE / "artifacts" / digest / "solve-with-weilan"


def run_contract(scripts_dir):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", CONTRACT, "-v", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=str(scripts_dir), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )
    text = proc.stdout + proc.stderr
    verdicts = {}
    for line in text.splitlines():
        s = line.strip()
        m = re.match(rf"^({re.escape(CONTRACT)}::\S+)\s+(PASSED|FAILED|ERROR|SKIPPED)", s)
        if m:
            verdicts[m.group(1)] = m.group(2)
    return {
        "returncode": proc.returncode,
        "verdicts": verdicts,
        "has_attribute_error": "AttributeError" in text,
        "has_assertion_error": "AssertionError" in text,
        "summary_line": (proc.stdout.strip().splitlines() or [""])[-1],
    }


def main():
    tmp = Path(tempfile.mkdtemp(prefix="claude-sham-"))
    try:
        sham = tmp / "sham-candidate"
        shutil.copytree(art(BASE), sham)
        rc = sham / "scripts" / "runtime_core.py"
        baseline_src = rc.read_text(encoding="utf-8")
        rc.write_text(baseline_src + SHAM_APPENDIX, encoding="utf-8")
        shutil.copy2(art(CAND) / "scripts" / CONTRACT, sham / "scripts" / CONTRACT)

        # Prove the sham really exposes the API the old test tripped on.
        api_probe = subprocess.run(
            [sys.executable, "-X", "utf8", "-c",
             "import runtime_core as m; "
             "print(hasattr(m, 'clear_canonical_workspace_cache'), "
             "'A new process resolves it again' in m.CANONICAL_WORKSPACE_CACHE_CONTRACT)"],
            cwd=str(sham / "scripts"), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120,
        )

        result = {
            "author": "claude",
            "question": "does the revised contract test fail on a cache-free sham that has the API?",
            "sham_construction": (
                "frozen baseline runtime_core.py + a no-op clear_canonical_workspace_cache() "
                "and a CANONICAL_WORKSPACE_CACHE_CONTRACT string; canonical_workspace itself "
                "is the baseline's, byte for byte, so nothing is cached"
            ),
            "sham_runtime_core_sha256": hashlib.sha256(rc.read_bytes()).hexdigest(),
            "baseline_runtime_core_sha256": hashlib.sha256(
                (art(BASE) / "scripts" / "runtime_core.py").read_bytes()).hexdigest(),
            "candidate_runtime_core_sha256": hashlib.sha256(
                (art(CAND) / "scripts" / "runtime_core.py").read_bytes()).hexdigest(),
            "sham_exposes_api_stdout": api_probe.stdout.strip(),
            "sham_arm": run_contract(sham / "scripts"),
            "real_candidate_arm": run_contract(art(CAND) / "scripts"),
        }
        s = result["sham_arm"]
        per_test = s["verdicts"]
        result["conclusion"] = {
            "sham_is_rejected": s["returncode"] != 0,
            "sham_rejected_by_assertion_not_attribute_error":
                s["has_assertion_error"] and not s["has_attribute_error"],
            "which_tests_catch_the_sham": sorted(
                n for n, v in per_test.items() if v in ("FAILED", "ERROR")),
            "which_tests_the_sham_passes": sorted(
                n for n, v in per_test.items() if v == "PASSED"),
        }
        OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({k: result[k] for k in
                          ("sham_exposes_api_stdout", "sham_arm", "real_candidate_arm",
                           "conclusion")}, indent=2, ensure_ascii=False))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
