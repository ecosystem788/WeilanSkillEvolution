"""Portable Task Scheduler and dashboard lifecycle for one installed release."""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


RUNTIME_DIR = Path("data/runtime")


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _namespace_project(resolved: str) -> str:
    candidate = None
    if resolved.startswith("\\\\?\\UNC\\"):
        candidate = "\\\\" + resolved[8:]
    elif resolved.startswith("\\\\?\\"):
        candidate = resolved[4:]
    if candidate and os.path.exists(candidate) and os.path.samefile(candidate, resolved):
        return candidate
    return resolved


def _path_identity(value: str) -> str:
    if not os.path.exists(value):
        raise ValueError(f"path-bearing action target does not exist: {value}")
    return _namespace_project(os.path.realpath(value))


def action_normalize(triple: dict) -> dict:
    arguments = list(triple["arguments"])
    if not arguments:
        raise ValueError("action arguments must include scheduler_cli.py")
    path_indexes = {0}
    for index, token in enumerate(arguments[:-1]):
        if token == "--install-root":
            path_indexes.add(index + 1)
    if len(path_indexes) != 2:
        raise ValueError("action must contain exactly one --install-root path")
    for index in path_indexes:
        arguments[index] = _path_identity(str(arguments[index]))
    return {
        "arguments": arguments,
        "execute": _path_identity(str(triple["execute"])),
        "working_directory": _path_identity(str(triple["working_directory"])),
    }


def action_sha256(triple: dict) -> str:
    return hashlib.sha256(_canonical(action_normalize(triple))).hexdigest()


def _runtime(root: Path) -> Path:
    return root / RUNTIME_DIR


def _registration(root: Path) -> Path:
    return _runtime(root) / "task-registration.json"


def _log(root: Path, event: dict) -> None:
    path = _runtime(root) / "runtime-events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _expected_action(root: Path, tick_only: bool) -> dict:
    script = root / "skills" / "solve-with-weilan" / "runtime" / "scheduler_cli.py"
    arguments = [str(script), "tick", "--install-root", str(root)]
    if tick_only:
        arguments.append("--tick-only")
    return {"execute": sys.executable, "arguments": arguments, "working_directory": str(root)}


def _powershell(script: str, payload: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if payload is not None:
        env["WEILAN_RUNTIME_PAYLOAD"] = json.dumps(payload, ensure_ascii=False)
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        text=True, encoding="utf-8", capture_output=True, env=env, timeout=30,
    )


def _task_query(name: str) -> dict | None:
    script = r"""
$p=$env:WEILAN_RUNTIME_PAYLOAD|ConvertFrom-Json
$t=Get-ScheduledTask -TaskName $p.name -ErrorAction SilentlyContinue
if($null -eq $t){exit 3}
$i=Get-ScheduledTaskInfo -TaskName $p.name
$a=$t.Actions[0]
@{execute=$a.Execute;arguments_display_string=$a.Arguments;working_directory=$a.WorkingDirectory;last_run=$i.LastRunTime.ToString('o');next_run=$i.NextRunTime.ToString('o')}|ConvertTo-Json -Compress
"""
    completed = _powershell(script, {"name": name})
    if completed.returncode == 3:
        return None
    if completed.returncode != 0:
        raise RuntimeError(f"Task Scheduler query failed: {completed.stderr or completed.stdout}")
    return json.loads(completed.stdout.strip().lstrip("\ufeff"))


def _argv_from_windows(value: str) -> list[str]:
    if os.name != "nt":
        raise RuntimeError("Task Scheduler action parsing requires Windows")
    argc = ctypes.c_int()
    shell32 = ctypes.windll.shell32
    kernel32 = ctypes.windll.kernel32
    shell32.CommandLineToArgvW.argtypes = (ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int))
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
    pointer = shell32.CommandLineToArgvW(value, ctypes.byref(argc))
    if not pointer:
        raise OSError(ctypes.get_last_error(), "CommandLineToArgvW failed")
    try:
        return [pointer[index] for index in range(argc.value)]
    finally:
        kernel32.LocalFree(pointer)


def _live_triple(live: dict) -> dict:
    return {
        "execute": live["execute"],
        "arguments": _argv_from_windows(live.get("arguments_display_string") or ""),
        "working_directory": live.get("working_directory") or "",
    }


