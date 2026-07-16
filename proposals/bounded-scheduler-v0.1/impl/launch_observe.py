"""一键启动微澜观察窗：脱离启动回合的 Job 后等待服务就绪，再打开浏览器。"""
from __future__ import annotations

import base64
import ctypes
import os
import socket
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from ctypes import wintypes

PORT = 8787
SERVER = Path(__file__).resolve().parent / "observe.py"
LOG = SERVER.parent / "observe-server.log"
DASHBOARD_URL = f"http://127.0.0.1:{PORT}/"

CREATE_BREAKAWAY_FROM_JOB = 0x01000000
ERROR_ACCESS_DENIED = 5
ERROR_NOT_SUPPORTED = 50
JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3
_ULONG_PTR = ctypes.c_size_t


class _PROCESS_ID_LIST_HEADER(ctypes.Structure):
    _fields_ = [
        ("NumberOfAssignedProcesses", wintypes.DWORD),
        ("NumberOfProcessIdsInList", wintypes.DWORD),
        ("ProcessIdList", _ULONG_PTR * 1),
    ]


@dataclass(frozen=True)
class LaunchResult:
    pid: int
    method: str
    launcher_job_before: frozenset[int]


def port_up(port: int = PORT) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _kernel32():
    if os.name != "nt":
        raise RuntimeError("launch_observe.py 只支持 Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.IsProcessInJob.argtypes = (wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL))
    kernel32.IsProcessInJob.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    )
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    return kernel32


def current_process_in_job() -> bool:
    kernel32 = _kernel32()
    in_job = wintypes.BOOL()
    if not kernel32.IsProcessInJob(kernel32.GetCurrentProcess(), None, ctypes.byref(in_job)):
        raise ctypes.WinError(ctypes.get_last_error())
    return bool(in_job.value)


def current_job_pids() -> frozenset[int]:
    """Return the immediate current Job membership; NULL is the documented Job handle."""
    if not current_process_in_job():
        return frozenset()
    kernel32 = _kernel32()
    size = 4096
    while size <= 1024 * 1024:
        buffer = ctypes.create_string_buffer(size)
        returned = wintypes.DWORD()
        if kernel32.QueryInformationJobObject(
            None,
            JOB_OBJECT_BASIC_PROCESS_ID_LIST,
            buffer,
            size,
            ctypes.byref(returned),
        ):
            header = ctypes.cast(buffer, ctypes.POINTER(_PROCESS_ID_LIST_HEADER)).contents
            count = int(header.NumberOfProcessIdsInList)
            offset = _PROCESS_ID_LIST_HEADER.ProcessIdList.offset
            array_type = _ULONG_PTR * count
            values = array_type.from_buffer(buffer, offset)
            return frozenset(int(values[index]) for index in range(count))
        error = ctypes.get_last_error()
        if error != 234:  # ERROR_MORE_DATA
            raise ctypes.WinError(error)
        size *= 2
    raise RuntimeError("当前 Job PID 列表超过 1 MiB，拒绝降级成弱判据")


def _base_creation_flags() -> int:
    return subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW


def _server_argv(python: Path, port: int) -> list[str]:
    return [str(python), str(SERVER), "--port", str(port)]


def _popen_server(python: Path, port: int, flags: int):
    # http.server 每个请求都会写日志；detached 后必须给它有效的 stdout/stderr 句柄。
    with LOG.open("a", encoding="utf-8") as log:
        return subprocess.Popen(
            _server_argv(python, port),
            creationflags=flags,
            close_fds=True,
            cwd=str(SERVER.parent),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
        )


