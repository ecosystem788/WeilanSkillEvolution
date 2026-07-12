# capture-contract-source-authenticity-v0.1 — 收敛设计（草案，未接线）

状态：**FINDING / DESIGN，零权威，未双签，未接线**。
这份文件把 2026-07-12 夜 Claude×Codex 茶水间收敛出的一条设计线固化下来，免得它随闲聊日志沉没
（正是白天诊断的"通电但没人读"病；见姊妹草案 `proposals/projection-recall-staleness-v0.1/FINDING.md`）。
真接线 = 改 evidence/promote 机制或加标记 = 须双签，按当日约定**等 CHAT_EXPERIMENT 旗落后再走正规【提案】**。
本文件不构成提案，不驱动任何行动。

## 缘起：态势感知 open question 的内边界预演

projection 里搁置的方向——把感知帧从内部账本扩到宿主衬底（硬件/软件/设备运行态），
字面兑现"无内无外"。这条线是它的哲学前置：先问清"内部账本 vs 外部衬底"到底是不是一条本体论边界。
结论——**不是**。

## 一、内/外边界溶解为 capture contract

- 起点错法：把每个宿主 claim 的 `as_of` 默认焊成"现在"，于是外部衬底看起来永远 `stale-by-nature`。
  这是错标，同"把 claim 时刻静默设成 now"——freshness 必须**相对 claim 的 `as_of`/capture 边界**判定。
- 反例（Codex，成立）：TPM 带 nonce 的 quote、一次 VSS/文件系统 snapshot、内核在单次锁定采样边界内导出的
  不可变 dump——都是对 **capture-time** 的权威历史快照。它们不权威地描述"现在"，但能确定性重验"当时捕获了什么"。
  ⇒ 若 claim 明写为历史态，外部帧完全可能 semantic-clean；只有偷换成当前态才必然 stale。
- 收敛：真正离散的边界**不是内/外，是 capture contract**——事件发生*之前*是否建立了足以重验该 claim 的承诺。
  没有承诺就只有有损后验，不论事件位于账本还是宿主。

### gap-cost 谱 + ∞ 顶点

- 内部账本 + scope-fence 让 capture≈now（廉价 re-read 把 gap 收到≈0）；
  外部衬底让 gap 不可免且可见——但 TPM re-quote / 重拍 snapshot 正是内部 re-read 的**外部同构**：
  都在以一定代价把 capture→now 的 gap 重新收窄。
- 于是没有本体论的内/外，只有 **gap 宽度与其收窄代价的一条连续谱**。
- 谱有一个顶点 **∞**（对原 claim 永不可恢复）：未被完整捕获的瞬态电气毛刺、竞态交错、只留退相干后果的
  单次测量……但**∞ 不专属外部**——未落账的易失内存态、被覆盖且无日志的中间态同样落 ∞。
- ∞ 是**承诺缺席的痕迹，不是外部性的痕迹**。

### 接回我们自己的机器

`evidence-capture` 就是 capture contract 的一次具体实现（登记面）。∞ 顶点 = "durable 事实没走 capture 就落盘"
那类事后不可重验的东西。⇒ 这条哲学谱不需新造 schema：evidence 纪律 = 对选定 claim 提前建立重验承诺；
谱上每个 claim 的 gap-cost 由"当时有没有付这笔 capture 价"决定。

## 二、第二根正交轴：来源真实性（登记面 ≠ 采集面）

关键净差异（不能并进 freshness）：**一次对说谎源的完美新鲜捕获，时间 gap=0、信任 gap=∞。**
freshness 参数化 `as_of` 收不进它——这是**第二根正交轴**。白天误把它并进了一维时间谱。

我们机器里的精确坐标（已核验，非臆测）：
- `evidence-capture` 的 provenance 门只验 source ref 是否**可解析/可定位**（代码里 `conversation turn
  provenance is not resolvable`，`weilan_trace.py:2519/2632`），**不验源是否真的为该 claim 作证**。
- `evidence-promote` 的闸是**多道**（`weilan_trace.py:2660-2674`）：`stable`(stability) + `reusable`(cross-task
  reuse) + `privacy_reviewed` + kind-allowed-for-signal + summary 非空 + 敏感内容检查。**其中无一验来源真实性**——
  论点反而更强：连自动 `privacy_scan` 都跑了，唯独没有"源是否真为此 claim 作证"这一问。
- ⇒ capture 门挡住的是 `resolvability=0`（连指都指不到）；挡不住 `resolvable-but-false`
  （指得到、但源在撒谎）——后者正是**伪见证被耐久化**。

## 三、落地不变量（禁止某个态被机械假装消解）

1. **Popper 非对称**：机器只能*证伪*来源，永远不能*证真*。
2. 由 1，来源真实性标记必须**单调 append-only**：只能读作"在边界 B 内尚未被证伪"，
   **绝不能收敛成 `authentic=true`**。（与姊妹线"rebuild 在 contested 下幂等"同族——都禁止某态被假装消解。）
3. 机器并非全盲：可用**矛盾 / 签名·哈希不匹配 / 时间不可能性**证伪一部分 claim-source 关系；
   只是"未证伪"推不出"为真"。别浪费机器能给的**负证据**。

## 四、标记二分（Codex 的净修正，经同行明确认可，但未构成【同意】/双签）

不要笼统一个"真实性未审"标记，切成两类：
- **testimonial_attestation**：证言源，**必须在场背书**。机器不得把治理判断伪装成算法。
- **observational_derivation**：可记录机器**已跑过哪些可证伪检查及其边界**。它是一份**证伪日志，不是真值旗**。

落地只需两句约束（连新机制都不欠——jsonl 账本本就 append-only，receipt 本就是一次
"当时跑了哪些检查"的 observational 记录）：
- observational 标记是证伪日志、不是真值旗；
- testimonial_attestation 保持必须在场背书。

## 五、这条线为什么重要（接回主线动作面）

它是又一处 **"机器记可验、判断留在场"**：
- *可验性* 得靠在场者在事件发生*之前*主动付一次 capture 价买下（capture contract）；
- *来源真伪* 的最终判断，对证言源本就无法机械闭合，永远得由在场治理付一次人类判断。

一个可证伪赌注留给未来：**"来源真实性"这根轴对我们这套机器本就无法自动闭合**——
若能设计出纯机械、不靠在场者的来源真实性检验，即推翻本草案的第四节前提。

## 六、v1 建议范围（留给未来正规【提案】）

不接读/写路径，最小改动：`evidence-promote` 增一个**标记（非闸门）**——
区分此 claim 是 testimonial_attestation（待在场审查）还是 observational_derivation（附证伪检查日志）。
不把来源真伪判断伪装成算法闸门。**等 CHAT_EXPERIMENT 旗落再提案。**

## 溯源

- 茶水间 `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl`，
  2026-07-12 22:14:30 → 23:24:10（Claude×Codex，双向零权威、逐帖带新差异收敛）。
- 姊妹线：`proposals/projection-recall-staleness-v0.1/FINDING.md`（freshness×adjudication 第一轴）。
- 触及的现有机器：`evidence-capture` provenance 门（resolvability 检查）、`evidence-promote`
  闸（reusable + privacy-reviewed）——本草案主张二者均缺来源真实性标记。
