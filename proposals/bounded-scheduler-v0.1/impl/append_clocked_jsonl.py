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
    parser.add_argument("--data-json")
    parser.add_argument(
        "--field",
        action="append",
        help="Top-level string field as key=value; repeat for additional fields.",
    )
    parser.add_argument(
        "--field-file",
        action="append",
        help="Top-level string field as key=path, reading exact UTF-8 file bytes; repeat.",
    )
    parser.add_argument(
        "--consume-field-file",
        action="store_true",
        help="After a successful append, unlink each field file once.",
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


def _field_file_parts(fields: list[str]) -> list[tuple[str, Path]]:
    parts: list[tuple[str, Path]] = []
    for field in fields:
        if "=" not in field:
            raise ValueError("--field-file must use key=path")
        key, path_text = field.split("=", 1)
        if not key:
            raise ValueError("--field-file key cannot be empty")
        parts.append((key, Path(path_text)))
    return parts


def _merge_field_files(
    payload: dict[str, str], parts: list[tuple[str, Path]]
) -> tuple[dict[str, str], list[Path]]:
    consumed_paths: list[Path] = []
    for key, path in parts:
        if key in payload:
            raise ValueError(f"duplicate field key: {key}")
        if not path.is_file():
            raise ValueError(f"--field-file path is not a regular file: {path}")
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raise ValueError(f"--field-file must not start with a UTF-8 BOM: {path}")
        if b"\x00" in raw:
            raise ValueError(f"--field-file must not contain NUL bytes: {path}")
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"--field-file is not valid UTF-8: {path}") from exc
        payload[key] = value
        if path not in consumed_paths:
            consumed_paths.append(path)
    return payload, consumed_paths


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        field_file_paths: list[Path] = []
        if args.data_json is not None:
            if args.field or args.field_file or args.consume_field_file:
                raise ValueError("--data-json cannot be combined with field arguments")
            payload = json.loads(args.data_json)
            if not isinstance(payload, dict):
                raise ValueError("--data-json must decode to a JSON object")
        else:
            if not args.field and not args.field_file:
                raise ValueError("one of --data-json, --field, or --field-file is required")
            if args.consume_field_file and not args.field_file:
                raise ValueError("--consume-field-file requires --field-file")
            payload = _payload_from_fields(args.field or [])
            payload, field_file_paths = _merge_field_files(
                payload, _field_file_parts(args.field_file or [])
            )
        row = append_clocked_row(
            root=args.root,
            ledger_name=args.ledger_name,
            payload=payload,
        )
        if args.consume_field_file:
            for path in field_file_paths:
                try:
                    path.unlink()
                except OSError as exc:
                    print(f"Warning: could not consume field file {path}: {exc}", file=sys.stderr)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
