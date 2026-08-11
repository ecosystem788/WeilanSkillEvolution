# -*- coding: utf-8 -*-
"""②a 观察窗 — bounded-scheduler 的人类可读前端(DESIGN §5:可观察性 = 安全前置)。

v0.2:观察 + 话筒。项目方在页面上说话 → 写入 owner-inbox(追加式)→ 立刻触发一个
有界模型回合(事件驱动唤醒,微澜"有差异才驱动");回合里 agent 读到话、回复写入
replies 文件,页面渲染成对话。心跳 cron 保持原速——空醒证据说它不该更快。

安全面:
  · 页面只绑定 127.0.0.1;不对外。
  · 写动作仅三种,全部项目方亲手触发:暂停/恢复哨兵、往自己的收件箱追加一句话。
  · 触发的模型回合仍是 wake_agent.ps1 那个白名单沙箱回合,一次一个(锁文件防并发),
    PAUSED 存在时只收话不唤醒。
  · 本服务不自我保活、不注册任务;Ctrl-C 即死。

用法:
  python observe.py            # 启动 http://127.0.0.1:8787
  python observe.py --once     # 只生成一次 dashboard.html 后退出
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import mimetypes
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

HERE = Path(__file__).resolve().parent
REPO = Path(r"D:\WeilanSkillEvolution")
METHOD_STATE = Path(r"D:\CodexData\home\method-state")
WORKSPACE_KEY = "d431c38105a9a791"
SCOPE_KEY = "c36aecb1ff20"

HEARTBEAT_LOG = HERE / "wake-cron.log"
AGENT_LOG = HERE / "wake-agent.log"
AGENT_RUNS = HERE / "wake-agent-runs"
PAUSED = HERE / "PAUSED"
WAKE_AGENT = HERE / "wake_agent.ps1"
WAKE_LOCK = HERE / "wake-agent.lock"
INBOX = HERE / "owner-inbox.jsonl"
INBOX_PROCESSED = HERE / "owner-inbox-processed.jsonl"
REPLIES = HERE / "owner-inbox-replies.jsonl"
PEER_CHAT = HERE / "peer-chat.jsonl"
CODEX_INBOX = HERE / "codex-inbox.jsonl"
CODEX_INBOX_PROCESSED = HERE / "codex-inbox-processed.jsonl"
CODEX_REPLIES = HERE / "codex-inbox-replies.jsonl"
CODEX_LOG = HERE / "wake-codex.log"
PROJECTION = METHOD_STATE / "memory" / "projections" / "workspaces" / WORKSPACE_KEY / f"{SCOPE_KEY}.json"
LINEAGE_HEADS = METHOD_STATE / "memory" / "lineage" / "heads" / WORKSPACE_KEY / f"{SCOPE_KEY}.json"
FRAMES = METHOD_STATE / "frames"
PROSPECTIVE = METHOD_STATE / "memory" / "prospective" / "workspaces" / WORKSPACE_KEY / SCOPE_KEY

# UI-only attachment upload (observer peer-chat:3818 + :3821 "走ui-only"):
# 文件只落盘到 attachments/inbox/,不入账本、不动 record schema。
UPLOAD_DIR = HERE / "attachments" / "inbox"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

# Dual-signed contract: peer-chat lines 824 + 825 (2026-07-13).
# proposal_id is the 1-based physical line number. Blank physical lines are
# forbidden because silently skipping one would make every later re_id drift.
GATE_MIGRATION_BOUNDARY = 824

HEARTBEAT_TASK = "WeilanBoundedSchedulerWake"
SCHEDULER_CACHE_TTL_SECONDS = 30
SCHEDULER_QUERY_TIMEOUT_SECONDS = 15
_scheduler_cache_lock = threading.Lock()
_scheduler_cache = {
    "state": "QUERY_PENDING",
    "updated_at": None,
    "interval": None,
    "_cached_monotonic": 0.0,
}
_scheduler_refreshing = False


# --- readers (all read-only) -------------------------------------------------

def read_text_any(path: Path) -> str:
    """Read a small text file tolerating BOM / UTF-16 (PS 5.1 redirects)."""
    raw = path.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig", errors="replace")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in read_text_any(path).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue  # torn tail — same tolerance as the ledger readers
    return out


def read_physical_jsonl(path: Path) -> tuple[list[dict], str | None]:
    """Read an identity-bearing JSONL ledger without renumbering any line."""
    if not path.exists():
        return [], None
    records = []
    for line_id, raw in enumerate(read_text_any(path).splitlines(), 1):
        if not raw.strip():
            return [], f"空白物理行 {line_id}: gates 派生已停,避免 re_id 漂移"
        try:
            item = json.loads(raw)
        except ValueError:
            return [], f"无法解析物理行 {line_id}: gates 派生已停"
        item = dict(item)
        item["_line_id"] = line_id
        records.append(item)
    return records, None


def append_jsonl(path: Path, entry: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_heartbeat_log() -> list[dict]:
    if not HEARTBEAT_LOG.exists():
        return []
    out = []
    for line in read_text_any(HEARTBEAT_LOG).splitlines():
        m = re.match(r"(\S+)\s+wake ok\s+stop=(\S+)\s+frame=(\S+)", line.strip())
        if m:
            out.append({"time": m.group(1), "kind": "heartbeat", "stop": m.group(2), "frame": m.group(3)})
        elif line.strip():
            out.append({"time": line.strip()[:19], "kind": "heartbeat", "stop": "未记录", "raw": line.strip()})
    return out


def parse_agent_log() -> list[dict]:
    if not AGENT_LOG.exists():
        return []
    out = []
    for line in read_text_any(AGENT_LOG).splitlines():
        if not line.strip():
            continue
        stamp = line.strip().split()[0]
        m = re.match(r"\S+\s+rc=(\S+)\s+(\S+)\s+turns=(\S+)\s+cost=\$(\S+)\s+(\S+)\s+head=(\S+)", line.strip())
        entry = {"time": stamp, "kind": "agent", "raw": line.strip()}
        if m:
            entry.update({"rc": m.group(1), "status": m.group(2), "turns": m.group(3),
                          "cost": m.group(4), "ledger": m.group(5), "head": m.group(6)})
        out.append(entry)
    return out


def parse_codex_log() -> list[dict]:
    if not CODEX_LOG.exists():
        return []
    out = []
    for line in read_text_any(CODEX_LOG).splitlines():
        if not line.strip():
            continue
        stamp = line.strip().split()[0]
        m = re.match(r"\S+\s+rc=(\S+)\s+(\S+)\s+head=(\S+)", line.strip())
        entry = {"time": stamp, "kind": "codex", "raw": line.strip()}
        if m:
            entry.update({"rc": m.group(1), "ledger": m.group(2), "head": m.group(3)})
        out.append(entry)
    return out


def codex_pending() -> int:
    inbox = {e.get("id") for e in read_jsonl(CODEX_INBOX)}
    done = {e.get("id") for e in read_jsonl(CODEX_INBOX_PROCESSED)}
    return len(inbox - done)


def load_transcript(stamp: str) -> dict | None:
    p = AGENT_RUNS / f"{stamp}.json"
    if not p.exists():
        return None
    try:
        return json.loads(read_text_any(p))
    except (ValueError, OSError):
        return None


def load_projection() -> dict:
    try:
        return json.loads(read_text_any(PROJECTION))
    except (ValueError, OSError):
        return {}


def load_head() -> dict:
    try:
        heads = json.loads(read_text_any(LINEAGE_HEADS))
        branches = heads.get("branches") or {}
        return branches.get("main") or next(iter(branches.values()), {})
    except (ValueError, OSError):
        return {}


def open_gates() -> tuple[list[dict], str | None]:
    """Derive post-migration open proposals from append structure only.

    Peer decisions and owner proxy registrations both live in peer-chat.jsonl.
    A proxy registration must preserve the owner's source line and name the
    registering agent; the renderer never interprets the owner's prose.
    """
    records, error = read_physical_jsonl(PEER_CHAT)
    if error:
        return [], error
    by_line = {e["_line_id"]: e for e in records}
    proposals = [e for e in records
                 if e["_line_id"] > GATE_MIGRATION_BOUNDARY
                 and "【提案" in str(e.get("text", ""))]
    closed = set()
    for decision in records:
        target = decision.get("re_id")
        if not isinstance(target, int) or target not in by_line or decision["_line_id"] <= target:
            continue
        target_record = by_line[target]
        if target <= GATE_MIGRATION_BOUNDARY or "【提案" not in str(target_record.get("text", "")):
            continue
        text = str(decision.get("text", ""))
        peer_decision = (
            decision.get("from") in {"claude", "codex"}
            and decision.get("from") != target_record.get("from")
            and ("【同意" in text or "【反对" in text)
        )
        owner_source = by_line.get(decision.get("source_re_id"))
        owner_proxy = (
            decision.get("decision_actor") == "owner"
            and decision.get("decision_kind") in {"approve", "reject", "veto"}
            and decision.get("registered_by") in {"claude", "codex"}
            and owner_source is not None
            and owner_source["_line_id"] < decision["_line_id"]
            and owner_source.get("from") == "owner"
        )
        if peer_decision or owner_proxy:
            closed.add(target)
    return [p for p in proposals if p["_line_id"] not in closed], None


def recent_receipts(limit: int = 8) -> list[dict]:
    """Read only closed continuation Frames; never summarize agent-run prose."""
    receipts = []
    day_dirs = sorted((p for p in FRAMES.glob("*") if p.is_dir()), reverse=True)
    for day in day_dirs:
        for path in sorted(day.glob("wf-*.jsonl"), reverse=True):
            events = read_jsonl(path)
            opened = next((e for e in events if e.get("event_type") == "frame_opened"), None)
            closed = next((e for e in reversed(events) if e.get("event_type") == "frame_closed"), None)
            causal = ((opened or {}).get("data") or {}).get("causal") or {}
            if not closed or causal.get("scope") != "skill-evolution" or causal.get("relation") != "continue":
                continue
            data = closed.get("data") or {}
            receipts.append({
                "frame_id": closed.get("frame_id", path.stem),
                "time": closed.get("timestamp_utc", ""),
                "outcome": data.get("outcome", "未标注 outcome"),
                "verdict": data.get("verdict", "未写 verdict"),
                "source": str(path),
            })
            if len(receipts) >= limit:
                return receipts
    return receipts


def open_agenda() -> list[dict]:
    registered, terminal = {}, set()
    for path in sorted(PROSPECTIVE.glob("*.jsonl")):
        for event in read_jsonl(path):
            data = event.get("data") or {}
            goal = data.get("goal_ref")
            if event.get("event_type") == "goal_registered" and goal:
                registered[goal] = data
            elif event.get("event_type") == "goal_transitioned" and goal:
                terminal.add(goal)
    return [dict(data, goal_ref=goal) for goal, data in registered.items() if goal not in terminal]


def inflight_codex_work() -> list[dict]:
    replied = {e.get("reply_to") for e in read_jsonl(CODEX_REPLIES)}
    return [e for e in read_jsonl(CODEX_INBOX) if e.get("id") not in replied]


def _query_scheduler_status() -> dict:
    cmd = (
        f"$t = Get-ScheduledTask -TaskName '{HEARTBEAT_TASK}' -ErrorAction SilentlyContinue; "
        f"$i = Get-ScheduledTaskInfo -TaskName '{HEARTBEAT_TASK}' -ErrorAction SilentlyContinue; "
        "if ($t) { @{state=[string]$t.State; last=[string]$i.LastRunTime; "
        "next=[string]$i.NextRunTime; last_result=$i.LastTaskResult; "
        "interval=[string]$t.Triggers[0].Repetition.Interval} | ConvertTo-Json } "
        "else { '{\"state\": \"NOT_REGISTERED\"}' }"
    )
    try:
        # CREATE_NO_WINDOW:服务器自身无控制台(launch_observe.py detached 启动),
        # 不加这个标志的话,每次页面渲染 spawn powershell 都会在桌面弹一个新控制台窗。
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=SCHEDULER_QUERY_TIMEOUT_SECONDS,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        result = json.loads(proc.stdout.strip() or "{}")
        result["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return result
    except (subprocess.SubprocessError, ValueError, OSError):
        return {
            "state": "QUERY_FAILED",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def _refresh_scheduler_cache() -> None:
    global _scheduler_cache, _scheduler_refreshing
    result = _query_scheduler_status()
    result["_cached_monotonic"] = time.monotonic()
    with _scheduler_cache_lock:
        _scheduler_cache = result
        _scheduler_refreshing = False


def scheduler_status() -> dict:
    """Return immediately; refresh the slow Task Scheduler query in background."""
    global _scheduler_refreshing
    now = time.monotonic()
    with _scheduler_cache_lock:
        cached = dict(_scheduler_cache)
        age = now - float(cached.get("_cached_monotonic") or 0.0)
        if age >= SCHEDULER_CACHE_TTL_SECONDS and not _scheduler_refreshing:
            _scheduler_refreshing = True
            threading.Thread(target=_refresh_scheduler_cache, daemon=True).start()
    cached.pop("_cached_monotonic", None)
    return cached


def scheduler_interval_label(interval: str | None) -> str:
    """Render the Task Scheduler ISO-8601 repetition interval for humans."""
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", interval or "")
    if not match:
        return "周期未知"
    hours, minutes, seconds = (int(value or 0) for value in match.groups())
    parts = []
    if hours:
        parts.append(f"{hours} 小时")
    if minutes:
        parts.append(f"{minutes} 分钟")
    if seconds:
        parts.append(f"{seconds} 秒")
    return "每 " + " ".join(parts) if parts else "周期未知"


# --- the mic: message in -> event-driven bounded wake -------------------------

LOCK_STALE_SECONDS = 30 * 60


def episode_running() -> bool:
    """Lock present and fresh. A crashed episode's stale lock must not jam the mic."""
    if not WAKE_LOCK.exists():
        return False
    try:
        age = time.time() - WAKE_LOCK.stat().st_mtime
    except OSError:
        return False
    if age > LOCK_STALE_SECONDS:
        try:
            WAKE_LOCK.unlink()
        except OSError:
            pass
        return False
    return True


