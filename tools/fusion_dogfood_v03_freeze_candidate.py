"""Build draft B1/B2 freeze-engineering candidate artifacts for v0.3 keep cases."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from fusion_dogfood_v03_harness import canonical_json, file_sha256, receipt_hash, sha256_text, tree_snapshot, write_json


ROOT = Path(__file__).resolve().parents[1]
SUITE_ID = "fusion-dogfood-v0.3"
KEEP_CASES = [
    "fusion-v03-stale-holder-collapse",
    "fusion-v03-budget-bound-ledger-triage",
]


def copy_tree_public_files(source: Path, destination: Path) -> list[dict]:
    rows = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        rows.append({
            "source_path": path.relative_to(ROOT).as_posix(),
            "fixture_path": target.relative_to(ROOT).as_posix(),
            "sha256": file_sha256(target),
            "bytes": target.stat().st_size,
            "redacted_fields": [],
        })
    return rows


def build_candidate(case_flow_root: Path, output_root: Path) -> dict:
    case_flow_root = Path(case_flow_root).resolve()
    output_root = Path(output_root).resolve()
    allowed_parent = (ROOT / "proposals" / "fusion-dogfood-extension-v0.3" / "freeze-candidates").resolve()
    if allowed_parent not in output_root.parents and output_root != allowed_parent:
        raise ValueError(f"output root must be under {allowed_parent}")
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    source_hash_rows = []
    case_rows = []
    for case_id in KEEP_CASES:
        public_case_path = case_flow_root / "case-designs" / f"{case_id}.json"
        public_case = json.loads(public_case_path.read_text(encoding="utf-8"))
        source_fixture = case_flow_root / "fixtures" / case_id
        destination_fixture = output_root / "fixtures" / case_id
        file_rows = copy_tree_public_files(source_fixture, destination_fixture)
        source_hash_rows.extend(file_rows)
        fixture_manifest = {
            "schema_version": "fusion_dogfood_fixture_manifest_v0.3",
            "suite_id": SUITE_ID,
            "case_id": case_id,
            "status": "draft_unfrozen",
            "source_fixture_root": source_fixture.relative_to(ROOT).as_posix(),
            "fixture_root": destination_fixture.relative_to(ROOT).as_posix(),
            "public_files": {row["fixture_path"]: row["sha256"] for row in file_rows},
            "redacted_fields": [],
            "tree_snapshot": tree_snapshot(destination_fixture),
            "hidden_artifacts_included": False,
        }
        fixture_manifest["manifest_hash"] = receipt_hash(fixture_manifest)
        write_json(destination_fixture / "fixture-manifest.json", fixture_manifest)
        source_hash_rows.append({
            "source_path": "generated fixture manifest",
            "fixture_path": (destination_fixture / "fixture-manifest.json").relative_to(ROOT).as_posix(),
            "sha256": file_sha256(destination_fixture / "fixture-manifest.json"),
            "bytes": (destination_fixture / "fixture-manifest.json").stat().st_size,
            "redacted_fields": [],
        })
        case_rows.append({
            "case_id": case_id,
            "public_case_design": public_case_path.relative_to(ROOT).as_posix(),
            "public_case_spec": public_case["public_case_spec"],
            "fixture_manifest": (destination_fixture / "fixture-manifest.json").relative_to(ROOT).as_posix(),
            "fixture_manifest_hash": fixture_manifest["manifest_hash"],
        })

    source_hashes = {
        "schema_version": "fusion_dogfood_source_hashes_v0.3",
        "suite_id": SUITE_ID,
        "status": "draft_unfrozen",
        "rows": source_hash_rows,
        "hidden_artifacts_included": False,
    }
    source_hashes["source_hashes_hash"] = receipt_hash(source_hashes)
    write_json(output_root / "source-hashes.json", source_hashes)

    case_set = {
        "schema_version": "fusion_dogfood_case_set_v0.3_draft",
        "suite_id": SUITE_ID,
        "status": "draft_unfrozen",
        "case_count": len(case_rows),
        "cases": case_rows,
        "freeze_ready": False,
        "freeze_blockers": [
            "R1 requires 3-5 new headroom cases; only two cases are confirmed keep",
            "cross-window case remains redesigned/blocked pending clean no-method execution surface",
            "owner one-shot approval freeze has not been requested or granted",
        ],
        "hidden_artifacts_included": False,
    }
    case_set["case_set_hash"] = sha256_text(canonical_json(case_set))
    write_json(output_root / "CASE_SET_DRAFT.json", case_set)

    receipt = {
        "schema_version": "fusion_dogfood_v03_b1b2_engineering_receipt_v0.1",
        "suite_id": SUITE_ID,
        "status": "draft_unfrozen_engineering_candidate",
        "case_ids": KEEP_CASES,
        "case_set": (output_root / "CASE_SET_DRAFT.json").relative_to(ROOT).as_posix(),
        "case_set_hash": case_set["case_set_hash"],
        "source_hashes": (output_root / "source-hashes.json").relative_to(ROOT).as_posix(),
        "source_hashes_hash": source_hashes["source_hashes_hash"],
        "calibration_evidence": {
            "real_rescored_aggregate": "proposals/fusion-dogfood-extension-v0.3/case-flow/calibration/real-baseline-2c539d0b-20260705/REAL_CALIBRATION_AGGREGATE_RESCORED.json",
            "stale_holder_short_rerun": "v03runs/stale-short-rerun/SHORT_RERUN_RESULT.json",
            "budget_winnability": "proposals/fusion-dogfood-extension-v0.3/case-flow/calibration/real-baseline-2c539d0b-20260705/BUDGET_WINNABILITY_VALIDATION.json",
        },
        "forbidden_actions_preserved": [
            "no evals/manifest.json edit",
            "no owner freeze",
            "no approval file",
            "no adoption",
            "no deployment",
            "no deployed Skill edit",
        ],
        "hidden_artifacts_included": False,
    }
    receipt["receipt_hash"] = receipt_hash(receipt)
    write_json(output_root / "B1_B2_ENGINEERING_RECEIPT.json", receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-flow-root", default="proposals/fusion-dogfood-extension-v0.3/case-flow")
    parser.add_argument("--output-root", default="proposals/fusion-dogfood-extension-v0.3/freeze-candidates/stale-budget-b1b2")
    args = parser.parse_args(argv)
    result = build_candidate(ROOT / args.case_flow_root, ROOT / args.output_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
