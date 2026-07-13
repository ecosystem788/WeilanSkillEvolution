"""Standalone Rule A prototype for witness precedence.

This module intentionally does not import or modify production prospective
runtime code. It checks whether a witness snapshot is strictly earlier than a
goal registration by either timestamp or offline ledger append order.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


class WitnessPrecedenceError(ValueError):
    """Raised when a witness snapshot cannot satisfy Rule A."""


def parse_utc_timestamp(value: str, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise WitnessPrecedenceError(f"{field_name} must be a non-empty timestamp string")

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WitnessPrecedenceError(f"{field_name} is not a valid ISO-8601 timestamp") from exc

    if parsed.tzinfo is None:
        raise WitnessPrecedenceError(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_witness_precedes_registration(
    *,
    registered_timestamp_utc: str,
    witness_snapshot: Mapping[str, Any] | None,
) -> bool:
    """Return True only when witness_snapshot.head_timestamp_utc is strictly prior."""

    if witness_snapshot is None:
        raise WitnessPrecedenceError("witness_snapshot is required for Rule A")
    if not isinstance(witness_snapshot, Mapping):
        raise WitnessPrecedenceError("witness_snapshot must be a mapping")

    witness_timestamp = parse_utc_timestamp(
        witness_snapshot.get("head_timestamp_utc"),
        field_name="source_snapshots.head_timestamp_utc",
    )
    registered_timestamp = parse_utc_timestamp(
        registered_timestamp_utc,
        field_name="registered event timestamp",
    )

    if witness_timestamp >= registered_timestamp:
        raise WitnessPrecedenceError(
            "source_snapshots.head_timestamp_utc must be strictly earlier than the registered event timestamp"
        )
    return True


def event_position(event_id: str, event_order: Iterable[Any] | Mapping[str, int]) -> int:
    """Resolve an event id to an offline append-order position."""

    if not isinstance(event_id, str) or not event_id:
        raise WitnessPrecedenceError("event_id must be a non-empty string")

    if isinstance(event_order, Mapping):
        if event_id not in event_order:
            raise WitnessPrecedenceError(f"event_id {event_id!r} is missing from event_order")
        position = event_order[event_id]
        if not isinstance(position, int):
            raise WitnessPrecedenceError("event_order positions must be integers")
        return position

    for index, entry in enumerate(event_order):
        if isinstance(entry, str):
            candidate_id, position = entry, index
        else:
            try:
                candidate_id, position = entry
            except (TypeError, ValueError) as exc:
                raise WitnessPrecedenceError(
                    "event_order entries must be event ids or (event_id, position) pairs"
                ) from exc

        if candidate_id == event_id:
            if not isinstance(position, int):
                raise WitnessPrecedenceError("event_order positions must be integers")
            return position

    raise WitnessPrecedenceError(f"event_id {event_id!r} is missing from event_order")


def validate_witness_precedes_by_event_order(
    *,
    registered_event_id: str,
    witness_snapshot: Mapping[str, Any] | None,
    event_order: Iterable[Any] | Mapping[str, int],
) -> bool:
    """Return True only when source_snapshots.head_event_id appears earlier."""

    if witness_snapshot is None:
        raise WitnessPrecedenceError("witness_snapshot is required for Rule A event-order check")
    if not isinstance(witness_snapshot, Mapping):
        raise WitnessPrecedenceError("witness_snapshot must be a mapping")

    witness_event_id = witness_snapshot.get("head_event_id")
    if not isinstance(witness_event_id, str) or not witness_event_id:
        raise WitnessPrecedenceError("source_snapshots.head_event_id must be a non-empty string")

    witness_position = event_position(witness_event_id, event_order)
    registered_position = event_position(registered_event_id, event_order)

    if witness_position >= registered_position:
        raise WitnessPrecedenceError(
            "source_snapshots.head_event_id must appear strictly before the registered event id"
        )
    return True