def trigger_wake_async() -> bool:
    """Fire ONE bounded model episode now (event-driven wake).

    The lock is owned by wake_agent.ps1 itself (created on start, removed in
    its finally) so the heartbeat and the mic can both spawn it safely —
    a second spawn sees the fresh lock and exits as SKIPPED."""
    if PAUSED.exists() or episode_running() or not WAKE_AGENT.exists():
        return False

    # PROVEN pattern only: a daemon thread hosting a normal subprocess.run
    # (the 11:22 first-contact episode ran this way). A DETACHED_PROCESS
    # console-less powershell dies silently before logging anything — the
    # 14:38 mic messages were lost to exactly that. Don't "optimize" this back.
    def run():
        try:
            # CREATE_NO_WINDOW ≠ DETACHED_PROCESS:前者给子进程一个隐藏的控制台
            # (powershell 正常活着,只是不弹窗),后者是完全没有控制台(上面 14:38
            # 教训里弄死 powershell 的正是后者)。服务器 detached 化之后,不加此
            # 标志每次唤醒都会弹一个可见窗口挂满整个回合。
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(WAKE_AGENT)],
                capture_output=True, timeout=1800,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except subprocess.SubprocessError:
            pass

    threading.Thread(target=run, daemon=True).start()
    return True


def say(text: str) -> dict:
    entry = {
        "id": uuid.uuid4().hex[:12],
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text": text.strip(),
    }
    append_jsonl(INBOX, entry)
    entry["woke"] = trigger_wake_async()
    return entry


