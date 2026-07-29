#!/usr/bin/env python3
"""只读探针:把"工作区里此刻生效的字节,有没有任何分支持有"从**单点问询**扩成**全体普查**。

为什么要有这个东西
------------------
`_probe_20260729_ref_class_reachability.py` 回答"这一串字节挂在谁身上",做法是对每一条
ref 各跑一次 `git rev-list --objects`——单次查询 1.2 秒可以接受,但那是 O(refs × 仓库)
**每个文件一遍**。要问"这台机器上此刻有多少份生效字节没有分支持有",按那个形状跑一遍
就是几十次全仓遍历。

本探针把遍历做**一次**:先把 checked-out branch 可达的 blob oid 收成一个集合,再把
`--all` 可达的收成第二个集合,然后所有待查文件只做集合成员判定。O(仓库 + 文件数)。

口径(三条,都是刻意选的,别读过头)
----------------------------------
1. **用 filtered oid,不用 raw sha256。** 本仓 core.autocrlf=true,git 存的是过滤后
   (LF)的字节。问"这份内容在不在 git 里"必须问 `git hash-object`(带 clean filter)
   的那颗 oid;拿工作区 raw 字节的 sha256 去问,CRLF 文件会一律假报"不在",那是仪器
   的错不是仓库的病。副产物 `filter_is_identity` 如实分列:false 表示 raw 字节本身
   确实不在对象库里,只有其 LF 规范形在——**这是可核性的真差异,不是记账细节**。
2. **untracked ≠ 病。** 一份刚写出来的临时脚本本来就不该在分支上。故本探针只**分类**
   不判罪:tracked_modified(曾被纳入治理、当前生效字节已偏离分支)与 untracked 分开
   计数,承重与否由读者按类别自己判。
3. **checkpoint-only 单列。** 若一份内容唯一的持有者是 `refs/codex/turn-diffs/**`
   一类工具私有 ref,那不是"在 git 里",是"在一条已实测会被同桶下一次快照顶掉的
   临时 ref 上"(证据 EVIDENCE_CHECKPOINT_REF_RETENTION.md)。

只读保证:只调 git 的读命令(symbolic-ref / rev-list / for-each-ref / hash-object /
ls-files / diff / cat-file),`hash-object` **不带 -w**,不写对象、不动 ref、不碰 index。
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys


def git(*args, repo=".", binary=False):
    p = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        **({} if binary else dict(text=True, encoding="utf-8", errors="replace")),
    )
    return p.returncode, p.stdout


def oid_set(repo, *revargs):
    """收一趟 rev-list --objects 的 oid 集合。行首 40 位 hex 是 oid,其后是路径。"""
    _, out = git("rev-list", "--objects", *revargs, repo=repo)
    s = set()
    for line in out.splitlines():
        if len(line) >= 40:
            s.add(line[:40])
    return s


def classify_ref(refname, checked_out):
    if checked_out is not None and refname == checked_out:
        return "checked_out_branch"
    if refname.startswith("refs/heads/"):
        return "other_local_branch"
    if refname.startswith("refs/remotes/"):
        return "remote"
    if refname.startswith("refs/tags/"):
        return "tag"
    if refname.startswith("refs/codex/"):
        return "codex_private_checkpoint"
    return "other_ref"


def bucket(path):
    """按承重类别粗分。分类是判断,不是事实——读者可以不同意,故原始 path 一并输出。"""
    p = path.replace("\\", "/")
    base = os.path.basename(p)
    if base.startswith("_append_") or base.startswith("_post_") or base.startswith("_emit_"):
        return "throwaway_appender"
    if p.startswith("deployments/"):
        return "deployment_artifact"
    if p.endswith(".jsonl") or p.endswith(".json"):
        return "ledger_or_state"
    if base.startswith("_probe_") or base.startswith("_audit_"):
        return "probe"
    if p.endswith(".py"):
        return "code"
    if p.endswith(".md") or p.endswith(".txt") or p.endswith(".tsv"):
        return "document"
    return "other"


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--repo", default=".")
    ap.add_argument("--include-untracked", action="store_true")
    ap.add_argument("--check-filter-identity", action="store_true",
                    help="对每份内容额外比对 raw 字节与 blob 字节是否逐字相等(多一次 cat-file)")
    args = ap.parse_args()
    repo = args.repo

    code, out = git("symbolic-ref", "-q", "HEAD", repo=repo)
    checked_out = out.strip() if code == 0 and out.strip() else None

    on_branch = oid_set(repo, checked_out) if checked_out else set()
    anywhere = oid_set(repo, "--all")

    # 只对"分支够不着"的那些做逐 ref 归属,省掉全量 ref × 全量文件
    _, refs_out = git("for-each-ref", "--format=%(refname)", repo=repo)
    all_refs = [r for r in refs_out.splitlines() if r.strip()]
    per_ref_cache = {}

    def holders(oid):
        found = []
        for refname in all_refs:
            if refname not in per_ref_cache:
                per_ref_cache[refname] = oid_set(repo, refname)
            if oid in per_ref_cache[refname]:
                found.append({"ref": refname, "class": classify_ref(refname, checked_out)})
        return found

    targets = []
    _, mod = git("diff", "--name-only", "HEAD", repo=repo)
    for p in mod.splitlines():
        if p.strip():
            targets.append((p.strip(), "tracked_modified"))
    if args.include_untracked:
        _, unt = git("ls-files", "--others", "--exclude-standard", repo=repo)
        for p in unt.splitlines():
            if p.strip():
                targets.append((p.strip(), "untracked"))

    rows = []
    for path, tracking in targets:
        full = os.path.join(repo, path)
        if not os.path.isfile(full):
            rows.append({"path": path, "tracking": tracking, "verdict": "GONE__not_a_regular_file"})
            continue
        code, oid_out = git("hash-object", "--", path, repo=repo)
        if code != 0:
            rows.append({"path": path, "tracking": tracking, "verdict": "HASH_OBJECT_FAILED"})
            continue
        oid = oid_out.strip()
        row = {
            "path": path,
            "tracking": tracking,
            "bucket": bucket(path),
            "worktree_blob_oid": oid,
            "on_checked_out_branch": oid in on_branch,
            "in_object_db_anywhere": oid in anywhere,
        }
        if args.check_filter_identity:
            with open(full, "rb") as fh:
                raw = fh.read()
            p = subprocess.run(["git", "-C", repo, "cat-file", "-p", oid], capture_output=True)
            row["filter_is_identity"] = (
                p.returncode == 0
                and hashlib.sha256(p.stdout).hexdigest() == hashlib.sha256(raw).hexdigest()
            )
        # `rev-list --objects --all` 只走 ref;一颗存在但不可达的松散对象在它眼里等于不存在。
        # 第一版把这两种都打成 ABSENT,实测当场翻车:peer-chat.jsonl 的当前内容被判 ABSENT,
        # 而 `git cat-file -e` 说它在——它是上一条 checkpoint ref 被顶掉后留下的孤儿。
        # 「不在对象库」与「在对象库但没人够得着」后果完全不同(后者有约两周 gc 宽限,凭 oid
        # 还取得回),必须分列。
        code_e, _ = git("cat-file", "-e", oid, repo=repo)
        row["object_present_in_db"] = (code_e == 0)
        if row["on_checked_out_branch"]:
            row["verdict"] = "durable_on_checked_out_branch"
        elif row["in_object_db_anywhere"]:
            hs = holders(oid)
            row["reaching_refs"] = hs
            kinds = {h["class"] for h in hs}
            if kinds and kinds <= {"codex_private_checkpoint"}:
                row["verdict"] = "CHECKPOINT_REF_ONLY__ephemeral_holder"
            elif hs:
                row["verdict"] = "REACHABLE_BUT_NOT_ON_CHECKED_OUT_BRANCH"
            else:
                row["verdict"] = "IN_ALL_BUT_NO_REF__reflog_or_index_only"
        elif row["object_present_in_db"]:
            row["verdict"] = "PRESENT_BUT_UNREACHABLE__orphan_object_no_ref_holds_it"
        else:
            row["verdict"] = "ABSENT__these_bytes_were_never_hashed_into_the_object_db"
        rows.append(row)

    summary = {}
    for r in rows:
        key = (r.get("tracking"), r.get("bucket"), r.get("verdict"))
        summary[" | ".join(str(k) for k in key)] = summary.get(
            " | ".join(str(k) for k in key), 0
        ) + 1

    print(json.dumps({
        "checked_out_branch_ref": checked_out,
        "detached_head": checked_out is None,
        "blobs_reachable_from_checked_out_branch": len(on_branch),
        "blobs_reachable_from_all_refs": len(anywhere),
        "n_targets": len(rows),
        "summary_by_tracking_bucket_verdict": dict(sorted(summary.items())),
        "rows": rows,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
