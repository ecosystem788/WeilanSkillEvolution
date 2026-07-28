#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立重建 CHARTER 六.1 否决通道证据分层 v2 的后像。

只读 target；块文本从 peer-chat.jsonl 的提案原行逐字提取，不从本脚本内嵌。
输出后像字节到工作树之外的文件，供执行步骤原样写入。
"""
import hashlib
import io
import json
import os
import sys

REPO = r"D:\WeilanSkillEvolution"
CHAT = os.path.join(REPO, r"proposals\bounded-scheduler-v0.1\impl\peer-chat.jsonl")
TARGET = os.path.join(REPO, "CHARTER.md")
PROPOSAL_TIME = "2026-07-29T07:14:25+09:00"
EXPECT_BASE = "5b2b9e14c137e5b712c844e0168f4a5b29c0171d7711641e341f347b1483e588"
EXPECT_FINAL = "9fdab08587d37db33906a4b4dcdfe47c5891dd4dbca1aae07153a8aa8c10dc35"
ANCHOR_SUB = "站立授权免掉的是"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHARTER.final.v2")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def proposal_text():
    for line in io.open(CHAT, encoding="utf-8"):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("time") == PROPOSAL_TIME and row.get("from") == "claude":
            return row["text"]
    raise SystemExit("提案原行未找到")


def fenced_blocks(text):
    blocks, cur, inside = [], None, False
    for ln in text.split("\n"):
        if ln.strip() == "```":
            if inside:
                blocks.append(cur)
                cur, inside = None, False
            else:
                cur, inside = [], True
            continue
        if inside:
            cur.append(ln)
    if inside:
        raise SystemExit("围栏未闭合")
    return blocks


def main():
    text = proposal_text()
    blocks = fenced_blocks(text)
    sizes = [len(b) for b in blocks]
    cands = [b for b in blocks if len(b) == 22]
    if len(cands) != 1:
        raise SystemExit("22 行块不唯一：%r" % (sizes,))
    block = cands[0]

    raw = open(TARGET, "rb").read()
    base = sha(raw)
    base_lines = raw.split(b"\n")
    report = {
        "block_fence_sizes": sizes,
        "base_actual": base,
        "base_expected": EXPECT_BASE,
        "base_ok": base == EXPECT_BASE,
        "base_bytes": len(raw),
        "base_lines_splitlines": len(raw.splitlines()),
        "crlf_count": raw.count(b"\r\n"),
        "has_bom": raw[:3] == b"\xef\xbb\xbf",
        "ends_single_lf": raw.endswith(b"\n") and not raw.endswith(b"\n\n"),
    }
    if not report["base_ok"]:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit("base 不符 → 签名失效")

    lines = raw.splitlines(keepends=True)
    idx = [i for i, l in enumerate(lines) if ANCHOR_SUB.encode("utf-8") in l]
    report["anchor_count"] = len(idx)
    if len(idx) != 1:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit("锚点 count != 1")
    at = idx[0]
    report["anchor_line"] = lines[at].decode("utf-8").rstrip("\n")

    ins = b"".join((l + "\n").encode("utf-8") for l in block)
    final = b"".join(lines[: at + 1]) + ins + b"".join(lines[at + 1 :])
    fsha = sha(final)
    report.update(
        final_actual=fsha,
        final_expected=EXPECT_FINAL,
        final_ok=fsha == EXPECT_FINAL,
        final_bytes=len(final),
        final_lines_splitlines=len(final.splitlines()),
        final_crlf=final.count(b"\r\n"),
        inserted_lines=len(block),
    )
    with open(OUT, "wb") as fh:
        fh.write(final)
    report["out"] = OUT
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["final_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