def _register(name: str, triple: dict) -> None:
    display = subprocess.list2cmdline(triple["arguments"])
    script = r"""
$p=$env:WEILAN_RUNTIME_PAYLOAD|ConvertFrom-Json
$a=New-ScheduledTaskAction -Execute $p.execute -Argument $p.arguments -WorkingDirectory $p.working_directory
$t=New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(5))
$t.Repetition.Interval='PT5M';$t.Repetition.Duration='P1D'
Register-ScheduledTask -TaskName $p.name -Action $a -Trigger $t -Description 'WeiLan portable bounded scheduler' -Force | Out-Null
"""
    completed = _powershell(script, {
        "name": name, "execute": triple["execute"], "arguments": display,
        "working_directory": triple["working_directory"],
    })
    if completed.returncode != 0:
        raise RuntimeError(f"Task Scheduler registration failed: {completed.stderr or completed.stdout}")


def _unregister(name: str) -> None:
    script = r"""
$p=$env:WEILAN_RUNTIME_PAYLOAD|ConvertFrom-Json
$t=Get-ScheduledTask -TaskName $p.name -ErrorAction SilentlyContinue
if($null -ne $t){Unregister-ScheduledTask -TaskName $p.name -Confirm:$false}
"""
    completed = _powershell(script, {"name": name})
    if completed.returncode != 0:
        raise RuntimeError(f"Task Scheduler removal failed: {completed.stderr or completed.stdout}")
    if _task_query(name) is not None:
        raise RuntimeError(f"Task Scheduler still reports owned task after removal: {name}")


def trigger_task(name: str) -> None:
    completed = _powershell("$p=$env:WEILAN_RUNTIME_PAYLOAD|ConvertFrom-Json;Start-ScheduledTask -TaskName $p.name", {"name": name})
    if completed.returncode != 0:
        raise RuntimeError(f"Task Scheduler trigger failed: {completed.stderr or completed.stdout}")


