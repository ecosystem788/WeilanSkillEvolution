#!/usr/bin/env python3
"""按 Codex 2026-07-31T18:32:39+09:00 的独立裁断，构造三份 proposed-final 全文。

只读源文件，落三份 `*.proposed-final.*` 到本目录，并打印每份的五件绑定所需量
（sha256 / 字节数 / 规范 LCS 增删数 / sections_touched）。**不改任何被提案文件。**

每处替换都带锚点断言：锚点不是恰好命中一次就整支退出、不产出任何东西。
签名方不必采用本脚本声明的数——可以只读跑一遍它自己导出后像（CONVENTION §六 强绑定）。

裁断的两条腿：
  规范腿 —— §5.3.d/e 明写 `.witness` 与 `.witness.post` 两份都要归档；
  机件腿 —— postcheck 输出两条派生路径，回执分列。
只打印路径不保证归档；只归档而路径继续隐身会复发。故两条腿同时改，测试[16]钉住机件那一腿。
"""

import hashlib
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, os.pardir, "cosign-bytewise-binding-v0.1"))

_spec = importlib.util.spec_from_file_location(
    "vb_ref", os.path.join(SRC, "verify_binding.py"))
_vb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vb)   # 复用机检器自己的规范 LCS，不另造一份口径


# ---------------------------------------------------------------- CONVENTION.md

CONV_PATCHES = [
    # 版本号
    ("# 双签的前像→后像绑定（v0.7）\n",
     "# 双签的前像→后像绑定（v0.8）\n"),

    # §5.3.d：制品名单里点名两份见证快照
    ("   d. **执行期制品（sidecar、见证快照、状态文件）必须写在工作树之外**，通过后再归档入仓。\n",
     "   d. **执行期制品（sidecar、执行前/后两份见证快照、状态文件）必须写在工作树之外**，\n"
     "      通过后再归档入仓。**两份**是 v0.8 新增，理由见 e。\n"),

    # §5.3.e：归档义务写成等式的两个操作数都要有前像
    ("   e. 见证快照全文留档为执行制品；回执只记它的规范摘要 `witness-digest`（见 §5.4），\n"
     "      使第三方能独立复算，而不必把上百行状态塞进回执。\n",
     "   e. **执行前与执行后两份**见证快照全文均留档为执行制品（`<state>.witness` 与\n"
     "      `<state>.witness.post`）；回执只记它们的规范摘要 `witness-digest`（见 §5.4），\n"
     "      使第三方能独立复算，而不必把上百行状态塞进回执。\n"
     "\n"
     "      **两份都要**是 v0.8 新增，且是承重的：守恒判据 `witness_digest_post ==\n"
     "      witness_digest_pre` 是一个**等式**，两个操作数都只以 64 位十六进制出现在回执里。\n"
     "      明细文件的 sha256 就是 digest 本身（`witness()` 取 `sha256(b\"\".join(lines))`，\n"
     "      `dump_lines` 原样落盘），所以明细在树上则 digest 可被第三方重算，明细不在则它只是\n"
     "      执行方的自陈值。只归档 pre，等式就只有一边有前像。\n"
     "      2026-07-31 普查坐实（`proposals/witness-post-archival-asymmetry-v0.1/`，六次落地）：\n"
     "      pre 明细 3 次可重算、post 明细仅 2 次，最近一次 post 缺档而没有任何闸口响——\n"
     "      因为 v0.7 的 d/e 都没点名 post，那两次归档 post 是**超规格的好习惯，不是合规**，\n"
     "      于是第三次自然掉回规格线。这与 `proposals/witness-archival-gap-v0.1/` 同型，\n"
     "      是那条被补上之后暴露出的下一层。\n"
     "\n"
     "      机检器须把**两条明细路径**打进 preflight/postcheck 的 JSON 输出\n"
     "      （`witness_path_pre` / `witness_path_post`，v0.8 新增）：路径此前只由 `args.state`\n"
     "      在机检器内部派生、不出现在任何输出字段里——两次普查里，唯一不被打印路径的制品，\n"
     "      正是那个不被归档的制品。两条腿缺一不可：只打印路径不保证归档，只归档而路径继续隐身\n"
     "      会复发（Codex 2026-07-31T18:32:39+09:00 独立判）。测试[16]钉住机件那一腿；\n"
     "      归档进仓机检器看不见（仓外制品按 d 恰在覆盖面外），那一腿由本条与回执核。\n"
     "\n"
     "      边界：归档提高的是伪造成本，不是对抗性可证——两份明细由同一方在同一次运行里生成，\n"
     "      它把造假从\"编一个 64 位串\"抬到\"伪造一份与账本、index、refs 全都自洽的明细\"。\n"
     "      覆盖面（f 的七条排除）也不因归档而改变。\n"),

    # §5.4 回执必记项：路径改成两份
    ("   见证快照与 sidecar 制品的路径。\n",
     "   **两份**见证快照（`.witness` / `.witness.post`，§5.3.e）与 sidecar 制品的路径。\n"),
]

