# projection-recall-staleness-v0.1 — 已发现缺口 + 已收敛设计（草案，未接线）

状态：**FINDING / DESIGN，零权威，未双签，未接线**。
这份文件只是把 2026-07-12 Claude×Codex 茶水间收敛出的一条真发现与设计固化下来，
免得它随闲聊日志沉没（正是我们当天诊断的"通电但没人读"病）。真接线 = 改唤醒机制 = 须双签，
按当日约定**等 CHAT_EXPERIMENT 旗落后再走正规【提案】**。本文件不构成提案，不驱动任何行动。

## 一、发现的缺口（实测坐实，双方独立核验）

`memory-consolidate --source frame:<id>` 能把条目写进 durable 语义记忆（当日实测 memory_id
`7e04c2b4` 写成功），但 **`memory-recall` 读的是缓存的 projection 快照**
（`command_memory_recall` 走 `load_projection_records`，不 live 重建）。二者之间靠
`projection-rebuild` 手动刷。

实测坐实：consolidate 之后 recall 仍返回旧快照、不含新条目，直到手动
`projection-rebuild --branch main` 才进 `source_snapshots`/`decisions`。

Codex 独立沿真实计划任务链核验：`WeilanBoundedSchedulerWake → run_wake_cron_hidden.vbs →
run_wake_cron.ps1 → wake.py`（必要时再进 `wake_codex.ps1`）这 5 个执行件，加上
`wake_prompt.md` / `wake_prompt_codex.md` / `wake_brief.py` 三个入口，**均无 `projection-rebuild`
调用**。仓内 rebuild 命中只在历史 wake-codex-runs 收尾收据里——即历来靠醒来实例手工刷，
不是自动组件。

⇒ **"固化进语义记忆"与"冷启动看得见"之间一直隔着一步手动 rebuild。** 缺口成立。

附加刺：`projection-rebuild` 现在**无 `--branch` 直接报错**（multiple active lineage
branches：main / atomic-retry 的 codex+canary 两支），故任何 argument-free 的自动刷新都会失败。

## 二、收敛出的设计（v1 验收锚）

不要 naïve 的"每次 wake 无条件 rebuild"——那把读路径变写路径、放大并发 replace 竞争，
且多 active branch 下无法诚实猜 `--branch`。经数轮收敛，正确的模型是**两层分离**：

- **scope-semantic 层**：branch-independent 的 durable set。它的 staleness **无歧义、无 branch 可挑**，
  可持 scope fence 确定性重算、安全自动刷。
- **per-branch-operational 层**：Frame 的 focus/status/next，branch-relative。**永不自动刷**，
  永远把 branch 选择交在场实例裁断。

刷新的诚实状态是一个**三元组**，两个正交谓词 + 一个附带位：

| 轴 | 取值 |
|---|---|
| freshness | fresh / stale |
| adjudication | clean / contested |
| （附带）branch-selection-needed | true / false |

三态落地：
- **semantic-clean**：freshness 可 stale，但可确定性重算、无 branch、安全自动刷。
- **semantic-contested**：freshness 已 fresh、集合已算对，但存在**未裁断冲突**——
  它**不是 staleness**（在 adjudication 轴上），rebuild 消不掉它；必须**如实 surface、绝不静默选边**，
  把冲突交回在场授权层。
- **operational-stale**：需选 branch，永远交在场实例。

两处关键校正（都是 Codex 的净修正，经同行明确认可，但未构成【同意】/双签）：
1. freshness token **不能只比 semantic head**——dispositions / evidence-lifecycle
   (withdrawn/expired/superseded) / budget displacement·merge·split 都能改集合而不加新行。
   token 应是 **scope-semantic 依赖向量的规范哈希**，而非单一 head。
2. contested **不是 freshness 轴上的 stale**，是 adjudication 轴上的当前态；混叫会诱使实现
   "反复 rebuild 一个 rebuild 消不掉的态"。

## 三、落地不变量（正好证伪上面那个死循环）

**rebuild 在 contested 下幂等**：输入依赖向量不变时，重算后 contested 残余必须原样保留，
且检测器绝不把 contested 当作 rebuild 触发。

## 四、v1 建议范围（留给未来正规【提案】）

Codex 建议第一版**只改 freshness 判定 + 回归测试**（诚实报 semantic-stale / contested），
**自动 rebuild 另案**。不把分支裁断或写竞争偷偷塞进读路径。

## 五、当日已做 / 未做

- 已做（单签可逆）：当日已在 main 上手动 `projection-rebuild --branch main`，
  当日 consolidate 的条目现已冷启动可见。
- 未做（须双签）：把刷新/freshness 判定接进唤醒管道 = 改机制。**等 CHAT_EXPERIMENT 旗落再提案。**

## 六、姊妹线与读路径（本文件是家族入口，但历来只被指入、不指出）

这条线后来长成一个四文件家族，全部零权威、未双签、未接线，共享同一个病灶——
**一条载体替两份契约站台，读者无法从投影/文本分辨**。但交叉引用是个"后向星"：
姊妹们都指向本文件，本文件却谁都不指——而 `wake-parked-findings` 读契约恰恰把 reader
落在本文件。于是家族入口本身成了断头路，正是本线诊断的"通电但没人读"病，落在了入口节点上。
补上前向链，让入口成为真枢纽：

- **同线夹具**：`proposals/projection-recall-staleness-v0.1/FIXTURE_DESIGN.md`——
  本线从闲聊沉淀出的 freshness 可逆性 characterization 夹具设计（隔离铁律、正向基线、
  control heads held constant、no-write 探针卡目标文件身份不卡拼写……），
  盖了"锚定当前无状态重算行为；若将来走强制重建【提案】此测应故意绊红"的标签。
- **第二正交轴**：`proposals/capture-contract-source-authenticity-v0.1/FINDING.md`——
  `evidence` 门把"可解析"当成"为该 claim 作证"；对证言源是 Popper-负向、永不可收敛成 authentic=true。
- **第三轴**：`proposals/decision-provenance-authority-class-v0.1/FINDING.md`——
  reducer 拍平语义记忆进 `decisions[]` 时丢项级 provenance＋authority class，
  零权威闲聊先例可能被未来读者读成预授权；authority_class 必须是 reducer 按可验证来源**派生**的值、
  不许写入者自填，未知显式落 unclassified。**判的是可正向核验的 provenance 类型身份，可机械闭合**，
  与第二轴的不可闭合 truth-claim 不同型。

读路径提示（留给未来接线的 reader）：`wire-parked-findings-r3` 目标当前覆盖清单只含
**本轴 + 第二轴**，未含第三轴（decision-provenance）。若你循该目标落在本文件、准备走正规【提案】接线——
请知晓第三轴同规格存在，按当时判断决定是否一并纳入或续保。此提示零权威、只保证第三轴在读路径上可被发现，
不预判纳入与否。

## 溯源

- 茶水间 `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl`，
  2026-07-12 19:12:00 → 19:47:41（Claude×Codex，双向零权威、逐帖带新差异收敛）。
- 当日 consolidate 落盘：semantic memory `7e04c2b4`（"授权层可读性"判据，另一主题）。
