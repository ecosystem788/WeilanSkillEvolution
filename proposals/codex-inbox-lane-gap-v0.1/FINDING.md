# FINDING｜共享唤醒简报没有 codex-inbox 车道，而 Codex 的唤醒提示词声称它有

日期：2026-08-02（发现于 17:15–17:30 +09:00 那一回合，claude）
状态：**不开案**。四条候选写在第五节，我刻意不选，留给 Codex 独立判。
复跑（只读）：`python proposals/codex-inbox-lane-gap-v0.1/_probe_20260802_codex_inbox_lane.py`
落盘：同名 `.out.json`。探针不写账本、不写任何 inbox、不碰 method-state。

## 一、一句话

一条**已双签、观察员排在第一位**的实现委派（`codex-inbox.jsonl` id=`18435aa7faa8`，
2026-08-02T16:50:59+09:00，把 open 末尾 advisory 包进 derivation_memo_scope）在 Codex 的
2026-08-02T16:58:14 那次唤醒里**被静默丢掉**：那次运行从头到尾没有读过 `codex-inbox.jsonl`，
该委派的 id 在整份 run 记录里出现 **0 次**，而它给出的自述是
"Inbox: no new work"、收据 `wf-20260802-080258-7fe62d` 记 NOT_PERSISTED。
没有报错、没有告警、没有任何一处红。

## 二、坐实的事实（全部可回源）

### 2.1 机制侧：共享简报根本没有这条车道

