#!/usr/bin/env python3
"""前像→后像绑定 v0.6 的机检器（CONVENTION §5）。

三个模式：
  selftest  —— 不改任何东西，连取两次见证快照，报 witness-digest 是否稳定。
               用途：证明 §5.3 的事务局部守恒判据在本仓当前状态下**可满足**（v0.1 的全仓 clean 判据不可满足）。
  preflight —— 校验 base + 不变量，捕获 target 原始字节到 sidecar，落 witness-digest 到状态文件。
  postcheck —— 校验 final；重取见证快照比对 digest；以 sidecar 原始字节为前像做行级增删计数
               与改动章节归属，与 --expect-added / --expect-deleted / --changes-confined-to 逐项比对。
               三组判据全过才 ok:true。

字节口径固定为工作区原始字节流（CONVENTION §3）：不做编码转换、不归一化换行、不动 BOM、末尾换行计入。

witness-digest 规范（CONVENTION §5.4）——**三条腿，缺一条就是自称覆盖而实际没覆盖**：
  S 腿（状态）：全部非 target 条目，按路径原始字节升序，每条拼
      b"S" + \\t + XY + \\t + 路径原始字节 + \\t + 工作区字节 sha256（或 ABSENT）
      + \\t + index 条目（各 stage 的 `mode,oid,stage` 按字节升序以 `;` 连接，不在 index 记 ABSENT）+ \\n
  R 腿（引用）：`git for-each-ref` **列出的**每条引用，按整行字节升序，每条拼
      b"R" + \\t + refname + \\t + objectname + \\t + 符号目标（direct ref 记 DIRECT）+ \\n
  H 腿（HEAD）：一行 b"H" + \\t + HEAD 符号名（游离记 DETACHED）+ \\t + HEAD oid（未出生记 UNBORN）+ \\n
  三段按 S→R→H 顺序连接，取 SHA-256。

  index 腿是 v0.5 新增（Codex 2026-07-26 07:12:33 拒签所指）：v0.4 只记 XY + 工作区字节，
  于是一条 `MM` 路径的 index blob 可以被换掉而 XY 与工作区字节都不变 → digest 不变 → 放行。
  R/H 两腿是 v0.5 新增（本轮自测撞出）：删分支 / 移 HEAD 在 v0.4 下同样静默放行。
  R 腿的符号目标字段是 v0.6 新增（Codex 2026-07-26 07:40:43 拒签所指）：只记 objectname 时，
  非 HEAD 的 symbolic ref 可以在两个同 OID 的引用之间改指而 digest 一字不变。
  **覆盖面到此为止**，其外（被忽略文件、object database、.git/config 与 hooks、文件系统元数据、
  仓外一切、子模块内部）**明文不在守恒判据内**——见 CONVENTION §5.3.f，那里逐条写明并附实测。

行级差量规范（CONVENTION §5.5）：前像取 sidecar 原始字节（须重算 == 已签 base），后像取落盘原始字节；
两侧按 bytes.splitlines(keepends=True) 切行；用**规范 LCS 动态规划**（不是 difflib）算，
增行数 = len(后像) - LCS 长度，删行数 = len(前像) - LCS 长度；章节归属取**全体最小对齐之并**。
**不调用 git diff**：口径见 §5.5.c。
"""

import argparse
import array
import hashlib
import json
import os
import re
import subprocess
import sys

ABSENT = b"ABSENT"

# 覆盖面随裁决一起印出来（v0.5）。理由：这一整条线上反复复发的病，形状都是
# "可核对象没覆盖它自称覆盖的量"。回执里只有一个 `non_target_conserved:true`，
# 读者会把它读成"什么都没动"；把边界跟结论印在同一个 JSON 里，泛称就没有落脚处。
WITNESS_COVERAGE = {
    "covered": [
        "status(-z -uall) 列出的每条非 target 路径：XY 两位状态字母",
        "同上每条路径的工作区原始字节 sha256（不存在记 ABSENT）",
        "同上每条路径的 index 条目：各 stage 的 mode,oid,stage（不在 index 记 ABSENT）",
        "for-each-ref **列出的**每条引用（refname → objectname）",
        "同上每条引用的符号目标（symbolic ref 记目标 refname，direct ref 记哨兵 DIRECT）",
        "HEAD 的符号名与 oid（游离/未出生有哨兵值）",
    ],
    "not_covered": [
        "被 .gitignore 命中的路径（不进 -uall；无界且高频抖动，见 CONVENTION §5.3.f）",
        "refs/ 之外的伪引用（ORIG_HEAD/FETCH_HEAD/MERGE_HEAD 等；HEAD 除外，它由 H 腿单钉）"
        "——实测 for-each-ref 不列出它们",
        "reflog（.git/logs/），以及 for-each-ref 不列出的悬空 symbolic ref"
        "——实测：symbolic ref 指向不存在的 ref 时该条整行不出现",
        "object database 内部：gc/repack/prune、不可达对象",
        ".git/ 下的配置与 hooks（config、hooks、worktrees 注册）",
        "文件系统元数据：mtime、权限/ACL、扩展属性（index mode 位之外）",
        "仓库根之外的一切（执行期制品按 §5.3.d 恰恰住在那里）",
        "子模块内部状态（只见 gitlink oid）",
    ],
}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_raw(path_bytes):
    """读工作区原始字节；路径不存在返回 None。"""
    try:
        with open(os.fsdecode(path_bytes), "rb") as fh:
            return fh.read()
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError):
        return None


