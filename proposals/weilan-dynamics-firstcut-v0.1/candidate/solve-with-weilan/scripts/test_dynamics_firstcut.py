"""Targeted harness for the dynamics-firstcut isolated candidate."""

from __future__ import annotations

import json
from pathlib import Path

import dynamics_firstcut as dynamics


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def test_emergence_exit():
    carriers, occurrences, config, oligarch_id = dynamics.emergence_fixture()
    result = dynamics.run_phase_map(
        carriers,
        occurrences,
        config,
        [dynamics.OccurrenceNarrowingProxy(), dynamics.StrictOccurrenceProxy()],
        oligarch_id,
    )
    require(result["exit_code"] == dynamics.EMERGES, "emergence fixture did not emerge")
    require(
        all(run["q_conserved"] for run in result["runs"].values()),
        "q was not conserved in emergence fixture",
    )


def test_honest_negative_exit():
    carriers, occurrences, config, oligarch_id = dynamics.needs_gate_fixture()
    result = dynamics.run_phase_map(
        carriers,
        occurrences,
        config,
        [dynamics.OccurrenceNarrowingProxy(), dynamics.StrictOccurrenceProxy()],
        oligarch_id,
    )
    require(result["exit_code"] == dynamics.NEEDS_GATE, "honest negative did not hold")


def test_true_stalled_survival_exit():
    carriers, occurrences, config, oligarch_id = dynamics.true_stalled_survival_fixture()
    scores = {
        carrier.carrier_id: dynamics.OccurrenceNarrowingProxy().score(
            carrier,
            occurrences[0],
            carriers,
        )
        for carrier in carriers
    }
    require(scores[oligarch_id] == 0.0, "survival fixture oligarch is not truly stalled")
    result = dynamics.run_phase_map(
        carriers,
        occurrences,
        config,
        [dynamics.OccurrenceNarrowingProxy(), dynamics.StrictOccurrenceProxy()],
        oligarch_id,
    )
    require(
        result["exit_code"] == dynamics.NEEDS_GATE,
        "true stalled oligarch did not survive to needs_gate",
    )


def test_parameter_phase_map_is_losable():
    phase_map = dynamics.parameter_phase_map()
    require(phase_map["cell_count"] == 4 * 4 * 3 * 3, "unexpected phase-map size")
    require(phase_map["contains_emergence"], "phase map has no collapse/emergence cells")
    require(phase_map["contains_needs_gate"], "phase map has no needs_gate cells")
    require(phase_map["survival_cell"] is not None, "true stalled survival cell is missing")
    survival = phase_map["survival_cell"]
    require(survival["exit_code"] == dynamics.NEEDS_GATE, "survival cell is not needs_gate")
    require(survival["oligarch_active"] is True, "survival cell oligarch did not remain active")
    require(phase_map["counts"][dynamics.EMERGES] > 0, "phase map only loses")
    require(phase_map["counts"][dynamics.NEEDS_GATE] > 0, "phase map only wins")
    require(
        all(cell["q_conserved"] for cell in phase_map["cells"]),
        "phase map contains non-conserving cells",
    )


def test_proxy_artifact_inconclusive():
    carriers, occurrences, config, oligarch_id = dynamics.artifact_fixture()
    result = dynamics.run_phase_map(
        carriers,
        occurrences,
        config,
        [dynamics.OccurrenceNarrowingProxy(), dynamics.CentroidAdhesionProxy()],
        oligarch_id,
    )
    require(result["exit_code"] == dynamics.INCONCLUSIVE, "proxy flip was not inconclusive")


def test_q_selector_not_recency():
    carriers = [
        dynamics.Carrier("recent_stalled_high_q", 0.50, (1.0, 0.0)),
        dynamics.Carrier("old_productive_mid_q", 0.30, (0.0, 1.0)),
        dynamics.Carrier("new_low_q", 0.20, (0.5, 0.5)),
    ]
    selected = dynamics.select_displacement(carriers, max_active=2)
    require(selected == ["new_low_q"], f"expected lowest-q displacement, got {selected}")


def test_self_read_adversarial_fixtures():
    report = dynamics.adversarial_proxy_report()
    require(report["stalled_oligarch_low"], "stalled centroid oligarch was not starved")
    require(report["productive_outlier_high"], "productive outlier was not rewarded")
    require(report["duplicate_penalized"], "duplicate carrier was over-rewarded")


def test_no_enumerated_gate_in_semantic_arena_path():
    source = Path(dynamics.__file__).read_text(encoding="utf-8")
    forbidden = [
        "collapse_pressure",
        "dominance",
        "persistence",
        "stagnation",
        "diversity_loss",
    ]
    found = [item for item in forbidden if item in source]
    require(not found, f"semantic arena path mentions enumerated gate terms: {found}")


def test_receipt_status():
    receipt = dynamics.build_receipt()
    require(receipt["status"] == "pass", json.dumps(receipt, indent=2, sort_keys=True))
    require(
        receipt["f4_single_ledger_invariant"]["displacement_selector_uses_q_not_recency"],
        "receipt did not bind q-based displacement",
    )


def main():
    tests = [
        test_emergence_exit,
        test_honest_negative_exit,
        test_true_stalled_survival_exit,
        test_parameter_phase_map_is_losable,
        test_proxy_artifact_inconclusive,
        test_q_selector_not_recency,
        test_self_read_adversarial_fixtures,
        test_no_enumerated_gate_in_semantic_arena_path,
        test_receipt_status,
    ]
    for test in tests:
        test()
    print(json.dumps(dynamics.build_receipt(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
