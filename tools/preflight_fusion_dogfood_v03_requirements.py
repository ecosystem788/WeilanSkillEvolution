"""Requirements-level preflight for the fusion-dogfood-v0.3 extension spec."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQ_PATH = ROOT / "proposals" / "fusion-dogfood-extension-v0.3" / "EXTENSION_REQUIREMENTS.md"


REQUIRED_MARKERS = {
    "rubric_firewall": [
        "Success criteria, scoring weights, and rubric content are never candidate-visible",
        "public case spec and all runner/calibration prompt templates must not contain them",
    ],
    "premise_mechanism_governance": [
        "## Premise: mechanism existence is assumed, mechanism governance is measured",
        "This premise is a **verifiable precondition, not an assumption**",
        "A case the deployed baseline cannot win for mechanical reasons",
    ],
    "guardrail_reserialization": [
        "carried v0.2 guardrail case must be reserialized",
        "old public `success` list is not carried forward candidate-visible",
    ],
    "budget_enforcement": [
        "truncates execution at budget",
        "records\n    `actual_usage` in every trial receipt",
    ],
    "budget_accounting_scope": [
        "Budget accounting must be declared in the public case spec",
        "unbudgeted candidate-controlled work is forbidden",
    ],
    "slow_loop_episode": [
        "harness terminates the context",
        "Episode 2's success must\n    **causally require the deposited state**",
    ],
    "ledger_authenticity": [
        "Ledger evidence must be authenticated by the harness",
        "hand-written or\n    post-hoc candidate-authored ledger files must be rejected",
    ],
    "negative_controls": [
        "**no-method**",
        "**append-only memory + retrieval**",
    ],
    "append_only_frozen": [
        "append-only control implementation is frozen",
        "configuration hash and retrieval policy appear in\n    every receipt",
    ],
    "separation_ordering": [
        "`no-method < append-only < method-baseline`",
        "If `no-method < append-only` is not observed",
    ],
    "firewall_scope": [
        "no full calibration transcripts",
        "receipt metadata, and published quarantine\n     summaries",
    ],
    "winnable_in_principle": [
        "**winnable-in-principle**",
        "demonstrating that an ideal\n      execution using only deployed-baseline mechanisms reaches a passing score within the\n      declared budget",
        "a case without a winnable walkthrough is invalid",
    ],
    "mechanism_availability_probe": [
        "**mechanism-availability probe passed**",
        "demonstrates the runtime actually emits\n       every observable class the hidden checks grade",
        "**mechanism-availability probe**",
        "If the probe fails, case engineering halts",
    ],
    "r16_self_tests": [
        "ledger authenticity checks reject a forged/post-hoc collapse event",
        "budget accounting scope is explicit and equivalent across no-method, append-only, and\n       method-baseline arms",
        "carried v0.2 guardrail case has been reserialized without candidate-visible `success`",
        "arm-purity self-test passes",
        "method-contaminated no-method probe trial is\n       detected and rejected from telemetry",
    ],
}

def _contains_all(text: str, markers: list[str]) -> bool:
    return all(marker in text for marker in markers)


def validate() -> dict:
    issues: list[str] = []
    if not REQ_PATH.is_file():
        return {
            "suite_id": "fusion-dogfood-v0.3",
            "requirements_valid": False,
            "issues": [f"missing {REQ_PATH.relative_to(ROOT).as_posix()}"],
            "checks": {},
        }

    text = REQ_PATH.read_text(encoding="utf-8")
    checks = {name: _contains_all(text, markers) for name, markers in REQUIRED_MARKERS.items()}
    for name, passed in checks.items():
        if not passed:
            issues.append(f"missing required v0.3 requirements markers: {name}")

    hidden_token = "evals/hidden/fusion-dogfood-v0.3/"
    checks["hidden_path_is_reference_only"] = hidden_token in text
    if not checks["hidden_path_is_reference_only"]:
        issues.append("hidden artifact path boundary is not referenced")

    checks["no_owner_authority_expansion"] = all(
        phrase in text
        for phrase in [
            "The owner approves\n     and freezes",
            "Approving or freezing the suite",
            "modifying `evals/manifest.json`",
            "modifying the deployed\nSkill",
        ]
    )
    if not checks["no_owner_authority_expansion"]:
        issues.append("owner authority / forbidden action boundary is incomplete")

    return {
        "suite_id": "fusion-dogfood-v0.3",
        "requirements_valid": not issues,
        "issues": issues,
        "checks": checks,
        "checked_file": REQ_PATH.relative_to(ROOT).as_posix(),
        "hidden_artifacts_read": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["requirements_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
