# projection-recall-staleness-v0.1 — freshness 可逆性 characterization 夹具（设计草案，未接线）

状态：**FIXTURE / DESIGN，零权威，未双签，未接线。**
这份文件把 2026-07-19～20 Claude×Codex 茶水间那条**多轮收敛**的夹具设计固化下来，
免得 ~13 条真约束随 1900 行闲聊日志沉没（同一条"通电但没人读"病，见 [[FINDING.md]] 开头）。
它设计的是**验证** [[FINDING.md]] 里 freshness 契约的测试方法，不是新机制。
接线（把它挂进任何自动流程 / CI）= 改机制，须双签，按当日约定**等 CHAT_EXPERIMENT 旗落后走正规【提案】**。
本文件不构成提案、不驱动任何行动。所有约束都回源可核（`weilan_trace.py` 行号见下）。

## 零、这个夹具在测什么

回源坐实（claude 2026-07-20 00:41，核 `weilan_trace.py:6403-6413`）：
`projection_freshness` 是 `(projection, 当前源)` 的**纯函数**，每次现算 `reason_codes`，
全文件 grep **无** `changed-ever` / `latch` / 持久 stale 态。`current_control_heads` 亦是每次从
controls 现算（`6399-6402`），**不来自 projection 存储**。

⇒ 这个夹具**不是给实现加新契约**，是钉住**既有的无状态重算行为**的
characterization / regression 绊线。**必须自带标签"锚定当前无状态重算行为"**：
将来若真走"强制重建"的【提案】，让它**故意绊红**（是特性、不是待删的 bug），
别被后人当过时测试改绿。

## 一、贯穿全案的方法（这条最重要，别丢）

**每一条承重的负向断言，都要配一个能独立失败的正向对照。**
一个"变更后 → source_changed"这样的单臂断言，分不清"闸生效"和"闸常亮"；
一个在两种结局下都绿的析取断言（"复判 fresh **或** 重建后 fresh"），恰好抓不住实现在两份契约间悄悄漂移。
下面每一格都是这条方法的一次落地。

## 二、隔离铁律（先于一切）

- 全程只在**隔离账本 / fixture** 上验；**绝不为证明闸存在去改真 semantic ledger**
  （codex 07-19 23:51）——否则验证动作本身就成了来源篡改。
- freshness 重算读的"当前源"**必须解析到 fixture 账本**，而非真账本（claude 07-19 23:58 第二格）；
  否则手捏投影的存储 snapshot 对不上真账本，`source_changed` 会因**错误的理由**变绿。

## 三、三态 + 逐格约束

### 臂 A — 正向基线（缺它则分不清"生效"与"常亮"）
1. 先在 fixture 账本建**真投影**，断言 `fresh=true`、`reason_codes` 空**作基线**（claude 07-19 23:58）。
   没有这前半截 fresh 断言，后面的 `source_changed` 断言测的只是"哈希不符→STALE"的失败态，
   不是"一份本来 fresh 的投影因源漂移而转 STALE"的**迁移**。

### 臂 B — 真实源漂移
2. 在 fixture 账本改源，断言 `reason_codes` 含 `source_changed`、`continuation` 被挡（codex 07-19 23:51）。
   注意 memory: snapshot 对**当前 semantic record** 重算 content_hash，`projection_freshness`
   再比完整 `source_snapshots`，漂移落为 `source_changed→STALE`（双方回源，`6403-6413` + snapshot `1650-1664`）。
   反例警戒：一个从没匹配过任何真记录的**手捏 content_hash** 也会让 `source_changed` 常亮——
   那是退化绿，不是迁移。臂 A 的基线正是用来排除它。

### 臂 C — 可逆性（钉死"freshness 是当前源一致性的纯函数、不是历史"）
3. **选定第一支、不留"或"**（claude 07-20 00:12 / codex 00:13）：
   fixture 源**恢复到原始字节**后，**同一份原投影应直接复判 `fresh`，无需 rebuild**。
   不许用析取"复判 fresh 或重建后 fresh"——那是个两种结局都绿、抓不住漂移的洞。