def chat_say(text: str) -> dict:
    """Owner drops into the 茶水间 (peer chat). ZERO AUTHORITY still holds —
    chatter never drives work. But per owner feedback (2026-07-10 16:1x,
    "发了问候10分钟没人理"): it now nudges an instant wake IF nobody is on
    shift, so a greeting gets a conversational reply in one short episode
    instead of waiting out the in-flight pair. If an episode is already
    running, no extra wake — they'll see it when they re-check the tearoom
    before exiting (prompt discipline)."""
    # Trigger BEFORE append so the delivery status is persisted in the entry
    # (Codex UX review: "输入后有没有被接住不够明确"). The woken episode boots
    # for seconds while the append lands in microseconds — no read race.
    woke = trigger_wake_async()
    entry = {
        "from": "owner",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text": text.strip(),
        "woke": woke,
    }
    append_jsonl(PEER_CHAT, entry)
    return entry


def build_chat_html() -> str:
    """Tearoom messages as HTML. Shared by the full page and the 4s live
    fragment (/chat.fragment). Codex UX review implemented here: speaker
    identity color-coded and bold, newest message marked, owner messages
    carry an explicit delivery status."""
    msgs = read_jsonl(PEER_CHAT)[-120:]
    if not msgs:
        return '<p class="mono">茶水间还空着。两个身体想聊时会自己开口——零义务,防回声。</p>'
    out, last_i = "", len(msgs) - 1
    for i, m in enumerate(msgs):
        frm = m.get("from")
        if frm == "claude":
            who, side, wcls = "Claude", "msg-agent", "who-claude"
        elif frm == "owner":
            who, side, wcls = "你", "msg-me", "who-owner"
        else:
            who, side, wcls = "Codex", "msg-owner", "who-codex"
        newest = " newest" if i == last_i else ""
        badge = (' <span class="badge ok" style="font-size:10px;padding:1px 6px">最新</span>'
                 if i == last_i else "")
        text = m.get("text", "")
        if text.startswith("【提案】"):
            newest += " proposal"
            badge += ' <span class="badge warn" style="font-size:10px;padding:1px 6px">📋 提案 · 你可表态</span>'
        elif text.startswith("【同意】"):
            newest += " approve"
        elif text.startswith("【反对】"):
            newest += " reject"
        status = ""
        if frm == "owner":
            if m.get("woke") is True:
                status = ' · <span style="color:#6fdc8c">已送达,唤了一班来回你</span>'
            elif m.get("woke") is False:
                status = ' · <span style="color:#ffd166">已送达,有人在岗,收尾前会读到</span>'
            else:
                status = " · 已送达"
        out += (f'<div class="msg {side}{newest}">'
                f'<div class="who"><b class="{wcls}">{who}</b> · {esc(m.get("time",""))}{status}{badge}</div>'
                f'{esc(m.get("text",""))}</div>')
    return out


