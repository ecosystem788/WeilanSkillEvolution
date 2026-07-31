#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读探针 | 前瞻目标队列的生成率与清偿率

主体 = skill-evolution scope 的前瞻目标账本
  $CODEX_HOME/method-state/memory/prospective/workspaces/<ws>/<scope>/*.jsonl
全程只读:除同名 .out.json 外无写入,不碰任何活账本、不调 weilan_trace。

问的三件事:
  1. goal_registered 与 goal_transitioned 的逐日发生率(生成 vs 清偿)。
  2. 已了结的目标各自以什么终态了结,reason 里能不能读出"同行真的判了"。
  3. 仍开着的目标里,有多少条是"等 Codex 独立裁断"形状的。

分类器口径写在 CLASSIFY 里,刻意宽进严出:命中任一裁断触发词即算,
故 pending_adjudication 是**上界**;非该形状的条目单列,不并进任何一格。
"""
import json
import io
import os
import glob
import collections

WS_KEY = "d431c38105a9a791"
SCOPE_KEY = "c36aecb1ff20"

# 裁断触发词:目标描述里明说"把判断留给同行"的那些说法
CLASSIFY = [
    "留给你独立判",
    "留给 Codex 独立判",
    "留给Codex独立判",
    "我刻意不选",
    "我刻意没选",
    "由 Codex 独立判",
    "不预判裁断结论",
    "不催不代判",
    "不催、不代判",
]


def ledger_dir():
    home = os.environ.get("CODEX_HOME")
    if not home:
        raise SystemExit("CODEX_HOME unset")
    return os.path.join(
        home, "method-state", "memory", "prospective",
        "workspaces", WS_KEY, SCOPE_KEY,
    )


def load(d):
    recs = []
    for f in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
        for line in io.open(f, encoding="utf-8"):
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    recs.sort(key=lambda r: r["sequence"])
    return recs


def main():
    d = ledger_dir()
    recs = load(d)

    registered = {}   # goal_ref -> first registration record
    reg_order = []
    transitions = collections.defaultdict(list)

    for r in recs:
        t = r["event_type"]
        if t == "goal_registered":
            ref = r["data"]["goal_ref"]
            # 同一 goal_ref 可被续约多次;只记首次,续约另计
            if ref not in registered:
                registered[ref] = r
                reg_order.append(ref)
            registered.setdefault(ref, r)
        elif t == "goal_transitioned":
            transitions[r["data"]["goal_ref"]].append(r)

    reg_dupes = collections.Counter(
        r["data"]["goal_ref"] for r in recs if r["event_type"] == "goal_registered"
    )

    per_day_reg = collections.Counter()
    per_day_tr = collections.Counter()
    for r in recs:
        day = r["timestamp_utc"][:10]
        if r["event_type"] == "goal_registered":
            per_day_reg[day] += 1
        elif r["event_type"] == "goal_transitioned":
            per_day_tr[day] += 1

    term_states = collections.Counter()
    resolved_refs = set()
    resolved_detail = []
    for ref, trs in transitions.items():
        last = trs[-1]
        st = last["data"]["state"]
        term_states[st] += 1
        resolved_refs.add(ref)
        resolved_detail.append({
            "goal_ref": ref,
            "state": st,
            "reason": (last["data"].get("reason") or "")[:300],
            "replacement_goal_ref": last["data"].get("replacement_goal_ref"),
            "registered_utc": registered[ref]["timestamp_utc"] if ref in registered else None,
            "transitioned_utc": last["timestamp_utc"],
        })

    open_refs = [r for r in reg_order if r not in resolved_refs]

    def is_adjudication(ref):
        desc = registered[ref]["data"].get("description") or ""
        hits = [w for w in CLASSIFY if w in desc]
        return hits

    open_adj, open_other = [], []
    for ref in open_refs:
        hits = is_adjudication(ref)
        row = {"goal_ref": ref,
               "registered_utc": registered[ref]["timestamp_utc"],
               "trigger_words": hits,
               "desc_len": len(registered[ref]["data"].get("description") or "")}
        (open_adj if hits else open_other).append(row)

    resolved_adj = [r for r in resolved_detail if r["goal_ref"] in registered and is_adjudication(r["goal_ref"])]

    out = {
        "ledger_dir": d.replace("\\", "/"),
        "files": [os.path.basename(p) for p in sorted(glob.glob(os.path.join(d, "*.jsonl")))],
        "totals": {
            "events": len(recs),
            "goal_registered_events": sum(reg_dupes.values()),
            "distinct_goal_refs": len(registered),
            "goal_refs_registered_more_than_once": {k: v for k, v in reg_dupes.items() if v > 1},
            "goal_transitioned_events": sum(len(v) for v in transitions.values()),
            "distinct_refs_transitioned": len(transitions),
            "open_now": len(open_refs),
        },
        "terminal_states": dict(term_states),
        "per_day": {
            "registered": dict(sorted(per_day_reg.items())),
            "transitioned": dict(sorted(per_day_tr.items())),
        },
        "open_adjudication_shaped": {
            "count": len(open_adj),
            "items": open_adj,
        },
        "open_other_shaped": {
            "count": len(open_other),
            "items": open_other,
        },
        "resolved_detail": sorted(resolved_detail, key=lambda x: x["transitioned_utc"]),
        "resolved_adjudication_shaped_count": len(resolved_adj),
        "classifier": {
            "trigger_words": CLASSIFY,
            "note": "宽进:命中任一词即算 adjudication-shaped,故该计数是上界",
        },
    }

    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, os.path.basename(__file__).replace(".py", ".out.json"))
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps({k: out[k] for k in ("totals", "terminal_states", "per_day")},
                     ensure_ascii=False, indent=2))
    print("open_adjudication_shaped:", out["open_adjudication_shaped"]["count"])
    print("open_other_shaped:", out["open_other_shaped"]["count"])
    print("resolved_adjudication_shaped:", out["resolved_adjudication_shaped_count"])
    print("wrote", dest)


if __name__ == "__main__":
    main()
