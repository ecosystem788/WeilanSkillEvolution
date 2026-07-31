#!/usr/bin/env python3
"""Report whether repo-relative files cited by one peer-chat bucket are reachable."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Iterable


LEDGER_NAME = "peer-chat.jsonl"
DIRECTORIES = (
    "baseline",
    "deployments",
    "docs",
    "evals",
    "packages",
    "proposals",
    "references",
    "scripts",
    "tests",
    "theory",
    "tools",
)
ROOT_FILES = (
    "AGENTS.md",
    "ARCHITECTURE.md",
    "CHARTER.md",
    "EVALUATION_POLICY.md",
    "ROADMAP.md",
)
EXTENSIONS = (
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
)
PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./:\\-])(?:"
    r"(?:" + "|".join(re.escape(item) for item in DIRECTORIES) + r")/"
    r"[A-Za-z0-9_./+\-]+|"
    + "|".join(re.escape(item) for item in ROOT_FILES)
    + r")"
)


class CheckError(RuntimeError):
    """A structured, caller-correctable check failure."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def _record_bytes_without_lf(raw: bytes) -> bytes:
    return raw[:-1] if raw.endswith(b"\n") else raw


def _record_sha256(raw: bytes) -> str:
    return hashlib.sha256(_record_bytes_without_lf(raw)).hexdigest()


def _run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace").strip()
        raise CheckError("git_failed", f"git {' '.join(args)}: {stderr}")
    return result


def _git_lines(root: Path, *args: str) -> set[str]:
    output = _run_git(root, *args).stdout.decode("utf-8", "replace")
    return {line.strip() for line in output.splitlines() if line.strip()}


def _strip_tail(candidate: str) -> str:
    while candidate and candidate[-1] in ".,;:)(`'\"-/":
        if candidate.lower().endswith(EXTENSIONS):
            break
        candidate = candidate[:-1]
    return candidate


def cited_paths(text: object) -> list[str]:
    if not isinstance(text, str):
        return []
    found: list[str] = []
    for match in PATH_RE.finditer(text):
        candidate = _strip_tail(match.group(0))
        if not candidate.lower().endswith(EXTENSIONS):
            continue
        path = PurePosixPath(candidate)
        if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
            continue
        normalized = path.as_posix()
        if normalized not in found:
            found.append(normalized)
    return found


def _is_ignored(root: Path, path: str) -> bool:
    result = _run_git(root, "check-ignore", "--no-index", "-q", "--", path, check=False)
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    stderr = result.stderr.decode("utf-8", "replace").strip()
    raise CheckError("git_failed", f"git check-ignore --no-index -- {path}: {stderr}")


def _classify(
    *, root: Path, path: str, tracked: set[str], historical: set[str]
) -> str:
    if path in tracked:
        return "tracked_head"
    if path in historical:
        return "history_only"
    if _is_ignored(root, path):
        return "ignored"
    disk_path = (root / Path(*PurePosixPath(path).parts)).resolve()
    try:
        disk_path.relative_to(root)
    except ValueError as exc:
        raise CheckError("invalid_path", f"path escapes root: {path}") from exc
    if disk_path.exists():
        return "disk_only"
    return "missing"


def _ledger_rows(ledger: Path) -> tuple[list[tuple[int, bytes, dict[str, object]]], list[dict[str, object]]]:
    rows: list[tuple[int, bytes, dict[str, object]]] = []
    parse_errors: list[dict[str, object]] = []
    for line_number, raw in enumerate(ledger.read_bytes().splitlines(keepends=True), 1):
        payload = _record_bytes_without_lf(raw)
        if not payload.strip():
            continue
        try:
            decoded = payload.decode("utf-8")
            record = json.loads(decoded)
            if not isinstance(record, dict):
                raise ValueError("record is not a JSON object")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            parse_errors.append(
                {
                    "physical_line": line_number,
                    "record_sha256": _record_sha256(raw),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        rows.append((line_number, raw, record))
    return rows, parse_errors


def check_bucket(*, root: Path, author: str, timestamp: str) -> dict[str, object]:
    ledger_root = root.resolve()
    if not ledger_root.is_dir():
        raise CheckError("invalid_root", f"root is not a directory: {ledger_root}")
    ledger = ledger_root / LEDGER_NAME
    if not ledger.is_file():
        raise CheckError("ledger_not_found", f"ledger does not exist: {ledger}")
    if not author or not timestamp:
        raise CheckError("invalid_identity", "--from and --time must be non-empty")

    rows, parse_errors = _ledger_rows(ledger)
    matches = [row for row in rows if row[2].get("from") == author and row[2].get("time") == timestamp]
    if not matches:
        raise CheckError("message_not_found", f"no record matches from={author!r}, time={timestamp!r}")

    repository_root_text = _run_git(
        ledger_root, "rev-parse", "--show-toplevel"
    ).stdout.decode("utf-8", "replace").strip()
    repository_root = Path(repository_root_text).resolve()
    tracked = _git_lines(repository_root, "ls-files")
    historical = _git_lines(
        repository_root, "log", "--all", "--pretty=format:", "--name-only"
    )
    records: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    for line_number, raw, record in matches:
        citations = []
        for path in cited_paths(record.get("text")):
            status = _classify(
                root=repository_root,
                path=path,
                tracked=tracked,
                historical=historical,
            )
            counts[status] += 1
            citations.append(
                {
                    "path": path,
                    "status": status,
                    "source_ref": f"{LEDGER_NAME}:{line_number}@{timestamp}",
                }
            )
        records.append(
            {
                "physical_line": line_number,
                "record_sha256": _record_sha256(raw),
                "from": author,
                "time": timestamp,
                "cited_path_count": len(citations),
                "citations": citations,
            }
        )

    warning_count = counts["disk_only"] + counts["missing"]
    return {
        "check": "cited_artifact_receipt_visibility",
        "authority": "report_only",
        "root": str(ledger_root),
        "repository_root": str(repository_root),
        "ledger": str(ledger),
        "identity": {"from": author, "time": timestamp},
        "matched_record_count": len(records),
        "records": records,
        "status_counts": dict(sorted(counts.items())),
        "warning_count": warning_count,
        "warning_statuses": ["disk_only", "missing"],
        "parse_errors": parse_errors,
        "boundary": "cited reachability is not artifact completeness or evidentiary verifiability",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report reachability of repo-relative file citations in one peer-chat (from,time) bucket."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--from", required=True, dest="author")
    parser.add_argument("--time", required=True, dest="timestamp")
    return parser


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False))


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        payload = check_bucket(root=args.root, author=args.author, timestamp=args.timestamp)
    except (CheckError, OSError) as exc:
        reason = exc.reason if isinstance(exc, CheckError) else "io_failed"
        detail = exc.detail if isinstance(exc, CheckError) else f"{type(exc).__name__}: {exc}"
        _emit(
            {
                "check": "cited_artifact_receipt_visibility",
                "authority": "report_only",
                "ok": False,
                "reason": reason,
                "detail": detail,
            }
        )
        return 2
    payload["ok"] = True
    _emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
