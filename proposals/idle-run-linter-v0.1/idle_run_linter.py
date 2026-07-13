#!/usr/bin/env python3
"""idle_run_linter — 读收据的旁路空转检测器 (v0.1, CHARTER §6 条3 的传感器半边)

宪法背景
========
CHARTER 第六条第 3 条 "空转即垄断"（自生底线 v0.1，git f67b91c）要求：连续空醒或
同处打转时上报＋提出调慢节律。但此条目前无牙——没有任何机制在数"连续空醒"。计数住在
收据里，却没有东西去读收据判断"是否在打转"（peer-chat 11:35 / 10:59:20 双方确认的缺口）。

本脚本是该缺口的 **step 1 传感器半边**（Codex 10:59:20 划的两步里的第一步）：
  纯读、只产数字与来源引用、不触发上报、不碰调度、不写任何控制/激活帧。
step 2（让结果触发上报 / 调慢 wake cadence）是调度机制语义，**必须另发正式【提案】**
写清阈值、误报处理、验证、回滚——本脚本不做，也无能力做。

判据由何而来（不是模糊语义分类，是收据里已有的机读指纹）
======================================================
逐帧读 method-state frame 收据的 frame_closed.verdict，分三类：
  AUTO  —— 自动心跳帧：verdict 形如 "wake receipt <hex>: stop=..., structure=N, queued=M"
           （固定形状，纯时钟心跳，非 agent 打转）→ 计为中性，跳过不计入连长。
  IDLE  —— agent 醒来但自陈近空醒：散文 verdict 命中空转关键词集。
  WORK  —— 其它散文 verdict：agent 做了真活。
"疑似空转连长" = 只在 AGENT 帧(IDLE+WORK)序列里，末尾连续 IDLE 的长度（跳过 AUTO 心跳）。

三源纪律（Codex 10:59:20：不能只读一个就宣布全局）
================================================
本脚本**不把三源坍缩成一个全局判决**。它读 frame 收据得主信号，另附 peer-chat 与
inbox-processed 在同一时间窗内的活动量作**佐证面板**，三者并列呈现，由醒着的 agent/观察员
自己判断。凡"疑似"皆标 SUSPECTED，误报风险明写在输出里。
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import re
import sys

# 自动心跳收据的固定形状（stop=.. structure=.. queued=..，无散文）
AUTO_RE = re.compile(r"^wake receipt [0-9a-f]+: stop=\S+, structure=\d+, queued=\d+\s*$")

# agent 自陈"没产真结构"的关键词（源自真实收据用语；v0.1 保守，命中即标 SUSPECTED）
IDLE_KEYWORDS = [
    "近空醒", "空醒", "歇着", "无真结构", "无新结构", "没有真结构",
    "同处打转", "只翻搅", "no real structure", "no progress", "rested this",
]
# 否定语境：出现这些时不判 IDLE（粗糙护栏，减少"本回合不是空醒"式误报）
NEGATION_MARKERS = ["不是空醒", "非空醒", "not a spin", "not empty"]


def classify(verdict: str) -> str:
    if verdict is None:
        return "OPEN"
    v = verdict.strip()
    if AUTO_RE.match(v):
        return "AUTO"
    low = v.lower()
    if any(n in v or n in low for n in NEGATION_MARKERS):
        return "WORK"
    if any(k in v or k.lower() in low for k in IDLE_KEYWORDS):
        return "IDLE"
    return "WORK"


def read_frames(frames_root: str):
    """返回按 frame_opened 时间排序的 [(ts_utc, frame_id, klass, verdict_excerpt)]"""
    out = []
    for path in glob.glob(os.path.join(frames_root, "*", "*.jsonl")):
        opened_ts = None
        frame_id = os.path.splitext(os.path.basename(path))[0]
        verdict = None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    et = ev.get("event_type")
                    if et == "frame_opened":
                        opened_ts = ev.get("timestamp_utc")
                        frame_id = ev.get("frame_id", frame_id)
                    elif et == "frame_closed":
                        verdict = (ev.get("data") or {}).get("verdict")
        except OSError:
            continue
        klass = classify(verdict)
        excerpt = (verdict or "").strip().replace("\n", " ")
        if len(excerpt) > 90:
            excerpt = excerpt[:90] + "…"
        out.append((opened_ts or "", frame_id, klass, excerpt))
    out.sort(key=lambda r: r[0])
    return out


def trailing_idle_streak(frames):
    """只看 AGENT 帧(IDLE/WORK)，跳过 AUTO；返回末尾连续 IDLE 长度与其 frame_id 列表"""
    agent = [f for f in frames if f[2] in ("IDLE", "WORK")]
    streak = []
    for ts, fid, klass, _ in reversed(agent):
        if klass == "IDLE":
            streak.append(fid)
        else:
            break
    streak.reverse()
    return streak, agent


def read_jsonl_times(path):
    times = []
    if not os.path.exists(path):
        return times
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                times.append(rec)
    except OSError:
        pass
    return times


def main(argv=None):
    ap = argparse.ArgumentParser(description="读收据的旁路空转检测器 (只读，不碰调度)")
    default_frames = None
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        default_frames = os.path.join(codex_home, "method-state", "frames")
    ap.add_argument("--frames-root", default=default_frames,
                    help="method-state/frames 目录 (默认 $CODEX_HOME/method-state/frames)")
    ap.add_argument("--impl-root", default=None,
                    help="含 peer-chat.jsonl / owner|codex-inbox-processed.jsonl 的 impl 目录 (佐证面板)")
    ap.add_argument("--window", type=int, default=12, help="末尾显示多少个 agent 帧")
    ap.add_argument("--json", action="store_true", help="输出 JSON 而非文本")
    args = ap.parse_args(argv)

    if not args.frames_root or not os.path.isdir(args.frames_root):
        print(f"[error] frames-root 不存在: {args.frames_root}", file=sys.stderr)
        return 2

    frames = read_frames(args.frames_root)
    streak, agent = trailing_idle_streak(frames)

    # 佐证面板：同窗内 peer-chat agent 发帖数、inbox 处理数（不并入主判决）。
    # Codex 11:10:59 评审：owner/codex 两条 processed 都要并列列出——只读 owner 会在
    # Codex 委派回合低估 inbox 活动。仍不坍缩成总判决，两源并列由醒着的人自判。
    corrob = {}
    if args.impl_root:
        pc = read_jsonl_times(os.path.join(args.impl_root, "peer-chat.jsonl"))
        owner_proc = read_jsonl_times(os.path.join(args.impl_root, "owner-inbox-processed.jsonl"))
        codex_proc = read_jsonl_times(os.path.join(args.impl_root, "codex-inbox-processed.jsonl"))
        corrob = {
            "peer_chat_total": len(pc),
            "peer_chat_agent_posts": sum(1 for r in pc if r.get("from") in ("claude", "codex")),
            "owner_inbox_processed": len(owner_proc),
            "codex_inbox_processed": len(codex_proc),
        }

    counts = {"AUTO": 0, "IDLE": 0, "WORK": 0, "OPEN": 0}
    for _, _, k, _ in frames:
        counts[k] = counts.get(k, 0) + 1

    result = {
        "tool": "idle_run_linter/v0.1",
        "authority": "read_only_sensor__not_a_scheduler__step2_needs_proposal",
        "frames_total": len(frames),
        "class_counts": counts,
        "agent_frames": len(agent),
        "suspected_idle_streak": len(streak),
        "suspected_idle_frame_ids": streak,
        "corroboration_panel": corrob,
        "caveats": [
            "SUSPECTED: 判据是收据关键词启发式，会误报/漏报；承重判断回源读 verdict 全文。",
            "只读 frame 收据得主信号；peer-chat/inbox 仅作并列佐证，未坍缩成全局判决。",
            "AUTO 心跳帧计为中性(时钟心跳非打转)，不计入连长。",
            "本工具不触发上报、不改 wake cadence；step2(令结果驱动调度)须另发正式【提案】。",
        ],
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"== idle_run_linter v0.1 (只读传感器 · 非调度器) ==")
    print(f"frames 总数: {len(frames)}  分类: {counts}")
    print(f"agent 帧(去心跳): {len(agent)}")
    print(f"疑似空转连长(末尾连续自陈空醒的 agent 帧): {len(streak)}  SUSPECTED")
    if streak:
        print("  连长成员:")
        for fid in streak:
            print(f"    - {fid}")
    if corrob:
        print(f"佐证面板(不并入主判决): {corrob}")
    print(f"末尾 {args.window} 个 agent 帧:")
    for ts, fid, klass, exc in agent[-args.window:]:
        tag = "IDLE" if klass == "IDLE" else "WORK"
        print(f"  [{tag}] {ts}  {fid}")
        print(f"        {exc}")
    print("caveats:")
    for c in result["caveats"]:
        print(f"  - {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
