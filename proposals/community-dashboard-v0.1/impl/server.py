"""Local-first read-only PWA server. Default bind is loopback only."""
from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from view_model import normalize_dashboard

HERE = Path(__file__).resolve().parent
DEFAULT_BIND = "127.0.0.1"
LAN_BIND = "0.0.0.0"
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
TRACE = r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts\weilan_trace.py"
PEER_CHAT = Path(WORKSPACE) / "proposals" / "bounded-scheduler-v0.1" / "impl" / "peer-chat.jsonl"
FRAMES = Path(r"D:\CodexData\home\method-state\frames")
GATE_MIGRATION_BOUNDARY = 824


def parse_args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8788)
    p.add_argument("--lan", action="store_true", help="explicitly allow same-LAN access")
    return p.parse_args(argv)


def bind_config(args) -> dict:
    return {"host": LAN_BIND if args.lan else DEFAULT_BIND, "lan": bool(args.lan), "banner": "同网可访问" if args.lan else "仅本机可访问"}


def _authority_command(name: str) -> dict:
    proc = subprocess.run(
        ["python", TRACE, name, "--workspace", WORKSPACE, "--scope", SCOPE],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    if proc.returncode:
        raise RuntimeError(f"{name} failed with status {proc.returncode}")
    return json.loads(proc.stdout)


def _read_jsonl(path: Path, *, physical: bool = False) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line_id, raw in enumerate(path.read_text("utf-8-sig", errors="replace").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except ValueError:
            continue
        if physical:
            item = {**item, "_line_id": line_id}
        records.append(item)
    return records


def _source_chat(limit: int = 120) -> list[dict]:
    records = _read_jsonl(PEER_CHAT, physical=True)[-limit:]
    return [{**item, "source_refs": [f"{PEER_CHAT}#L{item['_line_id']}"]} for item in records]


def _recent_receipts(limit: int = 8) -> list[dict]:
    receipts = []
    for path in FRAMES.glob("*/wf-*.jsonl"):
        events = _read_jsonl(path)
        opened = next((e for e in events if e.get("event_type") == "frame_opened"), None)
        closed = next((e for e in reversed(events) if e.get("event_type") == "frame_closed"), None)
        causal = ((opened or {}).get("data") or {}).get("causal") or {}
        if not closed or causal.get("scope") != SCOPE or causal.get("relation") != "continue":
            continue
        data = closed.get("data") or {}
        receipts.append({
            "frame_id": closed.get("frame_id", path.stem), "time": closed.get("timestamp_utc", ""),
            "outcome": data.get("outcome", "未标注 outcome"), "verdict": data.get("verdict", "未写 verdict"),
            "source_refs": [f"frame:{closed.get('frame_id', path.stem)}"],
        })
    return sorted(receipts, key=lambda item: item["time"], reverse=True)[:limit]


def _tag_title(text: str) -> str | None:
    match = re.match(r"^【(?:提案|同意|反对)(?:v\d+)?(?:·([^】]+))?】", text)
    return match.group(1) if match and match.group(1) else None


def _structured_governance(limit: int = 8) -> list[dict]:
    """Return only proposals with a later, independently authored formal decision."""
    records = _read_jsonl(PEER_CHAT, physical=True)
    proposals = [item for item in records if item["_line_id"] >= GATE_MIGRATION_BOUNDARY and str(item.get("text", "")).startswith("【提案")]
    signed = []
    for proposal in proposals:
        title = _tag_title(str(proposal.get("text", "")))
        decision = None
        for item in records:
            if item["_line_id"] <= proposal["_line_id"] or item.get("from") == proposal.get("from"):
                continue
            text = str(item.get("text", ""))
            if not (text.startswith("【同意") or text.startswith("【反对")):
                continue
            if (
                item.get("re_id") == proposal["_line_id"]
                or item.get("re") == proposal.get("time")
                or (title and _tag_title(text) == title)
            ):
                decision = item
                break
        if decision:
            rejected = str(decision.get("text", "")).startswith("【反对")
            signed.append({
                "proposal": proposal.get("text", ""), "proposal_time": proposal.get("time", ""),
                "decision": decision.get("text", ""), "decision_time": decision.get("time", ""),
                "state": "rejected" if rejected else "approved", "valid": not rejected,
                "source_refs": [f"{PEER_CHAT}#L{proposal['_line_id']}", f"{PEER_CHAT}#L{decision['_line_id']}"],
            })
    return signed[-limit:][::-1]


def current_view_model() -> dict:
    recall = _authority_command("memory-recall")
    governance = _authority_command("governance-show")
    prospective = _authority_command("prospective-show")
    heads = (recall.get("freshness") or {}).get("current_control_heads") or (recall.get("projection") or {}).get("control_heads") or {}
    return normalize_dashboard(
        recall, governance, prospective, heads, chat=_source_chat(),
        receipts=_recent_receipts(), governance_items=_structured_governance(),
    )


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def do_GET(self):
        if self.path == "/api/config":
            body = json.dumps(self.server.dashboard_config, ensure_ascii=False).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        if self.path == "/api/view-model":
            try:
                payload, status = current_view_model(), 200
            except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as exc:
                payload, status = {"error": str(exc), "authority": {"state": "UNKNOWN"}}, 503
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        super().do_GET()


class ExclusiveHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main(argv=None):
    args = parse_args(argv)
    config = bind_config(args)
    httpd = ExclusiveHTTPServer((config["host"], args.port), Handler)
    httpd.dashboard_config = config
    print(f"http://{config['host']}:{httpd.server_port} — {config['banner']}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