CONV_APPEND = (
    "- v0.8 2026-07-31（Claude），因 Codex 2026-07-31T18:32:39+09:00 的独立裁断而改\n"
    "  （该裁断不是拒签：它裁的是我 2026-07-31 那条【FINDING·不开案】里刻意不选的四条候选，\n"
    "  见 `proposals/witness-post-archival-asymmetry-v0.1/FINDING.md`）。\n"
    "  差异的形状：`non_target_conserved` 是等式 `post == pre`，而 §5.3.d 点名的三样制品\n"
    "  （sidecar、见证快照、状态文件）里，\"见证快照\"实际只落实了 pre 一份——`.witness.post`\n"
    "  既不在条款名单里，也没有任何机检看着它。普查六次双签落地：sidecar 6/6、preflight-state 6/6、\n"
    "  pre 明细 3 次可重算、post 明细仅 2 次，07-31 那次 post 缺档，全程零告警。\n"
    "  改（两条腿，Codex 判为缺一不可）：§5.3.d/e 明写两份见证快照都须归档并写明为什么\n"
    "  （只归档 pre，等式就只有一边有前像，第三方只能采信执行方的自陈值）；\n"
    "  机检器把 `witness_path_pre` / `witness_path_post` 打进 preflight 与 postcheck 的 JSON，\n"
    "  §5.4 回执必记项由\"见证快照的路径\"改为两份的路径。测试补[16]。\n"
    "  **本版明说机检够不着的那一位**：制品住在仓外（§5.3.d），机检器无从知道它有没有被归档进仓；\n"
    "  它能守的只是\"两条路径都印出来、且各自明细的 sha256 逐字等于配对的 digest\"。\n"
    "  归档本身仍是执行者的义务、由本条与回执核——这一位是人眼位，不假装它被机器守住\n"
    "  （与 v0.7 末尾那一位同性质）。\n"
    "  同轮不做的一件：见证前缀可作**次序权威**（preflight 见证里账本指纹命中一个记录边界前缀，\n"
    "  于是\"提案→同意→执行\"的次序不靠手写 time 而由机检背书，实测见 FINDING 第五节）。\n"
    "  它把制品从可核证据抬成程序次序权威，承重范围不同，Codex 判为另案，不塞进这次缺档修复。\n")


# ------------------------------------------------------------ verify_binding.py

VB_PATCHES = [
    ('"""前像→后像绑定 v0.6 的机检器（CONVENTION §5）。\n',
     '"""前像→后像绑定 v0.8 的机检器（CONVENTION §5）。\n'),

    ("               三组判据全过才 ok:true。\n",
     "               三组判据全过才 ok:true。\n"
     "\n"
     "v0.8：两份见证明细的路径（witness_path_pre / witness_path_post）进 JSON 输出。守恒判据\n"
     "`post == pre` 是等式，两个操作数都只以 64 位十六进制出现在回执里；明细文件的 sha256 就是\n"
     "digest 本身，故明细可定位则 digest 可被第三方重算，明细隐身则它只是执行方的自陈值。\n"
     "（CONVENTION §5.3.e。归档进仓是执行者的义务，仓外制品在覆盖面外，机检器看不见。）\n"),

    # preflight：路径提成变量并记进状态文件 → 随 **state 进 JSON
    ("    digest, lines = witness(args.repo, tgt)\n"
     "    dump_lines(args.state + \".witness\", lines)\n"
     "    state = {\"target\": args.target, \"base\": actual, \"sidecar\": args.sidecar,\n"
     "             \"sidecar_present\": raw is not None, \"witness_digest_pre\": digest,\n"
     "             \"non_target_entries\": sum(1 for l in lines if l.startswith(b\"S\\t\"))}\n",
     "    digest, lines = witness(args.repo, tgt)\n"
     "    # 明细路径必须进输出（v0.8）：它此前只在这里由 args.state 内部派生，不出现在任何字段里，\n"
     "    # 而两次普查都撞到同一件事——唯一不被打印路径的制品，正是那个不被归档的制品。\n"
     "    witness_path_pre = args.state + \".witness\"\n"
     "    dump_lines(witness_path_pre, lines)\n"
     "    state = {\"target\": args.target, \"base\": actual, \"sidecar\": args.sidecar,\n"
     "             \"sidecar_present\": raw is not None, \"witness_digest_pre\": digest,\n"
     "             \"witness_path_pre\": witness_path_pre,\n"
     "             \"non_target_entries\": sum(1 for l in lines if l.startswith(b\"S\\t\"))}\n"),

    # postcheck：两条路径都提成变量
    ("    digest, lines = witness(args.repo, tgt)\n"
     "    dump_lines(args.state + \".witness.post\", lines)\n"
     "    conserved = digest == state[\"witness_digest_pre\"]\n",
     "    digest, lines = witness(args.repo, tgt)\n"
     "    # pre 路径优先取状态文件里记下的那条；v0.8 之前写的状态文件没有该字段，派生式相同，\n"
     "    # 故回退到同一个派生式而不是 fail——旧状态文件不该因为多了一个字段而验不了。\n"
     "    witness_path_pre = state.get(\"witness_path_pre\") or (args.state + \".witness\")\n"
     "    witness_path_post = args.state + \".witness.post\"\n"
     "    dump_lines(witness_path_post, lines)\n"
     "    conserved = digest == state[\"witness_digest_pre\"]\n"),

    ("           \"witness_digest_post\": digest, \"non_target_conserved\": conserved,\n",
     "           \"witness_digest_post\": digest, \"non_target_conserved\": conserved,\n"
     "           \"witness_path_pre\": witness_path_pre, \"witness_path_post\": witness_path_post,\n"),

    ("        pre = set(open(args.state + \".witness\", \"rb\").read().splitlines(keepends=True))\n",
     "        pre = set(open(witness_path_pre, \"rb\").read().splitlines(keepends=True))\n"),
]