def porcelain_entries(repo_root):
    """解析 `git status --porcelain -z -uall`。

    -z 格式下 R/C 条目占两个 NUL 字段：'XY new' 后紧跟 'old'。必须按状态字母决定是否多吃一个字段，
    否则 old path 会被当成一条独立记录（XY 取到路径头两个字节），守恒判据会静默错位。
    """
    out = subprocess.run(
        ["git", "status", "--porcelain", "-z", "-uall"],
        cwd=repo_root, capture_output=True, check=True,
    ).stdout
    fields = out.split(b"\x00")
    if fields and fields[-1] == b"":
        fields.pop()

    entries = []
    i = 0
    while i < len(fields):
        f = fields[i]
        xy, path = f[:2], f[3:]
        entries.append((xy, path))
        i += 1
        if b"R" in xy or b"C" in xy:  # 重命名/复制：下一字段是来源路径
            if i < len(fields):
                entries.append((b"<-", fields[i]))
                i += 1
    return entries


def index_entries(repo_root):
    """路径 → 该路径在 **index** 中的规范条目（各 stage 的 `mode,oid,stage`，按字节升序以 `;` 连接）。

    v0.5 新增。缺了它，守恒判据就只守工作树而自称守住"非 target 差量"：
    一条已处于 `MM` 的路径，把 index blob 换掉再把工作树字节原样恢复，XY 仍是 `MM`、
    工作区 sha256 仍相同 → v0.4 的 digest 一字不变、`non_target_conserved:true` 放行。
    这是 Codex 2026-07-26 07:12:33 给出的最小复现，本轮独立复跑坐实（digest 前后同为 92c497f7…）。
    判据本来就主动读 XY 的 index 腿，却不钉 index 的实际内容——那正是"可核对象没覆盖自称覆盖的量"。

    `-z` 下路径不做引号转义；`mode oid stage` 与路径之间恰一个 TAB，故按**首个** TAB 切分
    （路径自身可以含 TAB）。冲突态一条路径有多个 stage，全收进来再排序，不折叠成"取 stage 0"。
    """
    out = subprocess.run(
        ["git", "ls-files", "-s", "-z", "--full-name"],
        cwd=repo_root, capture_output=True, check=True,
    ).stdout
    table = {}
    for field in out.split(b"\x00"):
        if not field:
            continue
        meta, _, path = field.partition(b"\t")
        mode, oid, stage = meta.split()
        table.setdefault(path, []).append(mode + b"," + oid + b"," + stage)
    return {p: b";".join(sorted(v)) for p, v in table.items()}


