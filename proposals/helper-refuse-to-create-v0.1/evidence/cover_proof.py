#!/usr/bin/env python3
"""Cover 5.1/5.2/5.3/5.4:实测试 append_clocked_jsonl.py 在 refuse-to-create 落地后的四类形状。
- 5.1:已存在账本 + 不带 --allow-create → rc=0 行落入
- 5.2:已存在账本 + 带 --allow-create → rc=0 行落入(等效正路径)
- 5.3:不存在账本 + 不带 --allow-create → rc=2 stderr 含 refuse to create
- 5.4:不存在账本 + 带 --allow-create → rc=0 行落入
每条都跑在隔离的临时 root,不让 helper 写入工作区。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HELPER = Path("D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl/append_clocked_jsonl.py")
PYTHON = sys.executable


def run(root, ledger, fields, allow_create=False, expect_rc=0, expect_stderr_substring=None,
        expect_file_created=None):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    cmd = [PYTHON, str(HELPER), "--root", str(root), "--file", ledger]
    if allow_create:
        cmd.append("--allow-create")
    cmd.extend(["--field", f"k={fields['k']}", "--field", f"v={fields['v']}",
                "--field", "source_ref=cover-test"])
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    out = {"rc": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr, "cmd": cmd}
    out["expect_rc_ok"] = proc.returncode == expect_rc
    if expect_stderr_substring:
        out["expect_stderr_ok"] = expect_stderr_substring in proc.stderr
    if expect_file_created is not None:
        path = root / ledger
        out["file_exists"] = path.exists()
        out["expect_file_ok"] = path.exists() == expect_file_created
    return out


def case_5_1():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "root_existing"
        root.mkdir()
        ledger = "peer.jsonl"
        (root / ledger).write_text("", encoding="utf-8")  # 已存在
        r = run(root, ledger, {"k": "case5.1", "v": "v1"}, allow_create=False, expect_rc=0,
                expect_file_created=True)
        return ("5.1", "已存在账本 + 不带 --allow-create", "正路径 rc=0 行落入",
                {"rc": r["rc"], "stderr_excerpt": r["stderr"][:120],
                 "stdout_excerpt": r["stdout"][:120], "expect_rc_ok": r["expect_rc_ok"],
                 "expect_file_ok": r["expect_file_ok"], "file_exists": r["file_exists"]})


def case_5_2():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "root_existing_with_flag"
        root.mkdir()
        ledger = "peer.jsonl"
        (root / ledger).write_text("", encoding="utf-8")  # 已存在
        r = run(root, ledger, {"k": "case5.2", "v": "v2"}, allow_create=True, expect_rc=0,
                expect_file_created=True)
        return ("5.2", "已存在账本 + 显式 --allow-create", "正面覆盖 --allow-create 与默认等价",
                {"rc": r["rc"], "stderr_excerpt": r["stderr"][:120],
                 "stdout_excerpt": r["stdout"][:120], "expect_rc_ok": r["expect_rc_ok"],
                 "expect_file_ok": r["expect_file_ok"], "file_exists": r["file_exists"]})


def case_5_3():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "root_new_no_flag"
        root.mkdir()
        ledger = "newledger.jsonl"
        # 不创建文件
        r = run(root, ledger, {"k": "case5.3", "v": "v3"}, allow_create=False, expect_rc=2,
                expect_stderr_substring="refuse to create new ledger file",
                expect_file_created=False)
        return ("5.3", "不存在账本 + 不带 --allow-create", "反路径 rc=2 + stderr 命中 + 文件未被创建",
                {"rc": r["rc"], "stderr_excerpt": r["stderr"][:200],
                 "stdout_excerpt": r["stdout"][:120], "expect_rc_ok": r["expect_rc_ok"],
                 "expect_stderr_ok": r["expect_stderr_ok"], "expect_file_ok": r["expect_file_ok"],
                 "file_exists": r["file_exists"]})


def case_5_4():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "root_new_with_flag"
        root.mkdir()
        ledger = "newledger.jsonl"
        r = run(root, ledger, {"k": "case5.4", "v": "v4"}, allow_create=True, expect_rc=0,
                expect_file_created=True)
        return ("5.4", "不存在账本 + 带 --allow-create", "反证 标志确实作用,仅显式 opt-in 才豁免",
                {"rc": r["rc"], "stderr_excerpt": r["stderr"][:120],
                 "stdout_excerpt": r["stdout"][:120], "expect_rc_ok": r["expect_rc_ok"],
                 "expect_file_ok": r["expect_file_ok"], "file_exists": r["file_exists"]})


def main():
    results = [case_5_1(), case_5_2(), case_5_3(), case_5_4()]
    all_ok = True
    out = {"helper": str(HELPER),
           "helper_sha256": subprocess.run(
               ["python", "-c",
                f"import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())",
                str(HELPER)],
               capture_output=True, text=True).stdout.strip(),
           "cases": []}
    for case_id, title, expect, detail in results:
        ok = all(detail[k] for k in detail if k.endswith("_ok"))
        out["cases"].append({"case": case_id, "title": title, "expect": expect,
                             "ok": ok, "detail": detail})
        all_ok = all_ok and ok
    out["all_ok"] = all_ok
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