# ------------------------------------------------------- test_verify_binding.py

TEST_PATCHES = [
    ('"""verify_binding.py 的临时仓测试（v0.6）。\n',
     '"""verify_binding.py 的临时仓测试（v0.8）。\n'),

    ("for-each-ref 够不到的（refs/ 外伪引用、悬空 symref）同样必须写进 not_covered。\n",
     "for-each-ref 够不到的（refs/ 外伪引用、悬空 symref）同样必须写进 not_covered。\n"
     "[16] 覆盖 2026-07-31 的缺档普查：守恒等式的两个操作数都要有可定位、可重算的前像。\n"),

    ("def main():\n"
     "    for fn in (case_happy, case_wrong_count, case_wrong_section, case_deletion_counted,\n",
     "def case_witness_paths_printed():\n"
     "    print(\"[16] 守恒等式的两个操作数都要有可定位的前像：两条见证明细路径都必须进 JSON\")\n"
     "    # 2026-07-31 普查（proposals/witness-post-archival-asymmetry-v0.1/）：六次落地里 pre 明细\n"
     "    # 3 次可重算、post 明细仅 2 次，最近一次 post 缺档而没有任何闸口响。病灶与\n"
     "    # witness-archival-gap 同形——路径只由 args.state 在机检器内部派生、不出现在任何输出里，\n"
     "    # 于是唯一不被打印路径的制品，正是那个不被归档的制品。\n"
     "    # 本例只钉机件那一腿：两条路径都印出来，且各自明细的 sha256 逐字等于配对的 digest\n"
     "    # （witness() 取 sha256(b\"\".join(lines))、dump_lines 原样落盘，故明细在盘上则 digest 可重算）。\n"
     "    # **归档进仓不在本例内**：制品按 §5.3.d 住在仓外，机检器看不见仓，测不了。那一腿由\n"
     "    # CONVENTION §5.3.e 与回执核，是明写的人眼位——本注释存在就是为了不让它被读成机器守住了。\n"
     "    with Repo() as r:\n"
     "        rc, pre = r.preflight()\n"
     "        check(\"preflight 成功\", rc == 0, json.dumps(pre, ensure_ascii=False)[:200])\n"
     "        p_pre = pre.get(\"witness_path_pre\")\n"
     "        check(\"preflight 印出 pre 明细路径\", bool(p_pre),\n"
     "              json.dumps(pre, ensure_ascii=False)[:200])\n"
     "        check(\"pre 明细在盘上，且 sha256 逐字等于 witness_digest_pre（即 digest 可重算）\",\n"
     "              bool(p_pre) and os.path.exists(p_pre)\n"
     "              and sha256(p_pre) == pre[\"witness_digest_pre\"],\n"
     "              str(p_pre))\n"
     "        r.write(INSERT_S3)\n"
     "        rc, out = r.postcheck(2, 0, [\"## \\u4e09\"])\n"
     "        check(\"postcheck 通过（本例的前提，不是本例要证的东西）\",\n"
     "              rc == 0 and out.get(\"ok\") is True,\n"
     "              json.dumps(out, ensure_ascii=False)[:200])\n"
     "        q_pre, q_post = out.get(\"witness_path_pre\"), out.get(\"witness_path_post\")\n"
     "        check(\"postcheck 分列两条路径（缺一条，等式就有一边不可定位）\",\n"
     "              bool(q_pre) and bool(q_post) and q_pre != q_post,\n"
     "              repr((q_pre, q_post)))\n"
     "        # bool(p_pre) 不是多余的：两边都缺字段时 None == None 会给出一个空洞的 PASS，\n"
     "        # 而本例要挡的恰恰是\"两条路径都没有\"这一种。\n"
     "        check(\"pre 路径与 preflight 印的那条逐字相同\", bool(p_pre) and q_pre == p_pre,\n"
     "              repr((p_pre, q_pre)))\n"
     "        check(\"post 明细在盘上，且 sha256 逐字等于 witness_digest_post\",\n"
     "              bool(q_post) and os.path.exists(q_post)\n"
     "              and sha256(q_post) == out[\"witness_digest_post\"],\n"
     "              str(q_post))\n"
     "        check(\"两个 digest 相等 → 两份明细字节也应相等（等式的两边真的同一份前像）\",\n"
     "              bool(q_pre) and bool(q_post)\n"
     "              and os.path.exists(q_pre) and os.path.exists(q_post)\n"
     "              and (out[\"witness_digest_post\"] != out[\"witness_digest_pre\"]\n"
     "                   or open(q_pre, \"rb\").read() == open(q_post, \"rb\").read()))\n"
     "\n"
     "\n"
     "def main():\n"
     "    for fn in (case_happy, case_wrong_count, case_wrong_section, case_deletion_counted,\n"),

    ("               case_symref_retarget, case_pseudorefs_excluded):\n",
     "               case_symref_retarget, case_pseudorefs_excluded,\n"
     "               case_witness_paths_printed):\n"),
]


