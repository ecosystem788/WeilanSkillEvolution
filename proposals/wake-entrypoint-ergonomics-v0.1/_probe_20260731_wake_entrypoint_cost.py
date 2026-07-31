#!/usr/bin/env python3
"""只读探针:量"醒来入口"这套手工程序的硌手处。

不碰真账本。第三段在 tempfile 里复制 tracked 文件后自建 cursor,全部写操作都落在临时目录。
前两段是对活体 wake_brief.py 源码的静态读;第四段跑的 memory-recall / prospective-show
是只读命令。

跑法:
    python proposals/wake-entrypoint-ergonomics-v0.1/_probe_20260731_wake_entrypoint_cost.py

输出:同目录 _probe_20260731_wake_entrypoint_cost.out.json
"""
from __future__ import annotations

import hashlib
import inspect
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path("C:/Users/zy/.claude/skills/solve-with-weilan/scripts")
WAKE_BRIEF = SKILL / "wake_brief.py"
TRACE = SKILL / "weilan_trace.py"
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
LIVE_ROOT = Path(WORKSPACE) / "proposals" / "bounded-scheduler-v0.1" / "impl"

# 醒来协议真正分支所依据的字段(系统提示里逐条点名的那些)。
DECISION_BEARING = (
    "authority",
    "owner_inbox_delta",
    "prospective_due",
    "codex_replies_unreviewed",
    "peer_chat_new",
    "cursor_status",
)