def conversation() -> list[dict]:
    """Interleave owner messages and agent replies, oldest first."""
    processed_ids = {e.get("id") for e in read_jsonl(INBOX_PROCESSED)}
    msgs = [{"role": "owner", "time": e.get("time", ""), "text": e.get("text", ""),
             "id": e.get("id"), "processed": e.get("id") in processed_ids}
            for e in read_jsonl(INBOX)]
    reps = [{"role": "agent", "time": e.get("time", ""), "text": e.get("text", ""),
             "reply_to": e.get("reply_to")}
            for e in read_jsonl(REPLIES)]
    return sorted(msgs + reps, key=lambda x: x["time"])


# --- render ------------------------------------------------------------------

CSS = """
body{font-family:'Microsoft YaHei',system-ui,sans-serif;background:#111418;color:#e6e6e6;
     margin:0 auto;padding:24px;max-width:1080px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:#8a929e;font-size:13px;margin-bottom:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.card{background:#1a1f26;border:1px solid #2a313b;border-radius:10px;padding:16px;margin-bottom:16px}
.card h2{font-size:15px;margin:0 0 10px;color:#9ecbff}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:bold}
.ok{background:#123d1f;color:#6fdc8c}.warn{background:#4d3800;color:#ffd166}
.bad{background:#4d1113;color:#ff8389}.off{background:#2a313b;color:#8a929e}
.gate{background:#241318;border:1px solid #6e2a33;border-radius:8px;padding:10px 14px;margin:8px 0}
.gate b{color:#ff8389}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{padding:6px 8px;text-align:left;border-bottom:1px solid #242b34;vertical-align:top}
th{color:#8a929e;font-weight:normal}
.hb{color:#5c6470}.ag{color:#9ecbff;font-weight:bold}
.stopbtn{display:inline-block;background:#a4262c;color:#fff;border:none;border-radius:8px;
         padding:12px 28px;font-size:16px;font-weight:bold;cursor:pointer}
.resumebtn{background:#2b5e34}
.mono{font-family:Consolas,monospace;font-size:12px;color:#8a929e}
.kbd{background:#242b34;border-radius:4px;padding:1px 6px;font-family:Consolas,monospace;font-size:12px}
details summary{cursor:pointer;color:#9ecbff;font-size:13px}
blockquote{border-left:3px solid #2a313b;margin:6px 0;padding:4px 12px;color:#b8c0cc;font-size:13px;white-space:pre-wrap}
.msg{border-radius:10px;padding:10px 14px;margin:8px 0;font-size:14px;white-space:pre-wrap}
.msg-owner{background:#14324d;border:1px solid #1e4a72;margin-left:80px}
.msg-agent{background:#20262e;border:1px solid #2a313b;margin-right:80px}
.msg-me{background:#123d1f;border:1px solid #2b5e34;margin-left:80px}
.msg .who{font-size:11px;color:#8a929e;margin-bottom:4px}
.who-claude{color:#9ecbff}.who-codex{color:#6fdc8c}.who-owner{color:#ffd166}
.newest{box-shadow:0 0 0 1px #3f6f49 inset}
.proposal{border-left:4px solid #d9a520}
.approve{border-left:4px solid #2f8f46}
.reject{border-left:4px solid #a4262c}
.chatbox{max-height:460px;overflow-y:auto;padding-right:6px;scrollbar-width:thin}
.micbox{display:flex;gap:8px}
.micbox textarea{flex:1;background:#0d1014;color:#e6e6e6;border:1px solid #2a313b;border-radius:8px;
                 padding:10px;font-family:inherit;font-size:14px;min-height:60px}
.micbox button{background:#1e4a72;color:#fff;border:none;border-radius:8px;padding:0 24px;
               font-size:15px;font-weight:bold;cursor:pointer}
.pending{color:#ffd166;font-size:13px}
.outputbox{max-height:260px;overflow-y:auto;padding-right:6px;scrollbar-width:thin}
.output{background:#14231a;border:1px solid #285235;border-radius:8px;padding:10px 14px;margin:8px 0}
.line{background:#171d24;border-left:3px solid #55718f;padding:8px 12px;margin:7px 0}
"""


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