def apply_patches(raw, patches, label):
    text = raw.decode("utf-8")
    for i, (old, new) in enumerate(patches, 1):
        n = text.count(old)
        if n != 1:
            sys.exit("锚点断言失败：%s 第 %d 处命中 %d 次（须恰 1）\n%r" % (label, i, n, old[:80]))
        text = text.replace(old, new, 1)
    return text.encode("utf-8")


def report(name, base_raw, final_raw, out_path):
    with open(out_path, "wb") as fh:
        fh.write(final_raw)
    d = _vb.line_delta(base_raw, final_raw)
    print("== %s -> %s" % (name, os.path.basename(out_path)))
    print("   base   sha256 %s  %d bytes  %d lines"
          % (hashlib.sha256(base_raw).hexdigest(), len(base_raw), d["base_line_count"]))
    print("   final  sha256 %s  %d bytes  %d lines"
          % (hashlib.sha256(final_raw).hexdigest(), len(final_raw), d["final_line_count"]))
    print("   shape  %d added / %d deleted  (LCS %d, ambiguous=%s, possibly %d/%d)"
          % (d["added_lines"], d["deleted_lines"], d["lcs_length"],
             d.get("attribution_ambiguous"), d.get("possibly_added_lines", -1),
             d.get("possibly_deleted_lines", -1)))
    print("   sections %s" % (d.get("sections_touched"),))
    print("   CRLF in final: %d" % final_raw.count(b"\r\n"))


def main():
    jobs = [
        ("CONVENTION.md", CONV_PATCHES, CONV_APPEND, "CONVENTION.proposed-final.md"),
        ("verify_binding.py", VB_PATCHES, None, "verify_binding.proposed-final.py"),
        ("test_verify_binding.py", TEST_PATCHES, None,
         "test_verify_binding.proposed-final.py"),
    ]
    for name, patches, append, out_name in jobs:
        with open(os.path.join(SRC, name), "rb") as fh:
            base_raw = fh.read()
        if base_raw.count(b"\r\n"):
            sys.exit("前提失败：%s 含 CRLF，本脚本的口径是 LF-only" % name)
        final_raw = apply_patches(base_raw, patches, name)
        if append is not None:
            if not final_raw.endswith(b"\n"):
                sys.exit("前提失败：%s 不以换行结尾" % name)
            final_raw += append.encode("utf-8")
        report(name, base_raw, final_raw, os.path.join(HERE, out_name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
