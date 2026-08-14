import struct
from pathlib import Path

import watcher_sentinel
from watcher_sentinel import (
    CooldownGate,
    _parse_notify_records,
    build_wake_command,
    handle_sentinel_event,
    parse_sentinel_name,
    process_events,
)


class _DenyStat:
    def __init__(self, error):
        self.error = error

    def stat(self):
        raise self.error


def test_parse_sentinel_name():
    assert parse_sentinel_name("sentinel.claude") == "claude"
    assert parse_sentinel_name("sentinel.codex") == "codex"
    assert parse_sentinel_name("sentinel.owner") is None
    assert parse_sentinel_name("watcher-skill-evolution.pid") is None
    assert parse_sentinel_name("sentinel.") is None
    assert parse_sentinel_name("README.md") is None


def test_build_wake_command_routes_to_same_entry_as_cron(tmp_path):
    codex_cmd = build_wake_command("codex", tmp_path)
    claude_cmd = build_wake_command("claude", tmp_path)
    assert codex_cmd[-1] == str(tmp_path / "wake_codex.ps1")
    assert claude_cmd[-1] == str(tmp_path / "wake_agent.ps1")
    assert codex_cmd[0] == "powershell"


def test_handle_sentinel_event_triggers_once_then_suppresses(tmp_path):
    sentinel = tmp_path / "sentinel.claude"
    sentinel.write_bytes(b"claude\n")
    calls = []
    gate = CooldownGate(window_seconds=30.0)

    def spawn(agent):
        calls.append(agent)

    first = handle_sentinel_event("claude", sentinel, gate, spawn, now=100.0)
    second = handle_sentinel_event("claude", sentinel, gate, spawn, now=120.0)
    assert first["decision"] == "triggered"
    assert second["decision"] == "suppressed_cooldown"
    assert calls == ["claude"]


def test_handle_sentinel_event_silent_when_sentinel_missing(tmp_path):
    missing = tmp_path / "sentinel.codex"
    gate = CooldownGate(window_seconds=30.0)
    outcome = handle_sentinel_event("codex", missing, gate, lambda agent: None, now=100.0)
    assert outcome["decision"] == "silent_missing"


def test_handle_sentinel_event_stop_on_permission(tmp_path):
    gate = CooldownGate(window_seconds=30.0)
    outcome = handle_sentinel_event(
        "codex", _DenyStat(PermissionError()), gate, lambda agent: None, now=100.0
    )
    assert outcome["decision"] == "stop_permission"


def test_process_events_ignores_own_log_filename(tmp_path):
    gate = CooldownGate(window_seconds=30.0)
    logs = []
    calls = []
    sentinel = tmp_path / "sentinel.claude"
    sentinel.write_bytes(b"claude\n")
    streak, stop = process_events(
        [(1, "sentinel.claude"), (3, "watcher.log"), (3, "watcher.log")],
        sentinel_dir=tmp_path, gate=gate, spawn=lambda agent: calls.append(agent),
        log=logs.append, memory_streak=0, now=100.0,
        ignore_names=frozenset({"watcher.log"}),
    )
    assert stop is None and streak == 0
    assert calls == ["claude"]
    assert not any("watcher.log" in line for line in logs)


def test_process_events_ignores_non_sentinel_names(tmp_path):
    gate = CooldownGate(window_seconds=30.0)
    logs = []
    calls = []
    streak, stop = process_events(
        [(1, "watcher-skill-evolution.pid")],
        sentinel_dir=tmp_path, gate=gate, spawn=lambda agent: calls.append(agent),
        log=logs.append, memory_streak=0, now=100.0,
    )
    assert stop is None and streak == 0 and calls == []


def test_process_events_oom_burst_stops_after_three(tmp_path):
    gate = CooldownGate(window_seconds=30.0)
    logs = []
    sentinel = tmp_path / "sentinel.claude"
    sentinel.write_bytes(b"claude\n")

    def oom_spawn(agent):
        raise MemoryError("simulated OOM")

    streak, stop = 0, None
    # Each iteration is a separate watch batch with advancing wall-clock:
    # within one batch cooldown correctly merges, so the burst accrues
    # across batches (systemd StartLimitBurst analog).
    for batch in range(3):
        streak, stop = process_events(
            [(1, "sentinel.claude")],
            sentinel_dir=tmp_path, gate=gate, spawn=oom_spawn,
            log=logs.append, memory_streak=streak, now=100.0 + batch * 100.0,
        )
    assert stop == 2
    assert streak == 3
    assert any("MemoryError" in line for line in logs)


def test_process_events_success_resets_memory_streak(tmp_path):
    gate = CooldownGate(window_seconds=30.0)
    logs = []
    calls = []
    sentinel = tmp_path / "sentinel.claude"
    sentinel.write_bytes(b"claude\n")
    streak, stop = process_events(
        [(1, "sentinel.claude")],
        sentinel_dir=tmp_path, gate=gate, spawn=lambda agent: calls.append(agent),
        log=logs.append, memory_streak=2, now=100.0,
    )
    assert stop is None and streak == 0 and calls == ["claude"]


def test_process_events_permission_stops(tmp_path):
    gate = CooldownGate(window_seconds=30.0)
    logs = []

    class _BadPath:
        def __truediv__(self, other):
            return _BadPath()

        def stat(self):
            raise PermissionError()

    streak, stop = process_events(
        [(1, "sentinel.claude")],
        sentinel_dir=_BadPath(), gate=gate, spawn=lambda agent: None,
        log=logs.append, memory_streak=0, now=100.0,
    )
    assert stop == 1
    assert any("permission failure" in line for line in logs)


def test_parse_notify_records():
    first_name = "sentinel.claude".encode("utf-16-le")
    second_name = "sentinel.codex".encode("utf-16-le")
    next_offset = 12 + len(first_name)
    chained = (
        struct.pack("<III", next_offset, 1, len(first_name)) + first_name
        + struct.pack("<III", 0, 3, len(second_name)) + second_name
    )
    events = _parse_notify_records(chained)
    assert events == [(1, "sentinel.claude"), (3, "sentinel.codex")]
    # truncated buffer must not raise
    assert _parse_notify_records(chained[:10]) == []