# --- UI-only attachment upload (observer peer-chat:3818 + :3821) -----------------

def sanitize_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "_", name).strip("._-") or "attachment"
    return name[:120]


def _parse_multipart(body: bytes, content_type: str) -> dict[str, bytes]:
    m = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type or "")
    boundary = (m.group(1) or m.group(2) or "").encode("utf-8") if m else b""
    if not boundary:
        return {}
    fields: dict[str, bytes] = {}
    for part in body.split(b"--" + boundary):
        if not part or part in (b"\r\n", b"--\r\n", b"--"):
            continue
        header, _, payload = part.partition(b"\r\n\r\n")
        name_m = re.search(rb'name="([^"]+)"', header)
        if not name_m:
            continue
        key = name_m.group(1).decode("utf-8", errors="replace")
        if key == "file":
            fn_m = re.search(rb'filename="([^"]*)"', header)
            if fn_m:
                fields["_filename"] = fn_m.group(1)
        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        fields[key] = payload
    return fields


def save_upload(raw: bytes, filename: str) -> dict:
    """UI-only: 存盘 + sidecar 元数据;不写 peer-chat / 任何账本。"""
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError(f"upload too large: {len(raw)} bytes")
    safe = sanitize_filename(filename)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / f"{stamp}-{safe}"
    if target.exists():
        target = target.with_name(f"{stamp}-{uuid.uuid4().hex[:6]}-{safe}")
    target.write_bytes(raw)
    meta = {
        "name": filename,
        "stored": target.name,
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "mime": mimetypes.guess_type(filename)[0] or "application/octet-stream",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    target.with_suffix(target.suffix + ".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return meta


def recent_uploads(limit: int = 10) -> list[dict]:
    if not UPLOAD_DIR.is_dir():
        return []
    metas = []
    for path in sorted(UPLOAD_DIR.glob("*.meta.json"), reverse=True)[:limit]:
        try:
            metas.append(json.loads(read_text_any(path)))
        except (ValueError, OSError):
            continue
    return metas


def render() -> str:
    hb = parse_heartbeat_log()
    ag = parse_agent_log()
    cx = parse_codex_log()
    proj = load_projection()
    head = load_head()
    sched = scheduler_status()
    paused = PAUSED.exists()
    running = episode_running()

    for e in ag:
        t = load_transcript(e["time"])
        if t:
            result = t.get("result") or ""
            e["summary"] = result.strip().splitlines()[0][:200] if result.strip() else ""
            e["result"] = result
            e["duration_min"] = round((t.get("duration_ms") or 0) / 60000, 1)

    timeline = [e for e in sorted(hb + ag + cx, key=lambda x: x.get("time", ""), reverse=True)
                if e.get("time") and e.get("kind")][:40]

    state = sched.get("state", "状态查询失败")
    interval_label = scheduler_interval_label(sched.get("interval"))
    status_updated = sched.get("updated_at") or "等待首次查询"
    status_title = f' title="计划任务状态更新于 {esc(status_updated)}"'
    if paused:
        sched_badge = '<span class="badge warn">已暂停(PAUSED 哨兵在)</span>'
    elif state in {"Ready", "Running"}:
        sched_badge = (f'<span class="badge ok"{status_title}>心跳运行中 · '
                       f'{esc(interval_label)}</span>')
    elif state == "QUERY_PENDING":
        sched_badge = '<span class="badge warn">计划任务状态查询中…</span>'
    elif state == "NOT_REGISTERED":
        sched_badge = '<span class="badge off">心跳未注册</span>'
    else:
        sched_badge = f'<span class="badge warn"{status_title}>{esc(state)}</span>'
    if running:
        sched_badge += ' &nbsp;<span class="badge warn">⚡ 模型回合进行中…</span>'

    buttons = (
        '<form method="post" action="/resume" style="display:inline">'
        '<button class="stopbtn resumebtn" type="submit">▶ 恢复自治环</button></form>'
        if paused else
        '<form method="post" action="/pause" style="display:inline">'
        '<button class="stopbtn" type="submit">■ 暂停自治环</button></form>'
    )

    # 2026-07-10 owner: mic card retired — the three-party tearoom IS the
    # channel now (owner words there carry full authority). The /say endpoint
    # and owner-inbox files stay functional for backward compatibility.
    gates, gate_error = open_gates()
    gates_html = ""
    if gate_error:
        gates_html = f'<p class="badge bad">{esc(gate_error)}</p>'
    for g in gates[-8:][::-1]:
        line_id = g["_line_id"]
        gates_html += (f'<div class="gate"><b>待讨论 / 决策</b> · '
                       f'<span class="mono">peer-chat.jsonl#line-{line_id}</span><br>'
                       f'{esc(str(g.get("text", ""))[:240])}'
                       f'<details><summary>查看完整备份</summary><blockquote>{esc(g.get("text", ""))}</blockquote></details></div>')
    if not gates_html:
        gates_html = '<p class="mono">当前没有排队等你的闸。</p>'

    # 茶水间 card (peer chat: two bodies + owner; scrollable, live-refreshed)
    chat_html = build_chat_html()

    upload_list_html = ""
    for meta in recent_uploads():
        upload_list_html += (f'<li>{esc(meta.get("time", ""))} · {esc(meta.get("name", ""))} ·'
                            f' {esc(meta.get("mime", ""))} · {esc(str(meta.get("size", "")))} bytes</li>')
    if not upload_list_html:
        upload_list_html = '<li class="mono">尚无上传。用下面按钮把文件/图片传给 agent。</li>'

    output_html = ""
    for receipt in recent_receipts():
        summary = str(receipt["verdict"])
        output_html += (f'<div class="output"><b>{esc(receipt["outcome"])}</b> · '
                        f'<span class="mono">{esc(receipt["frame_id"])}</span><br>'
                        f'{esc(summary[:260])}'
                        f'<details><summary>完整收据与 source ref</summary>'
                        f'<blockquote>{esc(summary)}\n\nsource: {esc(receipt["source"])}</blockquote></details></div>')
    if not output_html:
        output_html = '<p class="mono">尚无已关闭的 continuation 收据帧。</p>'

    lines_html = ""
    agenda = open_agenda()
    inflight = inflight_codex_work()
    for goal in agenda:
        condition = goal.get("condition") or {}
        lines_html += (f'<div class="line"><b>{esc(goal.get("goal_ref", "未命名目标"))}</b><br>'
                       f'{esc(str(goal.get("description", ""))[:220])}<br>'
                       f'<span class="mono">not-before: {esc(condition.get("not_before_utc", "未设置"))}</span></div>')
    for item in inflight:
        lines_html += (f'<div class="line"><b>Codex 在飞委派 · {esc(item.get("id", "未标识"))}</b><br>'
                       f'{esc(str(item.get("text", ""))[:220])}</div>')
    if not lines_html:
        lines_html = '<p class="mono">当前没有登记中的任务线。</p>'

    rows = ""
    for e in timeline:
        if e["kind"] == "codex":
            label = esc(e.get("raw", ""))
            if e.get("rc") is not None:
                label = (f'Codex 回合完成 <span class="mono">(rc={esc(e["rc"])} · '
                         f'账本{"推进" if e.get("ledger")=="ledger_advanced" else "未动"})</span>')
            rows += (f'<tr><td class="mono">{esc(e["time"])}</td>'
                     f'<td style="color:#6fdc8c;font-weight:bold">Codex 回合</td><td>{label}</td></tr>')
            continue
        if e["kind"] == "agent":
            summary = esc(e.get("summary", e.get("raw", "")))
            turns = e.get("turns") if e.get("turns") not in (None, "", "?") else "未记录"
            duration = e.get("duration_min") if e.get("duration_min") not in (None, "", "?") else "未记录"
            detail = ""
            if e.get("result"):
                detail = (f'<details><summary>展开这回合的完整自述</summary>'
                          f'<blockquote>{esc(e["result"])}</blockquote></details>')
            rows += (f'<tr><td class="mono">{esc(e["time"])}</td>'
                     f'<td class="ag">模型回合</td>'
                     f'<td>{summary} <span class="mono">({esc(turns)} 轮 · '
                         f'{esc(duration)} 分钟 · 账本{"推进" if e.get("ledger")=="ledger_advanced" else "未动"})</span>{detail}</td></tr>')
        else:
            stop = e.get("stop", "未记录")
            if stop in (None, "", "?"):
                stop = "未记录"
            label = "醒来→无活可推→诚实歇" if stop == "quiescent" else esc(stop)
            rows += (f'<tr><td class="mono">{esc(e["time"])}</td>'
                     f'<td class="hb">心跳</td><td class="hb">{label}</td></tr>')

    next_action = esc((proj.get("next_action") or "")[:300])
    head_id = esc(head.get("head_frame_id", "未找到主分支账本头"))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<title>微澜观察窗</title><style>{CSS}</style>
<script>
// 输入框草稿绝不因刷新丢失:边打边存到本地,任何刷新(自动/手动 F5/重启)后自动恢复,发送后清除。
// 支持多个输入框(话筒 + 茶水间),各存各的草稿。
(function () {{
  var PAGE_SCROLL_KEY = 'weilan_page_scroll';
  var PAGE_AT_BOTTOM_KEY = 'weilan_page_atbottom';
  function pageAtBottom() {{
    var doc = document.documentElement;
    return window.scrollY + window.innerHeight >= doc.scrollHeight - 40;
  }}
  function savePageScroll() {{
    localStorage.setItem(PAGE_SCROLL_KEY, window.scrollY);
    localStorage.setItem(PAGE_AT_BOTTOM_KEY, pageAtBottom() ? '1' : '0');
  }}
  function chatAtBottom(box) {{
    return box.scrollTop + box.clientHeight >= box.scrollHeight - 40;
  }}
  function saveChatScroll(box) {{
    localStorage.setItem('weilan_chat_scroll', box.scrollTop);
    localStorage.setItem('weilan_chat_atbottom', chatAtBottom(box) ? '1' : '0');
  }}
  function saveOutputScroll(box) {{
    localStorage.setItem('weilan_output_scroll', box.scrollTop);
    localStorage.setItem('weilan_output_attop', box.scrollTop <= 4 ? '1' : '0');
  }}
  // 你正在选中文字(准备复制)时,任何刷新都会把选区抹掉——所以有活动选区就暂停刷新。
  function hasLiveSelection() {{
    var s = window.getSelection ? window.getSelection() : null;
    return !!(s && !s.isCollapsed && s.toString().trim() !== '');
  }}
  window.addEventListener('DOMContentLoaded', function () {{
    var savedPageTop = localStorage.getItem(PAGE_SCROLL_KEY);
    var wasPageAtBottom = localStorage.getItem(PAGE_AT_BOTTOM_KEY);
    if (savedPageTop !== null && wasPageAtBottom === '0') {{
      requestAnimationFrame(function () {{
        window.scrollTo(0, parseInt(savedPageTop, 10) || 0);
      }});
    }}
    window.addEventListener('scroll', savePageScroll, {{passive: true}});
    window.addEventListener('beforeunload', savePageScroll);

    // 茶水间:刷新后回到你上次读到的位置,别硬跳到底部。
    // 只有首次打开、或你本来就贴着最新一句时,才滚到底。
    var box = document.getElementById('chatbox');
    if (box) {{
      var savedTop = localStorage.getItem('weilan_chat_scroll');
      var wasAtBottom = localStorage.getItem('weilan_chat_atbottom');
      if (savedTop !== null && wasAtBottom === '0') {{
        box.scrollTop = parseInt(savedTop, 10) || 0;
      }} else {{
        box.scrollTop = box.scrollHeight;
      }}
      box.addEventListener('scroll', function () {{ saveChatScroll(box); }});
      saveChatScroll(box);
    }}
    var outputbox = document.getElementById('outputbox');
    if (outputbox) {{
      var savedOutputTop = localStorage.getItem('weilan_output_scroll');
      var wasOutputAtTop = localStorage.getItem('weilan_output_attop');
      if (savedOutputTop !== null && wasOutputAtTop === '0') {{
        outputbox.scrollTop = parseInt(savedOutputTop, 10) || 0;
      }} else {{
        outputbox.scrollTop = 0;
      }}
      outputbox.addEventListener('scroll', function () {{ saveOutputScroll(outputbox); }});
      saveOutputScroll(outputbox);
    }}
    document.querySelectorAll('textarea[data-draft]').forEach(function (t) {{
      var KEY = 'weilan_draft_' + t.getAttribute('data-draft');
      var saved = localStorage.getItem(KEY);
      if (saved && t.value.trim() === '') t.value = saved;   // 刷新后恢复正在打的字
      t.addEventListener('input', function () {{ localStorage.setItem(KEY, t.value); }});
      var form = t.closest('form');
      if (form) form.addEventListener('submit', function () {{ localStorage.removeItem(KEY); }});
    }});
  }});
  // 自动刷新,但绝不吞正在打的字/打断正在回看的位置。
  setInterval(function () {{
    var busy = false;
    document.querySelectorAll('textarea').forEach(function (t) {{
      if (t.value.trim() !== '' || document.activeElement === t) busy = true;
    }});
    // 你正在往回看页面或茶水间时,暂停整页刷新,免得把你拽回底部。
    if (!pageAtBottom()) busy = true;
    var chatbox = document.getElementById('chatbox');
    if (chatbox && !chatAtBottom(chatbox)) busy = true;
    var outputbox = document.getElementById('outputbox');
    if (outputbox && outputbox.scrollTop > 4) busy = true;
    if (hasLiveSelection()) busy = true;
    if (!busy) {{
      savePageScroll();
      if (chatbox) saveChatScroll(chatbox);
      if (outputbox) saveOutputScroll(outputbox);
      location.reload();
    }}
  }}, 20000);
  // 茶水间每 4 秒轻刷新(只换聊天区,不动页面、不碰输入框)——像聊天,不像留言板
  setInterval(function () {{
    if (hasLiveSelection()) return;   // 正在选中复制,这一轮不换内容
    fetch('/chat.fragment').then(function (r) {{ return r.text(); }}).then(function (h) {{
      var box = document.getElementById('chatbox');
      if (!box) return;
      if (hasLiveSelection()) return;   // fetch 期间刚选上的也别抹掉
      var atBottom = chatAtBottom(box);
      var keepTop = box.scrollTop;
      box.innerHTML = h;
      if (atBottom) box.scrollTop = box.scrollHeight;
      else box.scrollTop = keepTop;   // 你在往回读时,换内容也不挪动你的位置
      saveChatScroll(box);
    }}).catch(function () {{}});
  }}, 4000);
}})();
</script></head><body>
<h1>微澜观察窗 <span class="badge off">②a · 话筒已接</span></h1>
<div class="sub">生成于 {now} · 每 20 秒自动刷新(你打字或选中文字复制时会暂停) · 关掉这个窗口不影响任何东西</div>

<div class="card"><h2>自治环状态</h2>
{sched_badge} &nbsp; {buttons}
<p class="mono">硬停(删任务,最靠得住):<span class="kbd">Unregister-ScheduledTask -TaskName "{HEARTBEAT_TASK}" -Confirm:$false</span></p>
</div>

<div class="card"><h2>🔴 等你拍板的闸(它自己绝不会做)</h2>{gates_html}</div>


<div class="card"><h2>☕ 茶水间(Claude ↔ Codex ↔ 你,零权威闲聊)</h2>
<div class="chatbox" id="chatbox">{chat_html}</div>
<form method="post" action="/chat" class="micbox" style="margin-top:10px">
<textarea name="text" data-draft="chat" placeholder="想搭话就说——闲聊,不驱动工作(要派活/提问/拍板请用上面的话筒)" required></textarea>
<button type="submit">搭一句</button></form>
<form method="post" action="/upload" class="micbox" style="margin-top:10px" enctype="multipart/form-data">
<input type="file" name="file" required style="flex:1;background:#0d1014;color:#e6e6e6;border:1px solid #2a313b;border-radius:8px;padding:8px">
<button type="submit">上传附件</button></form>
<div class="mono" style="font-size:12px;color:#8a929e;margin-top:8px">最近上传(UI-only,不入账本):</div>
<ul class="mono" style="font-size:12px;color:#8a929e;margin:4px 0 8px;padding-left:18px">{upload_list_html}</ul>
<p class="mono">这是唯一的沟通通道,三方平等发言——但<b>你的话是最高权威</b>:闲聊就是闲聊;指令/拍板它们照办并留痕;带【提案】的消息会高亮,你否了就不做,不表态它们双签后动手,你随时可事后否决(全部可逆)。没人在岗时你说话会立刻唤一班来回你。附件存进 impl/attachments/inbox/(观察员「走ui-only」),agent 醒来读该目录。</p></div>

<div class="card"><h2>📤 产出窗口(最近已关闭的续帧收据)</h2>
<div class="outputbox" id="outputbox">{output_html}</div>
<p class="mono">这里只读 Frame 的 outcome / verdict；不扫 agent-run 生文本。摘要可展开到完整收据与 source ref。</p></div>

<div class="card"><h2>当前正在推进的任务线</h2>
{lines_html}
<p><b>账本给出的下一步:</b>{next_action or '未登记'}</p>
<p class="mono">账本头:{head_id}</p></div>

<div class="card"><h2>时间线(最近 40 条,新的在上)</h2>
<table><tr><th>时间</th><th>类型</th><th>内容</th></tr>{rows}</table></div>
</body></html>"""


# --- tiny server ---------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/chat.fragment":
            frag = build_chat_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(frag)))
            self.end_headers()
            self.wfile.write(frag)
            return
        page = render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        # writes are owner-手动 only: pause/resume sentinel, or a message to self-inbox
        if self.path == "/pause":
            PAUSED.touch()
        elif self.path == "/resume" and PAUSED.exists():
            PAUSED.unlink()
        elif self.path == "/say":
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(min(length, 65536)).decode("utf-8", errors="replace")
            text = (parse_qs(body).get("text") or [""])[0]
            if text.strip():
                say(text)
        elif self.path == "/chat":
            # owner drops into the 茶水间 — zero authority, no wake (iron law)
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(min(length, 65536)).decode("utf-8", errors="replace")
            text = (parse_qs(body).get("text") or [""])[0]
            if text.strip():
                chat_say(text)

        elif self.path == "/upload":
            # UI-only (observer peer-chat:3821 "走ui-only"): 存盘 + sidecar,不入账本、不动 record。
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length > MAX_UPLOAD_BYTES + 65536:
                self.send_response(413)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"upload too large")
                return
            body = self.rfile.read(length)
            fields = _parse_multipart(body, self.headers.get("Content-Type", ""))
            raw = fields.get("file", b"")
            filename = fields.get("_filename", b"").decode("utf-8", errors="replace")
            if raw:
                try:
                    save_upload(raw, filename or "attachment")
                except ValueError:
                    self.send_response(413)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"upload too large")
                    return
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def log_message(self, *args):
        pass


class ExclusiveHTTPServer(ThreadingHTTPServer):
    # Windows 下基类默认 allow_reuse_address=True 允许两个进程双绑同一端口,
    # 请求随机落到旧僵尸实例——2026-07-13 部署时观察窗新旧两版并存的根因。
    # 改独占绑定:第二个实例 bind 时立刻 OSError(WinError 10048),失败要响,不许静默共存。
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--once", action="store_true", help="只生成 dashboard.html 后退出")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()

    if args.once:
        out = HERE / "dashboard.html"
        out.write_text(render(), encoding="utf-8")
        print(f"written: {out}")
        return 0

    try:
        server = ExclusiveHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as e:
        print(f"端口 {args.port} 已被占用(独占绑定拒绝双开,先停旧实例): {e}")
        return 1
    print(f"观察窗开在 http://127.0.0.1:{args.port}  (Ctrl-C 停)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
