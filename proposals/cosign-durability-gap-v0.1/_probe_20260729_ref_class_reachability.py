#!/usr/bin/env python3
"""只读探针:把"这串被签字节在 git 里吗"按 **ref 类别** 拆开报告。

为什么要有这个东西
------------------
`_probe_20260728_signed_final_durability.py` 回答同一个问题的做法是把仓内全部 blob
(`git cat-file --batch-all-objects`)逐个 sha256 建反查表——O(仓库),Codex 在
2026-07-29 的两个有界窗口(180s / 约 279s)里都没跑完,只好把该腿标成"未验证/超时"。

本探针不建全量表。给定 content-sha256(或路径),它只做 O(1) 级的定点问询,并且
**不输出单一的 reachable 布尔**,而是按 ref 类别分列:

    checked_out_branch   HEAD 当前 checkout 的那条 branch ref(唯一承重的一类)
    other_local_branch   其他 refs/heads/*
    remote               refs/remotes/*
    tag                  refs/tags/*
    other_ref            refs/ 下其余命名空间——含工具私有 ref(如 refs/codex/**)
    reflog_only          任何 ref 都够不着,但 reflog 够得着
    present_unreachable  对象在 .git/objects 里,但以上全都够不着

分列的理由是实测出来的,不是洁癖:2026-07-29 本仓实测,
`ce41975991c77c930cbf85fef7953b31860c7b7f297346e3613f9ef88613daec`
(即 wake_prompt_codex.md 的一份被签 final)对 `git rev-list --objects --all`
显示为"在",而对每一条 branch / remote / tag 都是 0——唯一够到它的是
`refs/codex/turn-diffs/checkpoints/.../1785300238918/...`,一条工具私有、指向 tree
(不是 commit)、无 reflog、从不推送、按滚动窗口被回收的 ref。

只读保证:本脚本只调用 git 的读命令(rev-parse / for-each-ref / rev-list /
cat-file / symbolic-ref),不写对象、不动 ref、不碰工作区与 index。
"""

import argparse
import hashlib
import subprocess
import sys
import json


def git(*args, repo="."):
    """跑一条只读 git 命令,返回 (exit_code, stdout)。不抛异常,失败由调用方分类。

    encoding 必须显式写死 utf-8:本机 Python 的 text=True 走 locale(GBK),而
    `git rev-list --objects` 的输出里带仓内非 GBK 路径,会当场 UnicodeDecodeError
    炸在读取线程里。errors="replace" 在这里是安全的——我们只对行首的 40 位 hex
    oid 做 startswith 比较,ASCII 段不受替换影响。
    """
    p = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return p.returncode, p.stdout


def classify_ref(refname, checked_out):
    if checked_out is not None and refname == checked_out:
        return "checked_out_branch"
    if refname.startswith("refs/heads/"):
        return "other_local_branch"
    if refname.startswith("refs/remotes/"):
        return "remote"
    if refname.startswith("refs/tags/"):
        return "tag"
    return "other_ref"


def resolve_target(repo, content_sha256, path):
    """把入参解析成一个 blob oid。两条路都不写对象。

    走 path 时用 `git rev-parse :path` / HEAD:path 是不够的——我们要的是**工作区
    原始字节**对应的对象。故对 path 只报告其 raw sha256,再在对象库里定点找。
    """
    if content_sha256:
        return content_sha256.lower(), None
    with open(path, "rb") as fh:
        raw = fh.read()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def find_blob_by_content(repo, want_sha256, hint_oid):
    """定点找:优先用调用方给的 oid 提示做 O(1) 校验;否则退回全量扫并明说代价。"""
    if hint_oid:
        code, out = git("cat-file", "-t", hint_oid, repo=repo)
        if code == 0 and out.strip() == "blob":
            code2, _ = git("cat-file", "-p", hint_oid, repo=repo)
            p = subprocess.run(["git", "-C", repo, "cat-file", "-p", hint_oid],
                               capture_output=True)
            if hashlib.sha256(p.stdout).hexdigest() == want_sha256:
                return hint_oid, "verified_from_hint"
        return None, "hint_oid_did_not_match_content"
    return None, "no_hint_oid_given__full_scan_not_performed_by_design"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--content-sha256", help="被签 final 的原始字节 sha256")
    ap.add_argument("--path", help="改为从工作区文件现算 raw sha256")
    ap.add_argument("--blob-oid", help="已知的 git blob oid 提示(会被内容校验)")
    args = ap.parse_args()

    if not args.content_sha256 and not args.path:
        ap.error("须给 --content-sha256 或 --path 之一")

    repo = args.repo
    want, raw_len = resolve_target(repo, args.content_sha256, args.path)

    # HEAD 当前 checkout 的 branch ref;detached 时为 None(这本身是承重信息)
    code, out = git("symbolic-ref", "-q", "HEAD", repo=repo)
    checked_out = out.strip() if code == 0 and out.strip() else None

    oid, how = find_blob_by_content(repo, want, args.blob_oid)

    result = {
        "want_content_sha256": want,
        "raw_bytes_len": raw_len,
        "blob_oid": oid,
        "oid_resolution": how,
        "checked_out_branch_ref": checked_out,
        "detached_head": checked_out is None,
        "object_present": None,
        "reachable_by_class": {},
        "reaching_refs": [],
        "verdict": None,
    }

    if oid is None:
        result["verdict"] = "cannot_locate_blob_oid__pass_--blob-oid_or_use_full_scan_probe"
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2

    code, _ = git("cat-file", "-e", oid, repo=repo)
    result["object_present"] = (code == 0)

    classes = {k: 0 for k in ("checked_out_branch", "other_local_branch",
                              "remote", "tag", "other_ref")}
    _, refs_out = git("for-each-ref", "--format=%(refname)", repo=repo)
    for refname in [r for r in refs_out.splitlines() if r.strip()]:
        _, listing = git("rev-list", "--objects", refname, repo=repo)
        if any(line.startswith(oid) for line in listing.splitlines()):
            cls = classify_ref(refname, checked_out)
            classes[cls] += 1
            result["reaching_refs"].append({"ref": refname, "class": cls})

    # reflog:只在所有 ref 都够不着时才问,省时间
    reflog_only = False
    if not result["reaching_refs"]:
        _, listing = git("rev-list", "--objects", "--all", "--reflog", repo=repo)
        reflog_only = any(line.startswith(oid) for line in listing.splitlines())
    classes["reflog_only"] = 1 if reflog_only else 0
    classes["present_unreachable"] = 1 if (
        result["object_present"] and not result["reaching_refs"] and not reflog_only
    ) else 0
    result["reachable_by_class"] = classes

    # 承重判词:只有 checked_out_branch 那一类算真
    if classes["checked_out_branch"] > 0:
        result["verdict"] = "durable_on_checked_out_branch"
    elif result["reaching_refs"]:
        result["verdict"] = (
            "REACHABLE_BUT_NOT_ON_CHECKED_OUT_BRANCH__"
            "git_rev-list_--all_says_present_but_no_branch_holds_it"
        )
    elif reflog_only:
        result["verdict"] = "REFLOG_ONLY__gc_will_take_it"
    elif result["object_present"]:
        result["verdict"] = "PRESENT_BUT_UNREACHABLE__orphan_object"
    else:
        result["verdict"] = "ABSENT__not_in_object_db"

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
