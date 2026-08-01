"""Claude's independent byte + discriminator re-verification of the REVISED candidate.

Read-only. Recomputes every hash from the official tools/evolution_core.tree_hash
rather than trusting any hash string written in the package, and re-runs the
discriminator by grafting the revised contract test onto a throwaway copy of the
frozen baseline tree (the baseline artifact tree itself is never written to).
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "tools"))
from evolution_core import tree_hash, changed_files  # noqa: E402

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"
PREV = "ec236760072cf20d3a65df3eebd4c4075e86f79e64971b59375e4937fb3d956f"
CONTRACT = "test_canonical_workspace_cache.py"
INSTALLS = {
    "claude_install": r"C:\Users\zy\.claude\skills\solve-with-weilan",
    "codex_install": r"D:\CodexData\skills\solve-with-weilan",
    "repo_mirror": str(REPO / "skill" / "solve-with-weilan"),
}
OUT = HERE / "_review2_20260801_claude_bytes_and_discriminator.out.json"


def art(digest):
    return HERE / "artifacts" / digest / "solve-with-weilan"


def fsha(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def pytest_on(scripts_dir, target):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pytest", target, "-v", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=str(scripts_dir), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )
    text = proc.stdout + proc.stderr
    verdicts = {}
    for line in text.splitlines():
        s = line.strip()
        for v in ("PASSED", "FAILED", "ERROR", "SKIPPED"):
            if s.startswith(f"{target}::") and f" {v}" in s:
                verdicts[s.split(" ")[0]] = v
    return {
        "returncode": proc.returncode,
        "verdicts": verdicts,
        "has_attribute_error": "AttributeError" in text,
        "has_assertion_error": "AssertionError" in text,
        "has_collection_error": "ERROR collecting" in text or "INTERNALERROR" in text,
        "summary_line": (proc.stdout.strip().splitlines() or [""])[-1],
    }


def main():
    r = {"author": "claude", "purpose": "independent re-verification of revised candidate"}

    # 1. Recompute every declared tree hash from the official tool.
    r["recomputed_tree_hashes"] = {
        "artifacts/baseline": tree_hash(art(BASE)),
        "artifacts/candidate_revised": tree_hash(art(CAND)),
        "artifacts/candidate_previous": tree_hash(art(PREV)),
        "working_baseline_dir": tree_hash(HERE / "baseline" / "solve-with-weilan"),
        "working_candidate_dir": tree_hash(HERE / "candidate" / "solve-with-weilan"),
    }
    r["hash_matches_declared"] = {
        "baseline": r["recomputed_tree_hashes"]["artifacts/baseline"] == BASE,
        "candidate_revised": r["recomputed_tree_hashes"]["artifacts/candidate_revised"] == CAND,
        "candidate_previous": r["recomputed_tree_hashes"]["artifacts/candidate_previous"] == PREV,
        "working_candidate_equals_frozen_revised":
            r["recomputed_tree_hashes"]["working_candidate_dir"] == CAND,
        "working_baseline_equals_frozen_baseline":
            r["recomputed_tree_hashes"]["working_baseline_dir"] == BASE,
    }

    # 2. Delta shape: baseline->revised must be exactly the two declared paths;
    #    previous->revised must be the test file only, runtime_core byte-identical.
    r["changed_baseline_to_revised"] = changed_files(art(BASE), art(CAND))
    r["changed_previous_to_revised"] = changed_files(art(PREV), art(CAND))
    r["runtime_core_sha256"] = {
        k: fsha(art(d) / "scripts" / "runtime_core.py")
        for k, d in (("baseline", BASE), ("previous", PREV), ("revised", CAND))
    }
    r["contract_test_sha256"] = {
        k: fsha(art(d) / "scripts" / CONTRACT)
        for k, d in (("baseline", BASE), ("previous", PREV), ("revised", CAND))
    }

    # 3. Install points must still equal the frozen baseline (zero deployment).
    r["install_points"] = {}
    for label, path in INSTALLS.items():
        p = Path(path)
        r["install_points"][label] = {
            "path": path,
            "exists": p.is_dir(),
            "tree_hash": tree_hash(p) if p.is_dir() else None,
            "equals_frozen_baseline": (tree_hash(p) == BASE) if p.is_dir() else None,
            "differs_from_baseline_paths": changed_files(art(BASE), p) if p.is_dir() else None,
        }

    # 4. Discriminator, run by me: revised test grafted onto a throwaway baseline copy.
    tmp = Path(tempfile.mkdtemp(prefix="claude-discrim-"))
    try:
        grafted = tmp / "baseline-with-revised-test"
        shutil.copytree(art(BASE), grafted)
        shutil.copy2(art(CAND) / "scripts" / CONTRACT, grafted / "scripts" / CONTRACT)
        r["graft_check"] = {
            "grafted_contract_sha256": fsha(grafted / "scripts" / CONTRACT),
            "grafted_runtime_core_sha256": fsha(grafted / "scripts" / "runtime_core.py"),
            "graft_touched_only_contract_file":
                changed_files(art(BASE), grafted) == [f"scripts/{CONTRACT}"],
        }
        r["discriminator"] = {
            "baseline_with_revised_test": pytest_on(grafted / "scripts", CONTRACT),
            "revised_candidate": pytest_on(art(CAND) / "scripts", CONTRACT),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    b = r["discriminator"]["baseline_with_revised_test"]
    c = r["discriminator"]["revised_candidate"]
    r["verdict_facets"] = {
        "baseline_fails_by_assertion_without_attribute_error":
            b["returncode"] != 0 and b["has_assertion_error"] and not b["has_attribute_error"],
        "baseline_verdicts": b["verdicts"],
        "candidate_all_passed":
            c["returncode"] == 0 and set(c["verdicts"].values()) == {"PASSED"},
        "candidate_verdicts": c["verdicts"],
        "zero_deployment":
            all(v["equals_frozen_baseline"] for k, v in r["install_points"].items()
                if k in ("claude_install", "codex_install")),
    }
    OUT.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "hash_matches_declared": r["hash_matches_declared"],
        "changed_baseline_to_revised": r["changed_baseline_to_revised"],
        "changed_previous_to_revised": r["changed_previous_to_revised"],
        "runtime_core_prev_eq_revised":
            r["runtime_core_sha256"]["previous"] == r["runtime_core_sha256"]["revised"],
        "graft_check": r["graft_check"],
        "verdict_facets": r["verdict_facets"],
        "install_equals_baseline": {
            k: v["equals_frozen_baseline"] for k, v in r["install_points"].items()},
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