def _cmd_exe_command(python: Path, port: int) -> str:
    """Build cmd /s /c quoting explicitly; subprocess.list2cmdline is not cmd syntax."""
    values = (str(python), str(SERVER), str(LOG))
    if any('"' in value for value in values):
        raise ValueError("Windows 路径含双引号，无法安全构造 cmd /s /c")
    return (
        f'cmd.exe /d /s /c ""{python}" "{SERVER}" --port {port} '
        f'>> "{LOG}" 2>&1"'
    )


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _start_via_wmi(python: Path, port: int) -> int:
    command = _cmd_exe_command(python, port)
    script = (
        "$ErrorActionPreference='Stop';"
        "$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{"
        "ShowWindow=[uint16]0};"
        "$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{"
        f"CommandLine={_ps_single_quote(command)};"
        f"CurrentDirectory={_ps_single_quote(str(SERVER.parent))};"
        "ProcessStartupInformation=$startup};"
        "if([int]$r.ReturnValue -ne 0){throw ('Win32_Process.Create failed: '+$r.ReturnValue)};"
        "$deadline=(Get-Date).AddSeconds(10);"
        "do{"
        "$children=@(Get-CimInstance Win32_Process -Filter ('ParentProcessId='+[int]$r.ProcessId) | "
        f"Where-Object {{$_.CommandLine -like '*observe.py*' -and $_.CommandLine -like '*--port {port}*'}});"
        "if($children.Count -eq 1){break};Start-Sleep -Milliseconds 100"
        "}while((Get-Date) -lt $deadline);"
        "if($children.Count -ne 1){throw ('WMI wrapper child count: '+$children.Count)};"
        "[Console]::Out.Write([string]$children[0].ProcessId)"
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-EncodedCommand",
            encoded,
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "无错误文本").strip()
        raise RuntimeError(f"WMI 启动观察窗失败(rc={completed.returncode}): {detail}")
    try:
        return int(completed.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"WMI 未返回有效 observe.py PID: {completed.stdout!r}") from exc


def _stop_failed_breakaway(process) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def start_server(port: int = PORT) -> LaunchResult:
    python = Path(sys.executable).with_name("python.exe")
    in_job = current_process_in_job()
    before = current_job_pids() if in_job else frozenset()
    flags = _base_creation_flags()

    if not in_job:
        process = _popen_server(python, port, flags)
        return LaunchResult(process.pid, "direct-not-in-job", before)

    try:
        process = _popen_server(python, port, flags | CREATE_BREAKAWAY_FROM_JOB)
    except OSError as exc:
        if getattr(exc, "winerror", None) not in (ERROR_ACCESS_DENIED, ERROR_NOT_SUPPORTED):
            raise
    else:
        # Popen returning is not proof: ask the launcher's immediate Job after creation.
        if process.pid not in current_job_pids():
            return LaunchResult(process.pid, "breakaway", before)
        _stop_failed_breakaway(process)

    pid = _start_via_wmi(python, port)
    if pid in current_job_pids():
        raise RuntimeError(f"WMI 目标 PID {pid} 仍在启动回合 Job；拒绝把新 PID 冒充脱离证据")
    return LaunchResult(pid, "wmi", before)


def _chrome_candidates() -> list[Path]:
    roots = [
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("ProgramFiles"),
        os.environ.get("LOCALAPPDATA"),
    ]
    return [
        Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe"
        for root in roots
        if root
    ]


def _find_chrome() -> Path | None:
    return next((path for path in _chrome_candidates() if path.is_file()), None)


def _start_chrome_via_wmi(chrome: Path, url: str) -> int:
    command = subprocess.list2cmdline([str(chrome), "--new-window", url])
    script = (
        "$ErrorActionPreference='Stop';"
        "$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{"
        f"CommandLine={_ps_single_quote(command)};"
        f"CurrentDirectory={_ps_single_quote(str(chrome.parent))}}};"
        "if([int]$r.ReturnValue -ne 0){throw ('Chrome Create failed: '+$r.ReturnValue)};"
        "[Console]::Out.Write([string]$r.ProcessId)"
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    completed = subprocess.run(
        [
            "powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
            "-WindowStyle", "Hidden", "-EncodedCommand", encoded,
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "no error text").strip()
        raise RuntimeError(f"Chrome WMI launch failed (rc={completed.returncode}): {detail}")
    return int(completed.stdout.strip())


def open_dashboard(url: str = DASHBOARD_URL) -> str:
    """Open a visible Chrome window without tying it to the launcher's Job."""
    chrome = _find_chrome()
    if chrome is not None:
        if current_process_in_job():
            _start_chrome_via_wmi(chrome, url)
            return "chrome-wmi"
        subprocess.Popen(
            [str(chrome), "--new-window", url],
            creationflags=_base_creation_flags(),
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return "chrome-direct"

    startfile = getattr(os, "startfile", None)
    if startfile is not None:
        startfile(url)
        return "windows-default"
    if webbrowser.open(url):
        return "webbrowser"
    raise RuntimeError(f"No browser accepted dashboard URL: {url}")


def wait_until_up(port: int = PORT) -> None:
    for _ in range(40):
        if port_up(port):
            return
        time.sleep(0.25)
    raise RuntimeError(f"观察窗 PID 已创建，但端口 {port} 在 10 秒内未监听")


def main() -> None:
    if not port_up(PORT):
        start_server(PORT)
        wait_until_up(PORT)
    open_dashboard(DASHBOARD_URL)


if __name__ == "__main__":
    main()
