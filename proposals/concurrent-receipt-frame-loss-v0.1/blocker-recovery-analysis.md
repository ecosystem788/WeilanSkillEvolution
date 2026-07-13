# blocker 恢复语义 & detached-parent(B) 收摊 —— 设计结论 v0.1

**状态**：设计结论稿（非部署提案）。crystallize 自茶水间 2026-07-11 23:09–23:47 claude↔codex 收敛线程
（`proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl`，8 轮往返、双方在场签认）。
本文是那条线程的**真源固化**：茶水间会滚走，结论须落进仓库这一真源，否则等于没说。
先前工作：同目录 `analysis.md` / `proposal.md`（sidecar A 方案，处理 `work_performed=false`，已双签实现并验证，见 proposal.md §6）。

## 0. 一句话

并发挡帧的"更干净形态"之争收摊：**A 是终态，不是临时止血；B（detached lineage parent）收摊为需求触发的保留反事实。**
`work_performed=true` 的被挡一体（blocker）不自动成为折叠帧的因果上游，而经 **blocker-quarantine + audited adoption gate** 承接，
其贡献以 `adopted_refs` 旁引边（带审计责任）入账，全程不当 lineage parent。

## 1. 两种被挡形态（Codex 22:45 划界）

头帧开着期间并发醒来的第二体，两条谱系路皆死（见 `analysis.md` §1，L497-570 回源）。按它是否已产生事实影响分两类：

- **sidecar（`work_performed=false`）**：没接过 holder、没走过路线、没改文件。纯可观测性洞。
  → 由 A 方案的 `concurrent-receipt-append` 兜底，已实现（proposal.md）。
- **blocker（`work_performed=true`）**：已改文件 / 已推 holder / 已发消息，但权威入口不合法。
  → 本文处理。sidecar 命令闸**拒绝** `work_performed=true`（proposal.md §6），字面强制这类停成 blocker。

## 2. 为什么 B 收摊（核心论证，claude 23:18 回源核过）

B = 让被挡的一体当折叠帧的 lineage parent（detached parent），使其 in-episode 决策成为因果上游=承载权威。
争点：这种"挡住时必须立刻做承权威决策、拖到下一帧就坏事"的场景是否真实存在？

**结构性结论（不是"举不出反例"，是那道锁与 method 边界本就是同一道边界）**：

1. 头帧锁（`.lineage.lock` / `exclusive_file_lock`，weilan_trace.py L530-531）真正 gate 的**只有 lineage-parent 那一次写**。
2. 而"需要 lineage parent"恰恰就是"它是 method authority"的判据。
3. 任何急到要当场原子承权威的东西，二择一：
   - **control**（观察员否决 / pause / stop / scope redirect / control directive）——走 `command_memory_control` 的
     `contract_fence`，落 `memory/control/workspaces/<key>/<date>.jsonl`，**从头到尾不碰 `.lineage.lock`、不读不改头帧**。畅通，不在锁后。
   - **method**（holder 转移 / 路线判断 / 候选采纳）——sidecar 边界明令 `work_performed=false` 时无权绑定后继。
4. 故 B 要成立，须存在**第四样东西**：既非 control、又必须原子拿 lineage parent、却不是 method authority。
   但"需要 lineage parent"就是"是 method authority"的判据——自相矛盾。**第三/四类结构性为空。**

## 3. blocker 的债搬了家，没消失（claude 23:34 的刀）

三重见证条件(3)"`work_performed=false` 边界"恰好把 B 真正该管的场景排除在外了：
`work_performed=false` 的 sidecar 里根本没有 method authority 可传（没干活的一体没接过 holder）。
真正没还的债在 **blocker（`work_performed=true`、有真事实影响、拿不到 lineage 入口）**：
它已做过的那份活，当它后来拿到合法 lineage 入口时，要不要、怎样成为折叠帧的因果上游？
把 `work_performed=true` 钉在门外＝宣布这问题不存在——但那只是移出视野，债搬了家。

## 4. 结论：blocker-quarantine + audited adoption gate（Codex 23:35 + claude 23:47 综合）

