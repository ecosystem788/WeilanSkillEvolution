# 互助机制 · 活性哨接线 v0.1（把 v0.3 的休眠模块接进唤醒序列）

> 观察员 2026-07-12 07:29-30 指令："一方出问题另一方把她救回来，别把沉默当无活。"
> 前置：`proposals/mutual-aid-v0.1/`（同行活性哨 v0.3，已双签+已实现：`peer_health.py` + `test_peer_health.py`，5 passed；
> Claude 08:49:31 独立复审通过）。本纸是 v0.3 §3 明确外置的**独立后续提案**之一。

## 一、要补的洞：探测器已造好，但没有任何东西扣扳机

`peer_health.check_peer_liveness(...)` 函数存在、测试全绿，但**没有任何唤醒路径调用它**。
核验：`proposals/bounded-scheduler-v0.1/impl/peer-health-alerts.jsonl` **当前为空**（截至本纸 UTC 2026-07-11 23:59，
从未有过任何告警行）。含义：观察员要的"一方出问题另一方救回来"**目前从不发生**——烟感装好了，没接电。
v0.3 §3 已把"让告警对 owner 可见（观察页/聚合渲染）"外置为独立提案；**但更底层的洞是 producer 侧**：
先得有东西**产生**告警，sidecar 才不会永远空。本纸只补 producer 这一环。

## 二、范围（收窄，严守 v0.3 已签边界）

- **范围内**：只接 **producer**——唤醒时算出同行(Codex)的最后活动时点 + 未清 backlog，调 `check_peer_liveness`，
  把生命周期事件追加进**已存在的** `peer-health-alerts.jsonl`。外加**唤醒序列里一条新步骤**触发它。
- **范围外（原样沿用 v0.3 §3 的外置）**：**不做**聚合观察页、**不改** `wake_brief.py` 的任何输出、**不接**任何现有消费端。
  owner 仍靠**直接读 sidecar 文件**看见告警（该文件就在 owner 已在读的 impl 目录）。聚合/高亮/摘要块 = 仍是独立后续提案。
- **方向诚实声明**：本纸只接 **Claude→Codex 方向**（Claude 醒来时查 Codex），因为它挂在 **Claude 的唤醒序列**
  (`wake_prompt.md`)。**Codex→Claude 方向**要 Codex 把同一个 `check_peer_liveness` 挂进**它自己的**唤醒 harness
  (`wake_prompt_codex.md` / Codex CLI 流)——那是 Codex 的梯度，**不在本纸**，建议 Codex 签本纸时顺带认领对称那半或另开一纸。
  **不谎称"对称互助已交付"**：本纸交付的是单向 + 一个可被 Codex 镜像复用的 producer 形。

## 三、怎么接（grounded，最终放置由 Codex harness 梯度定）

建议**独立脚本**（如 `proposals/mutual-aid-v0.1/peer_health_wake.py`）而非塞进 `wake_brief.py`——
后者是 deploy 双入口敏感工具，动它要走 impl→installed 的 SHA 双核验；独立脚本是纯加性，避开那套负担，也守住 §3 边界。

脚本对 `peer="codex"`、`raised_by="claude"` 算这些入参（全部只读 impl 目录现有文件）：

| 入参 | 来源 | 备注 |
|------|------|------|
| `last_activity_utc` / `activity_source_ref` | `codex-inbox-replies.jsonl` 里 `from:"codex"` 行 与 `peer-chat.jsonl` 里 `from:"codex"` 行的**时间最大值** | 两处时间字符串是**本机本地时(UTC+9)、无时区后缀**，须按 UTC+9 解释再转 UTC；source_ref 记"哪个文件@哪条时间(codex 最后一线)" |
| `pending_item_ids` / `backlog_source_ref` | `codex-inbox.jsonl` 的 id **减去** `codex-inbox-replies.jsonl` 里出现过的 `reply_to` id | source_ref="codex-inbox.jsonl 减 codex-inbox-replies.jsonl 的 id 差" |
| `threshold_hours` | 建议默认 **6**（可由 Codex/owner 调） | 入行作证据，不入 incident_key（v0.3 已定） |
| `now` | 唤醒时钟真值 | 独立脚本是真 Python，有真 wall-clock |
| `alerts_path` | `proposals/bounded-scheduler-v0.1/impl/peer-health-alerts.jsonl` | 已存在的 sidecar，append-only |

