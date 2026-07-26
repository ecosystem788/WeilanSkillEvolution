#!/usr/bin/env python3
"""Append one host-clock-stamped object to a local JSONL ledger."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Mapping


RESERVED_CLOCK_FIELDS = frozenset({"time", "time_authority"})


def _ledger_path(root: Path, ledger_name: str) -> Path:
    relative = Path(ledger_name)
    if relative.name != ledger_name or relative.suffix.lower() != ".jsonl":
        raise ValueError("--file must be one JSONL filename directly under --root")
    return root.resolve() / relative


def _clock_stamp(now: datetime | None = None) -> str:
    observed = now if now is not None else datetime.now().astimezone()
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("clock timestamp must include an explicit UTC offset")
    return observed.isoformat(timespec="seconds")


def append_clocked_row(
    *,
    root: Path,
    ledger_name: str,
    payload: Mapping[str, object],
    now: datetime | None = None,
) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a JSON object")
    if any(not isinstance(key, str) for key in payload):
        raise ValueError("payload keys must be strings")
    forbidden = sorted(RESERVED_CLOCK_FIELDS.intersection(payload))
    if forbidden:
        raise ValueError(f"caller cannot supply reserved clock fields: {', '.join(forbidden)}")

    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"--root is not an existing directory: {root}")
    ledger_path = _ledger_path(root, ledger_name)

    row = dict(payload)
    row["time"] = _clock_stamp(now)
    row["time_authority"] = "clock"
    encoded = (
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode("utf-8")

    if ledger_path.exists() and ledger_path.stat().st_size:
        with ledger_path.open("rb") as stream:
            stream.seek(-1, os.SEEK_END)
            if stream.read(1) != b"\n":
                raise ValueError(f"refusing to append after an unterminated line: {ledger_path}")

    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = os.open(ledger_path, flags, 0o666)
    try:
        written = os.write(descriptor, encoded)
        if written != len(encoded):
            raise OSError(f"short append: wrote {written} of {len(encoded)} bytes")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append one JSON object with host-owned time and time_authority fields."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--file", required=True, dest="ledger_name")
    payload = parser.add_mutually_exclusive_group(required=True)
    payload.add_argument("--data-json")
    payload.add_argument(
        "--field",
        action="append",
        help="Top-level string field as key=value; repeat for additional fields.",
    )
    return parser


def _payload_from_fields(fields: list[str]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for field in fields:
        if "=" not in field:
            raise ValueError("--field must use key=value")
        key, value = field.split("=", 1)
        if not key:
            raise ValueError("--field key cannot be empty")
        if key in payload:
            raise ValueError(f"duplicate --field key: {key}")
        payload[key] = value
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.data_json is not None:
            payload = json.loads(args.data_json)
            if not isinstance(payload, dict):
                raise ValueError("--data-json must decode to a JSON object")
        else:
            payload = _payload_from_fields(args.field)
        row = append_clocked_row(
            root=args.root,
            ledger_name=args.ledger_name,
            payload=payload,
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
