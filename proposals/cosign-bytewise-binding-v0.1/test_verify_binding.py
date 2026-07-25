#!/usr/bin/env python3
"""verify_binding.py 的临时仓测试（v0.6）。

只跑 `python test_verify_binding.py`；不依赖 pytest，不碰本仓工作树——
每个用例在 tempdir 里现建一个 git 仓，制品一律写在那个仓之外（CONVENTION §5.3.d）。

[1]-[8] 覆盖 Codex 2026-07-26 06:18:57 拒签所指的断裂：postcheck 必须真的做行级差量，
且**错计数**与**错章节**都要能被抓住。前者证明它在数，后者证明它数对了地方——
只测前者的话，一个把所有改动都算进 §3 的实现照样能过。
[9][10] 覆盖 06:44:57 拒签：口径必须真的是 LCS，且归属不许挑对齐。
[11]-[13] 覆盖 07:12:33 拒签与本轮自测：见证必须钉 index 与引用；
覆盖不到的（被忽略文件）必须由回执自己说出来，而不是躲在"非 target 差量为零"这个泛称底下。
[14][15] 覆盖 07:40:43 拒签与本轮自测：R 腿必须钉符号目标（同 OID 改指不许放行）；
for-each-ref 够不到的（refs/ 外伪引用、悬空 symref）同样必须写进 not_covered。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "verify_binding.py")

DOC = b"""# T

## \xe4\xb8\x80
a1
a2

## \xe4\xba\x8c
b1
b2

