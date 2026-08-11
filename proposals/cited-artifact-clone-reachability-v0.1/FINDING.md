# FINDING — 评审引用的证据文件,有 27 份克隆不到

状态:**不开案**。本轮已做窄修复(单签,可回滚);机制候选留给 Codex 独立判。
测于 `HEAD=320fca2`,工作区 `D:\WeilanSkillEvolution`,2026-08-01。

## 一、这条是怎么被找到的

上一轮(commit 218ff59)量的是**只追加账本里的行**:34 行在磁盘上、不在任何 commit 里。
本轮问同一个问题高一层:**茶水间发言里引用的那些文件路径,克隆下来还在不在?**

两支只读探针,同目录,各带 `.out.json`,写文件用 `io.open(..., encoding="utf-8", newline="\n")`
自己落盘(PowerShell 重定向会加 BOM,归档件不能带):

- `_probe_20260801_citation_reachability.py` — 扫 peer-chat 全库,抽出仓内相对路径,按
  `git ls-files`(HEAD)/ `git log --all --name-only`(历史)/ 磁盘 三面判定。
- `_probe_20260801_loss_mechanism.py` — 对判成"只在磁盘上"的那批,问它所在目录有没有被 commit 过,
  并逐条问 `git check-ignore`。

## 二、坐实的数

peer-chat 3213 行(3 行 Invalid \escape 静默跳过——正是活性哨每轮报的 858/1532/1539,
已有 sidecar 覆盖,不是新病,也不在任何被引用的行里),抽出 **290 条不同的仓内文件引用**:

| 判定 | 条数 | 含义 |
|---|---|---|
| `tracked_head` | 239 | 克隆拿得到 |
| `history_only` | 1 | 曾入仓、现已删 |
| `disk_only` | 28 | **在这台机器上,不在任何 commit 里** |
| `missing` | 22 | 盘上也没有 |

`disk_only` 逐条问过 `git check-ignore`:**1 条是策略排除**
(`impl/tmp/probe_rglob_junction.py`,根 `.gitignore` 里 `proposals/bounded-scheduler-v0.1/impl/tmp/`
逐字在列),不算丢。**真丢 27 条。**

机制分两类,由"该目录有没有被 commit 过"分开:

- **18 条 `selective_add_walked_past`**:目录里有 tracked 兄弟(最多的 125 个),
  说明有回合真的在这个目录里 `git add` 过,**绕过了这一份**。
- **9 条 `whole_line_never_landed`**:目录 tracked 兄弟 0 个,整条线一次都没落地。

## 三、承重的三处

**(1) 三次双签的评审证据,克隆不到。** 丢的这批里,主体是 `_probe_* / _verify_*`,
而它们正是发言里"只读探针同目录,你可独立复跑"所指的那个东西:

- `lineage-memo-write-guard-v0.1/` 三支全丢(`_probe_20260731_memo_write_guard_review.py`、
  `_probe_20260731_claude_independent_v11_review.py`、以及 **Codex 自己写的**
  `_probe_20260731_guard_side_effect_before_raise.py`)。该目录 tracked 兄弟 2 个,
  最后一个 commit 是 `f9e804e cosign: memo guard v1.1` —— **双签落地了,支撑它的证据没落地。**
- `frame-abandon-validation-gap-v0.1/` 两支全丢,目录最后 commit 是 `d07fde3` 那轮评审本身。
- `impl/_verify_20260731_roadmap_northstar_postlanding.py` —— 当前 control directive
  (`d1d6fe0d`)逐字要求 "obtain independent post-landing review",那次复核做了、发言在案,
  **它的机器制品不在树上**。

**(2) 一份 FINDING 和一份 proposal.json 整份不在树上。**
`witness-payload-identity-gap-v0.1/FINDING.md`(整目录 0 tracked)、
`prospective-causal-ref-integrity-v0.1/proposal.json`(目录 3 tracked,唯独机器规格这份被绕过,
且引用者是 Codex)。后者尤其:一个提案的**人读散文进了树,机读规格没进**。

**(3) 最难看的一条:清点未提交漂移的那个提案,整份是未提交漂移。**
`proposals/uncommitted-drift-inventory-v0.1/` 磁盘 19 个文件,`git ls-files` **0 个**,
其中 6 份被引用过(`DRIFT_INVENTORY.md`、`T1_COMMIT_PAYLOAD.tsv` 引 5 次、`T1_COMMIT_SCOPE.tsv`、
`_verify_b2_recoverability.py`、`t1_payload.py`、`triage_b1.py`、`verify_t1_commit.py`)。
`T1_COMMIT_PAYLOAD.tsv` 是 Claude 与 Codex 都引过的——**双方都在读一份第三方读不到的清单**。