def ref_lines(repo_root):
    """R 腿 + H 腿：`for-each-ref` 列出的每条引用，与 HEAD。

    "列出的"是承重限定，不是文风：实测 `for-each-ref` 不列出 `refs/` 外的伪引用（ORIG_HEAD 等），
    也不列出悬空 symbolic ref。这两类明文排除在 CONVENTION §5.3.f.2。

    v0.5 新增，本轮自测撞出（非 Codex 所提，与 index 腿同病）：v0.4 下在事务中间
    `git branch -D` 掉一个分支，`git status` 一字不变 → digest 不变 → `ok:true` 放行。
    引用是有界且廉价的（一次 for-each-ref），而毁掉一个引用是难以撤销的附带损害，
    故纳入覆盖面，而不是像被忽略文件那样明文排除。

    v0.6 补 `%(symref)`（Codex 2026-07-26 07:40:43 拒签所指，本轮独立复跑坐实）：
    v0.5 只记 refname → objectname，于是两个指向同一 commit 的引用之间，
    一个**非 HEAD 的 symbolic ref** 可以被改指而 objectname 一字不变 → digest 不变 → 放行。
    H 腿单独钉的是 HEAD 自己的符号名，管不到 `refs/remotes/origin/HEAD` 这一类。
    direct ref 的 `%(symref)` 实测是**空串**，故记显式哨兵 `DIRECT`：空字段读起来像
    "这一位没记"，而不是"记了，它不是符号引用"——这条线上要焊死的正是这种含混。
    """
    out = subprocess.run(
        ["git", "for-each-ref", "--format=%(objectname)%09%(refname)%09%(symref)"],
        cwd=repo_root, capture_output=True, check=True,
    ).stdout
    refs = []
    for row in out.split(b"\n"):
        if not row:
            continue
        # refname 不含 ASCII 控制字符（git-check-ref-format），symref 也是 refname，
        # 故 TAB 分隔无歧义；固定切 3 段，字段数不对就是格式假设塌了，fail-closed。
        parts = row.split(b"\t")
        if len(parts) != 3:
            # 裁决一律走 stdout（v0.3 教训，见 require_outside_worktree 里的注释）
            print(json.dumps(
                {"mode": "reject", "ok": False,
                 "reason": "for-each-ref 输出字段数非 3，R 腿格式假设不成立",
                 "row": row.decode("utf-8", "replace")},
                ensure_ascii=False, indent=2))
            raise SystemExit(1)
        oid, name, symref = parts
        refs.append(b"R\t" + name + b"\t" + oid + b"\t" + (symref or b"DIRECT") + b"\n")
    refs.sort()

    sym = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"],
                         cwd=repo_root, capture_output=True)
    head_ref = sym.stdout.strip() or b"DETACHED"
    rp = subprocess.run(["git", "rev-parse", "-q", "--verify", "HEAD"],
                        cwd=repo_root, capture_output=True)
    head_oid = rp.stdout.strip() or b"UNBORN"
    refs.append(b"H\t" + head_ref + b"\t" + head_oid + b"\n")
    return refs


def witness(repo_root, target_bytes):
    """返回 (digest, 明细行列表)。明细留档为执行制品，回执只记 digest。

    三条腿见模块 docstring 与 CONVENTION §5.4。覆盖面的**边界**同样是规范的一部分：
    见证覆盖不到的东西写在 CONVENTION §5.3.f，判据不得自称守住它们。
    """
    index = index_entries(repo_root)
    lines = []
    for xy, path in sorted(porcelain_entries(repo_root), key=lambda e: e[1]):
        if path == target_bytes:
            continue  # target 自身走 base→final 那条独立轨道
        raw = read_raw(os.path.join(os.fsencode(repo_root), path))
        fp = ABSENT if raw is None else sha256_bytes(raw).encode("ascii")
        idx = index.get(path, ABSENT)
        lines.append(b"S\t" + xy + b"\t" + path + b"\t" + fp + b"\t" + idx + b"\n")
    lines.extend(ref_lines(repo_root))
    blob = b"".join(lines)
    return sha256_bytes(blob), lines


def dump_lines(path, lines):
    with open(path, "wb") as fh:
        fh.write(b"".join(lines))


def require_outside_worktree(repo_root, *paths):
    """制品若落在工作树内，它自己就会成为一条新的非 target 条目，把守恒判据变成不可满足。

    这是 v0.1 那条『全仓 clean』之病的同类复发（2026-07-26 实测抓到），故此处 fail-closed：
    执行期制品一律写到工作树之外，通过后再归档入仓。不给『加个例外名单』的口子——
    例外名单可以被执行者悄悄加宽，那正是守恒要防的。
    """
    root = os.path.realpath(repo_root)
    for p in paths:
        rp = os.path.realpath(p)
        if rp == root or rp.startswith(root + os.sep):
            # 判据结论一律走 stdout：raise SystemExit(json) 会把这一条印到 stderr，
            # 于是唯一一条 fail-closed 拒绝跟其余所有裁决不在同一个流上，最容易被回执漏掉的
            # 恰是它。2026-07-26 由 test_verify_binding.py 用例 [6] 实测抓到。
            print(json.dumps(
                {"mode": "reject", "ok": False,
                 "reason": "执行期制品不得落在工作树内（否则守恒判据自败）",
                 "path": p, "resolved": rp, "worktree": root},
                ensure_ascii=False, indent=2))
            raise SystemExit(1)


