"""Build a compact wake briefing without changing authority sources.

This module is deliberately independent of weilan_trace.py internals.  The CLI
may shell out to the public trace command, while tests inject fixture JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


CURSOR_SCHEMA = "wake_cursor_v0.1"
TRACKED_CURSOR_FILES = ("peer-chat.jsonl", "codex-inbox-replies.jsonl", "concurrent-receipts.jsonl")

# Sentinel files that must exist under a live wake root.  Their absence means
# --root points at the wrong directory (e.g. a deployed scripts dir that holds
# only the script, not the inbox/chat files).  When they are missing the brief
# must NOT present as a healthy `incremental` empty result -- that is the silent
# false-zero the deployed-root audit surfaced.  owner-inbox.jsonl is deliberately
# excluded: the wake prompt treats its absence as normal ("不存在就跳过").
REQUIRED_SOURCE_FILES = ("peer-chat.jsonl", "codex-inbox-replies.jsonl")
_MISSING = object()


def parse_diagnostic(
    source: Path | str,
    line: int,
    reason_code: str,
    detail: str,
    record_bytes: bytes,
    byte_offset: int,
) -> dict[str, Any]:
    """Build the shared seven-field diagnostic for one physical JSONL record."""
    payload = record_bytes
    if payload.endswith(b"\r\n"):
        payload = payload[:-2]
    elif payload.endswith(b"\n"):
        payload = payload[:-1]
    try:
        raw_text: str | None = payload.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = None
    return {
        "source": Path(source).as_posix(),
        "line": int(line),
        "reason_code": reason_code,
        "detail": detail,
        "raw_text": raw_text,
        "raw_bytes_sha256": _sha256(record_bytes),
        "byte_offset": int(byte_offset),
    }


def _physical_records(data: bytes):
    """Yield (zero-based line, byte offset, record including its terminator)."""
    start = 0
    line_index = 0
    while start < len(data):
        newline = data.find(b"\n", start)
        end = len(data) if newline < 0 else newline + 1
        yield line_index, start, data[start:end]
        line_index += 1
        start = end


def _record_payload(record_bytes: bytes) -> bytes:
    if record_bytes.endswith(b"\r\n"):
        return record_bytes[:-2]
    if record_bytes.endswith(b"\n"):
        return record_bytes[:-1]
    return record_bytes


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return _jsonl_from_bytes(path, path.read_bytes())


def _jsonl_from_bytes(
    path: Path,
    data: bytes,
    start_line: int = 0,
    start_byte: int = 0,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_index, relative_offset, record_bytes in _physical_records(data):
        payload = _record_payload(record_bytes)
        if not payload.strip():
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            rows.append(
                parse_diagnostic(
                    path,
                    start_line + line_index + 1,
                    "decode_failure",
                    f"{type(exc).__name__}: {exc}",
                    record_bytes,
                    start_byte + relative_offset,
                )
            )
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            rows.append(
                parse_diagnostic(
                    path,
                    start_line + line_index + 1,
                    "invalid_json",
                    f"{type(exc).__name__}: {exc}",
                    record_bytes,
                    start_byte + relative_offset,
                )
            )
            continue
        if isinstance(value, dict):
            rows.append(value)
        else:
            rows.append(
                parse_diagnostic(
                    path,
                    start_line + line_index + 1,
                    "not_object",
                    "TypeError: JSONL row must be an object",
                    record_bytes,
                    start_byte + relative_offset,
                )
            )
    return rows


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _line_count(data: bytes) -> int:
    return data.count(b"\n")


def _normalize_eol(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _prefix_for_line_count(data: bytes, line_count: int) -> bytes | None:
    if line_count < 0:
        return None
    if line_count == 0:
        return b""
    start = 0
    for _ in range(line_count):
        newline = data.find(b"\n", start)
        if newline < 0:
            return None
        start = newline + 1
    return data[:start]


def cursor_entry_for(path: Path, byte_offset: int | None = None) -> dict[str, Any]:
    data = path.read_bytes() if path.exists() else b""
    prefix = data if byte_offset is None else data[:byte_offset]
    return {
        "byte_offset": len(prefix),
        "line_count": _line_count(prefix),
        "file_size": len(data),
        "content_tail_hash": _sha256(prefix),
        "normalized_prefix_hash": _sha256(_normalize_eol(prefix)),
    }


def load_cursor(cursor_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not cursor_path.exists():
        return None, "no_cursor"
    try:
        cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "unreadable_cursor"
    if not isinstance(cursor, dict) or cursor.get("schema_version") != CURSOR_SCHEMA:
        return None, "unreadable_cursor"
    return cursor, None


def validate_cursor(
    root: Path,
    cursor: dict[str, Any] | None,
    initial_reason: str | None,
) -> tuple[str, str | None, dict[str, Any] | None]:
    if cursor is None:
        return "full_rescan", initial_reason or "no_cursor", None

    files = cursor.get("files")
    if not isinstance(files, dict):
        return "full_rescan", "unreadable_cursor", None

    representation_drift_details: list[dict[str, Any]] = []
    for name in TRACKED_CURSOR_FILES:
        entry = files.get(name)
        if not isinstance(entry, dict):
            return "full_rescan", "no_cursor", None

        path = root / name
        data = path.read_bytes() if path.exists() else b""
        size = len(data)
        stored_size = int(entry.get("file_size", 0))
        offset = int(entry.get("byte_offset", 0))
        stored_lines = int(entry.get("line_count", 0))
        stored_hash = str(entry.get("content_tail_hash", ""))
        stored_normalized_hash = entry.get("normalized_prefix_hash")

        actual_offset = min(offset, size)
        actual_prefix = data[:actual_offset]
        details = {
            "tracked_file": name,
            "stored": {
                "file_size": stored_size,
                "byte_offset": offset,
                "line_count": stored_lines,
                "prefix_hash": stored_hash,
            },
            "actual": {
                "file_size": size,
                "byte_offset": actual_offset,
                "line_count": _line_count(actual_prefix),
                "prefix_hash": _sha256(actual_prefix),
            },
        }

        # write_cursor records the whole observed file, so these two values are
        # an integrity pair.  Do not let a tampered offset borrow the normalized
        # anchor and masquerade as representation-only drift.
        if offset != stored_size:
            return "full_rescan", "offset_oob" if offset > size else "prefix_mismatch", details

        raw_prefix_matches = offset <= size and _sha256(data[:offset]) == stored_hash
        if raw_prefix_matches:
            if _line_count(data[:offset]) != stored_lines:
                return "full_rescan", "line_count_mismatch", details
            continue

        line_prefix = _prefix_for_line_count(data, stored_lines)
        normalized_prefix_matches = (
            isinstance(stored_normalized_hash, str)
            and line_prefix is not None
            and _sha256(_normalize_eol(line_prefix)) == stored_normalized_hash
        )
        if normalized_prefix_matches:
            representation_drift_details.append(
                {
                    **details,
                    "stored_normalized_prefix_hash": stored_normalized_hash,
                    "actual_normalized_prefix_hash": _sha256(_normalize_eol(line_prefix)),
                }
            )
            continue

        if size < stored_size:
            return "full_rescan", "file_shrank", details
        if offset > size:
            return "full_rescan", "offset_oob", details
        return "full_rescan", "prefix_mismatch", details

    if representation_drift_details:
        return "representation_drift", "eol_only_prefix_change", {"files": representation_drift_details}
    return "incremental", None, None


def write_cursor(
    root: Path,
    cursor_path: Path,
    scope: str,
    updated_at_utc: str,
    *,
    preserve_previous: bool = False,
) -> dict[str, Any]:
    cursor = {
        "schema_version": CURSOR_SCHEMA,
        "scope": scope,
        "files": {name: cursor_entry_for(root / name) for name in TRACKED_CURSOR_FILES},
        "updated_at_utc": updated_at_utc,
    }
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(cursor, ensure_ascii=False, indent=2) + "\n"
    if preserve_previous and cursor_path.exists():
        # Copy before committing the replacement.  Never move the live cursor:
        # a crash between move and commit would manufacture a no_cursor window.
        cursor_path.with_name("wake-cursor.prev.json").write_bytes(cursor_path.read_bytes())
    # The cursor is a DISPOSABLE cache — validate_cursor already falls back to
    # full_rescan on any mismatch/corruption — so it does not need atomic-
    # replace durability. Prefer atomic (temp+os.replace) where the runtime can
    # do it, but degrade to a direct in-place write when os.replace is blocked
    # (Codex's workspace-write sandbox lets it create the temp but denies the
    # rename → WinError 5; 2026-07-10 incident). A torn in-place write just
    # trips full_rescan next wake — safe, never a data-loss path.
    tmp_path = cursor_path.with_suffix(cursor_path.suffix + ".tmp")
    try:
        tmp_path.write_text(payload, encoding="utf-8")
        os.replace(tmp_path, cursor_path)
    except OSError:
        cursor_path.write_text(payload, encoding="utf-8")
        try:
            tmp_path.unlink()
        except OSError:
            pass
    return cursor


def _processed_ids(path: Path) -> set[str]:
    return {str(row["id"]) for row in read_jsonl(path) if "id" in row}


def owner_inbox_delta(root: Path) -> list[dict[str, Any]]:
    processed = _processed_ids(root / "owner-inbox-processed.jsonl")
    return [row for row in read_jsonl(root / "owner-inbox.jsonl") if str(row.get("id", "")) not in processed]


def _tail_jsonl(root: Path, name: str, mode: str, cursor: dict[str, Any] | None) -> list[dict[str, Any]]:
    path = root / name
    if not path.exists():
        return []
    data = path.read_bytes()
    if mode in {"incremental", "representation_drift"} and cursor is not None:
        entry = cursor["files"][name]
        if mode == "representation_drift":
            stored_lines = int(entry["line_count"])
            prefix = _prefix_for_line_count(data, stored_lines)
            if prefix is None:
                return _jsonl_from_bytes(path, data, start_line=0, start_byte=0)
            return _jsonl_from_bytes(
                path,
                data[len(prefix) :],
                start_line=stored_lines,
                start_byte=len(prefix),
            )
        offset = int(entry["byte_offset"])
        prefix = data[:offset]
        return _jsonl_from_bytes(
            path,
            data[offset:],
            start_line=_line_count(prefix),
            start_byte=offset,
        )
    return _jsonl_from_bytes(path, data, start_line=0)


def _unfolded_concurrent_receipts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    folded = {
        str(row.get("wake_id"))
        for row in rows
        if row.get("wake_id") and row.get("folded_by_frame_id")
    }
    return [
        row
        for row in rows
        if row.get("wake_id") not in folded and not row.get("folded_by_frame_id")
    ]


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


PROSPECTIVE_ERROR_UNRECOGNIZED_SHAPE = "unrecognized_goal_shape"
PROSPECTIVE_ERROR_COMMAND_FAILED = "prospective_show_command_failed"


def _prospective_goals(raw: Any) -> list[dict[str, Any]]:
    """Extract goals from the real prospective-show shape.

    Real shape (weilan_trace.py command_prospective_show, measured 2026-08-04
    on scope skill-evolution): raw is a dict whose "goals" entry is a dict
    keyed by goal_ref; each goal carries condition.not_before_utc.  A list of
    goal dicts is also accepted as the goals container.  Anything else is not
    a recognized goal source and yields no goals; prospective_shape_error()
    says why, so an empty result is never silent.
    """
    if not isinstance(raw, dict):
        return []
    goals = raw.get("goals")
    if isinstance(goals, dict):
        return [item for item in goals.values() if isinstance(item, dict)]
    if isinstance(goals, list):
        return [item for item in goals if isinstance(item, dict)]
    return []


def prospective_shape_error(raw: Any) -> str | None:
    """Fail-closed shape guard for the prospective-show payload.

    Returns an error code when raw is not a recognized goal source, else
    None.  The brief must never present 'I could not read the goals' as
    'there are no due goals' (the zero-hits-read-as-zero-input family).
    The code is reported in-band in the brief; nothing here raises, writes
    method-state, or touches activation -- zero authority, same exit
    discipline as the liveness sentinel.
    """
    if isinstance(raw, dict) and "error" in raw and "goals" not in raw:
        return PROSPECTIVE_ERROR_COMMAND_FAILED
    if not isinstance(raw, dict):
        return PROSPECTIVE_ERROR_UNRECOGNIZED_SHAPE
    goals = raw.get("goals")
    if goals is None or not isinstance(goals, (dict, list)):
        return PROSPECTIVE_ERROR_UNRECOGNIZED_SHAPE
    entries = list(goals.values()) if isinstance(goals, dict) else list(goals)
    if entries and not any(isinstance(item, dict) for item in entries):
        return PROSPECTIVE_ERROR_UNRECOGNIZED_SHAPE
    return None


def _observed_events_by_name(raw: Any) -> dict[str, list[dict[str, Any]]]:
    """Index observed causal events by event_name.

    Real shape: raw["causal_events"] is a dict keyed by causal_event_id; each
    observed event carries observed_at_utc and has NO state/status field.
    Goals join to events through condition.event_name == event.event_name.
    Joining on goal.causal_event_id instead is unreliable: that id only
    appears while the event is inside the display window (measured 3/49 on
    2026-08-04; the window holds the newest 20 of 1059 events by default).
    """
    if not isinstance(raw, dict):
        return {}
    causal = raw.get("causal_events")
    if isinstance(causal, dict):
        events = causal.values()
    elif isinstance(causal, list):
        events = causal
    else:
        return {}
    by_name: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if isinstance(event, dict) and event.get("event_name") is not None:
            by_name.setdefault(str(event["event_name"]), []).append(event)
    return by_name


def prospective_due(raw: Any, now_utc: str) -> list[dict[str, Any]]:
    """Select ACTIVE goals whose not_before has passed.

    Each due goal is annotated with the observed causal events whose
    event_name matches condition.event_name, copied verbatim from the ledger
    (observed_at_utc IS the observation fact; weilan_trace has no READY state
    vocabulary, so no state is stamped onto ledger data).  Note the display
    window is truncated by default (prospective-show --limit 20): a due goal
    with an empty causal_events list may still have an observed event outside
    the window -- prospective_due_meta carries the truncation flag.

    Prospective state is never activation or action authority: due means the
    time condition is met, not that the goal is the work to do.
    """
    now = _parse_time(now_utc)
    observed = _observed_events_by_name(raw)
    due: list[dict[str, Any]] = []
    for goal in _prospective_goals(raw):
        state = str(goal.get("state", goal.get("status", ""))).upper()
        if state != "ACTIVE":
            continue
        condition = goal.get("condition")
        condition = condition if isinstance(condition, dict) else {}
        not_before = _parse_time(condition.get("not_before_utc"))
        if now is not None and not_before is not None and not_before > now:
            continue
        event_name = condition.get("event_name")
        matched = observed.get(str(event_name), []) if event_name is not None else []
        item = dict(goal)
        item["causal_events"] = [dict(event) for event in matched]
        due.append(item)
    return due


def _trace_script() -> str:
    return os.environ.get(
        "WEILAN_TRACE_SCRIPT",
        r"D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py",
    )


def _run_json(command: list[str], runner: Callable[[list[str]], str] | None = None) -> Any:
    try:
        output = runner(command) if runner else subprocess.check_output(command, text=True, encoding="utf-8")
        return json.loads(output)
    except Exception as exc:  # noqa: BLE001 - failures are reported in-band by contract.
        return {"error": str(exc), "command": command}


class _GitError(Exception):
    """A git invocation failed (non-zero exit or command not found)."""

    def __init__(self, message: str, command: list[str]) -> None:
        super().__init__(message)
        self.message = message
        self.command = command


def _run_git(workspace: str, command: list[str]) -> str:
    argv = ["git", "-C", workspace, *command]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError as exc:
        raise _GitError(str(exc), argv) from exc
    if proc.returncode != 0:
        raise _GitError(proc.stderr.strip() or f"exit {proc.returncode}", argv)
    return proc.stdout


def unpushed_commits_for(
    workspace: str,
    runner: Callable[[list[str]], str] | None = None,
) -> dict[str, Any]:
    """Count commits ahead of the upstream remote-tracking ref (read-only).

    4021 bridge (proposal peer-chat:4102 + agreement peer-chat:4105): the
    wake brief reports how many local commits are not yet pushed so the
    charter-daily-push rule has a machine-visible trigger.  Zero authority:
    this never pushes and never changes the push/scan_only_gate discipline.

    Fail-closed shape, so a broken sensor can never masquerade as '0
    unpushed': success is {"count", "head_short", "suggestion"}; the four
    failure classes are {"count": null, "error", "command"}:
    - git raises / non-zero: error "git_command_failed" (+ error_detail)
    - not a git repository:  error "not a git repository"
    - detached HEAD or no upstream: error "no_upstream_or_detached"
    A failed `git fetch` does not abort: the count falls back to the local
    remote-tracking ref and the result carries fetch_failed=True so a stale
    count is never presented as fresh.
    """
    call = runner if runner is not None else (lambda command: _run_git(workspace, command))

    def fail(code: str, command: list[str], detail: str = "") -> dict[str, Any]:
        payload: dict[str, Any] = {
            "count": None,
            "error": code,
            "command": ["git", "-C", workspace, *command],
        }
        if detail:
            payload["error_detail"] = detail
        return payload

    fetch_failed = False
    try:
        call(["fetch"])
    except _GitError:
        fetch_failed = True

    branch_command = ["rev-parse", "--abbrev-ref", "HEAD"]
    try:
        branch = call(branch_command).strip()
    except _GitError as exc:
        if "not a git repository" in exc.message:
            return fail("not a git repository", branch_command)
        return fail("git_command_failed", branch_command, detail=exc.message)
    if branch == "HEAD":
        return fail("no_upstream_or_detached", branch_command)

    upstream_command = ["rev-parse", "--abbrev-ref", "--symbolic-full-name", f"{branch}@{{upstream}}"]
    try:
        upstream = call(upstream_command).strip()
    except _GitError as exc:
        if "not a git repository" in exc.message:
            return fail("not a git repository", upstream_command)
        return fail("no_upstream_or_detached", upstream_command)

    count_command = ["rev-list", "--left-right", "--count", f"{upstream}...HEAD"]
    try:
        counts = call(count_command).strip()
    except _GitError as exc:
        if "not a git repository" in exc.message:
            return fail("not a git repository", count_command)
        return fail("git_command_failed", count_command, detail=exc.message)
    try:
        _left, right = counts.split()
        ahead = int(right)
    except ValueError:
        return fail("git_command_failed", count_command, detail=f"unexpected rev-list output: {counts!r}")

    head_short: str | None = None
    try:
        head_short = call(["rev-parse", "--short", "HEAD"]).strip()
    except _GitError:
        pass

    result: dict[str, Any] = {
        "count": ahead,
        "head_short": head_short,
        "suggestion": "本醒可推" if ahead > 0 else "无可推",
    }
    if fetch_failed:
        result["fetch_failed"] = True
    return result


def _authority_from(recall_raw: Any) -> dict[str, Any]:
    if not isinstance(recall_raw, dict):
        return {"error": "memory-recall did not return a JSON object", "raw": recall_raw}
    return {
        "activation": recall_raw.get("activation"),
        "control": recall_raw.get("control"),
        "freshness": recall_raw.get("freshness"),
    }


def _source(ref: str, kind: str, **extra: Any) -> dict[str, Any]:
    item = {"ref": ref, "kind": kind}
    item.update(extra)
    return item


def _source_refs(sources: list[dict[str, Any]]) -> list[str]:
    return [str(source["ref"]) for source in sources if isinstance(source, dict) and "ref" in source]


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256(payload)


_CLOCK_DISPLAY_FIELDS = frozenset({"eligible_after_utc", "remaining_seconds", "eligible_now"})


def _clock_annotated_open_agenda(items: list[Any], now_utc: str) -> list[Any]:
    now = _parse_time(now_utc)
    annotated: list[Any] = []
    for item in items:
        if not isinstance(item, dict):
            annotated.append(item)
            continue
        condition = item.get("condition")
        event_kind = str(condition.get("event_kind", "")).lower() if isinstance(condition, dict) else ""
        eligible_after = condition.get("not_before_utc") if isinstance(condition, dict) else None
        not_before = _parse_time(eligible_after)
        if event_kind != "clock" or now is None or not_before is None:
            annotated.append(item)
            continue
        remaining_seconds = (not_before - now).total_seconds()
        annotated.append(
            {
                **item,
                "eligible_after_utc": eligible_after,
                "remaining_seconds": remaining_seconds,
                "eligible_now": remaining_seconds <= 0,
            }
        )
    return annotated


def _fingerprint_open_agenda(items: Any) -> Any:
    if not isinstance(items, list):
        return items
    return [
        {key: value for key, value in item.items() if key not in _CLOCK_DISPLAY_FIELDS}
        if isinstance(item, dict)
        else item
        for item in items
    ]


def site_fingerprint_for(brief: dict[str, Any]) -> dict[str, Any]:
    source_refs = _source_refs(brief.get("sources", []))
    fingerprint_subset = {
        "authority": brief.get("authority"),
        "owner_inbox_delta": brief.get("owner_inbox_delta", []),
        "prospective_due": brief.get("prospective_due", []),
        # The shape-guard error is part of the situation: 'no due goals' and
        # 'could not read the goals' must never hash to the same fingerprint.
        "prospective_due_error": brief.get("prospective_due_error"),
        "open_agenda": _fingerprint_open_agenda(brief.get("open_agenda", [])),
        "peer_chat_new": brief.get("peer_chat_new", []),
        "cursor_status": brief.get("cursor_status"),
        "source_refs": source_refs,
    }
    return {
        "hash": _stable_hash(fingerprint_subset),
        "inbox_has_work": bool(brief.get("owner_inbox_delta")),
        "prospective_has_due": bool(brief.get("prospective_due")),
        "open_agenda_present": bool(brief.get("open_agenda")),
        "peer_chat_has_route_change": bool(brief.get("peer_chat_new")),
        "source_refs": source_refs,
    }


def build_brief(
    *,
    root: Path,
    workspace: str,
    scope: str,
    updated_at_utc: str,
    now_utc: str | None = None,
    recall_fixture: Any = _MISSING,
    prospective_fixture: Any = _MISSING,
    runner: Callable[[list[str]], str] | None = None,
    git_runner: Callable[[list[str]], str] | None = None,
    commit_cursor: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    now = now_utc or updated_at_utc
    trace_script = _trace_script()

    recall_raw = (
        recall_fixture
        if recall_fixture is not _MISSING
        else _run_json([sys.executable, trace_script, "memory-recall", "--workspace", workspace, "--scope", scope], runner)
    )
    prospective_raw = (
        prospective_fixture
        if prospective_fixture is not _MISSING
        else _run_json([sys.executable, trace_script, "prospective-show", "--workspace", workspace, "--scope", scope], runner)
    )

    cursor_path = root / "wake-cursor.json"
    cursor, cursor_reason = load_cursor(cursor_path)
    cursor_mode, reason, mismatch_details = validate_cursor(root, cursor, cursor_reason)

    shape_error = prospective_shape_error(prospective_raw)

    brief = {
        "authority": _authority_from(recall_raw),
        "owner_inbox_delta": owner_inbox_delta(root),
        "prospective_due": [] if shape_error is not None else prospective_due(prospective_raw, now),
        "open_agenda": _clock_annotated_open_agenda(
            recall_raw.get("open_agenda", [])
            if isinstance(recall_raw, dict) and isinstance(recall_raw.get("open_agenda", []), list)
            else [],
            now,
        ),
        "codex_replies_unreviewed": _tail_jsonl(root, "codex-inbox-replies.jsonl", cursor_mode, cursor),
        "peer_chat_new": _tail_jsonl(root, "peer-chat.jsonl", cursor_mode, cursor),
        "concurrent_receipts_new": _unfolded_concurrent_receipts(
            _tail_jsonl(root, "concurrent-receipts.jsonl", cursor_mode, cursor)
        ),
        "unpushed_commits": unpushed_commits_for(workspace, git_runner),
        "sources": [
            _source("command:memory-recall", "command", workspace=workspace, scope=scope),
            _source("command:prospective-show", "command", workspace=workspace, scope=scope),
            _source((root / "owner-inbox.jsonl").as_posix(), "file"),
            _source((root / "owner-inbox-processed.jsonl").as_posix(), "file"),
            _source((root / "codex-inbox-replies.jsonl").as_posix(), "file"),
            _source((root / "peer-chat.jsonl").as_posix(), "file"),
            _source((root / "concurrent-receipts.jsonl").as_posix(), "file"),
            _source(cursor_path.as_posix(), "cursor"),
        ],
        "cursor_status": {"status": cursor_mode},
    }
    if reason:
        brief["cursor_status"]["reason"] = reason
    if mismatch_details is not None:
        brief["cursor_status"]["details"] = mismatch_details

    if shape_error is not None:
        # Fail-closed visibility: the brief says WHY the due list is empty
        # instead of letting 'unreadable' masquerade as 'nothing due'.
        brief["prospective_due_error"] = shape_error
        if shape_error == PROSPECTIVE_ERROR_COMMAND_FAILED and isinstance(prospective_raw, dict):
            brief["prospective_due_error_detail"] = str(prospective_raw.get("error"))
    elif isinstance(prospective_raw, dict):
        # Display-only epistemic qualifier (deliberately NOT in the
        # fingerprint subset): the attached-event window is the newest
        # --limit entries, so a due goal with no attached events may still
        # have an observed event outside the window.
        causal = prospective_raw.get("causal_events")
        brief["prospective_due_meta"] = {
            "causal_event_count": prospective_raw.get("causal_event_count"),
            "causal_events_shown": len(causal) if isinstance(causal, (dict, list)) else 0,
            "causal_events_truncated": bool(prospective_raw.get("causal_events_truncated")),
        }

    missing_sources = [name for name in REQUIRED_SOURCE_FILES if not (root / name).exists()]
    if missing_sources:
        # Wrong root: the live conversation files are absent.  Override the
        # healthy-looking mode with an abnormal status so the wake-prompt
        # fallback fires instead of trusting a blind, empty brief.
        prior_status = brief["cursor_status"]
        brief["cursor_status"] = {
            "status": "missing_sources",
            "missing_sources": missing_sources,
            "prior_status": prior_status,
        }

    for ref in _collect_source_refs(recall_raw):
        brief["sources"].append(_source(str(ref), "recall_source_ref"))
    for ref in _collect_source_refs(prospective_raw):
        brief["sources"].append(_source(str(ref), "prospective_source_ref"))

    brief["site_fingerprint"] = site_fingerprint_for(brief)

    if commit_cursor:
        write_cursor(
            root,
            cursor_path,
            scope,
            updated_at_utc,
            preserve_previous=cursor_mode == "full_rescan" and mismatch_details is not None,
        )
    return brief


def _collect_source_refs(value: Any) -> list[Any]:
    refs: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "sources" and isinstance(child, list):
                refs.extend(child)
            else:
                refs.extend(_collect_source_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(_collect_source_refs(child))
    return refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--scope", required=True)
    # Prefer an explicit --root; otherwise derive the live root from --workspace,
    # NOT from __file__.  Deriving from __file__ points a deployed copy at its own
    # scripts dir, which holds none of the inbox/chat files -> silent false-zero.
    parser.add_argument("--root", default=None)
    parser.add_argument("--updated-at-utc")
    args = parser.parse_args(argv)

    if args.root is not None:
        root = Path(args.root)
    else:
        root = Path(args.workspace) / "proposals" / "bounded-scheduler-v0.1" / "impl"

    stamp = args.updated_at_utc or datetime.now(timezone.utc).isoformat()
    brief = build_brief(
        root=root,
        workspace=args.workspace,
        scope=args.scope,
        updated_at_utc=stamp,
    )
    json.dump(brief, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
