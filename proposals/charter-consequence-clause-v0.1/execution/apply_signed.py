"""执行 2026-07-27 双签(Claude 提案 23:12:37 + Codex 强绑定同意 23:30:47)的 CHARTER 精确文本替换。

只读 target 并在内存里施加替换;--write 才落盘。锚点与替换文本**从已签的 peer-chat 消息里提取**,
不手抄。制品全部写在工作树之外。
"""
import argparse
import hashlib
import io
import json
import pathlib
import sys

REPO = pathlib.Path(r"D:\WeilanSkillEvolution")
TARGET = REPO / "CHARTER.md"
CHAT = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl" / "peer-chat.jsonl"
PROPOSAL_TIME = "2026-07-27T23:12:37+09:00"
BASE_SHA = "8330e7a2c0e066c44fa1b280f94787a06a9a59e674fc82f527d23ef1dd580bde"
FINAL_SHA = "5b2b9e14c137e5b712c844e0168f4a5b29c0171d7711641e341f347b1483e588"


def signed_blocks():
    """从已签提案里取两个 fenced block:第一个=锚点,第二个=替换。"""
    msg = None
    bad = 0
    with io.open(CHAT, encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                d = json.loads(raw)
            except ValueError:
                bad += 1
                continue
            if d.get("from") == "claude" and d.get("time") == PROPOSAL_TIME:
                msg = d
    sys.stderr.write("unparsable_chat_lines=%d\n" % bad)
    if msg is None:
        sys.exit("找不到被签提案")
    text = msg["text"]
    head = text.index("## 三、唯一改动")
    tail = text.index("## 四、五件绑定")
    section = text[head:tail]
    parts = section.split("```")
    # parts: [前言, block1, 中间, block2, 后言]
    if len(parts) != 5:
        sys.exit("fenced block 数不是 2,拒绝继续: %d" % (len(parts) - 1))
    anchor = parts[1]
    repl = parts[3]
    # 去掉 fence 自带的首尾换行:开栏后紧跟一个 \n,收栏前一个 \n
    assert anchor.startswith("\n") and anchor.endswith("\n")
    assert repl.startswith("\n") and repl.endswith("\n")
    return anchor[1:], repl[1:]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    anchor_s, repl_s = signed_blocks()
    anchor = anchor_s.encode("utf-8")
    repl = repl_s.encode("utf-8")

    base = TARGET.read_bytes()
    report = {
        "base_sha256": sha(base),
        "base_bytes": len(base),
        "base_lines": len(base.splitlines()),
        "base_matches_signed": sha(base) == BASE_SHA,
        "anchor_bytes": len(anchor),
        "anchor_count": base.count(anchor),
        "repl_bytes": len(repl),
        "has_bom": base.startswith(b"\xef\xbb\xbf"),
        "crlf_count": base.count(b"\r\n"),
        "ends_with_single_lf": base.endswith(b"\n") and not base.endswith(b"\n\n"),
    }
    if report["anchor_count"] != 1:
        report["verdict"] = "REFUSE: anchor count != 1"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(2)
    if not report["base_matches_signed"]:
        report["verdict"] = "REFUSE: base drifted, signature void"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(2)

    final = base.replace(anchor, repl)
    report["final_sha256"] = sha(final)
    report["final_bytes"] = len(final)
    report["final_lines"] = len(final.splitlines())
    report["final_matches_signed"] = sha(final) == FINAL_SHA
    if not report["final_matches_signed"]:
        report["verdict"] = "REFUSE: computed final != signed proposed-final"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(2)

    report["verdict"] = "preflight-ok"
    if args.write:
        TARGET.write_bytes(final)
        after = TARGET.read_bytes()
        report["written"] = True
        report["readback_sha256"] = sha(after)
        report["readback_ok"] = sha(after) == FINAL_SHA
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
