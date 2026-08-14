#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""watcher_sentinel.py - OS watcher v1 (D2): sentinel event-driven wake.

Resident process that watches one sentinel directory (default
impl/watcher) with ReadDirectoryChangesW and, when a sentinel.<agent> file
appears or changes, triggers the existing wake chain for that agent
(wake_codex.ps1 / wake_agent.ps1 - the same entry point the cron fallback
uses).  It reads only sentinel metadata (filename suffix, mtime, byte size)
and never parses sentinel content beyond the filename; it never writes the
watched directory, never writes any ledger, and never reads peer-chat.

Red lines (peer-chat:3927/4031): only flips the flag, holds no state, never
auto-starts work, never writes the ledger itself.  Self-trigger loop is cut
three ways: sentinels live in the watcher's own inbox (read side-channel,
not the main table), the worker never parses content, and a hard cooldown
merges bursts (edit 2: default 30s, pinned by test_watcher_cooldown.py).

Fail-closed (edit suggestions, 2026-08-14):
  * sentinel missing at event time -> silent no-trigger (no panic logging)
  * cannot open/watch the sentinel dir (permission) -> log once, stop
  * OOM burst (MemoryError x3) -> stop + log (systemd StartLimitBurst analog)

The PID file and the start/stop/status commands are handled by
watcher-skill-evolution-*.ps1 and documented in README.md; this process
itself never writes the watched directory.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import struct
import subprocess
import sys
import time


WAKE_AGENTS = ("claude", "codex")
SENTINEL_PREFIX = "sentinel."
DEFAULT_COOLDOWN_SECONDS = 30.0
START_LIMIT_BURST = 3
WATCH_BUFFER_BYTES = 64 * 1024

FILE_LIST_DIRECTORY = 0x0001
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_NOTIFY_CHANGE_FILE_NAME = 0x00000001
FILE_NOTIFY_CHANGE_SIZE = 0x00000002
FILE_NOTIFY_CHANGE_LAST_WRITE = 0x00000010
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HANDLE,
]
_kernel32.CreateFileW.restype = wintypes.HANDLE
_kernel32.ReadDirectoryChangesW.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.BOOL,
    wintypes.DWORD,
    wintypes.LPDWORD,
    wintypes.LPVOID,
    wintypes.LPVOID,
]
_kernel32.ReadDirectoryChangesW.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL


class WatcherSetupError(RuntimeError):
    """The watcher could not start watching (e.g. missing/denied directory)."""


def parse_sentinel_name(name: str):
    """sentinel.claude -> 'claude'; sentinel.codex -> 'codex'; else None."""
    if not name.startswith(SENTINEL_PREFIX):
        return None
    agent = name[len(SENTINEL_PREFIX):]
    return agent if agent in WAKE_AGENTS else None


class CooldownGate:
    """Hard cooldown: at most one trigger per window; bursts merge.

    Boundary semantics: an event exactly at window seconds after the last
    trigger is allowed (>=).  Pinned by test_watcher_cooldown.py; changing
    the default window requires dual sign (2026-08-14 edit 2).
    """

    def __init__(self, window_seconds=DEFAULT_COOLDOWN_SECONDS):
        if window_seconds < 0:
            raise ValueError("cooldown window must be >= 0")
        self.window_seconds = float(window_seconds)
        self._last_trigger = None

    def try_acquire(self, now: float) -> bool:
        if self._last_trigger is not None and (now - self._last_trigger) < self.window_seconds:
            return False
        self._last_trigger = now
        return True

    def reset(self) -> None:
        self._last_trigger = None

    @property
    def last_trigger(self):
        return self._last_trigger


def build_wake_command(agent: str, wake_script_dir: Path) -> list[str]:
    """Same entry point the cron fallback uses (wake_codex/wake_agent)."""
    script = Path(wake_script_dir) / ("wake_codex.ps1" if agent == "codex" else "wake_agent.ps1")
    return [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]