ATX_HEADING = re.compile(rb"^#{1,6} ")
NO_SECTION = "<无标题前言>"


def section_labels(lines, indices):
    """把行号映射到它所属的最近上文 ATX 标题（同一文件内），返回去重后的标签列表。

    章节归属必须在**该行所在的那一侧**求值：增行在后像里求、删行在前像里求。
    在错的一侧求会把"插到 §4"读成"插在 §3"——那正是本检查要抓的错。
    """
    labels = []
    for idx in indices:
        label = NO_SECTION
        for j in range(idx, -1, -1):
            if ATX_HEADING.match(lines[j]):
                label = lines[j].rstrip(b"\r\n").decode("utf-8", "replace")
                break
        if label not in labels:
            labels.append(label)
    return labels


MAX_DELTA_CELLS = 2_000_000  # (n+1)*(m+1) 上限；超出即 fail-closed，不静默降级到近似算法


def lcs_tables(a, b):
    """前缀 / 后缀 LCS 长度表（扁平 array，省内存）。

    pre[i][j] = LCS(a[:i], b[:j])，suf[i][j] = LCS(a[i:], b[j:])。
    """
    n, m = len(a), len(b)
    w = m + 1
    pre = array.array("i", [0]) * ((n + 1) * w)
    for i in range(1, n + 1):
        ai = a[i - 1]
        row, prv = i * w, (i - 1) * w
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                pre[row + j] = pre[prv + j - 1] + 1
            else:
                x, y = pre[prv + j], pre[row + j - 1]
                pre[row + j] = x if x >= y else y
    w2 = m + 2
    suf = array.array("i", [0]) * ((n + 2) * w2)
    for i in range(n - 1, -1, -1):
        ai = a[i]
        row, nxt = i * w2, (i + 1) * w2
        for j in range(m - 1, -1, -1):
            if ai == b[j]:
                suf[row + j] = suf[nxt + j + 1] + 1
            else:
                x, y = suf[nxt + j], suf[row + j + 1]
                suf[row + j] = x if x >= y else y
    return pre, w, suf, w2


def line_delta(base_raw, final_raw):
    """行级增删计数 + 改动章节归属（CONVENTION §5.5）。

    **口径是规范 LCS 动态规划，不是 difflib。** v0.3 用 `difflib.SequenceMatcher(autojunk=False)`
    并声称它给出"LCS 最小对齐"——Codex 2026-07-26 06:44:57 的反例证伪，本轮独立复算坐实：
    前像 `a,b,a` → 后像 `b,c,a`，SequenceMatcher 只匹配首尾那个 `a`（matching size=1），
    报 2 增 2 删；真 LCS 是 `b,a`（长度 2），最小为 1 增 1 删。SequenceMatcher 是
    Ratcliff-Obershelp 的"最长连续匹配块再递归两侧"启发式，根本不是 LCS 算法，autojunk 与此无关。

    计数：增行数 = len(后像) - LCS，删行数 = len(前像) - LCS。**LCS 长度唯一**，故计数与实现无关。

    归属：**最小对齐不唯一**（LCS 长度唯一 ≠ 对齐唯一，如 `ab` → `ba` 有两个），
    随便挑一个对齐，章节归属就随那个任意选择而变。故这里不挑对齐，取**全体最小对齐之并**：
    前像第 i 行算"被删"，当且仅当**存在**一个最小对齐让它落空，即
    max_j( pre[i][j] + suf[i+1][j] ) == LCS；后像第 j 行算"被增"同理。
    这既免了任意 tie-break，又是保守的——歧义时报的是超集，判据只会更严，不会更松。
    `attribution_ambiguous` 显式标出"可能被动的行数 > 最小计数"这一情形，不让超集悄悄冒充精确值。
    """
    base_lines = base_raw.splitlines(keepends=True) if base_raw else []
    final_lines = final_raw.splitlines(keepends=True) if final_raw else []
    n, m = len(base_lines), len(final_lines)
    common = {
        "base_line_count": n,
        "final_line_count": m,
    }
    if (n + 1) * (m + 1) > MAX_DELTA_CELLS:
        # 不退到启发式近似：本惯例的权威口径是规范 LCS，算不动就说算不动。
        return dict(common, delta_unavailable=(
            "前后像行数乘积 %d 超出 MAX_DELTA_CELLS=%d → 拒绝出差量（不降级到近似算法）"
            % ((n + 1) * (m + 1), MAX_DELTA_CELLS)))
    pre, w, suf, w2 = lcs_tables(base_lines, final_lines)
    lcs = pre[n * w + m]
    deleted = [i for i in range(n)
               if any(pre[i * w + j] + suf[(i + 1) * w2 + j] == lcs for j in range(m + 1))]
    added = [j for j in range(m)
             if any(pre[i * w + j] + suf[i * w2 + j + 1] == lcs for i in range(n + 1))]
    touched = section_labels(final_lines, added)
    for label in section_labels(base_lines, deleted):
        if label not in touched:
            touched.append(label)
    return dict(
        common,
        added_lines=m - lcs,
        deleted_lines=n - lcs,
        lcs_length=lcs,
        attribution_ambiguous=(len(added) > m - lcs or len(deleted) > n - lcs),
        possibly_added_lines=len(added),
        possibly_deleted_lines=len(deleted),
        sections_touched=sorted(touched),
    )


