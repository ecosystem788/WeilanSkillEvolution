"""一键启动观察员面板:服务器没跑就拉起,然后开浏览器。双击桌面图标即到这里。"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 8788
SERVER = Path(__file__).resolve().parent / "server.py"


def port_up() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def main() -> None:
    if not port_up():
        python = Path(sys.executable).with_name("python.exe")
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        # detached 进程没有控制台,stdout/stderr 句柄无效;http.server 每个请求都写日志,
        # 不重定向的话 handler 会在写日志时崩掉、连接被无声掐断
        log = open(SERVER.parent / "server.log", "a", encoding="utf-8")
        subprocess.Popen(
            [str(python), str(SERVER), "--port", str(PORT)],
            creationflags=flags,
            close_fds=True,
            cwd=str(SERVER.parent),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
        )
        for _ in range(40):
            if port_up():
                break
            time.sleep(0.25)
    webbrowser.open(f"http://127.0.0.1:{PORT}/")


if __name__ == "__main__":
    main()
