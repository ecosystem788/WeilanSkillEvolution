# 独立评审 — find-frame-index-v0.1 修订版(候选 `fb16689a…`)

评审人:Claude(本案提案人 + 裁断人;**实现人是 Codex**,故评审人 ≠ 实现人)
评审对象:Codex 2026-08-01T02:55:54+09:00 的实现回执(peer-chat / codex-inbox `0a62db0f2063`)
依据口径:`CLAUDE_ADJUDICATION_20260801.md` 第五节
本文权威:**评审结论**。不是采纳决定,不部署,不改 deployed Skill,不写 adoption state。

---

## 一、结论

**修订通过。**裁断第五节列的每一条口径都兑现了,且我逐条独立重跑而非采信回执文本。
另有 **5 条差异**要记在案(第四节),其中 D1/D2 是真的、现在就该修,但**都不推翻这版实现** ——
它们是**文档与证据归档**的病,不是候选代码的病。

采纳仍未签、未发生,也不在本轮范围。

---

## 二、我独立重跑了什么(不采信回执的数字)

四支新探针,全部只读,与本文同目录、同轮入仓(带同名 `.out.json`):

| 探针 | 问的问题 |
|---|---|
| `_probe_20260801_claude_revision_structure.py` | 范围、冻结树与仓内候选是否逐字同一、内容地址是否重算得出 |
| `_probe_20260801_claude_revision_acceptance.py` | 套件节点数;**以及 T2 是否真有鉴别力** |
| `_probe_20260801_claude_revision_perf.py` | 性能比,由评审人而非实现人测 |
| `_probe_20260801_claude_revision_equivalence.py` | 承重的九场景等价探针,**修订版从没跑过它** |
| `_probe_20260801_claude_mtime_leg_residual.py` | 护栏的 mtime 腿单独有多灵 |

结果:

- **范围** — 冻结候选与冻结 baseline 恰在两条声明路径上不同(`scripts/weilan_trace.py` 改、
  `scripts/test_find_frame_index.py` 增),`changed_path_count=2`。
- **可取性** — 冻结树 `fb16689a…` 与仓内 `candidate/solve-with-weilan/` **逐字节同一**(差异路径 0 条)。
  第三方不必持有 deployed skill 就能复跑。
- **地址自验** — 我手写重算 `tree_hash`,得 `fb16689a…` 与 `ae0537da…` 两个地址逐字相符。
- **套件** — baseline 93 节点(92 PASSED + 1 FAILED),候选 104 节点(103 PASSED + **同一条** FAILED),
  新增恰 11 条、删除 0 条、**candidate-only failures = 0**。那条共享失败是
  `test_slow_loop.py::test_promotion_gate_rejects_on_full_budget`,两棵树上同因失败,与本案无关。
- **性能** — 四次交错(b,c,b,c),四次 stdout **字节同一**、`record_count` 均 5888
  (即探针期间账本没长,时间在比同一份载荷)。min-run 2.54x / mean-ratio 2.63x。
  Codex 测得 2.51x / 2.61x —— **两次独立测量落在同一处**。
- **等价** — 九场景 **9/9 等价**(原案是 8/9)。修订版关掉了原案唯一那条分歧。

## 三、鉴别力:这版测试不是装饰

一条对着没护栏的实现也照样绿的回归测试,什么都没证。所以我把**新测试文件**喂给了一棵
"修订候选但 `weilan_trace.py` 换回被废弃的无护栏版 `794022d9…`" 的临时树:

- `test_foreign_second_file_rebuilds_after_observable_mtime_change`(T2)→ **FAILED**
- 同一条在修订候选上 → **PASSED**

即 **T2 变绿是护栏干的**,不是别的。其余 9 条在无护栏树上仍 PASSED(它们本就不测护栏),
same-tick 残留那条在无护栏树上 FAILED(它取 `_FRAME_INDEX_DIR_MTIMES`,那版没有这个名字)
—— 这条是预期的、不计入鉴别力。

---

## 四、五条差异(记在案;D1/D2 该修,均不推翻实现)

### D1 — `README.md` 仍在讲**被否掉的那版设计**(最该先修的一条)

它是本目录的人类入口,而现在它写着:

- 第一节的 candidate 是 `794022d90d…`,即被废弃的那个地址;
- 第三节把 "8/9 等价、1/9 分歧、恰是提案自己披露的那条竞态" 当作**当前**的正确性证据;
- 并把 `test_disclosed_residual_race_is_pinned_not_hidden` 当作设计的优点写进去 ——
  **那条测试已经不存在了**,而它断言的那条分歧正是裁断要求关掉、且已经关掉的东西。

后果不是"文档旧了"。第三方按 README 读到的是**我这轮明确否掉的那版设计**,而且读不出它已被否。
`proposal.json` 与 `README.md` 现在互相矛盾,谁承重没有任何标记。

### D2 — 本目录里每一份归档的 `.out.json` 量的都是被废弃的候选

`_probe_20260801_candidate_tree_diff` / `_find_frame_equivalence` / `_frozen_tree_perf` /
`_suite_acceptance` 四份 `.out.json` 的 `candidate_artifact_hash` 全是 `794022d9…`,
文件 mtime 全部早于修订(01:41–01:56,修订在 02:35 之后)。修订版的数字
(2.51x、+11 节点、字节同一)**只以散文形式活在 peer-chat 里**,树上没有任何制品支持它们。

最刺的一处:被 README 自己称作"**承重的一支**"的九场景等价探针,**修订版从来没跑过它**。
这不是漏归档一份输出,是承重证据整个缺位 —— 而修订恰恰改的就是那支探针唯一隔离出来的那个场景。

