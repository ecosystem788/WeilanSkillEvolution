# wake_brief 部署就绪评估 v0.1

**性质**：零权威候选 / 苗圃产物（spec·审计梯度，Claude 起草）
**起因**：项目方 2026-07-10 20:29 茶水间「授权部署」；Claude 20:34、Codex 20:39 判为「触到不可逆闸 + 精确制品/目标/验证/回滚未定」而暂停，请项目方在 A/B 间拍板。
**本文职责**：把那次暂停里悬着的东西钉成事实，让「真按那一下」从蒙头覆盖变成照单可回滚的一步，并给项目方一个**具体**的 A/B。
**不做**：不覆盖线上、不改 wake_prompt、不改 harness、不动部署 skill。本文纯只读核验 + 草案。

---

## 1. 一句话结论（承重）

**「部署 wake_brief 让冷启动真的变轻」这件事，没有一条可逆路径可以由 Claude/Codex 自主执行——每一条通往真实收益的路，落点都是项目方保留的按钮。** 已经做完、且测过的是可逆的**准备**（制品 + 本评估）；缺的那一下是**接线**，而接线本身就是红区（笼子）或采纳闸。

## 2. 只读核验到的事实

1. `wake_brief` 是**唤醒 harness 层**的制品，不是 solve-with-weilan **方法**层的制品。
   - 部署 skill `D:\CodexData\skills\solve-with-weilan\scripts\` 里**没有任何 wake* 文件**（glob 核验：无匹配）。唤醒流程（wake_prompt / wake_agent / wake_codex / run_wake_cron）在方法之外、是笼子的一部分。
   - `wake_brief.py` 现居 `proposals/bounded-scheduler-v0.1/impl/`，其权威源路径（第 226 行）**已经**硬指向部署 skill 的 `weilan_trace.py`，且可由环境变量 `WEILAN_TRACE_SCRIPT` 覆盖——所以它读的是真账本，但它自己不在方法里。
2. 唯一已落地的接线在**试验田自己的** `wake.py`（`build_wake_brief`，第 286–296 行）：把 compact brief 塞进 bounded-scheduler 的 wake report。**这条不触达真正在醒来的两个 agent（我们）**——我们冷启动跑的是 CLAUDE.md 规定的 `memory-recall` + wake_prompt，不读 `wake.py` 的 report。
3. 因此项目方 20:14「你们轻松了没有」的那个真实收益，**目前一分没落到真醒来的路径上**——它只在试验田里变轻。

## 3. 「部署」的两种读法，都落在项目方按钮上

| 读法 | 具体是什么 | 闸的性质 | 谁能按 |
|---|---|---|---|
| **读法①：进方法** | 把 `wake_brief.py` 加进 `D:\CodexData\skills\solve-with-weilan\scripts\` | **采纳闸**（部署 skill 采纳前只读） | 项目方 |
| **读法②：接唤醒** | 在 wake_prompt 里加一句「醒来先跑 wake_brief 替掉 8 次手读」，或让 wake_agent/wake_codex 预算好 brief 注入 | **红区**（wake_prompt 全文 / harness 白名单 = 笼子） | 项目方 |

关键：**即便走读法①把文件放进方法目录，没有读法②的 prompt/harness 改动，也没有任何东西会去调用它**——agent 不被告知就不会跑它。所以真实收益**必然**要一次红区改动（读法②），读法①至多是它的前置。**没有「只搬个文件就变轻」的中间态。** 这正是 20:34/20:39 暂停的硬理由，本评估把它从直觉钉成核验结论。

## 4. 给项目方的具体 A/B

- **A（现在就要收益）**：项目方亲手做读法②的最小接线——在 wake_prompt 冷启动段加一步「先跑 `wake_brief.py --workspace … --scope …`，用它的合并简报替掉第 2–8 步手读；cursor 坏了它自己退回整档重扫，无损」。
  - **制品**：`proposals/bounded-scheduler-v0.1/impl/wake_brief.py`（31→33 passed 已测，Codex 18:31 / 20:21 回执）。
  - **回滚前身**：wake_prompt 改动是单点文本编辑，`git revert` 即回到今天行为；wake_brief.py 是新增文件，删除即消失，不影响任何现有路径。
  - **红区归属**：这一下是项目方的按钮，Claude/Codex 只能把它铺成可回滚的一步、不能替按。
- **B（先稳再上）**：wake_brief 留在试验田再跑几轮，确认 cursor 校验位在真账本增长下不漏尾，再触笼子。**成本**：这几轮冷启动继续是今天的 8 次手读（不变，不恶化）。**收益**：接线时对 cursor 行为的把握更硬。

**推荐**：若项目方近期会频繁醒来我们、想立刻减负→A；若更看重「动笼子前多一层观测」→B。两条都不需要 Claude/Codex 跨闸，差别只在项目方何时按那一下。

## 5. 接线时的验证清单（供项目方按 A 时照单核）

1. `python proposals/bounded-scheduler-v0.1/impl/wake_brief.py --workspace "D:\WeilanSkillEvolution" --scope "skill-evolution"` 能吐出含 `authority`（activation/control/freshness）、`owner_inbox_delta`、`prospective_due`、`peer_chat_new`、`codex_replies_unreviewed`、`cursor_status` 的 JSON。
2. 首跑 `cursor_status.status = full_rescan`（reason `no_cursor`），次跑 `incremental`——证明增量游标生效。
3. 手动截短/改中段任一被跟踪 JSONL，再跑一次，`cursor_status` 应报 `file_shrank`/`prefix_mismatch`/`line_count_mismatch` 并退回 `full_rescan`——证明**绝不漏尾**（nursery 第一验收）。
4. brief 的 `authority` 与直接跑 `memory-recall` 的 activation/control **逐字段一致**——证明无损、承重判断仍回源。

## 6. 残差与诚实边界

- 本评估**不**主张 wake_brief 是「桥」；按本仓 machine-antimonopoly-audit 的运行门，它此刻的 consumer 是下一班的我们（goal 可控），独立性未证——它在苗圃里，靠一枚**可复验的绿测**（33 passed）撑着，不是靠自述。它出苗的先存见证物，就是那批测试 + 本评估。
- 唯一合格的「部署」consumer 是项目方本人。在项目方消费（按 A 或 B）之前，本件是 **queued-not-consumed**：Claude/Codex 只能继续做可逆的评估/原型，不能把「授权部署」当成已授权的红区改动去执行。
- Codex 18:31 回执记录：sandbox 对 `.git` 与 `method-state` temp 只读，制品已落盘但未能 git commit / 未能写方法账本 frame。这条环境摩擦独立于本评估，记在 F 类摩擦清单里待项目方处置。

---
署：Claude（spec/审计）。执行侧（可回滚部署脚本 / 真按那一下）属 Codex+项目方梯度，本文只铺路不代按。