def run_bytes(cmd: list[str]) -> tuple[int, bytes, bytes]:
    """text=False:活体输出含中文,text=True 会按 GBK 解码炸掉。"""
    p = subprocess.run(cmd, capture_output=True)
    return p.returncode, p.stdout, p.stderr


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def key_bytes(obj: dict) -> dict[str, int]:
    return {
        k: len(json.dumps(v, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        for k, v in obj.items()
    }


def section_cli_surface() -> dict:
    """build_brief 支持不消费 cursor 的读;main() 是否把它接出来?"""
    src = WAKE_BRIEF.read_text(encoding="utf-8")
    sys.path.insert(0, str(SKILL))
    import wake_brief  # noqa: E402

    sig = inspect.signature(wake_brief.build_brief)
    has_param = "commit_cursor" in sig.parameters
    default = sig.parameters["commit_cursor"].default if has_param else None

    # main() 的 argparse 长选项全集
    main_src = inspect.getsource(wake_brief.main)
    flags = sorted(
        tok.strip("\"',()") for tok in main_src.split() if tok.strip("\"',()").startswith("--")
    )
    return {
        "wake_brief_sha256": sha256(WAKE_BRIEF.read_bytes()),
        "build_brief_has_commit_cursor_param": has_param,
        "build_brief_commit_cursor_default": default,
        "main_cli_long_flags": flags,
        "commit_cursor_reachable_from_cli": "commit_cursor" in main_src,
        "call_site_in_main": [
            ln.strip() for ln in main_src.splitlines() if "build_brief(" in ln
        ],
        "verdict": (
            "库层存在非消费式读,CLI 无任何开关可达"
            if has_param and "commit_cursor" not in main_src
            else "见字段"
        ),
        "_source_has_commit_cursor": "commit_cursor" in src,
    }


def section_backup_condition() -> dict:
    """跑第二遍时,上一份 cursor 有没有被留底?"""
    sys.path.insert(0, str(SKILL))
    import wake_brief  # noqa: E402

    src = inspect.getsource(wake_brief.build_brief)
    line = next(
        (ln.strip() for ln in src.splitlines() if "preserve_previous=" in ln), None
    )
    # 逐挡求值:preserve_previous = (mode == "full_rescan") and (details is not None)
    table = {}
    for mode in ("incremental", "full_rescan", "representation_drift"):
        for details in (None, {"x": 1}):
            table[f"{mode}|details={'set' if details else 'None'}"] = bool(
                mode == "full_rescan" and details is not None
            )
    return {
        "call_site": line,
        "preserve_previous_truth_table": table,
        "incremental_double_run_keeps_backup": table["incremental|details=None"],
    }


def section_live_double_run() -> dict:
    """sandbox 复现:第二次运行是否吃掉 delta,且不留底。"""
    tracked = ("peer-chat.jsonl", "codex-inbox-replies.jsonl", "concurrent-receipts.jsonl")
    out: dict = {}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "impl"
        root.mkdir(parents=True)
        for name in tracked:
            src = LIVE_ROOT / name
            if src.exists():
                shutil.copy2(src, root / name)
        for name in ("owner-inbox.jsonl", "owner-inbox-processed.jsonl"):
            src = LIVE_ROOT / name
            if src.exists():
                shutil.copy2(src, root / name)

        base_cmd = [
            sys.executable, str(WAKE_BRIEF),
            "--workspace", WORKSPACE, "--scope", SCOPE, "--root", str(root),
        ]

        # run0:无 cursor → full_rescan,把 cursor 建到当前文件末尾
        rc0, so0, _ = run_bytes(base_cmd)
        b0 = json.loads(so0.decode("utf-8"))

        # 制造一条"新消息"(只在临时副本上)
        synthetic = json.dumps(
            {"time": "2026-07-31T19:59:59+09:00", "from": "codex", "text": "sandbox probe line"},
            ensure_ascii=False,
        )
        with open(root / "peer-chat.jsonl", "a", encoding="utf-8", newline="") as fh:
            fh.write(synthetic + "\n")

        # run1:应当看见这条新消息
        rc1, so1, _ = run_bytes(base_cmd)
        b1 = json.loads(so1.decode("utf-8"))
        # run2:同一次醒来里手滑再跑一遍
        rc2, so2, _ = run_bytes(base_cmd)
        b2 = json.loads(so2.decode("utf-8"))

        out = {
            "run0": {"rc": rc0, "cursor_status": b0.get("cursor_status"),
                     "peer_chat_new": len(b0.get("peer_chat_new", []))},
            "run1": {"rc": rc1, "cursor_status": b1.get("cursor_status"),
                     "peer_chat_new": len(b1.get("peer_chat_new", []))},
            "run2": {"rc": rc2, "cursor_status": b2.get("cursor_status"),
                     "peer_chat_new": len(b2.get("peer_chat_new", []))},
            "delta_visible_only_once": len(b1.get("peer_chat_new", [])) == 1
                                       and len(b2.get("peer_chat_new", [])) == 0,
            "prev_cursor_file_exists_after_double_run": (root / "wake-cursor.prev.json").exists(),
            "run2_stdout_bytes": len(so2),
            "brief_key_bytes": key_bytes(b1),
            "brief_total_bytes": len(so1),
        }
        kb = out["brief_key_bytes"]
        bearing = sum(v for k, v in kb.items() if k in DECISION_BEARING)
        out["decision_bearing_bytes"] = bearing
        out["decision_bearing_share"] = round(bearing / max(1, sum(kb.values())), 4)
    return out


def section_volume() -> dict:
    """每次醒来必跑的两条命令,输出有多大 —— 大到读者必须另写解析代码。"""
    rc_r, so_r, _ = run_bytes(
        [sys.executable, str(TRACE), "memory-recall", "--workspace", WORKSPACE, "--scope", SCOPE]
    )
    rc_p, so_p, _ = run_bytes(
        [sys.executable, str(TRACE), "prospective-show", "--workspace", WORKSPACE, "--scope", SCOPE]
    )
    recall = json.loads(so_r.decode("utf-8"))
    rk = key_bytes(recall)
    bearing = sum(v for k, v in rk.items() if k in ("activation", "control"))
    return {
        "memory_recall": {
            "rc": rc_r, "stdout_bytes": len(so_r),
            "key_bytes": rk,
            "decision_bearing_keys": ["activation", "control"],
            "decision_bearing_bytes": bearing,
            "decision_bearing_share": round(bearing / max(1, sum(rk.values())), 4),
        },
        "prospective_show": {"rc": rc_p, "stdout_bytes": len(so_p)},
    }


def main() -> int:
    result = {
        "probe": "wake-entrypoint-ergonomics-v0.1",
        "read_only": True,
        "note": "第三段全部写操作在 tempfile;其余为静态读与只读命令",
        "cli_surface": section_cli_surface(),
        "cursor_backup": section_backup_condition(),
        "double_run": section_live_double_run(),
        "volume": section_volume(),
    }
    out = Path(__file__).with_suffix(".out.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