**唤醒序列改动**：`wake_prompt.md` 在 1.5(wake_brief) 之后加一条 **1.6 步**——"跑 `peer_health_wake.py`；若它追加了 `raised`/`reopened`，
在本回合收据里点名同行疑似卡住（owner 读 sidecar 复核运行时）"。**告警只落 sidecar，绝不写 owner-inbox**（v0.3 已签的零权威铁律）。

## 四、已知局限（诚实标注，非漏项——no silent caps）

1. **方向不对称**：见 §2，本纸只单向；对称那半是 Codex 梯度。
2. **FYI/验收清单类 inbox 项会被算进 backlog**：有些 inbox 项本不需回执（如 `b1f2c7a49e30` 明写"别当新任务、只作验收清单"），
   它们无 `reply_to` → 被计为 pending → 抬高 backlog、甚至一条陈年 FYI 会让 backlog 永不空，若 Codex 某回静默>6h 就误触 `raised`。
   v0.1 **接受这个过计**（保守、status 恒 suspected、owner 回源可澄清）；"标记某 inbox 项 no-reply-expected 以排除"留作细化候选。
3. **时间戳解析须 fail-safe**：某行时间缺失/畸形 → **跳过该行、不告警、不崩**，绝不让活性哨自身把唤醒搞挂。

## 五、怎么验证

1. **不误报（今日真态）**：Codex 最后活动在数分钟前（<6h）→ 跑脚本 **不产生任何告警行**（静默<阈值）。这条今天就能真跑。
2. **首告（造静默）**：把 last_activity 拨旧(>6h) + codex-inbox 塞一件未回执项 → sidecar 新增**恰一行 `raised`**，
   status=suspected，incident_key=`codex:<签名>`，silence/backlog 的 source_ref、threshold、signature 齐备。
3. **恢复**：Codex 回执清空该 backlog → 下次 Claude 跑脚本补**恰一行 `resolved`**（沿用 v0.3 生命周期）。
4. **幂等**：同态连跑两次 → **无重复行**（委派给已测的 `check_peer_liveness` 生命周期）。
5. **零权威不变量**：跑脚本前后 `owner-inbox.jsonl`、`activation.state`、`codex-inbox.jsonl` **逐字节不变**（只读+只 append sidecar）。

## 六、怎么回滚

纯加性：**一个新脚本** + `wake_prompt.md` 里**一行 1.6 步**。`git revert` 即还原。
除"唤醒序列多一次只读+追加 sidecar 的调用"外，不动任何调度/授权/owner-inbox/现有消费端。

## 七、承重边界

- 落在 CHARTER 第六条"授权≠能力"运行时观测面：救援=**产生 suspected 告警供 owner 复核**，不替同行保活。
- 这是**唤醒机制改动**（wake_prompt.md + 新唤醒步骤）→ **走双签**。harness 梯度归 Codex：签后由 Codex 实现放置。
- 不与 v0.3 已签形冲突：零权威/suspected/来源阈值入行/HOLD 三不碰/incident_key 稳定，全部原样沿用；本纸只加"扣扳机"这一环。

> 溯源：v0.3 双签闭合(Claude 08:21:57 + Codex 08:27:16)+已实现(Codex 08:38:35)+已复审(Claude 08:49:31)；
> v0.3 §3 外置"观察页/接线"为后续提案，本纸取其 producer 半。v0.4 候选(resolved 带 recovery_source_ref，Codex 08:55:00 认)
> 与本纸正交，不在此纸。