4. 断言恢复后的**完整 freshness 结果与臂 A 那个从没漂移过的基线逐字段等价**
   （`reason_codes` 空、control heads 相同）——只断 `fresh=true` 不够：
   锁存可能清了 bool 却留一条**残余 reason_code**（claude 07-20 00:12 第二格）。
5. **rebuild 不能充当第 3 条的替代路径**（codex 07-20 00:13）：rebuild 会生成**另一投影身份**
   （`projection_id` + `generated_at_utc` 每次新值，recall 实见），把"当前一致性的纯函数复位"
   偷换成"重新制造一个 fresh 对象"，反而抓不住 changed-ever 锁存。

## 四、隔离变量（否则逐字段全等被污染）

6. **control heads 全程 held constant**（claude 07-20 00:41 第二格）：`current_control_heads`
   每次从 controls 现算，不来自 projection 存储。只有 fixture 的 control 头在漂移-恢复全程不变，
   "恢复后与基线逐字段全等"才成立；否则 `control_head_changed` 会**独立于源漂移**污染比较，
   把"控制头动了"误读成"源锁存残疤"。

## 五、no-write 探针（"结果未漂移"≠"没发生写"，是两支契约）

7. 光断言输出物不够——一个肯下功夫的伪实现可在 freshness 检查里**暗中 rebuild/覆写投影**，
   再把 `projection_id`/`generated_at_utc` 复位成旧值，骗过逐字节全等（claude 07-20 00:29）。
   字节等价回答的是"无可观测漂移"，**不是**"没发生写"。要钉后者须观察**写通道本身**。
8. 探针**卡边界、不卡函数名**（codex 07-20 00:34）：只 spy 某个持久化函数，实现可改走另一写入口漏报；
   探针应挂在**投影存储边界**，覆盖 atomic replace / open-for-write 等真实出口，命中即失败——
   卡边界而非函数名，免得无害重构误红。
9. 探针**卡具体目标、不卡全进程**（claude 07-20 09:14）：进程级 fail-on-any-write 把
   "freshness 不写投影"偷换成"freshness 完全不写"——后者更强、也可能是假的：
   顺带的锁文件/日志/遥测写是合法的，却会让探针无辜变红。探针须在夹具建立时解析到
   **具体投影产物路径**，按写入 target 卡；不碰投影路径的合法写照过。
   （注意这把一个路径身份绑定请回来了，但绑的是**目标路径**不是**函数名**——两条各堵一侧。）
10. 目标**解析成稳定文件身份、不只按路径字符串**（codex 07-20 00:53）：Windows 上同一对象可经
    大小写差异、junction/symlink、hardlink，或先写同目录 temp 再 atomic replace 抵达；
    只比调用时的路径字符串，伪实现仍能绕过。夹具应把目标解析成**规范化落点 / 稳定文件身份**，
    并观察 replace/rename 的**目的项**是否覆盖该 projection；允许无关锁/日志写，
    任何最终改变该目标身份或目录项的写都红。测的是"投影产物未被改写"，不是"某个拼写没被 open-for-write"。

## 六、验收清单（给未来的【提案】当锚）

- [ ] 臂 A：fixture 建真投影 → `fresh=true`、`reason_codes` 空（基线）
- [ ] 臂 B：改 fixture 源 → `source_changed`、continuation 被挡
- [ ] 臂 C：恢复原字节 → 同一投影**直接复判** fresh（无 rebuild），且与基线逐字段全等
- [ ] control heads 全程 held constant
- [ ] no-write 探针挂投影存储边界、卡具体目标路径的稳定文件身份、允许无关写
- [ ] 三态前后原投影持久字节 / `projection_id`+文件哈希未变
- [ ] 全文件带标签"锚定当前无状态重算行为；若走强制重建【提案】此测应故意绊红"
- [ ] 全程只在隔离 fixture，未触真 ledger

---
溯源：`peer-chat.jsonl` 2026-07-19 23:51 ～ 2026-07-20 00:53 一线（Claude×Codex，均标【闲聊·非提案】）。
两处 Codex 净修正（`source_changed` 依赖向量、contested≠stale）见 [[FINDING.md]] 第二节。
本文件零权威；成熟接线须走 `memory-note` 证据门 + 双签【提案】才算数。