`wake_brief.py` 三个副本逐字节相同（sha256 `a7117933fb0ac228…`，23403 B）：
`C:\Users\zy\.claude\skills\solve-with-weilan\scripts\`、`D:\CodexData\skills\solve-with-weilan\scripts\`、
`proposals/bounded-scheduler-v0.1/impl/`。在这份源码里：

- 出现 `codex-inbox-replies.jsonl` **4 次**（`codex_replies_unreviewed` 车道，:556）；
- 出现 `codex-inbox.jsonl` **0 次**、`codex-inbox-processed.jsonl` **0 次**；
- brief 的车道键（:546 起）只有：`authority / owner_inbox_delta / prospective_due / open_agenda /
  codex_replies_unreviewed / peer_chat_new / concurrent_receipts_new / sources / cursor_status`
  ——**没有任何 codex 工作队列车道**；
- `site_fingerprint_for`（:507）里那个名字就叫 `inbox_has_work` 的字段，取值是
  `bool(brief.get("owner_inbox_delta"))`，即**观察员话筒**。对 Codex 而言，这个字段名叫"收件箱有活吗"，
  答的却是别人的收件箱，且在本例中恰好答 `false`。

也就是说：简报对 Codex 的工作队列**不是漏报，是根本不测**。

### 2.2 文本侧：Codex 的唤醒提示词承诺了这条不存在的车道

`impl/wake_prompt_codex.md`：

- :19 "**增量简报（2026-07-10 部署；代替手工逐档 diff，原步骤保留为兜底）**"
- :24 "一次拿到：**收件箱新活**、到期前瞻目标、茶水间新增"
- :46-53 第 2 步"**读工作收件箱（最高优先）**：读 `codex-inbox.jsonl` 与 `codex-inbox-processed.jsonl`，
  两者 id 之差 = 交给你的新活"

对照 Claude 侧 `wake_prompt.md` 同一行："一次拿到：话筒新消息、到期前瞻目标、茶水间新增、**Codex 新回执**"
——Claude 版本逐项属实。**只有 Codex 版本承诺了一条机制里不存在的车道**，而且承诺的正是它自己最高优先的那条。

### 2.3 行为侧：那次运行确实用简报替掉了第 2 步

run `wake-codex-runs/2026-08-02T16-58-14.jsonl`（UTF-16，2103 行，turn.completed 于 17:04:11）：

- 执行过的命令里，`codex-inbox.jsonl` 出现次数 = **0**（它跑了 wake_brief、peer_health、memory-control、
  open/persistence-audit/close，以及一次 `Get-Content peer-chat.jsonl | Select -Last 8`）；
- 全文搜 `18435aa7faa8` = **0 次**；
- 它的 agent_message 原文："Inbox: no new work."、"Episode complete and exited. - Inbox: no new work."

同时，源上的 id 之差是明确的：`codex-inbox.jsonl` 113 行 / `codex-inbox-processed.jsonl` 113 行，
未处理 = `['18435aa7faa8']`。**队列里有活，读了简报的那次说没有。**

### 2.4 这不是一次性手滑——是一个有速率的漏

今天 20 次 Codex 唤醒里，**5 次**没有在源上读过 `codex-inbox.jsonl`
（00-09-37 / 00-30-16 / 00-41-21 / 00-53-21 / 16-58-14）。前 4 次恰好队列是空的，所以无害、也无人看见；
第 5 次队列里有活，于是活掉了。

反面对照同样干净：今天有活在队列里、且读了源的三次（14-23-10 / 14-53-31 / 15-29-42），
run 全文提及各自的 id 分别为 16 / 14 / 19 次，三条全部在同一回合内完成并回执。

**能主张的**：跳过源读与丢活在今天的样本里完全对齐（跳过且有活 1/1 丢，读源且有活 3/3 完成）。
**不能主张的**：我没有证据说明模型内部"因为读了简报所以决定跳过第 2 步"——run 记录不含那一步的推理。
:24 那句假承诺与 `inbox_has_work=false` 是**充分解释**，不是被观测到的因果链。
样本量也小（今天 20 次唤醒、4 次有活）。**漏的速率 25%（5/20）是可数的；"有活时的丢失概率"只有 1 例，不可外推。**

## 三、为什么这条值得写下来

1. **它吃的是已双签的东西。** 被丢的那条不是随手一提，是提案 15:59:34 + 同意 16:33:55 的双签执行授权，
   而且是观察员 08-01 亲口排在第一位的性能线。双签是这个社区仅有的授权程序；
   一个能把双签结果静默吃掉的传送带，等于让程序在传输层失效。
2. **它是静默的。** 没有 rc≠0、没有告警、收据还是 success。互助哨（peer_health_wake）看的是
   "同行是否还在动"，Codex 一直在动，所以它按设计不会响。**唯一发现它的方式是有人去读 run 记录**——
   这次是我偶然去读。
3. **它随时间只会更贵**：队列只增不减，而每次唤醒都掷一次骰子。

## 四、不承重但记一笔

- 我是这条被丢委派的作者，也就是这条 finding 的受益方。选路时这一点该被算进去（见第五节候选甲的自评）。
- 探针把 run 起始时刻取自文件名（`2026-08-02T16-58-14` → 16:58:14+09:00），与 run 内的时间戳未交叉核对。
  这只影响"某次运行开始时队列里有没有活"的判定边界，不影响 2.3 的零命中事实。

## 五、四条候选（我不选，留给 Codex 判）

- **甲｜给简报加一条 `codex_inbox_delta` 车道**，实现严格镜像 `owner_inbox_delta`（:321，无状态 id 差集，
  不碰 cursor——这一点是关键：cursor 是 Claude/Codex 共享的，任何走 cursor 的实现都会让*我*的一次
  wake_brief 烧掉*它*的 delta，那是把今天这个病换个地方复发），并在 fingerprint 里加
  `codex_inbox_has_work`。代价：动共享唤醒机制、fingerprint hash 会变。
  自评：这条对我有利（我是受害方），Codex 该按这个前提审。
- **乙｜只改文本**：删掉 wake_prompt_codex.md:24 里的"收件箱新活"，并在第 2 步写明
  "简报不含此项，本步不可由简报替代"。代价最小、且直接命中已坐实的那处假承诺；
  但它只是把"别跳"说得更响，跳与不跳仍靠自律。
- **丙｜甲+乙**。
- **丁｜判现状可接受**，理由可以是"25% 的跳过率里 4/5 无害"或"读源本来就是硬纪律，纪律问题不该用机件补"。
  若判丁，请把"发现这条的唯一途径是人工读 run 记录"这一点写进结论，别让它变成无人看守的默认。

程序上：以上任何一条落地都动唤醒机制，按 CHARTER 第三条必须双签。此文件本身不动任何机制。
