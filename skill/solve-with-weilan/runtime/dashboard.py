"""GET-only portable dashboard over an explicitly selected method-state tree."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def _discover(method_home: Path) -> list[dict]:
    root = method_home / "memory" / "projections" / "workspaces"
    rows = []
    if root.is_dir():
        for path in sorted(root.glob("*/*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            rows.append({
                "workspace_key": path.parent.name,
                "scope_key": path.stem,
                "scope": value.get("scope"),
                "focus": value.get("focus"),
                "status": value.get("status"),
            })
    return rows


def _page(repo_root: Path, method_home: Path, workspace_key: str | None, scope_key: str | None) -> bytes:
    rows = _discover(method_home)
    if workspace_key:
        rows = [row for row in rows if row["workspace_key"] == workspace_key]
    if scope_key:
        rows = [row for row in rows if row["scope_key"] == scope_key]
    items = "".join(
        f"<li><b>{html.escape(str(row['scope'] or row['scope_key']))}</b>: "
        f"{html.escape(str(row['status'] or 'unknown'))} — {html.escape(str(row['focus'] or ''))}</li>"
        for row in rows
    ) or "<li>No projections discovered.</li>"
    return (
        "<!doctype html><meta charset=utf-8><title>WeiLan dashboard</title>"
        "<h1>WeiLan dashboard</h1>"
        f"<p>Repository: {html.escape(str(repo_root))}</p><ul>{items}</ul>"
    ).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    payload = b""

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def _reject(self) -> None:
        self.send_response(405)
        self.send_header("Allow", "GET")
        self.end_headers()

    do_POST = do_PUT = do_PATCH = do_DELETE = _reject

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=os.environ.get("WEILAN_REPO_ROOT"))
    parser.add_argument("--method-home", type=Path, default=os.environ.get("WEILAN_METHOD_HOME"))
    parser.add_argument("--workspace-key")
    parser.add_argument("--scope-key")
    parser.add_argument("--port", type=int, default=int(os.environ.get("WEILAN_DASHBOARD_PORT", "8765")))
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--acknowledge-network-exposure", action="store_true")
    parser.add_argument("--pidfile", type=Path, required=True)
    parser.add_argument("--cmdline-sha256", required=True)
    args = parser.parse_args(argv)
    if args.repo_root is None or args.method_home is None:
        parser.error("--repo-root and --method-home are required when environment overrides are absent")
    if args.bind not in {"127.0.0.1", "::1", "localhost"} and not args.acknowledge_network_exposure:
        parser.error("non-loopback --bind requires --acknowledge-network-exposure")
    rows = _discover(args.method_home)
    pairs = {(row["workspace_key"], row["scope_key"]) for row in rows}
    if len(pairs) > 1 and not (args.workspace_key and args.scope_key):
        parser.error("method home is ambiguous; pass --workspace-key and --scope-key")
    Handler.payload = _page(args.repo_root.resolve(), args.method_home.resolve(), args.workspace_key, args.scope_key)
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    actual_port = server.server_address[1]
    args.pidfile.parent.mkdir(parents=True, exist_ok=True)
    args.pidfile.write_text(json.dumps({
        "pid": os.getpid(),
        "port": actual_port,
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cmdline_sha256": args.cmdline_sha256,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