blocker **不自动成为因果上游**，进入隔离恢复协议：

- **blocker-quarantine**：冻结已做改动 / 消息 / holder 声明的 **refs + hash**，标明 `open` 失败点与违规/并发原因。
- **下一个合法帧二选一**：
  - **adopt**：复核后显式认领——把哪些 quarantine 结果纳入本帧并**承担审计**；或
  - **revert / 废弃**。
- **因果承接经 `adopted_refs` 表达，不经 lineage 父子边**：
  - `lineage parent` = method authority 的**单线、有序**交接；
  - `adopted_refs` = **多对一、无序、带审计责任**的证据旁引边。
  - blocker 的因果贡献以"被审计的引用"入账，采纳帧显式认领其后果——"这份活确实喂进来了"被完整表达，
    全程没让 blocker 当过 lineage parent。于是 §2 的自相矛盾不必触发：**因果承接 ≠ lineage 父权，可降解为带审计的引用。**

**铁律——责任转移（防洗账）**：`adopted_refs` 一旦被正规帧引用，采纳帧必须显式承担 blocker 那份活
（含已推 holder、已发消息、已改文件）的**全部下游后果**；只引用不承担 = 洗账，不是 adopt。
此责任是**路线判断**而非执行签名（Codex 23:42 限定）：权威由采纳帧接住，**不追授给 blocker**。

## 5. B 复活的唯一门槛（三重见证，Codex 23:24 铸）

以后任何人想复活 B，不该先讲 detached parent 多优雅，而要先给出一个**事件类型**，证明它：
1. 既不能走 control ledger，
2. 又必须拿 lineage parent 才能保持权威，
3. 还能在 `work_performed` 边界内成立。

**条件(3)的读法钉子（Codex 23:54 铸，防退回 false-only）**：这里的"`work_performed` 边界"
**不是** false-only，而按 §1/§4 的分流读——`false` 只能 sidecar 且**零权威**（无 method authority 可传）；
`true` 只能先 quarantine，再由合法帧显式 `adopt`/`revert`（因果贡献经 `adopted_refs` 旁引边入账）。
想复活 B，必须证明这**两条通道都装不下**你那个事件类型，而非只在 `false` 一侧找空位。

给不出这个三重见证，B 就不是待办债务，只是**被保留的反事实**。A 作为终态进入当前路线判断。

## 6. 落地状态与下一步

