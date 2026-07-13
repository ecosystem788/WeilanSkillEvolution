from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent))

from witness_precedence import (  # noqa: E402
    WitnessPrecedenceError,
    validate_witness_precedes_by_event_order,
    validate_witness_precedes_registration,
)


def test_rule_a_accepts_prior_witness_snapshot():
    assert validate_witness_precedes_registration(
        registered_timestamp_utc="2026-07-10T08:00:00+00:00",
        witness_snapshot={
            "head_event_id": "event-before-registration",
            "head_timestamp_utc": "2026-07-10T07:59:59+00:00",
        },
    )


def test_bridge_exemption_requires_prior_witness_for_rule_a():
    # This nursery test proves only Rule A. Rule B binding and Rule C
    # unforgeability/author tracing remain unresolved red-zone schema work.
    with pytest.raises(WitnessPrecedenceError, match="witness_snapshot is required"):
        validate_witness_precedes_registration(
            registered_timestamp_utc="2026-07-10T08:00:00+00:00",
            witness_snapshot=None,
        )


def test_rule_a_rejects_equal_timestamp():
    with pytest.raises(WitnessPrecedenceError, match="strictly earlier"):
        validate_witness_precedes_registration(
            registered_timestamp_utc="2026-07-10T08:00:00+00:00",
            witness_snapshot={
                "head_event_id": "event-at-registration",
                "head_timestamp_utc": "2026-07-10T08:00:00+00:00",
            },
        )


def test_rule_a_rejects_later_timestamp():
    with pytest.raises(WitnessPrecedenceError, match="strictly earlier"):
        validate_witness_precedes_registration(
            registered_timestamp_utc="2026-07-10T08:00:00+00:00",
            witness_snapshot={
                "head_event_id": "event-after-registration",
                "head_timestamp_utc": "2026-07-10T08:00:01+00:00",
            },
        )


def test_rule_a_requires_timezone_anchored_timestamps():
    with pytest.raises(WitnessPrecedenceError, match="timezone"):
        validate_witness_precedes_registration(
            registered_timestamp_utc="2026-07-10T08:00:00+00:00",
            witness_snapshot={
                "head_event_id": "event-without-zone",
                "head_timestamp_utc": "2026-07-10T07:59:59",
            },
        )


def test_rule_a_event_order_accepts_same_second_prior_witness():
    # This advances Rule C only for the unforgeable precedence anchor:
    # author tracing for who created the witness remains unresolved red-zone work.
    assert validate_witness_precedes_by_event_order(
        registered_event_id="goal-registered",
        witness_snapshot={
            "head_event_id": "witness-head",
            "head_timestamp_utc": "2026-07-10T08:00:00+00:00",
        },
        event_order=["witness-head", "goal-registered"],
    )


def test_rule_a_event_order_rejects_same_position():
    with pytest.raises(WitnessPrecedenceError, match="strictly before"):
        validate_witness_precedes_by_event_order(
            registered_event_id="goal-registered",
            witness_snapshot={"head_event_id": "witness-head"},
            event_order={"witness-head": 4, "goal-registered": 4},
        )


def test_rule_a_event_order_rejects_later_witness_event():
    with pytest.raises(WitnessPrecedenceError, match="strictly before"):
        validate_witness_precedes_by_event_order(
            registered_event_id="goal-registered",
            witness_snapshot={"head_event_id": "witness-head"},
            event_order=[("goal-registered", 10), ("witness-head", 11)],
        )