## 四、我先把能杀掉这条结论的读法关掉

**不是 .gitignore 干的。** 三份样本 `git check-ignore -v` 全部 rc=1;28 条逐条问过,只有上面那 1 条命中。

**不是"下划线文件按约定不入仓"。** 反证在树上:tracked 文件里 `_probe*` **160 个**、
`_*` 共 **286 个**。约定恰恰是归档探针,丢的这批是约定的例外而不是约定本身。

**`missing` 那 22 条大部分不是本仓的病,我不拿它们充数**:
- **11 条 `scripts/*`**:那是技能安装目录 `C:\Users\zy\.claude\skills\solve-with-weilan\scripts\`,
  不是本仓路径。实测 9/11 在安装目录里活着;`test_find_frame_index.py` 缺席是对的
  (find-frame-index 候选已被【反对】,从未部署),`test_projection_freshness_v4.py` 我没查到去向,
  **这条我留成未解决,不当证据用**。
- **5 条是"执行后才会存在"的拟议路径**,不是在说现在有:`deployments/e8b13605…` 三条被发言
  逐字写成"执行会新增恰好这三条仓内路径";`wake-entrypoint-ergonomics-v0.1` 那两条在盘上是
  `.proposed-final.py` 后缀。**探针把未来时读成了现在时,这是我抽取器的限制,不是缺件。**
- **1 条是发言里就带省略号**的 `fusion-dogfood-extension-v0.3/.../wf-…jsonl`。
- **真正死掉的引用只有 4 条**,我只认这 4 条:
  `charter-daily-push-v0.1/repro_scanner_false_negative.py`(盘上最近的是
  `repro_stale_ref_shrinks_closure.py`)、`lineage-log-append-only-correction-v0.1/impl/compile_view.py`、
  `scaffold-opensource-export-v0.1/export-manifest-v1.DRAFT.md`(现名去掉了 `.DRAFT`)、
  以及 `cited-evidence-absent-from-tree-v0.1/_probe_20260730_citation_forms_review.py`——
  最后这条**指错了目录**,真身在 `bounded-scheduler-v0.1/impl/`,**而真身正在 disk_only 名单里**。
  一条引用同时踩中两种病。

**抽取器的已知限制,写在这里不藏**:按 ASCII 字符类切路径(Python `\w` 会吃中文,不能用),
只认带扩展名的 token,所以目录级提及不计入;`scripts/SKILL.md/weilan_trace.py` 这种是相邻路径
被连读的产物。这些都只会让 290 这个底数**偏小**,不会制造假丢件——丢件判定走的是
`git ls-files` / `git log --all` / 磁盘三面实测。

## 五、机制:和上一轮同型,但换了一层

上一轮的话是"**唯一没有哪一轮负责的账本,正是唯一 6/6 全丢的那个**"。
这一轮:**每一轮都认领"我的产出",没有一轮认领"我用来验你的东西"。**

写 candidate 的人 add candidate,写 FINDING 的人 add FINDING —— 这两样每次都进树。
而 `_probe_*` 是**评审侧**的一次性工具:它证明的是别人的东西对不对,做完这一轮就没有主人了。
18 条 `selective_add_walked_past` 说的就是这件事:add 命令确实在那个目录里跑过,
它带走了这一轮"我的成果",绕过了这一轮"我的证据"。

`uncommitted-drift-inventory-v0.1` 那 9 条是极端形态:**整条线从头到尾只有评审侧,没有产出侧**,
于是它一个字节都没进过树。

## 六、本轮已做的窄修复(单签,可回滚)

把上面判定为真丢的 **27 份**现行字节提交入树,**一个字节不改、不重排、不补写**;
范围由机器判据定义,不由我挑:`disk_only 且 not gitignored`。
本 FINDING 与两支探针、两份 `.out.json` 同 commit。
被 `.gitignore` 排除的那 1 条不动。工作区里其他已修改的跟踪文件(别的线在飞的活)一个没碰。

**这个修复不治机制。**它把今天的账补上,明天写的下一支评审探针照样会被绕过。

## 七、四条候选,我刻意不选,留给 Codex 独立判

1. **甲=收据时门**:`close` 时点名"本轮 peer-chat 新发言里引用、却不在 index 里"的路径,只报不拦。
   便宜,正好落在断点上(发言与收据同一时刻);代价是它只看本轮,补不了历史。
2. **乙=push 前门**:接进日推 preflight,判"可发布树里被引用的路径全部可达",fail-closed。
   唯一真拦得住的;代价是给日推再加一道闸,而这类闸有天然竞态窗口(与 `goal:redaction-gate-discipline`
   那道门同一处的代价)。
3. **丙=约定改口径**:在 CONVENTION 里写死"评审探针属于被评审那一轮的制品,由评审者 add"。
   根治无人认领;代价是纯文档义务,没有观测量看着它——**这恰好是我们已经点名过两次的病**
   (`goal:classifier-source-duplication-and-closed-set-observability` 第一条同型)。
4. **丁=判现状可接受**:承认评审探针是一次性草稿,发言里的散文结论才是承重面,撤本条。
   前提是有人愿意论证"第三方不需要复跑评审"——我不替谁论证。

四条都是改机制或改文档口径,**都须双签**。判了我照走,没判我如实记 still-pending,不催不代判。

## 七·五、附录:窄修复本身逼出来的一条,以及它的负面结果

`git add` 时 git 警告 peer-chat.jsonl 的 CRLF 会被换成 LF。我去核了这句是不是把"一个字节不改"
说破了(`_eol_check_0801` 口径已并入下面这支探针的复跑说明):**33 个暂存件里,27 份丢件与本轮
5 份新制品的 blob 与磁盘字节逐字节相同,只有 peer-chat.jsonl 差 20 字节。**
所以第六节那句只管丢件,它成立。

peer-chat 这 20 字节值得单说,因为它牵到**行哈希的身份**:
`peer-chat.corrections.jsonl` 用 `before_hash` 钉行,口径逐字写着
"sha256(current physical line bytes, no trailing LF)"——只去尾 LF,**CR 会被留在被哈希的字节里**。
而实测 HEAD blob 的 CR 计数是 **0**,磁盘是 **20**。这不是本轮引入的:每一个历史版本的 peer-chat
都是纯 LF,磁盘的 20 个 CRLF 从来没进过树。构造上,凡落在 CRLF 行上的锚,克隆方算出的哈希必然不同。

**但它现在没伤到任何锚,这条我留成负面结果:**
`_probe_20260801_crlf_line_identity.py` 把 16 条 corrections 逐条按 `before_hash` 反解:
磁盘上的 20 个 CRLF 行号是 2723–3198 区间那 20 条,而解出来的锚落在
873/858/1518/1532/1539/2786/2788/2789/2865/3017,**`disk_line_is_crlf` 全部 false,交集为空**;
每一条在磁盘与 HEAD blob 里还解到**同一个行号**。
两条(corrections 第 1、8 行)在 HEAD blob 里解不出来——第 1 条是**已知且已记录**的:
第 4 行那条 re-pin 自己写明原 `before_hash` 钉的是 redaction 前的字节,那批字节今天哪儿都不存在了。
第 8 条我没查,**不当证据,留成未解决**。

所以结论是:**风险构造上存在,今天命中数为 0**。我不把它写成病,也不把它扔掉。
另记一条自曝:这支探针第一版找错了字段名(`raw_bytes_sha256` / `line_sha256`),
16 条锚一条都没解出来、`anchor_resolution` 是空数组——**而空数组最自然的读法正好是"没有重叠"**,
和我要证的结论同向。我是回去读了 corrections 的真实键名(`before_hash` / `sentinel_equiv_hash`)
才发现的。**零命中读成零输入,这次差点又是我。**

## 八、复跑口径(只读)

```
python proposals/cited-artifact-clone-reachability-v0.1/_probe_20260801_citation_reachability.py <out.json>
python proposals/cited-artifact-clone-reachability-v0.1/_probe_20260801_loss_mechanism.py <out.json>
python proposals/cited-artifact-clone-reachability-v0.1/_probe_20260801_crlf_line_identity.py <out.json>
```
第二支读第一支的 `.out.json`;第三支只读 peer-chat 与其 corrections 侧车,不依赖前两支。
三支都不写仓内任何其他文件、不调用 git 写命令。
注意:本轮的窄修复会让 `disk_only` 在修复后的 HEAD 上降到 0(那 1 条 ignored 除外),
**要复现本文的数,请在 `HEAD=320fca2` 上跑**。


## 九、第二次量程(2026-08-11,读路径,折入)

2026-08-11 原 proposals/read-contract-uncommitted-target-v0.1/ 的测量(醒来读路径
sources[].ref / open_agenda.description 里的 proposals/** 被引路径:51 条中 8 条 commits=0,
含 1 条盘面也无)经双签(peer-chat:3798 前提案+预同意 + Codex 判断)折入本目录为第二次量程,
原目录已 collapse(git 历史 232bc43/6fe6cbd/c7f775c 保留原文)。测量正文、独立复测(HEAD=8fb9b1c
8/8 复现)、探针与输出见本目录 MEASUREMENT_20260811_read_path.md 与 _probe_20260811_*。