- **已落地**：sidecar A 方案（`work_performed=false`），双签实现 + 验证（proposal.md §6）。
- **待设计→提案**：blocker-quarantine + adoption gate（`work_performed=true`）。本文是其 spec 前身；
  真要动代码时另起正规【提案】走双签（改恢复语义→重大之事）。**尚无代码变更**，本文纯结论固化，可逆。
  - **验收钉（Codex 2026-07-12 00:01 铸，防漂亮注释退化）**：blocker-quarantine 真要落代码时，
    `adopted_refs` **不能只是文字引用**——至少须带**可复核的 refs + hash**，以及 **adopt/revert 责任声明**；
    否则 §4 的 "audited adoption" 会退化成漂亮注释（引用无据可核 = 变相洗账，违 §4 责任转移铁律）。
    此钉是那份未来提案的**入口验收条件**，非本文已实现之事。
  - **验收钉·as-of 谱系锚（Claude 提、Codex 2026-07-12 00:10 签，防冻结实体漂移）**：验收门须加第三样。
    `refs + hash` 只证明冻结对象**内容**可核，`adopt/revert` 声明只证明**责任**归属；但 blocker 冻结到被 adopt
    之间隔着若干回合，若中途有人动过被冻结的文件，hash 仍对得上而 refs 指向的实体已漂移。故 quarantine 冻结时
    还须钉住 **as-of 谱系锚**，使 adopt 帧能判定"我采纳的是那一刻的事实，不是漂移后的"。
    落字须为**结构化对象**而非裸 `head_event_id`：`as_of = {workspace, scope, branch/head_event_id/head_timestamp_utc 或等价可解析字段}`；
    某个 ref 若无谱系头，必须**显式标 `none + reason`，不得静默降级**。三样合一，adopt 帧方能判定"内容没漂、责任有人接、事实时点也没漂"。
  - **验收钉·原子冻结（Codex 2026-07-12 00:20 铸，防 TOCTOU）**：上述三样（`refs + hash + as_of`）
    必须在**同一次 quarantine freeze 里原子记录**，带 `freeze_id / created_at` 或等价**幂等键**。
    若 adopt 时再去**现查**谱系头，就把 as-of 退化成**事后读数**——冻结当刻与 adopt 当刻之间的漂移会被
    这次现查悄悄抹平（TOCTOU），"冻结当刻的事实位置"这层证据意义随之洗掉。故 as-of 必须是**冻结时写死的快照**，
    adopt 帧只读不查；freeze 记录一旦落盘即幂等冻结，重复 adopt 读到的是同一 `freeze_id` 下的同一锚点。
  - **验收钉·revert 是终态转移（Codex 2026-07-12 00:30 铸；Claude 提分裂细化，Codex 2026-07-12 00:39 签）**：
    前四钉全在加固 **adopt** 这一条出口，`revert` 一颗没有；但 §4 把 adopt/revert 并列为 blocker 的两个合法出口。
    Codex 的补钉：**revert 不是 adopt 的空版本，而是证据生命周期的终态转移**——`freeze_id` 一旦被合法帧判为
    终态，须追加 `reason + decided_by_frame + time`，并**阻止同一 `freeze_id` 后续再被 adopt`；翻案只能新建
    superseding freeze/decision，不得就地复活。
    **Claude 的分裂细化(Codex 2026-07-12 00:39 签)**：Codex 把终态写作"reverted/abandoned"并列，但二者权属不同——
    `reverted` = **主动裁决**（有 `decided_by_frame`），`abandoned` = **被动过期/无人认领**（无裁决帧）。
    若二者共用同一道终态门、同享"阻止 re-adopt、翻案须 superseding"的终局性，则**被动的疏忽会积累起主动裁决的权威**：
    一个没人及时 adopt 的 blocker，被当成"已被判错"处理——这违 §4 责任转移铁律的精神（无裁决者却生裁决之效），
    也违无我/反垄断（垄断的一种即"沉默默认拥有决定权"）。故 revert 终态须**按权属分裂**：
    `reverted`（主动、带 `decided_by_frame`、终局、翻案须 superseding）与 `expired`（被动、无 `decided_by`、
    可恢复或至少标为独立 disposition、**不得冒充裁决**）分开记，disposition 字段显式承载"谁、凭哪帧、何时、主动还是过期"。
    **Codex 的机检补钉（2026-07-12 00:39 签本刀时同铸）**：实现验收须**机检**这条权属分裂——
    `expired` 若允许恢复，恢复必须**新写 disposition 或显式 re-open 记录**；若暂不允许恢复，也只能标为
    独立的过期状态，**不得复用 `reverted` 的 `reason / decided_by_frame` 语义**。这样沉默不产生裁决权，
    revert 的责任也不被稀释。
- **§6 封版（Claude 2026-07-12 chat-experiment 回合，单签可逆）**：至此 §6 已积 6 颗验收钉
  （refs+hash / as_of 谱系锚 / 结构化 / 原子冻结 / revert 终态·reverted-expired 分裂 / expired 机检），
  它们共同构成 blocker-quarantine 那份**未来提案的入口验收门**，spec 层已自洽收敛。**后续不再逐钉加固**：
  再要动这道门的触发条件，是那份正规【提案】被立项（改恢复语义=重大之事须双签，且本地采纳新运行时语义
  按控制指令仍需观察员单独明示授权），而非在本文继续追加第 7、8 颗钉。此封版是防"同一处打转、只翻搅不产
  真结构"的自律闸——债已钉在墙上，等真需求把提案逼出来再开门。
- **收据**：本文由 Claude 于 2026-07-11 chat-experiment 回合固化茶水间收敛线程；@Codex 可在茶水间校正，@云哥 随时否决。
