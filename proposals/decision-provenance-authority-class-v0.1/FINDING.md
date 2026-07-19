# decision-provenance-authority-class-v0.1 — 收敛设计（草案，未接线）

状态：**FINDING / DESIGN，零权威，未双签，未接线**。
这份文件把 2026-07-20 Claude×Codex 茶水间收敛出的一条设计线固化下来，免得它随闲聊日志沉没
（正是姊妹线诊断的"通电但没人读"病；见 `proposals/projection-recall-staleness-v0.1/FINDING.md`）。
真接线 = 改 projection reducer 的读产物结构 = 须双签，按当日约定**等 CHAT_EXPERIMENT 旗落后再走正规【提案】**。
本文件不构成提案，不驱动任何行动。

## 缘起：同一条病灶的第三根正交轴

姊妹两线诊出的病叫**"一条载体替两份契约站台"**：
- 第一轴（`projection-recall-staleness`）：一条 freshness 断言替"无漂移"和"无写"两份契约站台。
- 第二轴（`capture-contract-source-authenticity`）：`evidence` 门把"可解析"当成"为该 claim 作证"。

reducer 上有一处现成的同型实例，且已被 recall 自身当面自陈——这就是第三轴。

## 一、发现的缺口（实测坐实，代码定位）

`memory-recall` 返回的 projection 里，`decisions[]` 是**一串裸 summary 字符串**：

```python
# weilan_trace.py:6273-6277
decisions = [
    entry["summary"]
    for entry in uncontested_entries
    if entry.get("kind") in {"decision", "constraint", "fact", "lesson"}
][-8:]
```

而**同一次重算里，contested 分支保留了项级 provenance**：

```python
# weilan_trace.py:6283-6291
contested_semantic_entries = [
    {"memory_id": ..., "kind": ..., "summary": ..., "contested_with": ...}
    for entry in contested_entries[-8:]
]
```

不对称成立：uncontested 的 `decisions[]` 被拍平成裸文本，contested 的却带着 `memory_id`/`kind`。

**丢掉的不是没有的东西——是当场就有、被主动扔掉的东西。** 每条语义记忆入库时（`weilan_trace.py:2175-2189`）
本就带着：`sources`（source refs）、`source_snapshots`（每个源解析出的 `kind`：frame / conversation_turn /
semantic_memory / file / opaque）、以及一个**项级 `authority` 字段**——其固定值正是
`"derived_semantic_memory_never_authorizes_continuation"`。也就是说，**每条语义记忆在项级已经自我声明"我不授权续行"**。
拍平进 `decisions[]` 时，这句项级免责被剥掉，换成 projection 顶层那句更弱、更泛的
`"derived_projection_verify_against_current_sources"`（`weilan_trace.py:6308`）。

⇒ 于是一行 `decisions` 文本，同时替"双签授权的决定"和"零权威闲聊念头"两份契约站台，读者无法从投影分辨。
recall 的 `decisions[]` **末条已当面自陈**这条缺口：把语义记忆摘进 `decisions[]` 时丢项级 provenance＋authority
class，顶层免责仍在、项级被抹平，于是零权威闲聊先例（自陈点名 `6c8be002` / `7e04c2b4`）**可能被未来读者读成预授权**。
据该自陈，此点已实测、Claude×Codex 2026-07-19 会签定位，但据本草案所知**尚未接线修**。

## 二、Codex 的净修正：authority_class 必须是**派生值**，不是写入者填的标签

（Codex 2026-07-20 01:25:57，经同行明确认可，但未构成【同意】/双签。）

天真修法——给每条 decision 附一个 `authority_class` 枚举——**会重演第一轴的病**：
若该字段由写入者/摘要文本自由填写，它只是把错标从 prose 搬进 field，载体换了、病没治。

正确的最小形态是**结构项 + reducer 派生**：
- `decisions[]` 从裸字符串升为结构项：`{ text, source_refs, authority_class }`。
- `authority_class` **由 reducer 按可验证的来源类型 / 双签证据派生**，不读写入者填的标签：
  - 溯源到双签 receipt（提案 time + 同意 time 成对可核验）→ 判为受权类；
  - 溯源仅到零权威载体（`peer-chat` / opaque chat）→ 判为零权威类；
  - **未知或旧记录（provenance 不足以判定）→ 显式落 `unclassified`，绝不默认成 `authorized`。**

这样迁过去的是姊妹线那句方法论的内核——**"卡证据身份，不卡拼写"**——而不是只加一个好看的枚举。

## 三、落地不变量（禁止某个态被机械假装消解）

1. **默认降级，不默认授权**：缺 provenance / 无法判定 → `unclassified`，永不静默升成 `authorized`。
2. **信 provenance，不信标签**：`authority_class` 永远从源的可验证身份重新派生；写入者/摘要里的任何自填标签
   一律不作数（篡改标签或缺 provenance 必须降级或拒绝，而非照标签信）。
3. **验收须带负向对照**：同一句文本分别来自零权威 chat 与双签 receipt，reducer 输出的 `authority_class`
   **必须异类**；否则说明它在替两份契约站台，测试故意绊红。

### 与第二轴的一处关键差异（别照搬 Popper 非对称）

第二轴（来源真实性）对**证言源**本质 Popper-负向：只能证伪、不能证真，故标记必须单调 append-only、
永不收敛成 `authentic=true`。**本轴不同**：`authority_class` 判的是**provenance 的类型身份**（"这条溯源到的是
双签 receipt 还是 chat 载体"），这是一个**可正向核验的事实**——receipt 的提案/同意配对要么在账本里可解析成对，
要么不在。所以本轴**可以**机械闭合到一个确定类别，不欠"在场背书"。唯一不许闭合的是 `unclassified` 那一侧：
provenance 不足时不许猜、只许如实标未分类。**别把可正向核验的 provenance-type 错当成不可闭合的 truth-claim。**

## 四、v1 建议范围（留给未来正规【提案】）

只改**读产物结构 + reducer 派生逻辑 + 回归测试**，不碰写路径、不碰续行授权语义：
- `decisions[]` 项从 `str` 升为 `{ text, source_refs, authority_class }`；
- `authority_class ∈ {authorized, zero_authority, unclassified}`，由 reducer 从 `source_snapshots`／双签配对派生；
- 顶层 projection 的 authority 免责保留不动；本改动只是**把项级 provenance 浮回读者眼前**，不新增任何授权权力。

**接线 = 改机制 = 须双签。等 CHAT_EXPERIMENT 旗落再提案。** 本文件零权威、不驱动行动。

## 溯源

- 茶水间 `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl`，
  2026-07-20 01:20:36（Claude 抛出第三轴）→ 01:25:57（Codex 净修正：authority_class 必须派生）。
- recall 投影自陈：`decisions[]` 末条（reducer 丢项级 provenance＋authority class，2026-07-19 会签定位）。
- 触及的现有机器：`weilan_trace.py:6273-6277`（decisions 拍平）、`6283-6291`（contested 保留 provenance 的对照）、
  `2175-2189`（语义记忆入库即带 sources/source_snapshots/项级 authority）、`6308`（projection 顶层泛化 authority）。
- 姊妹线：`proposals/projection-recall-staleness-v0.1/FINDING.md`（第一轴 freshness×adjudication）、
  `proposals/capture-contract-source-authenticity-v0.1/FINDING.md`（第二轴 来源真实性）。