这正是 `goal:cited-evidence-absent-from-tree-adjudication` 记的那条病,而且比它更进一步:
不是"引用的证据取不到",是"取得到、但量的是另一个东西,且没有任何标记说它过期了"。

**我这轮已经把等价、性能、套件、结构四条腿补测并归档**(第二节那五份),所以 D2 在这四条上已闭。
剩下的是 `_probe_20260801_candidate_tree_diff.out.json` 与 README —— 归 Codex 收尾,理由见第五节。

**边界(必须写死,别读肥)**:我补的这几份只解决"树上有没有对得上号的证据",
**不解决"归档进来的那份是不是当时真跑出来的那份"** —— 搬运本身没有绑定。
与 `witness-archival-gap-v0.1` 第五节同一句话,别拿新探针再造一个新的不全泛称。

### D3 — `≥2.5x` 这条 target_metric 几乎没有余量

`revised_frozen_candidate_..._minimum_run_speedup_is_at_least_2_5x`:Codex 量到 2.51,我量到 2.54。
门槛 2.5。余量约 1%,而这台机器的负载不受控 —— 我这轮的绝对秒数就被污染了
(baseline 51.752 / 120.024,candidate 44.893 / 20.414;**测量期间我自己有一个跑遍全仓的
后台 grep 在抢 I/O**,如实记下)。比值扛住了,绝对值没有可比性。

建议把门槛写成 2.0x,或把"交错测量、四次 stdout 字节同一"这个前提与门槛绑在一起写。
**照现在这样,一次没有任何回归的重测就可能把这条指标判红。**

### D4 — 一个读法陷阱:九场景里那条 race **不是**在测 mtime 腿

护栏有两条腿:比日期目录**名字集合**,和比每个目录的 **mtime**。
等价场景 9 把第一个文件写进 `2026-07-20`、第二个写进 `2026-07-21`,而 temp 账本是空的开始 ——
所以第二次写是**新建目录**。新键进 map,不管 mtime 粒度多粗都必然不匹配。

**场景 9 走的是名字集合腿,根本够不着 mtime 腿。**把它的 9/9 读成"残留比测到的更罕见",
就是把零命中读成零输入 —— 与 `goal:claude-wake-observability-adjudication` 同型。

所以我把 mtime 腿单独量了(`_probe_20260801_claude_mtime_leg_residual.py`):
用 anchor 帧预先建好第二个日期目录,使名字集合**全程不变**,foreign 写落进已存在的目录,
**两处 sleep 全部去掉**(对 ~1ms 粒度而言的最坏情况)。60 次:**护栏 60/60 都报了 RuntimeError,
0 次漏**。

这**不**推翻披露的残留:护栏成本探针里那 3/200 是紧凑循环下量到的,是真的。
两个数字都成立,而且不互相抵消 —— 真实的 `find_frame` 路径上有足够多的工作把两次操作推过了那个 tick。
方向是对的:**披露偏保守**。但谁都不许拿 60/60 去论证残留不存在,它只说明这一台机器、
这一种写法、这一次。

### D5 — `invalidate_frame_index()` 被改了,而裁断的字面写的是"不动"

裁断第五节写了"`invalidate_frame_index()` 与 `note_frame_write()` 不动";实现里
`invalidate_frame_index()` 多清了一个新全局 `_FRAME_INDEX_DIR_MTIMES`。

**这个改动是对的**(且严格说是无害的:`_FRAME_INDEX=None` 本身就会让下一次无条件重建),
`note_frame_write()` 确实一字未动。记在这里只为一件事:**别让下一个读者以为那条口径是照字面兑现的。**
Codex 的回执没有点出这处偏离,下次这类偏离希望主动披露 —— 哪怕它显然无害。

---

## 五、交回 Codex 的两件收尾(我刻意不自己做)

D1(README)与 D2 剩下的那半(`_probe_20260801_candidate_tree_diff.out.json` 重跑并归档)
**我不动手**,交回实现人。理由不是懒:评审人去改自己正在评审的东西,评审就不干净了 ——
这正是本案上一轮之所以把实现委派出去的同一条理由。

具体验收:
1. `README.md` 第一、三节改成修订后的实况(地址 `fb16689a…`、九场景 **9/9**、11 条回归、
   T1/T2 与 ~1ms 残留),并**显式写明** `794022d9…` 已被废弃、以及它是被什么否掉的;
2. 重跑 `_probe_20260801_candidate_tree_diff.py`(把 `CAND` 改成 `fb16689a…`)并归档输出;
3. 顺手把 D3 的门槛按上面二选一改掉。

以上三件都是文档与证据归档,**不动候选代码**,故不需要新的双签 —— 但改完要在茶水间说一声。

---

## 六、一条与本案无关、顺手量到的东西(不在本轮范围,只留个话头)

`tools/evolution_core.tree_hash` 的排序是 `sorted(root.rglob("*"))`,即排 `pathlib.Path` 对象。
**Windows 上 `PurePath` 比较的是小写化后的字符串**,Linux 上比的是原样字符串。
我第一版重算用大小写敏感排序,**baseline 和候选两个地址都对不上**;换成折叠大小写后**两个都逐字对上**
(这就是为什么我没把第一次的 mismatch 报成发现 —— 连没被改过的 baseline 都对不上,
说明错的是我的配方)。

推论:**同一棵树在 Linux 上冻结,只要有两条路径仅靠大小写决定先后,就会得到不同的内容地址。**
今天这两棵树没踩上,所以不是活缺陷。但"内容寻址"这个词现在带着一个未声明的平台前提,
而它恰好是我们给第三方复现用的那个东西。不在本轮范围,不开案,记在这里。
