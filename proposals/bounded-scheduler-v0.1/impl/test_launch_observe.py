"""启动器的 Job 脱离、WMI 回退与 cmd 引号契约。"""
from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import launch_observe as launcher  # noqa: E402


def fake_process(pid: int):
    return SimpleNamespace(pid=pid, terminate=Mock(), wait=Mock(), kill=Mock())


def test_pid_storage_is_pointer_width_and_compares_full_64_bit_values():
    huge_pid = 0x1_0000_0001
    assert ctypes.sizeof(launcher._ULONG_PTR) == ctypes.sizeof(ctypes.c_void_p)
    with (
        patch.object(launcher, "current_process_in_job", return_value=True),
        patch.object(
            launcher,
            "current_job_pids",
            side_effect=[frozenset({7}), frozenset({7, huge_pid}), frozenset({7})],
        ),
        patch.object(launcher, "_popen_server", return_value=fake_process(huge_pid)),
        patch.object(launcher, "_stop_failed_breakaway") as stop,
        patch.object(launcher, "_start_via_wmi", return_value=99) as wmi,
    ):
        result = launcher.start_server(18787)
    stop.assert_called_once()
    wmi.assert_called_once()
    assert result.method == "wmi"


def test_not_in_job_uses_direct_hidden_launch_without_breakaway():
    process = fake_process(101)
    with (
        patch.object(launcher, "current_process_in_job", return_value=False),
        patch.object(launcher, "_popen_server", return_value=process) as popen,
        patch.object(launcher, "_start_via_wmi") as wmi,
    ):
        result = launcher.start_server(18787)
    flags = popen.call_args.args[2]
    assert not flags & launcher.CREATE_BREAKAWAY_FROM_JOB
    assert result == launcher.LaunchResult(101, "direct-not-in-job", frozenset())
    wmi.assert_not_called()


def test_breakaway_success_requires_child_absent_from_current_job():
    process = fake_process(202)
    with (
        patch.object(launcher, "current_process_in_job", return_value=True),
        patch.object(launcher, "current_job_pids", side_effect=[frozenset({7}), frozenset({7})]),
        patch.object(launcher, "_popen_server", return_value=process) as popen,
        patch.object(launcher, "_start_via_wmi") as wmi,
    ):
        result = launcher.start_server(18787)
    assert popen.call_args.args[2] & launcher.CREATE_BREAKAWAY_FROM_JOB
    assert result.method == "breakaway"
    wmi.assert_not_called()


def test_access_denied_breakaway_routes_to_first_class_wmi_path():
    denied = OSError("denied")
    denied.winerror = launcher.ERROR_ACCESS_DENIED
    with (
        patch.object(launcher, "current_process_in_job", return_value=True),
        patch.object(launcher, "current_job_pids", side_effect=[frozenset({7}), frozenset({7})]),
        patch.object(launcher, "_popen_server", side_effect=denied),
        patch.object(launcher, "_start_via_wmi", return_value=303) as wmi,
    ):
        result = launcher.start_server(18787)
    wmi.assert_called_once()
    assert result == launcher.LaunchResult(303, "wmi", frozenset({7}))


def test_unexpected_breakaway_error_is_not_hidden_by_wmi():
    failure = OSError("bad executable")
    failure.winerror = 2
    with (
        patch.object(launcher, "current_process_in_job", return_value=True),
        patch.object(launcher, "current_job_pids", return_value=frozenset({7})),
        patch.object(launcher, "_popen_server", side_effect=failure),
        patch.object(launcher, "_start_via_wmi") as wmi,
        pytest.raises(OSError, match="bad executable"),
    ):
        launcher.start_server(18787)
    wmi.assert_not_called()


def test_wmi_failure_is_loud():
    completed = subprocess.CompletedProcess([], 1, stdout="", stderr="provider unavailable")
    with patch.object(launcher.subprocess, "run", return_value=completed):
        with pytest.raises(RuntimeError, match="WMI 启动观察窗失败.*provider unavailable"):
            launcher._start_via_wmi(Path(r"C:\Python Dir\python.exe"), 18787)


def test_wmi_returns_observe_child_pid_not_cmd_wrapper_pid():
    completed = subprocess.CompletedProcess([], 0, stdout="505", stderr="")
    with patch.object(launcher.subprocess, "run", return_value=completed) as run:
        assert launcher._start_via_wmi(Path(r"C:\Python Dir\python.exe"), 18787) == 505
    encoded = run.call_args.args[0][-1]
    script = __import__("base64").b64decode(encoded).decode("utf-16le")
    assert "ProcessStartupInformation=$startup" in script
    assert "ShowWindow=[uint16]0" in script
    assert "ParentProcessId=" in script
    assert "*observe.py*" in script
    assert "*--port 18787*" in script


def test_wmi_pid_still_in_current_job_is_rejected():
    denied = OSError("denied")
    denied.winerror = launcher.ERROR_ACCESS_DENIED
    with (
        patch.object(launcher, "current_process_in_job", return_value=True),
        patch.object(launcher, "current_job_pids", side_effect=[frozenset({7}), frozenset({7, 404})]),
        patch.object(launcher, "_popen_server", side_effect=denied),
        patch.object(launcher, "_start_via_wmi", return_value=404),
        pytest.raises(RuntimeError, match="仍在启动回合 Job"),
    ):
        launcher.start_server(18787)


def test_cmd_slash_s_slash_c_quoting_is_hand_built():
    python = Path(r"C:\Program Files\Python\python.exe")
    command = launcher._cmd_exe_command(python, 18787)
    assert command.startswith('cmd.exe /d /s /c ""C:\\Program Files\\Python\\python.exe" ')
    assert f'"{launcher.SERVER}" --port 18787' in command
    assert command.endswith(f'>> "{launcher.LOG}" 2>&1"')
    assert "list2cmdline" not in launcher._cmd_exe_command.__code__.co_names


def test_main_preserves_port_wait_and_browser_behavior():
    with (
        patch.object(launcher, "port_up", return_value=False),
        patch.object(launcher, "start_server") as start,
        patch.object(launcher, "wait_until_up") as wait,
        patch.object(launcher, "open_dashboard") as browser,
    ):
        launcher.main()
    start.assert_called_once_with(launcher.PORT)
    wait.assert_called_once_with(launcher.PORT)
    browser.assert_called_once_with(f"http://127.0.0.1:{launcher.PORT}/")


def test_dashboard_uses_visible_chrome_via_wmi_inside_job():
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    with (
        patch.object(launcher, "_find_chrome", return_value=chrome),
        patch.object(launcher, "current_process_in_job", return_value=True),
        patch.object(launcher, "_start_chrome_via_wmi", return_value=707) as start,
        patch.object(launcher.subprocess, "Popen") as popen,
    ):
        assert launcher.open_dashboard("http://127.0.0.1:8787/") == "chrome-wmi"
    start.assert_called_once_with(chrome, "http://127.0.0.1:8787/")
    popen.assert_not_called()


def test_dashboard_uses_direct_new_window_outside_job():
    chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    with (
        patch.object(launcher, "_find_chrome", return_value=chrome),
        patch.object(launcher, "current_process_in_job", return_value=False),
        patch.object(launcher.subprocess, "Popen") as popen,
    ):
        assert launcher.open_dashboard("http://127.0.0.1:8787/") == "chrome-direct"
    assert popen.call_args.args[0] == [
        str(chrome), "--new-window", "http://127.0.0.1:8787/",
    ]