def start(root: Path, install_receipt: dict, *, tick_only: bool, task_name: str | None) -> dict:
    root = root.resolve()
    config_path = _runtime(root) / "runtime.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    if not tick_only and not config.get("agent_command"):
        raise ValueError("runtime.json must configure agent_command, or pass --tick-only explicitly")
    if task_name is not None and not task_name.startswith("WeilanReleaseTest-"):
        raise ValueError("--task-name is test-only and must start with WeilanReleaseTest-")
    name = task_name or f"WeilanScheduler-{install_receipt['install_id']}"
    triple = _expected_action(root, tick_only)
    expected_hash = action_sha256(triple)
    receipt_path = _registration(root)
    old = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.is_file() else None
    if old and old.get("task_name") != name:
        raise ValueError(f"registration receipt owns task {old.get('task_name')}; stop it before selecting another name")
    live = _task_query(name)
    if live and old is None:
        raise ValueError(f"task already exists without this install's registration receipt: {name}")
    healthy = False
    if live and old:
        try:
            live_hash = action_sha256(_live_triple(live))
            healthy = live_hash == old.get("action_sha256") == expected_hash
        except (OSError, ValueError):
            healthy = False
    receipt = {
        "task_name": name,
        "action": triple,
        "action_sha256": expected_hash,
        "arguments_display_string": subprocess.list2cmdline(triple["arguments"]),
        "registered_utc": _now(),
        "tick_only": bool(tick_only),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not healthy:
        try:
            _register(name, triple)
        except Exception:
            if old is None:
                receipt_path.unlink(missing_ok=True)
            else:
                receipt_path.write_text(json.dumps(old, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            raise
        _log(root, {"time_utc": _now(), "event": "task_registered" if live is None else "task_repinned", "task_name": name})
    return {"entry": "start", "status": "running", "task": _task_query(name), "registration": receipt}


def _cmdline_identity(command_line: str) -> str:
    argv = _argv_from_windows(command_line)
    if len(argv) < 2 or argv[-2] != "--cmdline-sha256":
        raise ValueError("dashboard command line lacks ownership marker")
    return hashlib.sha256(subprocess.list2cmdline(argv[:-2]).encode("utf-8")).hexdigest()


def _pid_status(root: Path, *, clean_stale: bool = True) -> dict:
    path = _runtime(root) / "dashboard.pid"
    if not path.is_file():
        return {"live": False, "port": None}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        env = os.environ.copy(); env["WEILAN_RUNTIME_PID"] = str(int(data["pid"]))
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "$p=Get-CimInstance Win32_Process -Filter (\"ProcessId=$env:WEILAN_RUNTIME_PID\") -ErrorAction SilentlyContinue;if($null -eq $p){exit 3};[Console]::Out.Write($p.CommandLine)"],
            text=True, encoding="utf-8", capture_output=True, env=env, timeout=15,
        )
        live = completed.returncode == 0 and _cmdline_identity(completed.stdout) == data["cmdline_sha256"]
        http_ok = False
        if live:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{data['port']}/", timeout=1) as response:
                    http_ok = response.status == 200
            except OSError:
                pass
        if live and http_ok:
            return {"live": True, "pid": data["pid"], "port": data["port"], "http_200": True}
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        pass
    if clean_stale:
        path.unlink(missing_ok=True)
        _log(root, {"time_utc": _now(), "event": "stale_dashboard_pidfile_cleaned"})
    return {"live": False, "port": None, "stale_cleaned": bool(clean_stale)}


def open_dashboard(root: Path, install_receipt: dict, *, port: int, bind: str, acknowledge: bool) -> dict:
    root = root.resolve()
    if bind not in {"127.0.0.1", "::1", "localhost"} and not acknowledge:
        raise ValueError("non-loopback --bind requires --acknowledge-network-exposure")
    current = _pid_status(root)
    if current.get("live"):
        return {"entry": "open-dashboard", "status": "already_running", "url": f"http://127.0.0.1:{current['port']}/", "dashboard": current}
    script = root / "skills" / "solve-with-weilan" / "runtime" / "dashboard.py"
    method_home = _runtime(root) / "method-state"
    pidfile = _runtime(root) / "dashboard.pid"
    args = [sys.executable, str(script), "--repo-root", install_receipt["repo_root"], "--method-home", str(method_home), "--port", str(port), "--bind", bind, "--pidfile", str(pidfile)]
    if acknowledge:
        args.append("--acknowledge-network-exposure")
    # Hash the deterministic command prefix; the marker itself is excluded.
    digest = hashlib.sha256(subprocess.list2cmdline(args).encode("utf-8")).hexdigest()
    command = args + ["--cmdline-sha256", digest]
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    child = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
    if os.name == "nt":
        # Deliberately detach ownership after the pid/cmdline receipt becomes authoritative.
        child._handle.Close()  # type: ignore[attr-defined]
        child.returncode = 0
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        state = _pid_status(root, clean_stale=False)
        if state.get("live"):
            return {"entry": "open-dashboard", "status": "running", "url": f"http://127.0.0.1:{state['port']}/", "dashboard": state}
        time.sleep(0.1)
    raise RuntimeError("dashboard did not become live within 10 seconds")


def status(root: Path) -> dict:
    root = root.resolve()
    registration = None
    task = None
    receipt_path = _registration(root)
    if receipt_path.is_file():
        registration = json.loads(receipt_path.read_text(encoding="utf-8"))
        task = _task_query(registration["task_name"])
    ticks = _runtime(root) / "scheduler-ticks.jsonl"
    tick_age = None
    if ticks.is_file():
        tick_age = max(0.0, time.time() - ticks.stat().st_mtime)
    return {"task_registered": task is not None, "task": task, "registration": registration, "last_tick_age_seconds": tick_age, "dashboard": _pid_status(root)}


def stop(root: Path) -> dict:
    root = root.resolve()
    receipt_path = _registration(root)
    task_name = None
    if receipt_path.is_file():
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
        task_name = data["task_name"]
        _unregister(task_name)
        receipt_path.unlink(missing_ok=True)
    dash = _pid_status(root, clean_stale=False)
    pidfile = _runtime(root) / "dashboard.pid"
    if dash.get("live"):
        env = os.environ.copy(); env["WEILAN_RUNTIME_PID"] = str(dash["pid"])
        completed = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", "Stop-Process -Id $env:WEILAN_RUNTIME_PID -Force"], env=env, capture_output=True, timeout=15)
        if completed.returncode != 0:
            raise RuntimeError("dashboard process could not be terminated after ownership verification")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and _pid_status(root, clean_stale=False).get("live"):
            time.sleep(0.1)
    pidfile.unlink(missing_ok=True)
    _log(root, {"time_utc": _now(), "event": "runtime_stopped", "task_name": task_name})
    return {"entry": "stop", "status": "stopped", "task_name": task_name}


def remove_runtime_residue(root: Path) -> None:
    runtime = _runtime(root)
    for name in ("dashboard.pid", "task-registration.json", "scheduler-ticks.jsonl", "runtime-events.jsonl", "runtime.json"):
        (runtime / name).unlink(missing_ok=True)
    method_home = runtime / "method-state"
    if method_home.exists():
        import shutil
        shutil.rmtree(method_home)
    for directory in (method_home, runtime, runtime.parent):
        try:
            directory.rmdir()
        except OSError:
            pass
