"""Verify source/frozen identities and the exact two-path candidate delta."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from evolution_core import changed_files, tree_hash  # noqa: E402

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a"
PREVIOUS_CAND = "ec236760072cf20d3a65df3eebd4c4075e86f79e64971b59375e4937fb3d956f"
EXPECTED = ["scripts/runtime_core.py", "scripts/test_canonical_workspace_cache.py"]
EXPECTED_REVISION = ["scripts/test_canonical_workspace_cache.py"]
OUT = HERE / "_probe_candidate_tree_diff.out.json"


def main():
    base_source = HERE / "baseline" / "solve-with-weilan"
    cand_source = HERE / "candidate" / "solve-with-weilan"
    base_frozen = HERE / "artifacts" / BASE / "solve-with-weilan"
    cand_frozen = HERE / "artifacts" / CAND / "solve-with-weilan"
    previous_cand_frozen = HERE / "artifacts" / PREVIOUS_CAND / "solve-with-weilan"
    changed = changed_files(base_frozen, cand_frozen)
    revision_changed = changed_files(previous_cand_frozen, cand_frozen)
    result = {
        "declared_base_artifact_hash": BASE,
        "declared_candidate_artifact_hash": CAND,
        "base_source_hash": tree_hash(base_source),
        "candidate_source_hash": tree_hash(cand_source),
        "base_frozen_hash": tree_hash(base_frozen),
        "candidate_frozen_hash": tree_hash(cand_frozen),
        "changed_paths": changed,
        "expected_changed_paths": EXPECTED,
        "exact_two_path_delta": changed == EXPECTED,
        "previous_candidate_artifact_hash": PREVIOUS_CAND,
        "revision_changed_paths": revision_changed,
        "expected_revision_changed_paths": EXPECTED_REVISION,
        "revision_changes_only_the_contract_test": revision_changed == EXPECTED_REVISION,
        "runtime_core_unchanged_from_previous_candidate": (
            (previous_cand_frozen / "scripts" / "runtime_core.py").read_bytes()
            == (cand_frozen / "scripts" / "runtime_core.py").read_bytes()
        ),
        "all_hashes_match": (
            tree_hash(base_source) == tree_hash(base_frozen) == BASE
            and tree_hash(cand_source) == tree_hash(cand_frozen) == CAND
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if (
        result["exact_two_path_delta"]
        and result["all_hashes_match"]
        and result["revision_changes_only_the_contract_test"]
        and result["runtime_core_unchanged_from_previous_candidate"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
