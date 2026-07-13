"""Compile an append-only raw JSONL ledger plus corrections into a strict view."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def line_without_lf(line: bytes) -> bytes:
    return line[:-1] if line.endswith(b"\n") else line


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def default_paths(raw_path: Path) -> tuple[Path, Path, Path]:
    stem = raw_path.name.removesuffix(".jsonl")
    return (
        raw_path.with_name(f"{stem}.corrections.jsonl"),
        raw_path.with_name(f"{stem}.view.jsonl"),
        raw_path.with_name(f"{stem}.view.rejections.jsonl"),
    )


def _rejection(reason: str, correction_raw: str) -> dict[str, str]:
    return {"correction_raw": correction_raw, "reason": reason}


def _load_corrections(
    path: Path, raw_hashes: set[str]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    accepted: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []
    if not path.exists():
        return accepted, rejected

    for physical_line in path.read_bytes().splitlines(keepends=True):
        raw = line_without_lf(physical_line)
        display = raw.decode("utf-8", errors="replace")
        try:
            record = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            rejected.append(_rejection("malformed_correction", display))
            continue
        if not isinstance(record, dict):
            rejected.append(_rejection("correction_not_object", display))
            continue
        before_hash = record.get("before_hash")
        corrected = record.get("corrected_json")
        expected_after = record.get("after_hash")
        if not isinstance(before_hash, str) or before_hash not in raw_hashes:
            rejected.append(_rejection("before_hash_not_found", display))
            continue
        if not isinstance(corrected, dict):
            rejected.append(_rejection("corrected_json_not_object", display))
            continue
        actual_after = sha256_hex(canonical(corrected))
        if expected_after != actual_after:
            rejected.append(_rejection("after_hash_mismatch", display))
            continue
        if before_hash in accepted:
            rejected.append(_rejection("duplicate_before_hash", display))
            continue
        accepted[before_hash] = record
    return accepted, rejected


def compile_view(
    raw_path: Path,
    corrections_path: Path | None = None,
    view_path: Path | None = None,
    rejections_path: Path | None = None,
) -> dict[str, int]:
    raw_path = Path(raw_path)
    defaults = default_paths(raw_path)
    corrections_path = Path(corrections_path or defaults[0])
    view_path = Path(view_path or defaults[1])
    rejections_path = Path(rejections_path or defaults[2])

    raw_lines = raw_path.read_bytes().splitlines(keepends=True)
    hashes = [sha256_hex(line_without_lf(line)) for line in raw_lines]
    corrections, rejected = _load_corrections(corrections_path, set(hashes))

    output: list[bytes] = []
    applied = 0
    for line_number, (physical_line, before_hash) in enumerate(
        zip(raw_lines, hashes), start=1
    ):
        raw = line_without_lf(physical_line)
        correction = corrections.get(before_hash)
        if correction is not None:
            value = dict(correction["corrected_json"])
            value["_corrected_from"] = before_hash
            value["_correction_reason"] = correction.get("reason")
            applied += 1
        else:
            try:
                value = json.loads(raw.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("raw JSONL value is not an object")
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                value = {
                    "_lineage": "unparseable",
                    "before_hash": before_hash,
                    "raw_preserved": True,
                    "source": f"{raw_path}:{line_number}",
                }
        output.append(canonical(value) + b"\n")

    view_path.write_bytes(b"".join(output))
    rejection_bytes = b"".join(canonical(item) + b"\n" for item in rejected)
    rejections_path.write_bytes(rejection_bytes)
    return {"applied": applied, "rejected": len(rejected), "view_lines": len(output)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("--corrections", type=Path)
    parser.add_argument("--view", type=Path)
    parser.add_argument("--rejections", type=Path)
    args = parser.parse_args(argv)
    result = compile_view(args.raw, args.corrections, args.view, args.rejections)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
