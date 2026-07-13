"""Regression tests for E1 correction and seed replay binding."""

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from e1_replay_core import (  # noqa: E402
    case_level_non_saturated_delta,
    validate_fixed_suite_baseline_binding,
)


def test_e1_s_uses_case_level_saturation_expected_0034375():
    shadow_result = {
        "comparisons": [
            {
                "case_id": "fusion-s0-env-probe-attribution",
                "trial": 1,
                "baseline_score": 0.8,
                "delta": 0.0,
            },
            {
                "case_id": "fusion-p2-instrument-noise-recovery",
                "trial": 1,
                "baseline_score": 0.8625,
                "delta": 0.1375,
            },
            {
                "case_id": "fusion-p2-instrument-noise-recovery",
                "trial": 2,
                "baseline_score": 1.0,
                "delta": 0.0,
            },
            {
                "case_id": "fusion-saturated-example",
                "trial": 1,
                "baseline_score": 1.0,
                "delta": 0.5,
            },
        ]
    }
    result = case_level_non_saturated_delta(
        shadow_result,
        [
            "fusion-s0-env-probe-attribution",
            "fusion-p2-instrument-noise-recovery",
            "fusion-saturated-example",
        ],
    )
    if result["non_saturated_case_ids"] != [
        "fusion-s0-env-probe-attribution",
        "fusion-p2-instrument-noise-recovery",
    ]:
        raise AssertionError(result)
    expected = 0.034375
    actual = result["non_saturated_hard_case_mean_delta"]
    if abs(actual - expected) > 1e-12:
        raise AssertionError(f"expected {expected}, got {actual}")


def test_seed_guardrail_rejects_stale_baseline_binding():
    try:
        validate_fixed_suite_baseline_binding(
            "a40521f88e93b61262c6e24edd52c636efc02a732dacee3e7e2edccf16659170",
            current_deployed_artifact="49e656d2aa0fdd6e6b48989f30975a9e06f7bda11a57e143869698f5d2c5dcfe",
            direct_predecessor_artifact="8e9c75555f0059f41a1f9b11f7c5c7fdc9f0e28d6be514bc920984e679ebd4cb",
        )
    except ValueError as error:
        if "stale_baseline_binding" not in str(error):
            raise AssertionError(error) from error
    else:
        raise AssertionError("stale baseline binding was accepted")


def main():
    test_e1_s_uses_case_level_saturation_expected_0034375()
    test_seed_guardrail_rejects_stale_baseline_binding()
    print(json.dumps({
        "valid": True,
        "test_e1_s_uses_case_level_saturation_expected_0034375": True,
        "test_seed_guardrail_rejects_stale_baseline_binding": True,
    }, indent=2))


if __name__ == "__main__":
    main()