def _spawn_wake(agent: str, wake_script_dir: Path):
    command = build_wake_command(agent, wake_script_dir)
    subprocess.Popen(
        command,
        creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def process_events(
    events,
    *,
    sentinel_dir,
    gate,
    spawn,
    log,
    memory_streak,
    start_limit_burst=START_LIMIT_BURST,
    now=None,
    ignore_names=frozenset(),
):
    """Process one ReadDirectoryChangesW batch.

    Returns (memory_streak, stop_code): stop_code is None to keep watching, 1
    after a permission failure (log once, stop), or 2 after the OOM burst
    limit (systemd StartLimitBurst analog).  Missing sentinels are silent.
    """
    if now is None:
        now = time.time()
    for action, name in events:
        if name in ignore_names:
            # Defense-in-depth: never react to (or log) our own log writes,
            # so a misconfigured --log inside the watched dir cannot turn
            # into a self-noise loop that fills the disk.
            continue
        agent = parse_sentinel_name(name)
        try:
            outcome = handle_sentinel_event(agent, sentinel_dir / name, gate, spawn, now)
        except MemoryError:
            memory_streak += 1
            log(
                f"MemoryError during wake trigger "
                f"({memory_streak}/{start_limit_burst}); "
                "logging once and stopping"
            )
            if memory_streak >= start_limit_burst:
                return memory_streak, 2
            continue
        memory_streak = 0
        log(f"event action={action} name={name!r} -> {outcome}")
        if outcome["decision"] == "stop_permission":
            log("permission failure reading sentinel: logging once and stopping")
            return memory_streak, 1
    return memory_streak, None


def handle_sentinel_event(agent, sentinel_path, gate, spawn, now: float) -> dict:
    """Decide one sentinel event; returns an outcome dict (no side effects
    beyond an allowed spawn).  Fail-closed: missing sentinel is silent;
    permission failure asks the caller to log once and stop."""
    if agent is None:
        return {"decision": "ignored_not_sentinel"}
    try:
        stat = sentinel_path.stat()
    except FileNotFoundError:
        return {"decision": "silent_missing", "agent": agent}
    except PermissionError:
        return {"decision": "stop_permission", "agent": agent}
    if not gate.try_acquire(now):
        return {"decision": "suppressed_cooldown", "agent": agent}
    spawn(agent)
    return {
        "decision": "triggered",
        "agent": agent,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def _parse_notify_records(data: bytes) -> list[tuple[int, str]]:
    events: list[tuple[int, str]] = []
    offset = 0
    while offset + 12 <= len(data):
        next_offset, action, name_len = struct.unpack_from("<III", data, offset)
        start = offset + 12
        end = start + name_len
        if end > len(data):
            break
        name = data[start:end].decode("utf-16-le", errors="replace")
        events.append((action, name))
        if next_offset == 0:
            break
        offset += next_offset
    return events


def _read_changes(handle, buf, buf_size: int) -> bytes:
    written = wintypes.DWORD(0)
    ok = _kernel32.ReadDirectoryChangesW(
        handle,
        buf,
        buf_size,
        False,
        FILE_NOTIFY_CHANGE_FILE_NAME | FILE_NOTIFY_CHANGE_SIZE | FILE_NOTIFY_CHANGE_LAST_WRITE,
        ctypes.byref(written),
        None,
        None,
    )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    return ctypes.string_at(buf, written.value)


def make_logger(log_path: Path):
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(message: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')}  {message}"
        try:
            with log_path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
        except OSError:
            pass
        print(line, file=sys.stderr)

    return log


def run_watch(
    sentinel_dir,
    wake_script_dir,
    *,
    cooldown_seconds=DEFAULT_COOLDOWN_SECONDS,
    log=None,
    spawn=None,
    dry_run=False,
    start_limit_burst=START_LIMIT_BURST,
    ignore_names=frozenset(),
) -> int:
    sentinel_dir = Path(sentinel_dir)
    wake_script_dir = Path(wake_script_dir)
    if log is None:
        log = lambda message: print(message, file=sys.stderr)
    if not sentinel_dir.is_dir():
        raise WatcherSetupError(f"sentinel dir missing or not a directory: {sentinel_dir}")

    if spawn is None:
        if dry_run:
            def spawn(agent, _dir=wake_script_dir):
                log(f"dry-run: would run {' '.join(build_wake_command(agent, _dir))}")
                return None
        else:
            def spawn(agent, _dir=wake_script_dir):
                return _spawn_wake(agent, _dir)

    gate = CooldownGate(cooldown_seconds)
    handle = _kernel32.CreateFileW(
        str(sentinel_dir),
        FILE_LIST_DIRECTORY,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        None,
    )
    if handle is None or handle == INVALID_HANDLE_VALUE:
        raise WatcherSetupError(
            f"cannot open sentinel dir for watching: {ctypes.WinError(ctypes.get_last_error())}"
        )
    buffer = ctypes.create_string_buffer(WATCH_BUFFER_BYTES)
    memory_streak = 0
    log(f"watcher start scope=skill-evolution sentinel_dir={sentinel_dir} cooldown={gate.window_seconds}s")
    try:
        while True:
            data = _read_changes(handle, buffer, len(buffer))
            events = _parse_notify_records(data)
            memory_streak, stop_code = process_events(
                events,
                sentinel_dir=sentinel_dir,
                gate=gate,
                spawn=spawn,
                log=log,
                memory_streak=memory_streak,
                start_limit_burst=start_limit_burst,
                ignore_names=ignore_names,
            )
            if stop_code is not None:
                return stop_code
    finally:
        _kernel32.CloseHandle(handle)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sentinel-dir", required=True, type=Path)
    parser.add_argument(
        "--wake-script-dir",
        type=Path,
        default=None,
        help="dir with wake_codex.ps1 / wake_agent.ps1 (default: parent of --sentinel-dir)",
    )
    parser.add_argument(
        "--cooldown-seconds",
        type=float,
        default=DEFAULT_COOLDOWN_SECONDS,
        help=f"hard cooldown window (default {DEFAULT_COOLDOWN_SECONDS}s; pinned)",
    )
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--scope", default="skill-evolution")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    sentinel_dir = Path(args.sentinel_dir)
    wake_script_dir = Path(args.wake_script_dir) if args.wake_script_dir else sentinel_dir.parent
    log_path = Path(args.log) if args.log else sentinel_dir.parent / "watcher.log"
    log = make_logger(log_path)
    try:
        return run_watch(
            sentinel_dir,
            wake_script_dir,
            cooldown_seconds=args.cooldown_seconds,
            log=log,
            dry_run=args.dry_run,
            ignore_names=frozenset({log_path.name}),
        )
    except WatcherSetupError as exc:
        log(f"watcher setup failure: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
