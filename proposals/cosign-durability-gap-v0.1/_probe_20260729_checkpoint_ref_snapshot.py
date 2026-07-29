#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读:把 refs/codex/turn-diffs/checkpoints/** 的**全保真**现状打成 JSON。

存在的理由(写给下一个读它的人):
2026-07-29 我在 EVIDENCE_REF_CLASS_REACHABILITY.md 里把 checkpoint ref 路径记成了
`refs/codex/turn-diffs/checkpoints/…/1785300238918/94248885-…` —— 中段两级哈希被我省成了
一个省略号。几小时后那条 ref 被删了,而要判"它是被同桶的新 ref 顶掉的、还是整桶被摘掉的",
需要的恰恰是被我省掉的那两级。省略号的代价就是这次判不下来。

所以这支探针只做一件事:把**下次要用到的每一个字节**都记下来——ref 全路径(不省略)、
目标对象 oid 与类型、路径里编码的毫秒戳解码值,以及 .git/refs/codex 子树里每个目录/文件的
mtime。目录 mtime 是可用证人,依据是同日在临时仓的实测(见 EVIDENCE_CHECKPOINT_REF_RETENTION.md
第三节):git 删除深层松散 ref 会向上摘掉变空的祖先目录,并把**第一个仍非空的祖先**的 mtime
顶到删除时刻。

零权威、零写入:不 update-ref、不 gc、不碰任何 ref。输出拿去和下一次的输出逐字 diff。
"""
import datetime
import json
import os
import subprocess
import sys

JST = datetime.timezone(datetime.timedelta(hours=9))
REF_GLOB = "refs/codex/turn-diffs/checkpoints/**"


def run(args, cwd):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("命令失败 %s: %s" % (args, p.stderr.strip()))
    return p.stdout


def decode_ms(seg):
    """路径里那一级若是毫秒戳就解码,不是就如实返回 None。"""
    if not seg.isdigit():
        return None
    try:
        return datetime.datetime.fromtimestamp(int(seg) / 1000, JST).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def main():
    repo = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    git_dir = run(["git", "rev-parse", "--absolute-git-dir"], repo).strip()

    refs = []
    fmt = "%(objectname)\t%(objecttype)\t%(refname)"
    for line in run(["git", "for-each-ref", REF_GLOB, "--format=" + fmt], repo).splitlines():
        if not line.strip():
            continue
        oid, otype, refname = line.split("\t", 2)
        segs = refname.split("/")
        # refs/codex/turn-diffs/checkpoints/<h1>/<h2>/<stamp>/<uuid>
        refs.append({
            "refname": refname,                     # 全路径,不得省略
            "object": oid,
            "object_type": otype,
            "bucket_h1": segs[4] if len(segs) > 4 else None,
            "bucket_h2": segs[5] if len(segs) > 5 else None,
            "stamp_raw": segs[6] if len(segs) > 6 else None,
            "stamp_decoded_jst": decode_ms(segs[6]) if len(segs) > 6 else None,
            "leaf": segs[7] if len(segs) > 7 else None,
        })
    refs.sort(key=lambda r: r["refname"])

    tree_root = os.path.join(git_dir, "refs", "codex")
    fs = []
    if os.path.isdir(tree_root):
        for dirpath, dirnames, filenames in os.walk(tree_root):
            dirnames.sort()
            for name in [""] + sorted(filenames):
                path = os.path.join(dirpath, name) if name else dirpath
                st = os.stat(path)
                fs.append({
                    "kind": "file" if name else "dir",
                    "path": os.path.relpath(path, git_dir).replace("\\", "/"),
                    "mtime_jst": datetime.datetime.fromtimestamp(st.st_mtime, JST).isoformat(),
                })
    fs.sort(key=lambda e: (e["path"], e["kind"]))

    print(json.dumps({
        "probe": "checkpoint_ref_snapshot",
        "authority": "none_read_only_snapshot_for_byte_diff",
        "git_dir": git_dir,
        "git_version": run(["git", "--version"], repo).strip(),
        # logallrefupdates=true 仍不给 refs/codex/** 建 reflog(只覆盖 heads/remotes/notes/HEAD),
        # 记下来是为了让下一个人别再去翻 .git/logs 找这条线的历史。
        "core_logallrefupdates": run(
            ["git", "config", "--get", "core.logallrefupdates"], repo).strip() or None,
        "reflog_dir_exists": os.path.isdir(os.path.join(git_dir, "logs", "refs", "codex")),
        "ref_count": len(refs),
        "bucket_h1_count": len({r["bucket_h1"] for r in refs}),
        "refs": refs,
        "fs_mtimes": fs,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
