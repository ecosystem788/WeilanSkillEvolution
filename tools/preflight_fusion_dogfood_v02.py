"""Preflight validation for the draft fusion-dogfood-v0.2 suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE = "fusion-dogfood-v0.2"
V1_CASE_HASH = "355465c562cea211108095267d3dc659d0e6f72f59d7615eff2b3653b57c68d1"
V1_CASE_FILE_HASH = "045cb6e8119eb7e68d89edca013de2bce949221e799ff223c72ceab484ac17ac"


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(rel_path: str):
    return json.loads((ROOT / rel_path).read_text(encoding="utf-8"))


def add_issue(bucket, condition, message):
    if not condition:
        bucket.append(message)


def validate(args):
    structural_issues = []
    freeze_blockers = []

    case_path = ROOT / "evals" / "cases" / f"{SUITE}.draft.json"
    manifest_path = ROOT / "evals" / f"{SUITE}-manifest.draft.json"
    source_hash_path = ROOT / "evals" / "hidden" / SUITE / "source-hashes.json"
    hidden_independence_path = ROOT / "evals" / "hidden" / SUITE / "hidden-artifact-independence.json"
    calibration_path = ROOT / "proposals" / "fusion-dogfood-extension-v0.2" / "calibration" / "calibration-plan.draft.json"
    snapshot_root = ROOT / "proposals" / "fusion-dogfood-extension-v0.2" / "source-snapshots"

    for path in [case_path, manifest_path, source_hash_path, hidden_independence_path, calibration_path]:
        add_issue(structural_issues, path.exists(), f"missing required artifact: {path.relative_to(ROOT).as_posix()}")
    if structural_issues:
        return {"suite_id": SUITE, "structural_valid": False, "freeze_ready": False, "structural_issues": structural_issues, "freeze_blockers": ["missing required files"]}

    v1_case_path = ROOT / "evals" / "cases" / "fusion-dogfood-v0.1.json"
    v1_cases = json.loads(v1_case_path.read_text(encoding="utf-8"))
    add_issue(structural_issues, sha_file(v1_case_path) == V1_CASE_FILE_HASH, "v0.1 case file sha256 changed")
    add_issue(structural_issues, sha_text(canonical_json(v1_cases)) == V1_CASE_HASH, "v0.1 case canonical sha256 changed")

    case_set = json.loads(case_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_hashes = json.loads(source_hash_path.read_text(encoding="utf-8"))
    hidden_independence = json.loads(hidden_independence_path.read_text(encoding="utf-8"))
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))

    add_issue(structural_issues, case_set.get("suite_id") == SUITE, "case-set suite_id mismatch")
    add_issue(structural_issues, case_set.get("status") == "draft_unfrozen" and case_set.get("frozen") is False, "case-set must remain draft_unfrozen")
    add_issue(structural_issues, manifest.get("status") == "draft" and manifest.get("frozen") is False, "manifest must remain draft")
    add_issue(structural_issues, manifest.get("case_spec_hash") == sha_text(canonical_json(case_set)), "manifest case_spec_hash mismatch")
    add_issue(structural_issues, manifest.get("case_spec_file_sha256") == sha_file(case_path), "manifest case_spec_file_sha256 mismatch")

    v1_count = len(v1_cases.get("cases", []))
    cases = case_set.get("cases", [])
    new_cases = cases[v1_count:]
    headroom_cases = [case for case in new_cases if case.get("guardrail_case") is not True]
    guardrail_cases = [case for case in new_cases if case.get("guardrail_case") is True]
    new_case_ids = [case.get("case_id") for case in new_cases]
    add_issue(structural_issues, len(new_cases) in {4, 5, 6}, "new case count must be 4-6")
    add_issue(structural_issues, case_set.get("new_case_ids") == new_case_ids, "new_case_ids does not match case tail")
    add_issue(structural_issues, cases[:v1_count] == v1_cases.get("cases", []), "v0.1 inherited cases are not verbatim in draft case-set")

    for case in new_cases:
        cid = case.get("case_id", "<missing>")
        add_issue(structural_issues, case.get("level") in {"L2", "L3"}, f"{cid}: new cases must be L2/L3")
        add_issue(structural_issues, case.get("trial_count") == 2, f"{cid}: trial_count must be 2")
        add_issue(structural_issues, "method_impact_trace" in case.get("expected_receipt_fields", []), f"{cid}: method_impact_trace missing")
        add_issue(structural_issues, bool(case.get("fixture_sources")), f"{cid}: fixture_sources missing")
        add_issue(structural_issues, abs(sum(case.get("scoring_weights", {}).values()) - 1.0) < 1e-9, f"{cid}: scoring weights must sum to 1")
        if case.get("guardrail_case") is True:
            add_issue(structural_issues, case.get("excluded_from_headroom") is True, f"{cid}: guardrail_case must set excluded_from_headroom")
    add_issue(structural_issues, any(case.get("budget_saturation_case") is True for case in new_cases), "no budget_saturation_case flagged")

    hashed_paths = set()
    for case_id, case_hashes in source_hashes.get("new_cases", {}).items():
        rows = case_hashes.get("candidate_visible", [])
        add_issue(structural_issues, bool(rows), f"{case_id}: no source hash rows")
        for row in rows:
            fixture_path = row.get("fixture_path")
            add_issue(structural_issues, isinstance(fixture_path, str) and fixture_path, f"{case_id}: source row missing fixture_path")
            if not fixture_path:
                continue
            hashed_paths.add(fixture_path)
            path = ROOT / fixture_path
            snapshot_path = row.get("snapshot_path")
            add_issue(structural_issues, path.is_file(), f"{fixture_path}: hashed path is not a file")
            if row.get("source_path") == "generated fixture manifest":
                if path.is_file():
                    add_issue(structural_issues, row.get("sha256") == sha_file(path), f"{fixture_path}: sha256 mismatch")
                continue
            add_issue(structural_issues, isinstance(snapshot_path, str) and snapshot_path, f"{fixture_path}: missing snapshot_path")
            if snapshot_path:
                snapshot_file = ROOT / snapshot_path
                add_issue(structural_issues, snapshot_file.is_file(), f"{fixture_path}: snapshot_path is not a file")
            if path.is_file():
                add_issue(structural_issues, row.get("sha256") == sha_file(path), f"{fixture_path}: sha256 mismatch")
                if path.name == "guardrail-result.rebound.json":
                    data = json.loads(path.read_text(encoding="utf-8"))
                    redaction = data.get("public_fixture_redaction")
                    add_issue(structural_issues, "interpretation" not in data, f"{fixture_path}: interpretation not redacted")
                    add_issue(structural_issues, isinstance(redaction, dict), f"{fixture_path}: missing public_fixture_redaction marker")
                    if isinstance(redaction, dict):
                        removed = set(redaction.get("removed_fields", []))
                        add_issue(
                            structural_issues,
                            {"interpretation", "interpretation.diagnostic_summary"}.issubset(removed),
                            f"{fixture_path}: redaction marker missing removed paths",
                        )
                    add_issue(
                        structural_issues,
                        set(row.get("redacted_fields", [])) >= {"interpretation", "interpretation.diagnostic_summary"},
                        f"{fixture_path}: source-hashes row missing redacted_fields",
                    )
                    if snapshot_path and (ROOT / snapshot_path).is_file():
                        snapshot_data = json.loads((ROOT / snapshot_path).read_text(encoding="utf-8"))
                        add_issue(structural_issues, "interpretation" in snapshot_data, f"{fixture_path}: unredacted snapshot lacks interpretation")
                elif snapshot_path and (ROOT / snapshot_path).is_file():
                    add_issue(structural_issues, row.get("sha256") == sha_file(ROOT / snapshot_path), f"{fixture_path}: non-redacted fixture differs from snapshot")
    for case in new_cases:
        for fixture_source in case.get("fixture_sources", []):
            add_issue(structural_issues, fixture_source in hashed_paths, f"{fixture_source}: fixture source not in source-hashes")

    authority_sources = [
        source for case in new_cases
        if case.get("case_id") == "fusion-authority-existing-authorization"
        for source in case.get("fixture_sources", [])
    ]
    add_issue(
        structural_issues,
        not any(source.endswith("LOCAL_STATUS.md") for source in authority_sources),
        "authority guardrail fixture must not include LOCAL_STATUS.md",
    )
    add_issue(structural_issues, snapshot_root.is_dir(), "source-snapshots root missing")

    public_fixture_files = [
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "evals" / "fixtures" / SUITE).rglob("*")
        if path.is_file()
    ]
    calibration_leaks = [path for path in public_fixture_files if "calibration" in path.lower()]
    add_issue(structural_issues, not calibration_leaks, "calibration-only files found in public fixtures: " + ", ".join(calibration_leaks[:5]))
    add_issue(structural_issues, hidden_independence.get("candidate_firewall"), "hidden-artifact independence receipt lacks candidate firewall")

    global_manifest = ROOT / "evals" / "manifest.json"
    if global_manifest.exists():
        global_text = global_manifest.read_text(encoding="utf-8")
        add_issue(structural_issues, SUITE not in global_text, "draft suite appears in evals/manifest.json before owner freeze")

    calibration_cases = calibration.get("cases", [])
    completed = [
        item for item in calibration_cases
        if item.get("case_id") in {case.get("case_id") for case in headroom_cases}
        and item.get("trial_count", 0) > 0
        and isinstance(item.get("weighted_baseline_mean"), (int, float))
    ]
    if len(completed) != len(headroom_cases):
        freeze_blockers.append("R2 calibration pending for one or more non-guardrail headroom cases")
    for item in completed:
        mean = item.get("weighted_baseline_mean")
        if mean >= 0.85:
            freeze_blockers.append(f"R2 headroom failed for {item.get('case_id')}: weighted_baseline_mean={mean}")
    below_095 = sum(1 for item in completed if item.get("weighted_baseline_mean", 1.0) < 0.95)
    if len(completed) == len(headroom_cases) and below_095 < 2:
        freeze_blockers.append("R7 headroom arithmetic fails: fewer than two calibrated non-guardrail headroom cases below 0.95")
    if calibration.get("r7_headroom_check", {}).get("status") == "pending_calibration":
        freeze_blockers.append("R7 headroom arithmetic pending calibration")

    structural_valid = not structural_issues
    freeze_ready = structural_valid and not freeze_blockers
    return {
        "suite_id": SUITE,
        "structural_valid": structural_valid,
        "freeze_ready": freeze_ready,
        "structural_issues": structural_issues,
        "freeze_blockers": freeze_blockers,
        "new_case_count": len(new_cases),
        "headroom_case_count": len(headroom_cases),
        "guardrail_cases": [case.get("case_id") for case in guardrail_cases],
        "budget_saturation_cases": [case.get("case_id") for case in new_cases if case.get("budget_saturation_case") is True],
        "case_spec_hash": sha_text(canonical_json(case_set)),
        "case_spec_file_sha256": sha_file(case_path),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-freeze-ready", action="store_true")
    args = parser.parse_args(argv)
    result = validate(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["structural_valid"]:
        return 1
    if args.require_freeze_ready and not result["freeze_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