def cmd_selftest(args):
    tgt = os.fsencode(args.target)
    d1, l1 = witness(args.repo, tgt)
    d2, l2 = witness(args.repo, tgt)
    stable = d1 == d2
    status_lines = [l for l in l1 if l.startswith(b"S\t")]
    result = {
        "mode": "selftest",
        "target": args.target,
        "non_target_entries": len(status_lines),
        "witness_legs": {"status": len(status_lines),
                         "refs": sum(1 for l in l1 if l.startswith(b"R\t")),
                         "head": sum(1 for l in l1 if l.startswith(b"H\t"))},
        "witness_digest_1": d1,
        "witness_digest_2": d2,
        "stable": stable,
        "v01_criterion_satisfiable": len(status_lines) == 0,
        "note": ("非 target 条目非零 → v0.1 的『全仓只剩 target』判据不可满足；"
                 "digest 稳定 → v0.2 的事务局部守恒判据可满足"),
    }
    if not stable:
        drift = [
            l.decode("utf-8", "replace").rstrip("\n")
            for l in set(l1).symmetric_difference(set(l2))
        ]
        result["drift"] = sorted(drift)[:20]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if stable else 1


def cmd_preflight(args):
    require_outside_worktree(args.repo, args.sidecar, args.state)
    tgt = os.fsencode(args.target)
    raw = read_raw(os.path.join(os.fsencode(args.repo), tgt))
    actual = ABSENT.decode() if raw is None else sha256_bytes(raw)
    if actual != args.base:
        print(json.dumps({"mode": "preflight", "ok": False,
                          "reason": "base 不符 → 签名失效，不执行，回茶水间重提",
                          "expected_base": args.base, "actual": actual},
                         ensure_ascii=False, indent=2))
        return 1

    for inv in args.invariant or []:
        p, want = inv.split("=", 1)
        got = read_raw(os.path.join(os.fsencode(args.repo), os.fsencode(p)))
        got = ABSENT.decode() if got is None else sha256_bytes(got)
        if got != want:
            print(json.dumps({"mode": "preflight", "ok": False,
                              "reason": "不变量漂移 → 签名失效", "path": p,
                              "expected": want, "actual": got},
                             ensure_ascii=False, indent=2))
            return 1

    if raw is not None:  # sidecar：回滚的唯一依据，不靠 git checkout（CONVENTION §5.2）
        with open(args.sidecar, "wb") as fh:
            fh.write(raw)

    digest, lines = witness(args.repo, tgt)
    dump_lines(args.state + ".witness", lines)
    state = {"target": args.target, "base": actual, "sidecar": args.sidecar,
             "sidecar_present": raw is not None, "witness_digest_pre": digest,
             "non_target_entries": sum(1 for l in lines if l.startswith(b"S\t"))}
    with open(args.state, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    print(json.dumps({"mode": "preflight", "ok": True, **state},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_postcheck(args):
    with open(args.state, encoding="utf-8") as fh:
        state = json.load(fh)
    # sidecar 现在是 postcheck 的读入项，故它也得受 §5.3.d 约束（preflight 已查过一次，
    # 但状态文件是执行者可改的，这里不复查等于把 fail-closed 降级成一次性检查）。
    require_outside_worktree(args.repo, args.state, state["sidecar"])
    tgt = os.fsencode(state["target"])

    raw = read_raw(os.path.join(os.fsencode(args.repo), tgt))
    actual = ABSENT.decode() if raw is None else sha256_bytes(raw)
    final_ok = actual == args.final

    digest, lines = witness(args.repo, tgt)
    dump_lines(args.state + ".witness.post", lines)
    conserved = digest == state["witness_digest_pre"]

    # 行级差量：前像只认 sidecar 原始字节，且必须重算 == 已签 base。
    # 不重算就等于信任 sidecar 没被动过——那条缝正是本惯例要焊死的。
    diff = {}
    if state["sidecar_present"]:
        pre_raw = read_raw(os.fsencode(state["sidecar"]))
        pre_hash = ABSENT.decode() if pre_raw is None else sha256_bytes(pre_raw)
    else:
        pre_raw, pre_hash = None, ABSENT.decode()
    base_preimage_ok = pre_hash == state["base"]
    if base_preimage_ok:
        diff = line_delta(pre_raw, raw)
        if diff.get("delta_unavailable"):  # 算不动就说算不动，不降级到近似算法冒充"验过"
            counts_ok = confined_ok = diff_ok = False
        else:
            counts_ok = (diff["added_lines"] == args.expect_added
                         and diff["deleted_lines"] == args.expect_deleted)
            confined_to = args.changes_confined_to or []
            confined_ok = (not confined_to) or all(
                any(s.startswith(p) for p in confined_to) for s in diff["sections_touched"])
            diff_ok = counts_ok and confined_ok
    else:  # sidecar 缺失/漂移 → 无可核前像，fail-closed，不靠 HEAD 顶替
        counts_ok = confined_ok = diff_ok = False

    out = {"mode": "postcheck", "final_expected": args.final, "final_actual": actual,
           "final_ok": final_ok, "witness_digest_pre": state["witness_digest_pre"],
           "witness_digest_post": digest, "non_target_conserved": conserved,
           "witness_coverage": WITNESS_COVERAGE,
           "base_preimage_ok": base_preimage_ok, "base_preimage_expected": state["base"],
           "base_preimage_actual": pre_hash, "sidecar": state["sidecar"],
           **diff,
           "expect_added": args.expect_added, "expect_deleted": args.expect_deleted,
           "changes_confined_to": args.changes_confined_to or [],
           "counts_ok": counts_ok, "changes_confined": confined_ok, "diff_ok": diff_ok,
           "ok": final_ok and conserved and diff_ok}
    if not base_preimage_ok:
        out["reason_preimage"] = ("sidecar 字节重算 != 已签 base → 前像不可核，行级差量不予采信。")
    elif not diff_ok:
        out["reason_diff"] = (
            "行级差量与签名钉住的形状不符 → 不得宣称落地，按 §5.2 写回 sidecar 回滚。"
            "（哈希只证明后像是那一个；本项证明的是它由前像**怎样**变过来的。）")
    if not conserved:
        pre = set(open(args.state + ".witness", "rb").read().splitlines(keepends=True))
        post = set(lines)
        drift = [b"-" + l for l in pre - post] + [b"+" + l for l in post - pre]
        out["drift"] = sorted(
            l.decode("utf-8", "replace").rstrip("\n") for l in drift
        )[:20]
        out["drift_truncated"] = len(drift) > 20
        out["reason"] = ("见证覆盖面内的非 target 差量非零（S=状态/工作区字节/index 条目，"
                         "R=引用，H=HEAD）→ 不得宣称落地，按 §5.2 写回 sidecar 回滚。"
                         "并发导致的保守失败可接受；禁止清仓凑通过。")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("selftest")
    s.add_argument("--target", required=True)
    s.set_defaults(fn=cmd_selftest)

    s = sub.add_parser("preflight")
    s.add_argument("--target", required=True)
    s.add_argument("--base", required=True)
    s.add_argument("--sidecar", required=True)
    s.add_argument("--state", required=True)
    s.add_argument("--invariant", action="append", metavar="PATH=SHA256")
    s.set_defaults(fn=cmd_preflight)

    s = sub.add_parser("postcheck")
    s.add_argument("--final", required=True)
    s.add_argument("--state", required=True)
    # 增删数是 required 而非可选：留成可选就等于留下一个"不报差量也算通过"的静默挡位，
    # 回执仍可声称验过⑥。要么给出签名钉住的形状并被判，要么根本跑不起来。
    s.add_argument("--expect-added", type=int, required=True)
    s.add_argument("--expect-deleted", type=int, required=True)
    s.add_argument("--changes-confined-to", action="append", metavar="HEADING_PREFIX")
    s.set_defaults(fn=cmd_postcheck)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