## \xe4\xb8\x89
c1
c2
"""

FAILURES = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (" :: " + detail if detail else ""))
    if not cond:
        FAILURES.append(name)


def run(repo, *argv):
    p = subprocess.run([sys.executable, CHECKER, "--repo", repo] + list(argv),
                       capture_output=True, cwd=repo)
    try:
        return p.returncode, json.loads(p.stdout.decode("utf-8"))
    except ValueError:
        return p.returncode, {"_stdout": p.stdout.decode("utf-8", "replace"),
                              "_stderr": p.stderr.decode("utf-8", "replace")}


def sha256(path):
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class Repo:
    """临时 git 仓 + 仓外制品目录。"""

    def __init__(self, doc=DOC):
        self.doc = doc

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="vb-test-")
        self.repo = os.path.join(self.tmp, "repo")
        self.out = os.path.join(self.tmp, "artifacts")  # 仓外
        os.makedirs(self.repo)
        os.makedirs(self.out)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=self.repo, check=True)
        self.target = os.path.join(self.repo, "DOC.md")
        self.write(self.doc)
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.repo, check=True)
        self.sidecar = os.path.join(self.out, "sidecar.bin")
        self.state = os.path.join(self.out, "state.json")
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, raw):
        with open(self.target, "wb") as fh:
            fh.write(raw)

    def base(self):
        return sha256(self.target)

    def preflight(self):
        return run(self.repo, "preflight", "--target", "DOC.md", "--base", self.base(),
                   "--sidecar", self.sidecar, "--state", self.state)

    def postcheck(self, added, deleted, confine=None):
        argv = ["postcheck", "--final", sha256(self.target), "--state", self.state,
                "--expect-added", str(added), "--expect-deleted", str(deleted)]
        for c in confine or []:
            argv += ["--changes-confined-to", c]
        return run(self.repo, *argv)


# 在 "## 三" 段内追加两行；在 "## 二" 段内追加两行。两者增删计数完全相同，
# 只有章节归属不同——错段用例靠这一对区分。
INSERT_S3 = DOC + b"c3\nc4\n"
INSERT_S2 = DOC.replace(b"## \xe4\xba\x8c\nb1\nb2\n", b"## \xe4\xba\x8c\nb1\nb2\nb3\nb4\n")


def case_happy():
    print("[1] 只在 §3 内加 2 行，形状与签名一致 → ok:true")
    with Repo() as r:
        rc, pre = r.preflight()
        check("preflight ok", rc == 0 and pre.get("ok") is True, json.dumps(pre)[:200])
        r.write(INSERT_S3)
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("postcheck ok:true", rc == 0 and out.get("ok") is True, json.dumps(out)[:300])
        check("added=2", out.get("added_lines") == 2, str(out.get("added_lines")))
        check("deleted=0", out.get("deleted_lines") == 0, str(out.get("deleted_lines")))
        check("sections_touched 只有 §3",
              out.get("sections_touched") == ["## 三"], str(out.get("sections_touched")))


def case_wrong_count():
    print("[2] 错计数：实际加 2 行，签名说加 4 行 → ok:false")
    with Repo() as r:
        r.preflight()
        r.write(INSERT_S3)
        rc, out = r.postcheck(4, 0, ["## 三"])
        check("postcheck ok:false", rc != 0 and out.get("ok") is False, json.dumps(out)[:200])
        check("counts_ok=false", out.get("counts_ok") is False)
        check("如实报实测 added=2", out.get("added_lines") == 2)
        check("final 哈希本身仍对（证明这一刀不是 final 在挡）", out.get("final_ok") is True)


def case_wrong_section():
    print("[3] 错章节：计数对（2 增 0 删）但落在 §2 → ok:false")
    with Repo() as r:
        r.preflight()
        r.write(INSERT_S2)
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("added=2/deleted=0（计数确实骗得过）",
              (out.get("added_lines"), out.get("deleted_lines")) == (2, 0))
        check("counts_ok=true", out.get("counts_ok") is True)
        check("changes_confined=false", out.get("changes_confined") is False)
        check("postcheck ok:false", rc != 0 and out.get("ok") is False)
        check("点名实际落在 §2",
              out.get("sections_touched") == ["## 二"], str(out.get("sections_touched")))


def case_deletion_counted():
    print("[4] 删行：删掉 §1 的 1 行 → deleted=1，且章节在**前像**侧求值")
    with Repo() as r:
        r.preflight()
        r.write(DOC.replace(b"a1\na2\n", b"a1\n"))
        rc, out = r.postcheck(0, 1, ["## 三"])
        check("deleted=1", out.get("deleted_lines") == 1, str(out.get("deleted_lines")))
        check("added=0", out.get("added_lines") == 0)
        check("sections_touched=§1（前像侧）",
              out.get("sections_touched") == ["## 一"], str(out.get("sections_touched")))
        check("ok:false（不在 §3）", out.get("ok") is False)


def case_sidecar_tampered():
    print("[5] sidecar 被动过 → 前像不可核，fail-closed，不拿 HEAD 顶替")
    with Repo() as r:
        r.preflight()
        r.write(INSERT_S3)
        with open(r.sidecar, "ab") as fh:
            fh.write(b"tampered\n")
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("base_preimage_ok=false", out.get("base_preimage_ok") is False)
        check("ok:false", rc != 0 and out.get("ok") is False)
        check("不输出可采信的差量", "added_lines" not in out, str(out.get("added_lines")))


def case_artifact_inside_worktree():
    print("[6] 制品落在仓内 → §5.3.d fail-closed（postcheck 侧也查 sidecar）")
    with Repo() as r:
        r.preflight()
        state = json.load(open(r.state, encoding="utf-8"))
        inside = os.path.join(r.repo, "sidecar.bin")
        shutil.copyfile(r.sidecar, inside)
        state["sidecar"] = inside
        with open(r.state, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
        r.write(INSERT_S3)
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("拒绝执行", rc != 0 and out.get("ok") is False, json.dumps(out)[:200])
        check("理由是制品在工作树内", "工作树" in str(out.get("reason", "")))


def case_expectations_required():
    print("[7] 不给 --expect-added/--expect-deleted 根本跑不起来（无静默挡位）")
    with Repo() as r:
        r.preflight()
        r.write(INSERT_S3)
        rc, out = run(r.repo, "postcheck", "--final", sha256(r.target), "--state", r.state)
        check("argparse 拒绝", rc != 0, str(rc))
        check("报缺参数", "expect-added" in out.get("_stderr", ""), out.get("_stderr", "")[:200])


def case_conservation_still_binds():
    print("[8] 差量对但顺手改了别的文件 → 守恒仍然挡住")
    with Repo() as r:
        r.preflight()
        r.write(INSERT_S3)
        with open(os.path.join(r.repo, "other.txt"), "wb") as fh:
            fh.write(b"sneaked\n")
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("diff_ok=true", out.get("diff_ok") is True)
        check("non_target_conserved=false", out.get("non_target_conserved") is False)
        check("ok:false", out.get("ok") is False)
        check("点名 other.txt", any("other.txt" in d for d in out.get("drift", [])),
              str(out.get("drift")))


def case_interleaved_lcs():
    print("[9] 交错重复行 aba→bca：口径必须是真 LCS（1 增 1 删），不是 difflib 的 2 增 2 删")
    # Codex 2026-07-26 06:44:57 的反例，钉死在这里。v0.3 用 difflib.SequenceMatcher(autojunk=False)
    # 并声称那是"LCS 最小对齐"——它只匹配首尾那个 a，报 2/2。真 LCS 是 b,a（长度 2）→ 1/1。
    # 前 8 例全是直线插入/删除，交错重复行是它们够不着的地方，故全过也抓不到。
    import difflib
    before, after = b"a\nb\na\n", b"b\nc\na\n"
    sm = difflib.SequenceMatcher(a=before.splitlines(True), b=after.splitlines(True),
                                 autojunk=False)
    sm_add = sum(j2 - j1 for t, _, _, j1, j2 in sm.get_opcodes() if t in ("replace", "insert"))
    sm_del = sum(i2 - i1 for t, i1, i2, _, _ in sm.get_opcodes() if t in ("replace", "delete"))
    check("反例前提：difflib 在此确实非最小（2 增 2 删）", (sm_add, sm_del) == (2, 2),
          "difflib=%d/%d" % (sm_add, sm_del))
    with Repo(before) as r:
        r.preflight()
        r.write(after)
        rc, out = r.postcheck(1, 1)
        check("added=1（真 LCS）", out.get("added_lines") == 1, str(out.get("added_lines")))
        check("deleted=1（真 LCS）", out.get("deleted_lines") == 1, str(out.get("deleted_lines")))
        check("lcs_length=2", out.get("lcs_length") == 2, str(out.get("lcs_length")))
        check("ok:true", rc == 0 and out.get("ok") is True, json.dumps(out)[:300])
        # 反向锁：若有人改回 difflib，签名钉 2/2 就会通过——这里要求它被判为不符。
        _, out2 = r.postcheck(2, 2)
        check("difflib 的 2/2 必须被判不符", out2.get("counts_ok") is False,
              str((out2.get("added_lines"), out2.get("deleted_lines"))))


AMBIG = b"""# T
## \xe4\xb8\x80
x
## \xe4\xba\x8c
x
"""


def case_ambiguous_attribution():
    print("[10] 最小对齐不唯一：归属取全体最小对齐之并（保守超集），并显式标 ambiguous")
    # LCS 长度唯一 ≠ 最小对齐唯一。这里删掉 "## 二" 整节及其中的 x，而 §1 里有个一模一样的 x——
    # "被删的是哪个 x" 有两个都最小的答案。挑任一对齐都是任意 tie-break，"改在哪一节"就随实现细节漂。
    # 故归属不挑对齐，取并集：宁可报超集（判据只会更严），不可让错段蒙混过关。
    with Repo(AMBIG) as r:
        r.preflight()
        r.write(b"# T\n## \xe4\xb8\x80\nx\n")
        rc, out = r.postcheck(0, 2, ["## 二"])
        check("deleted=2（计数仍唯一）", out.get("deleted_lines") == 2, str(out.get("deleted_lines")))
        check("counts_ok=true", out.get("counts_ok") is True)
        check("attribution_ambiguous=true", out.get("attribution_ambiguous") is True)
        check("possibly_deleted=3 > deleted=2", out.get("possibly_deleted_lines") == 3,
              str(out.get("possibly_deleted_lines")))
        check("章节报超集（§1 §2 都在）",
              out.get("sections_touched") == ["## 一", "## 二"], str(out.get("sections_touched")))
        check("保守失败而非放行（声称『只动 §2』被挡下）",
              rc != 0 and out.get("changes_confined") is False and out.get("ok") is False)


def git(repo, *argv, check=True):
    return subprocess.run(["git"] + list(argv), cwd=repo, capture_output=True, check=check)


def case_index_only_mutation():
    print("[11] 工作树字节不变、只换 index blob（MM→MM）→ 守恒必须挡住（v0.5 index 腿）")
    # Codex 2026-07-26 07:12:33 的拒签复现，本轮独立复跑坐实：v0.4 的见证只记 XY + 工作区字节，
    # 于是一条已处于 MM 的路径，index 前像被换掉而 XY 与工作区字节都不变 → digest 一字不变 → 放行。
    # 这是"可核对象没覆盖自称覆盖的量"，正是本惯例从头到尾要封的形状。
    with Repo() as r:
        other = os.path.join(r.repo, "other.txt")
        with open(other, "wb") as fh:
            fh.write(b"committed\n")
        git(r.repo, "add", "other.txt")
        git(r.repo, "commit", "-qm", "other")      # 先跟踪，否则造出来的是 AM 而不是 MM
        with open(other, "wb") as fh:
            fh.write(b"index-one\n")
        git(r.repo, "add", "other.txt")            # index != HEAD → X=M
        with open(other, "wb") as fh:
            fh.write(b"worktree-fixed\n")          # 工作树 != index → Y=M，即 MM
        before_xy = git(r.repo, "status", "--porcelain").stdout
        check("前提：other.txt 确为 MM（Codex 复现所指的那一种）",
              before_xy.strip() == b"MM other.txt", repr(before_xy))
        rc, pre = r.preflight()
        check("preflight ok", rc == 0 and pre.get("ok") is True, json.dumps(pre)[:200])

        with open(other, "wb") as fh:              # 只动 index，工作树字节原样恢复
            fh.write(b"index-two\n")
        git(r.repo, "add", "other.txt")
        with open(other, "wb") as fh:
            fh.write(b"worktree-fixed\n")
        after_xy = git(r.repo, "status", "--porcelain").stdout
        check("前提：XY 与工作区字节都没变（v0.4 就是靠这个漏过去的）",
              before_xy == after_xy and open(other, "rb").read() == b"worktree-fixed\n",
              repr((before_xy, after_xy)))

        r.write(INSERT_S3)
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("diff_ok=true（这一刀不是差量在挡）", out.get("diff_ok") is True)
        check("non_target_conserved=false", out.get("non_target_conserved") is False,
              json.dumps(out)[:300])
        check("ok:false", rc != 0 and out.get("ok") is False)
        check("drift 点名 other.txt", any("other.txt" in d for d in out.get("drift", [])),
              str(out.get("drift")))


def case_refs_mutation():
    print("[12] 事务中删掉一个分支 → 守恒必须挡住（v0.5 R/H 腿）")
    # 本轮自测撞出，非 Codex 所提，与 [11] 同病：v0.4 下 `git branch -D` 后 git status 一字不变，
    # digest 不变 → ok:true。毁掉一个引用是难撤销的附带损害，故纳入覆盖面而不是明文排除。
    with Repo() as r:
        git(r.repo, "branch", "sidebranch")
        r.preflight()
        git(r.repo, "branch", "-D", "sidebranch")
        r.write(INSERT_S3)
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("diff_ok=true", out.get("diff_ok") is True)
        check("non_target_conserved=false", out.get("non_target_conserved") is False)
        check("ok:false", rc != 0 and out.get("ok") is False)
        check("drift 点名 sidebranch", any("sidebranch" in d for d in out.get("drift", [])),
              str(out.get("drift")))
        # v0.6 反向锁：sidebranch 是一条 direct ref，它的 R 行必须记显式哨兵 DIRECT。
        # 谁把哨兵改回空串（`%(symref)` 对 direct ref 实测就是空串），那一位就与
        # "根本没记符号目标"不可区分——本例会红。
        check("direct ref 的 R 行记显式哨兵 DIRECT",
              any("sidebranch" in d and d.endswith("DIRECT") for d in out.get("drift", [])),
              str(out.get("drift")))


def case_ignored_files_excluded():
    print("[13] 边界钉桩：被忽略文件**不在**覆盖面内——判据放行，且必须自己说出来")
    # 这不是"通过"用例，是把 CONVENTION §5.3.f 明文排除的那条边界钉住：
    # 覆盖不到就必须写明覆盖不到（无界 + 高频抖动，全量哈希会让判据不可满足或极慢），
    # 不许留在"非 target 差量为零"这种泛称底下装作守住了。谁哪天把它纳入覆盖，本例会红，
    # 逼着同一份稿子里把 §5.3.f 的排除条一并改掉——文档与行为不许各说各话。
    with Repo() as r:
        with open(os.path.join(r.repo, ".gitignore"), "wb") as fh:
            fh.write(b"ign*\n")
        git(r.repo, "add", ".gitignore")
        git(r.repo, "commit", "-qm", "ignore")
        ign = os.path.join(r.repo, "ignored.bin")
        with open(ign, "wb") as fh:
            fh.write(b"secret-one\n")
        r.preflight()
        with open(ign, "wb") as fh:
            fh.write(b"DESTROYED\n")               # 事务顺手毁掉一个被忽略文件
        r.write(INSERT_S3)
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("覆盖面外 → 判据确实放行（这是被声明的行为，不是 bug）",
              rc == 0 and out.get("ok") is True, json.dumps(out)[:200])
        check("回执必须自带覆盖面边界", "witness_coverage" in out)
        check("边界里明写排除 .gitignore 命中路径",
              any(".gitignore" in s for s in out["witness_coverage"]["not_covered"]),
              str(out.get("witness_coverage", {}).get("not_covered")))
        check("被忽略文件确实被毁了（证明这条边界是真的，不是假设）",
              open(ign, "rb").read() == b"DESTROYED\n")


def case_symref_retarget():
    print("[14] 同 OID、只改非 HEAD symbolic ref 的目标 → 守恒必须挡住（v0.6 R 腿符号目标）")
    # Codex 2026-07-26 07:40:43 的拒签复现，本轮独立复跑坐实：v0.5 的 R 行只记
    # refname → objectname。令 refs/remotes/origin/{main,alt} 指向同一 commit，
    # 把 refs/remotes/origin/HEAD 从 main 改指 alt——`for-each-ref --format=%(objectname)%09%(refname)`
    # 前后字节完全相同，digest 不变，`non_target_conserved:true`、`ok:true` 放行。
    # H 腿钉的是 HEAD 自己的符号名，够不到这一类。
    with Repo() as r:
        oid = git(r.repo, "rev-parse", "HEAD").stdout.strip().decode()
        git(r.repo, "update-ref", "refs/remotes/origin/main", oid)
        git(r.repo, "update-ref", "refs/remotes/origin/alt", oid)
        git(r.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        oid_before = git(r.repo, "for-each-ref",
                         "--format=%(objectname)%09%(refname)").stdout
        r.preflight()

        git(r.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/alt")
        oid_after = git(r.repo, "for-each-ref",
                        "--format=%(objectname)%09%(refname)").stdout
        check("前提：v0.5 那两列前后字节完全相同（v0.5 就是靠这个漏过去的）",
              oid_before == oid_after, repr((oid_before, oid_after)))
        check("前提：符号目标确实变了",
              git(r.repo, "symbolic-ref", "refs/remotes/origin/HEAD").stdout.strip()
              == b"refs/remotes/origin/alt")

        r.write(INSERT_S3)
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("diff_ok=true（这一刀不是差量在挡）", out.get("diff_ok") is True)
        check("non_target_conserved=false", out.get("non_target_conserved") is False,
              json.dumps(out, ensure_ascii=False)[:300])
        check("ok:false", rc != 0 and out.get("ok") is False)
        drift = out.get("drift", [])
        check("drift 点名改指的那条引用", any("origin/HEAD" in d for d in drift), str(drift))
        check("drift 同时给出前后两个符号目标（否则读者看不出变的是符号腿）",
              any("origin/main" in d for d in drift) and any("origin/alt" in d for d in drift),
              str(drift))
        # 注：direct ref 的 DIRECT 哨兵不在本例的 drift 里——drift 只含**变化的**行，
        # 而这里变的恰是符号行。哨兵的反向锁钉在 [12]（那里漂移的是一条 direct ref）。


def case_pseudorefs_excluded():
    print("[15] 边界钉桩：refs/ 之外的伪引用**不在**覆盖面内——放行，且必须自己说出来")
    # 与 [13] 同一形状，本轮自测撞出（非 Codex 所提）：实测 for-each-ref 不列出 ORIG_HEAD
    # 一类伪引用，也不列出悬空 symbolic ref。既然覆盖不到，就必须写在 not_covered 里，
    # 不许躲在"for-each-ref 的全部引用"这句读起来像"全部引用"的话底下。
    # 谁哪天把它纳入覆盖，本例会红，逼着同一份稿子把 §5.3.f 的排除条一并改掉。
    with Repo() as r:
        oid = git(r.repo, "rev-parse", "HEAD").stdout.strip().decode()
        git(r.repo, "update-ref", "ORIG_HEAD", oid)
        listed = git(r.repo, "for-each-ref", "--format=%(refname)").stdout
        check("前提：for-each-ref 确实不列出 ORIG_HEAD", b"ORIG_HEAD" not in listed,
              repr(listed))
        r.preflight()
        git(r.repo, "update-ref", "-d", "ORIG_HEAD")   # 事务顺手删掉它
        r.write(INSERT_S3)
        rc, out = r.postcheck(2, 0, ["## 三"])
        check("覆盖面外 → 判据确实放行（这是被声明的行为，不是 bug）",
              rc == 0 and out.get("ok") is True, json.dumps(out, ensure_ascii=False)[:200])
        check("边界里明写排除 refs/ 之外的伪引用",
              any("ORIG_HEAD" in s for s in out["witness_coverage"]["not_covered"]),
              str(out.get("witness_coverage", {}).get("not_covered")))
        check("ORIG_HEAD 确实被删了（证明这条边界是真的，不是假设）",
              git(r.repo, "rev-parse", "-q", "--verify", "ORIG_HEAD",
                  check=False).returncode != 0)


def main():
    for fn in (case_happy, case_wrong_count, case_wrong_section, case_deletion_counted,
               case_sidecar_tampered, case_artifact_inside_worktree,
               case_expectations_required, case_conservation_still_binds,
               case_interleaved_lcs, case_ambiguous_attribution,
               case_index_only_mutation, case_refs_mutation, case_ignored_files_excluded,
               case_symref_retarget, case_pseudorefs_excluded):
        fn()
    print()
    if FAILURES:
        print("FAILED: " + "; ".join(FAILURES))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
