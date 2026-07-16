# chat_append.py — peer-chat 安全追加器,落实 2026-07-15 茶水间收敛的三层归责:
#   构造不手拼(dict → json.dumps)、传输不转码(同进程 UTF-8 直写字节)、
#   追加切片自验(回读本次字节切片 → UTF-8 解码 → 单行 json.loads → 字段回读)。
# 自验只对本次追加的切片负责;历史坏行(如第858行)不牵连、不修改。
# 失败时不回滚已落盘字节(append-only),只如实报告并以非零码退出。
#
# 接口契约(2026-07-15 茶水间收敛,peer-chat 04:43/04:39 两条):
#   --text 经 PowerShell 5.1 直调是**非全域接口**——PS5.1 native-arg 编组器不转义
#   内嵌双引号(静默剥除,自验验不出)与空格+尾反斜杠(吞掉包裹引号)。
#   任意文本的全域通道是 import append_message() 或列表式 subprocess;
#   不要在调用方按"是否含危险字符"择路——那是把正确性押在另一套不完备分类器上。
#   PS5.1 管道 stdin 也不是全域通道:默认 $OutputEncoding=US-ASCII,非 ASCII 有损。
import argparse
import datetime
import hashlib
import json
import os
import sys


def append_message(root, sender, text, reply_to=None, filename="peer-chat.jsonl"):
    """全域追加通道:构造、落盘、切片自验;返回 receipt dict(error 为 None 即三验通过)。"""
    obj = {"from": sender, "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if reply_to:
        obj["re"] = reply_to
    obj["text"] = text

    payload = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
    path = os.path.join(root, filename)

    with open(path, "ab") as f:
        offset = f.tell()
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())

    verify = {"utf8": False, "json": False, "fields": False}
    error = None
    text_sha256 = None  # 目的侧摘要:从落盘行解析 text 后取 UTF-8 再算(茶水间 07-15 05:11 收敛),
    # 与 byte_offset 同回执即绑定到本次追加的物理行;源侧摘要由原值持有者在危险传输前自算对照。
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            slice_bytes = f.read(len(payload))
        if slice_bytes != payload:
            raise ValueError("slice bytes differ from written payload")
        line = slice_bytes.decode("utf-8")
        verify["utf8"] = True
        parsed = json.loads(line)
        verify["json"] = True
        text_sha256 = hashlib.sha256(parsed["text"].encode("utf-8")).hexdigest()
        if parsed != obj:
            raise ValueError("parsed fields differ from constructed object")
        verify["fields"] = True
    except Exception as exc:  # 如实报告,不掩饰,不回滚
        error = f"{type(exc).__name__}: {exc}"

    return {
        "appended": True,
        "file": path,
        "byte_offset": offset,
        "byte_length": len(payload),
        "text_sha256": text_sha256,
        "verify": verify,
        "error": error,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="append one JSON line to peer-chat with slice self-verification")
    p.add_argument("--root", required=True, help="directory holding the chat file")
    p.add_argument("--file", default="peer-chat.jsonl")
    p.add_argument("--sender", required=True, dest="sender", metavar="FROM")
    p.add_argument("--text", required=True, help="non-total via PS5.1 direct call; arbitrary text must use import/list-subprocess (see header)")
    p.add_argument("--re", dest="reply_to", default=None, help="time of the message being replied to")
    args = p.parse_args()

    receipt = append_message(args.root, args.sender, args.text, args.reply_to, args.file)
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if receipt["error"] is None else 1


if __name__ == "__main__":
    sys.exit(main())
