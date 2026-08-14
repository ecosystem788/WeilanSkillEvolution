#!/usr/bin/env python3
"""Append one host-clock-stamped object to a local JSONL ledger.

Wake contract (OS watcher v1, D2): --wake-true must be paired with an explicit
--wake-agent=claude|codex, otherwise the helper refuses and never silently
flips a wake sentinel.  On success the helper atomically writes
watcher/sentinel.<agent>; the watcher reads only sentinel metadata, and a
sentinel write failure never loses the ledger row (cron fallback still reads
it).  See watcher/README.md for the full contract.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Mapping


RESERVED_CLOCK_FIELDS = frozenset({"time", "time_authority"})
RESERVED_WAKE_FIELDS = frozenset({"wake"})
RESERVED_FIELDS = RESERVED_CLOCK_FIELDS | RESERVED_WAKE_FIELDS
WAKE_AGENTS = frozenset({"claude", "codex"})
DEFAULT_SENTINEL_DIRNAME = "watcher"


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


def write_wake_sentinel(
    sentinel_dir: Path,
    agent: str,
    *,
    ledger_name: str,
    row_time: str,
) -> Path:
    """Atomically write one watcher sentinel file (sentinel.<agent>).

    The sentinel lives in the watcher's own directory (default <root>/watcher),
    outside every ledger.  Content first line = agent (metadata); the worker
    reads only the filename suffix plus mtime/byte size and never parses the
    rest.  Write is atomic (temp file + os.replace) so a reader never sees a
    half-written sentinel.
    """
    if agent not in WAKE_AGENTS:
        raise ValueError(f"--wake-agent must be one of claude, codex; got {agent!r}")
    sentinel_dir = Path(sentinel_dir)
    sentinel_dir.mkdir(parents=True, exist_ok=True)
    target = sentinel_dir / f"sentinel.{agent}"
    tmp = sentinel_dir / f".sentinel.{agent}.{os.getpid()}.tmp"
    content = (
        f"{agent}\n"
        f"ledger={ledger_name}\n"
        f"row_time={row_time}\n"
    ).encode("utf-8")
    descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        written = os.write(descriptor, content)
        if written != len(content):
            raise OSError(f"short sentinel write: wrote {written} of {len(content)} bytes")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.replace(tmp, target)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return target


def append_clocked_row(
    *,
    root: Path,
    ledger_name: str,
    payload: Mapping[str, object],
    now: datetime | None = None,
    wake: bool = False,
) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a JSON object")
    if any(not isinstance(key, str) for key in payload):
        raise ValueError("payload keys must be strings")
    forbidden = sorted(RESERVED_FIELDS.intersection(payload))
    if forbidden:
        raise ValueError(f"caller cannot supply reserved fields: {', '.join(forbidden)}")

    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"--root is not an existing directory: {root}")
    ledger_path = _ledger_path(root, ledger_name)

    row = dict(payload)
    row["time"] = _clock_stamp(now)
    row["time_authority"] = "clock"
    row["wake"] = bool(wake)
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
        description=(
            "Append one JSON object with host-owned time, time_authority, and wake fields. "
            "wake defaults to false; pass --wake-true for caller-flagged wake triggers. "
            "Caller cannot supply any of {time, time_authority, wake} via --field/--data-json."
        )
    )
    parser.add_argument(
        "--root",
        required=True,
        type=Path,
        help=(
            "Ledger home directory (the helper's working directory): --file must name one "
            "existing .jsonl directly under it. Missing ledgers are refused unless "
            "--allow-create is passed (single-shot opt-in)."
        ),
    )
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
    parser.add_argument(
        "--allow-create",
        action="store_true",
        help=(
            "Override refuse-to-create trip-wire: allow writing a brand-new ledger file. "
            "Default is to refuse; this helper only appends to existing JSONL files."
        ),
    )
    parser.add_argument(
        "--wake-true",
        action="store_true",
        dest="wake_true",
        help=(
            "Stamp this appended row with wake=true AND atomically flip the "
            "watcher sentinel for the given --wake-agent. Must be paired with "
            "--wake-agent=claude|codex; without it the helper refuses (rc=2, "
            "zero writes, never a silent flip). Default is wake=false."
        ),
    )
    parser.add_argument(
        "--wake-agent",
        choices=sorted(WAKE_AGENTS),
        help=(
            "Agent to wake via the sentinel (claude or codex). Only meaningful "
            "with --wake-true; requiring it closes who the watcher may wake. "
            "The helper writes watcher/sentinel.<agent>; the watcher reads only "
            "the filename suffix + mtime/byte size."
        ),
    )
    parser.add_argument(
        "--sentinel-dir",
        type=Path,
        default=None,
        help=(
            "Directory that receives sentinel files. Default: <root>/watcher "
            "(the watcher's own directory, same root as its PID file)."
        ),
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
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        if args.wake_true and args.wake_agent is None:
            raise ValueError(
                "refuse: --wake-true requires --wake-agent=claude|codex "
                "(never silently flip a wake sentinel)"
            )
        if args.wake_agent is not None and not args.wake_true:
            raise ValueError("refuse: --wake-agent requires --wake-true")
        field_file_paths: list[Path] = []
        target = _ledger_path(args.root, args.ledger_name)
        if not target.exists() and not args.allow_create:
            raise ValueError(
                f"refuse to create new ledger file: {target}. "
                "Pass --allow-create to override (single-shot opt-in)."
            )
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
            wake=args.wake_true,
        )
        if args.wake_true:
            sentinel_dir = args.sentinel_dir or (target.parent / DEFAULT_SENTINEL_DIRNAME)
            try:
                write_wake_sentinel(
                    sentinel_dir,
                    args.wake_agent,
                    ledger_name=args.ledger_name,
                    row_time=row["time"],
                )
            except OSError as exc:
                # Fallback path: the row is already in the ledger, so the
                # message is never lost; it just waits for the next cron round
                # instead of a second-level watcher response.
                print(
                    "Warning: wake sentinel write failed (row is in ledger; "
                    f"cron fallback still reads it): {exc}",
                    file=sys.stderr,
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
