import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from preflight_fusion_dogfood_v03_requirements import validate  # noqa: E402


def test_v03_requirements_preflight_passes():
    result = validate()
    if not result["requirements_valid"]:
        raise AssertionError(json.dumps(result, ensure_ascii=False, indent=2))
    expected_checks = {
        "rubric_firewall",
        "premise_mechanism_governance",
        "guardrail_reserialization",
        "budget_enforcement",
        "budget_accounting_scope",
        "slow_loop_episode",
        "ledger_authenticity",
        "negative_controls",
        "append_only_frozen",
        "separation_ordering",
        "firewall_scope",
        "winnable_in_principle",
        "mechanism_availability_probe",
        "r16_self_tests",
        "hidden_path_is_reference_only",
        "no_owner_authority_expansion",
    }
    missing = expected_checks - set(result["checks"])
    if missing:
        raise AssertionError(f"missing checks: {sorted(missing)}")
    failed = [name for name in expected_checks if result["checks"][name] is not True]
    if failed:
        raise AssertionError(f"failed checks: {failed}")
    if result["hidden_artifacts_read"] is not False:
        raise AssertionError("requirements preflight must not read hidden artifacts")
