"""Isolated WeiLan dynamics-firstcut arena.

This module is intentionally proposal-local. It models one semantic-slot arena
where q flows by self-read structural output, and the displacement selector
chooses the lowest-q carrier for the existing budget validator to evict.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
from dataclasses import dataclass, field
from typing import Iterable, Protocol


EMERGES = "collapse_emerges_from_conservation"
NEEDS_GATE = "collapse_needs_gate"
INCONCLUSIVE = "inconclusive"
BLOCKED = "blocked_engineering"


@dataclass
class Carrier:
    carrier_id: str
    q: float
    vector: tuple[float, ...]
    specificity: float = 1.0
    protected: bool = False
    active: bool = True
    history: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class Occurrence:
    vector: tuple[float, ...]
    specificity: float = 1.0


@dataclass(frozen=True)
class DynamicsConfig:
    max_active: int
    horizon: int
    survival_floor: float
    bleed_rate: float


class SelfReadProxy(Protocol):
    name: str

    def score(
        self,
        carrier: Carrier,
        occurrence: Occurrence,
        active_carriers: list[Carrier],
    ) -> float:
        ...


def cosine(left: Iterable[float], right: Iterable[float]) -> float:
    left_values = tuple(float(value) for value in left)
    right_values = tuple(float(value) for value in right)
    if len(left_values) != len(right_values):
        raise ValueError("vectors must have equal dimension")
    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left_values, right_values)) / (left_norm * right_norm)


class OccurrenceNarrowingProxy:
    name = "occurrence_narrowing_v0"

    def score(
        self,
        carrier: Carrier,
        occurrence: Occurrence,
        active_carriers: list[Carrier],
    ) -> float:
        similarity = max(0.0, cosine(carrier.vector, occurrence.vector))
        narrow = max(0.0, 1.0 - min(1.0, abs(carrier.specificity - occurrence.specificity)))
        redundancy = max(
            (
                max(0.0, cosine(carrier.vector, other.vector))
                for other in active_carriers
                if other.carrier_id != carrier.carrier_id
            ),
            default=0.0,
        )
        # Structural output is read from field behavior: occurrence fit,
        # narrowing, and an anti-redundancy penalty. No fixture labels enter.
        return max(0.0, similarity * (0.55 + 0.45 * narrow) - 0.30 * redundancy)


class StrictOccurrenceProxy:
    name = "strict_occurrence_v0"

    def score(
        self,
        carrier: Carrier,
        occurrence: Occurrence,
        active_carriers: list[Carrier],
    ) -> float:
        del active_carriers
        similarity = max(0.0, cosine(carrier.vector, occurrence.vector))
        narrow = max(0.0, 1.0 - min(1.0, abs(carrier.specificity - occurrence.specificity)))
        return similarity * narrow


class CentroidAdhesionProxy:
    name = "centroid_adhesion_artifact_v0"

    def score(
        self,
        carrier: Carrier,
        occurrence: Occurrence,
        active_carriers: list[Carrier],
    ) -> float:
        del occurrence
        total_q = sum(item.q for item in active_carriers if item.active)
        if total_q <= 0:
            return 0.0
        dimensions = len(carrier.vector)
        centroid = []
        for index in range(dimensions):
            centroid.append(
                sum(item.q * item.vector[index] for item in active_carriers if item.active)
                / total_q
            )
        return max(0.0, cosine(carrier.vector, tuple(centroid)))


def validate_config(config: DynamicsConfig) -> list[str]:
    issues: list[str] = []
    if config.max_active < 1:
        issues.append("max_active must be positive")
    if config.horizon < 1:
        issues.append("horizon must be positive")
    if not 0 < config.survival_floor < 1:
        issues.append("survival_floor must be in (0,1)")
    if not 0 < config.bleed_rate <= 1:
        issues.append("bleed_rate must be in (0,1]")
    return issues


def validate_carriers(carriers: list[Carrier]) -> list[str]:
    issues: list[str] = []
    ids = [carrier.carrier_id for carrier in carriers]
    if len(ids) != len(set(ids)):
        issues.append("carrier ids must be unique")
    active = [carrier for carrier in carriers if carrier.active]
    if not active:
        issues.append("at least one active carrier is required")
    dimensions = {len(carrier.vector) for carrier in carriers}
    if len(dimensions) != 1:
        issues.append("all carrier vectors must have the same dimension")
    for carrier in carriers:
        if carrier.q < 0 or not math.isfinite(carrier.q):
            issues.append(f"{carrier.carrier_id}: q must be finite and non-negative")
        if carrier.specificity < 0 or not math.isfinite(carrier.specificity):
            issues.append(f"{carrier.carrier_id}: specificity must be finite and non-negative")
    return issues


def active_carriers(carriers: list[Carrier]) -> list[Carrier]:
    return [carrier for carrier in carriers if carrier.active]


def select_displacement(carriers: list[Carrier], max_active: int) -> list[str]:
    active = active_carriers(carriers)
    overflow = max(0, len(active) - max_active)
    if overflow == 0:
        return []
    candidates = [carrier for carrier in active if not carrier.protected]
    candidates.sort(key=lambda item: (item.q, item.carrier_id))
    return [carrier.carrier_id for carrier in candidates[:overflow]]


def redistribute_released_q(
    carriers: list[Carrier],
    released_q: float,
    scores: dict[str, float],
) -> None:
    if released_q <= 0:
        return
    active = active_carriers(carriers)
    if not active:
        return
    receivers = [
        carrier
        for carrier in active_carriers(carriers)
        if scores.get(carrier.carrier_id, 0.0) > 0
    ]
    total_score = sum(scores[carrier.carrier_id] for carrier in receivers)
    if total_score <= 0:
        share = released_q / len(active)
        for carrier in active:
            carrier.q += share
        return
    for carrier in receivers:
        carrier.q += released_q * scores[carrier.carrier_id] / total_score


def apply_q_flow(
    carriers: list[Carrier],
    occurrence: Occurrence,
    config: DynamicsConfig,
    proxy: SelfReadProxy,
) -> dict[str, float]:
    active = active_carriers(carriers)
    scores = {
        carrier.carrier_id: proxy.score(carrier, occurrence, active)
        for carrier in active
    }
    total_score = sum(scores.values())
    total_q = sum(carrier.q for carrier in active)
    if total_score > 0 and total_q > 0:
        target_q = {
            carrier.carrier_id: total_q * scores[carrier.carrier_id] / total_score
            for carrier in active
        }
        for carrier in active:
            carrier.q += config.bleed_rate * (target_q[carrier.carrier_id] - carrier.q)
    return scores


def release_starved_carriers(
    carriers: list[Carrier],
    config: DynamicsConfig,
    scores: dict[str, float],
) -> list[str]:
    released: list[str] = []
    while True:
        active = active_carriers(carriers)
        candidates = [
            carrier
            for carrier in active
            if not carrier.protected and carrier.q < config.survival_floor
        ]
        if not candidates:
            return released
        if len(active) <= 1:
            return released
        carrier = min(candidates, key=lambda item: (item.q, item.carrier_id))
        released.append(carrier.carrier_id)
        released_q = carrier.q
        carrier.q = 0.0
        carrier.active = False
        redistribute_released_q(carriers, released_q, scores)


def apply_displacement_selector(carriers: list[Carrier], config: DynamicsConfig) -> list[str]:
    displaced = select_displacement(carriers, config.max_active)
    released_q = 0.0
    for carrier_id in displaced:
        carrier = next(item for item in carriers if item.carrier_id == carrier_id)
        released_q += carrier.q
        carrier.q = 0.0
        carrier.active = False
    if displaced:
        active = active_carriers(carriers)
        if active:
            share = released_q / len(active)
            for carrier in active:
                carrier.q += share
    return displaced


def run_once(
    carriers: list[Carrier],
    occurrences: list[Occurrence],
    config: DynamicsConfig,
    proxy: SelfReadProxy,
    oligarch_id: str,
) -> dict:
    issues = validate_config(config) + validate_carriers(carriers)
    if not occurrences:
        issues.append("at least one occurrence is required")
    if oligarch_id not in {carrier.carrier_id for carrier in carriers}:
        issues.append("oligarch_id must name a carrier")
    if issues:
        return {"exit_code": BLOCKED, "issues": issues}

    initial_q = sum(carrier.q for carrier in carriers)
    history = []
    for step in range(config.horizon):
        occurrence = occurrences[step % len(occurrences)]
        scores = apply_q_flow(carriers, occurrence, config, proxy)
        starved = release_starved_carriers(carriers, config, scores)
        displaced = apply_displacement_selector(carriers, config)
        current = {
            carrier.carrier_id: {
                "q": round(carrier.q, 12),
                "active": carrier.active,
            }
            for carrier in carriers
        }
        history.append(
            {
                "step": step + 1,
                "proxy": proxy.name,
                "scores": {key: round(value, 12) for key, value in sorted(scores.items())},
                "starved": starved,
                "displaced": displaced,
                "carriers": current,
            }
        )
        oligarch = next(carrier for carrier in carriers if carrier.carrier_id == oligarch_id)
        if not oligarch.active:
            final_q = sum(carrier.q for carrier in carriers)
            return {
                "exit_code": EMERGES,
                "oligarch_id": oligarch_id,
                "steps": step + 1,
                "q_conserved": math.isclose(initial_q, final_q, rel_tol=0, abs_tol=1e-9),
                "initial_total_q": round(initial_q, 12),
                "final_total_q": round(final_q, 12),
                "history": history,
            }
    final_q = sum(carrier.q for carrier in carriers)
    return {
        "exit_code": NEEDS_GATE,
        "oligarch_id": oligarch_id,
        "steps": config.horizon,
        "q_conserved": math.isclose(initial_q, final_q, rel_tol=0, abs_tol=1e-9),
        "initial_total_q": round(initial_q, 12),
        "final_total_q": round(final_q, 12),
        "history": history,
    }


def run_phase_map(
    carriers: list[Carrier],
    occurrences: list[Occurrence],
    config: DynamicsConfig,
    proxies: list[SelfReadProxy],
    oligarch_id: str,
) -> dict:
    runs = {}
    for proxy in proxies:
        result = run_once(copy.deepcopy(carriers), occurrences, config, proxy, oligarch_id)
        runs[proxy.name] = {
            "exit_code": result["exit_code"],
            "steps": result.get("steps"),
            "q_conserved": result.get("q_conserved"),
        }
    exit_codes = {run["exit_code"] for run in runs.values()}
    if BLOCKED in exit_codes:
        exit_code = BLOCKED
    elif len(exit_codes) > 1:
        exit_code = INCONCLUSIVE
    else:
        exit_code = next(iter(exit_codes))
    return {"exit_code": exit_code, "runs": runs}


def emergence_fixture() -> tuple[list[Carrier], list[Occurrence], DynamicsConfig, str]:
    carriers = [
        Carrier("stalled_oligarch", 0.86, (1.0, 0.0), specificity=0.2),
        Carrier("productive_narrow", 0.07, (0.0, 1.0), specificity=1.0),
        Carrier("productive_neighbor", 0.07, (0.0, 0.92), specificity=0.95),
    ]
    occurrences = [Occurrence((0.0, 1.0), specificity=1.0)]
    return carriers, occurrences, DynamicsConfig(3, 8, 0.09, 0.45), "stalled_oligarch"


def needs_gate_fixture() -> tuple[list[Carrier], list[Occurrence], DynamicsConfig, str]:
    carriers = [
        Carrier("self_feeding_oligarch", 0.86, (1.0, 0.0), specificity=1.0),
        Carrier("weak_neighbor", 0.07, (0.0, 1.0), specificity=1.0),
        Carrier("weak_duplicate", 0.07, (0.0, 0.9), specificity=1.0),
    ]
    occurrences = [Occurrence((1.0, 0.0), specificity=1.0)]
    return carriers, occurrences, DynamicsConfig(3, 8, 0.09, 0.45), "self_feeding_oligarch"


def true_stalled_survival_fixture() -> tuple[list[Carrier], list[Occurrence], DynamicsConfig, str]:
    """A stopped oligarch that survives only because frozen parameters allow it.

    The oligarch has zero structural output for the incoming occurrence under the
    self-read proxy, but its initial q is high, bleed is weak, the survival floor
    is low enough, and horizon is short enough that conservation alone does not
    starve it out. This is the honest negative tooth: same mechanism, no gate,
    genuinely losable.
    """

    carriers = [
        Carrier("true_stalled_survivor", 0.96, (1.0, 0.0), specificity=0.0),
        Carrier("productive_narrow", 0.02, (0.0, 1.0), specificity=1.0),
        Carrier("productive_neighbor", 0.02, (0.0, 0.92), specificity=0.95),
    ]
    occurrences = [Occurrence((0.0, 1.0), specificity=1.0)]
    return carriers, occurrences, DynamicsConfig(3, 8, 0.55, 0.03), "true_stalled_survivor"


def artifact_fixture() -> tuple[list[Carrier], list[Occurrence], DynamicsConfig, str]:
    return emergence_fixture()


def stalled_fixture_with_parameters(
    oligarch_q: float,
    bleed_rate: float,
    survival_floor: float,
    horizon: int,
) -> tuple[list[Carrier], list[Occurrence], DynamicsConfig, str]:
    if not 0 < oligarch_q < 1:
        raise ValueError("oligarch_q must be in (0,1)")
    remaining = 1.0 - oligarch_q
    carriers = [
        Carrier("phase_stalled_oligarch", oligarch_q, (1.0, 0.0), specificity=0.0),
        Carrier("phase_productive_narrow", remaining / 2.0, (0.0, 1.0), specificity=1.0),
        Carrier("phase_productive_neighbor", remaining / 2.0, (0.0, 0.92), specificity=0.95),
    ]
    occurrences = [Occurrence((0.0, 1.0), specificity=1.0)]
    config = DynamicsConfig(3, horizon, survival_floor, bleed_rate)
    return carriers, occurrences, config, "phase_stalled_oligarch"


def final_oligarch_state(result: dict, oligarch_id: str) -> dict:
    if not result.get("history"):
        return {"q": None, "active": None}
    return result["history"][-1]["carriers"][oligarch_id]


def parameter_phase_map() -> dict:
    q_values = [0.55, 0.75, 0.90, 0.96]
    bleed_values = [0.03, 0.12, 0.30, 0.45]
    floor_values = [0.05, 0.25, 0.55]
    horizon_values = [4, 8, 16]
    cells = []
    counts = {EMERGES: 0, NEEDS_GATE: 0, INCONCLUSIVE: 0, BLOCKED: 0}
    for oligarch_q in q_values:
        for bleed_rate in bleed_values:
            for survival_floor in floor_values:
                for horizon in horizon_values:
                    carriers, occurrences, config, oligarch_id = stalled_fixture_with_parameters(
                        oligarch_q,
                        bleed_rate,
                        survival_floor,
                        horizon,
                    )
                    result = run_once(
                        carriers,
                        occurrences,
                        config,
                        OccurrenceNarrowingProxy(),
                        oligarch_id,
                    )
                    counts[result["exit_code"]] += 1
                    final_state = final_oligarch_state(result, oligarch_id)
                    cells.append(
                        {
                            "q": oligarch_q,
                            "bleed": bleed_rate,
                            "floor": survival_floor,
                            "horizon": horizon,
                            "exit_code": result["exit_code"],
                            "steps": result.get("steps"),
                            "final_oligarch_q": final_state["q"],
                            "oligarch_active": final_state["active"],
                            "q_conserved": result.get("q_conserved"),
                        }
                    )
    survival_cells = [
        cell for cell in cells
        if cell["exit_code"] == NEEDS_GATE
        and cell["q"] == 0.96
        and cell["bleed"] == 0.03
        and cell["floor"] == 0.55
        and cell["horizon"] == 8
    ]
    collapse_cells = [cell for cell in cells if cell["exit_code"] == EMERGES]
    return {
        "axes": {
            "q": q_values,
            "bleed": bleed_values,
            "floor": floor_values,
            "horizon": horizon_values,
        },
        "cell_count": len(cells),
        "counts": counts,
        "contains_emergence": bool(collapse_cells),
        "contains_needs_gate": counts[NEEDS_GATE] > 0,
        "survival_cell": survival_cells[0] if survival_cells else None,
        "sample_emergence_cell": collapse_cells[0] if collapse_cells else None,
        "cells": cells,
    }


def adversarial_proxy_report() -> dict:
    proxy = OccurrenceNarrowingProxy()
    carriers = [
        Carrier("stalled_centroid_oligarch", 0.80, (1.0, 0.0), specificity=0.1),
        Carrier("productive_outlier", 0.10, (0.0, 1.0), specificity=1.0),
        Carrier("duplicate_neighbor", 0.10, (0.0, 1.0), specificity=0.4),
    ]
    occurrence = Occurrence((0.0, 1.0), specificity=1.0)
    scores = {
        carrier.carrier_id: proxy.score(carrier, occurrence, carriers)
        for carrier in carriers
    }
    return {
        "proxy": proxy.name,
        "scores": {key: round(value, 12) for key, value in sorted(scores.items())},
        "stalled_oligarch_low": scores["stalled_centroid_oligarch"] == 0.0,
        "productive_outlier_high": scores["productive_outlier"] > scores["stalled_centroid_oligarch"],
        "duplicate_penalized": scores["duplicate_neighbor"] < scores["productive_outlier"],
    }


def build_receipt() -> dict:
    carriers, occurrences, config, oligarch_id = emergence_fixture()
    emergence = run_phase_map(
        carriers,
        occurrences,
        config,
        [OccurrenceNarrowingProxy(), StrictOccurrenceProxy()],
        oligarch_id,
    )
    carriers, occurrences, config, oligarch_id = needs_gate_fixture()
    needs_gate = run_phase_map(
        carriers,
        occurrences,
        config,
        [OccurrenceNarrowingProxy(), StrictOccurrenceProxy()],
        oligarch_id,
    )
    carriers, occurrences, config, oligarch_id = true_stalled_survival_fixture()
    true_stalled_scores = {
        carrier.carrier_id: OccurrenceNarrowingProxy().score(
            carrier,
            occurrences[0],
            carriers,
        )
        for carrier in carriers
    }
    true_stalled_survival = run_phase_map(
        carriers,
        occurrences,
        config,
        [OccurrenceNarrowingProxy(), StrictOccurrenceProxy()],
        oligarch_id,
    )
    carriers, occurrences, config, oligarch_id = artifact_fixture()
    artifact = run_phase_map(
        carriers,
        occurrences,
        config,
        [OccurrenceNarrowingProxy(), CentroidAdhesionProxy()],
        oligarch_id,
    )
    displacement_carriers = [
        Carrier("recent_stalled_high_q", 0.50, (1.0, 0.0)),
        Carrier("old_productive_mid_q", 0.30, (0.0, 1.0)),
        Carrier("new_low_q", 0.20, (0.5, 0.5)),
    ]
    displaced = select_displacement(displacement_carriers, max_active=2)
    adversarial = adversarial_proxy_report()
    phase_map = parameter_phase_map()
    passed = (
        emergence["exit_code"] == EMERGES
        and needs_gate["exit_code"] == NEEDS_GATE
        and true_stalled_survival["exit_code"] == NEEDS_GATE
        and true_stalled_scores["true_stalled_survivor"] == 0.0
        and artifact["exit_code"] == INCONCLUSIVE
        and phase_map["contains_emergence"]
        and phase_map["contains_needs_gate"]
        and phase_map["survival_cell"] is not None
        and all(cell["q_conserved"] for cell in phase_map["cells"])
        and displaced == ["new_low_q"]
        and adversarial["stalled_oligarch_low"]
        and adversarial["productive_outlier_high"]
        and adversarial["duplicate_penalized"]
    )
    return {
        "schema_version": "weilan_dynamics_firstcut_receipt_v0.1",
        "status": "pass" if passed else "fail",
        "authority": "isolated_candidate_probe_never_adopts_or_deploys",
        "f1_path_binding": {
            "displace_selector_layer": "scripts/dynamics_firstcut.py:select_displacement",
            "budget_validator_kept_external": "enforce_semantic_budget is not modified by this probe",
            "semantic_arena_no_enumerated_gate": True,
        },
        "f2_exit_precedence": {
            "emergence_fixture": emergence,
            "needs_gate_fixture": needs_gate,
            "true_stalled_survival_fixture": {
                **true_stalled_survival,
                "oligarch_self_read_score": round(
                    true_stalled_scores["true_stalled_survivor"], 12
                ),
            },
            "artifact_fixture": artifact,
            "phase_map": phase_map,
        },
        "f3_self_read_proxy_controls": adversarial,
        "f4_single_ledger_invariant": {
            "q_conserved_in_emergence_runs": all(
                run["q_conserved"] for run in emergence["runs"].values()
            ),
            "displacement_selector_uses_q_not_recency": displaced == ["new_low_q"],
            "selected_displacement": displaced,
        },
        "explicit_boundaries": [
            "constructed oligarch",
            "hand-set scarcity",
            "isolated semantic-slot arena only",
            "no deployed skill modification",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print machine-readable receipt")
    args = parser.parse_args(argv)
    receipt = build_receipt()
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(receipt["status"])
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
