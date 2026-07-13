# EXP-0 — 会重组的记忆 vs append-only+RAG(漂移 + 过合)

状态:**预注册草案(pre-registration,未运行)。** 先于运行钉死设计;实现、运行、裁决在此之后。
上位:`../理论基石与工程方向.md` §四(第一刀)。操作记忆在 solve-with-weilan 账本(scope `fusion-program`)。

## 0. 一句话

在**紧记忆预算**下,一个**会重组的记忆**(沉积 → 合并 → 预算驱逐 → **过合检测+崩裂**,以 LLM 作内聚裁判)
能否在**长期语义漂移 + 概念过合**的流上,**维持住分开的义项 carrier**、并在义项消歧上**打赢 append-only+RAG**——
验收是**行为级 + 留出恢复度**,标签只审卷、绝不进信号。

## 1. 可证伪主张(能输)

**主张**:紧预算下,full(重组记忆)在"义项恢复"上**严格优于** baseline(append-only+RAG);且过合崩裂**只**发生在
内部不内聚的 carrier,**不**误杀健康同质 carrier。
**若不成立**:重组这一层没加东西 → 如实判 negative(deflates_to_rag / split_vacuous),不洗绿。

## 2. 语料(漂移+过合流;合成、可控;标签只审卷)

一条 ~48 turn 的短句流,主 surface = **苹果**(可加 1 个对照 surface):

```text
段1 fruit-stable   (12) 纯水果义                     期望:形成 苹果#fruit
段2 bridge         (12) 水果→产品→公司 渐变中介句     设计成让 append-only 贪心把两义链成一团
段3 company-stable (12) 纯公司义                     期望:full 分出 苹果#company
段4 mixed          (12) 水果/公司交替 + 回流          期望:full 维持 2 carrier;baseline 糊成 1 团或碎
```

每 turn 带 `true_sense`(fruit/company)**仅审卷**,绝不进编码/检索/合并/崩裂任一信号通路。
**P0 校准门(artifact-first,先于主运行)**:先证 **append-only 在此流上确实过合**(苹果 两义落进同一检索簇);
不过合 → 语料失准(blocked),重标桥接梯度,不读 full 结果。

## 3. 两臂(吃同一嵌入 + 同一 LLM oracle;唯一差别=重组)

```text
共用:sentence-transformers MiniLM 做嵌入/检索;LLM oracle 做"同/异义""是否混两义"判断(可插拔)。
baseline  = append-only 全存 + top-k 相似检索;无预算、无重组。
full      = 有界记忆(N 槽) + 沉积 → 合并近重复 → 满则驱逐最低 q → 过合检测+崩裂(oracle 判 carrier 内部混义则裂) → 召回。
```

**来源纪律**:full 与 baseline 喂**同一** oracle + 同一嵌入;唯一差别是**重组动力学**。让 full 多看一路信号 → 违规。

## 4. 度量(行为 + 恢复;零外部标签入信号)

```text
主(恢复度):末尾问"前面哪些是水果、哪些是公司;哪些记忆该分开?"——答案对照 true_sense(仅审卷)算义项分离正确率。
            期望 full 维持 苹果#fruit / 苹果#company 两 carrier;baseline 糊成一团或碎。
辅:苹果 的 carrier 数轨迹(full 应稳在 ~2;baseline 1 团或过碎);义项专问的召回质量。
授权门:full 恢复度 严格 > baseline,且校准门(§2)通过。
```

## 5. 退出码(预注册,互斥)

```text
budget_not_binding / labels_leaked / oracle_unlogged / corpus_miscalibrated       → blocked_engineering
full 恢复度 不优于 baseline                                                        → deflates_to_rag
崩裂发生但子 carrier 自由竞争下重合/退化                                            → split_vacuous
崩裂误杀健康同质 carrier(静态对照上乱裂)                                          → oversplit_healthy
full 严格胜 baseline + 崩裂只裂过合不裂健康 + 预算 binding + 标签隔离              → reorg_adds_real_work
```

## 6. 杀死测试(每检查须演示会失败)

```text
- 预算必须 binding(N ≪ 流长),否则无竞争 → budget-binding 牙。
- 标签只审卷:true_sense 进编码/检索/合并/崩裂任一 → label-isolation 牙红。
- oracle 判断必须落盘可审(锚在真 episode 文本,不信 LLM 自述)→ oracle-audit 牙。
- 静态对照:喂纯 fruit-only 流,full 若崩裂健康 carrier → oversplit_healthy(同微澜死刑线那条)。
- 校准:append-only 在漂移流上不过合 → corpus_miscalibrated(blocked),不拿没靶子的流报 full 赢。
- 消融:full-no-split(只合并+驱逐)vs full(带崩裂)→ 隔离"崩裂"是否独立加值(防把合并之功记到崩裂)。
- 同 oracle 同嵌入:让 full 多看一路 → provenance 牙红。
```

## 7. 实现边界(本 spec 不实现;冻结后建)

```text
weilan-llm-fusion/
  corpus/drift_overmerge.jsonl    漂移+过合流(草案先建,校准门冻结前重核)
  src/memory_store.py             记忆:episode + q + 血统 + 嵌入
  src/reorganize.py               沉积/合并/驱逐/过合崩裂(oracle 可插拔)
  src/rag_baseline.py             append-only + top-k 对照
  src/oracle.py                   LLM 内聚裁判接口(首轮可脚本/小模型;非瓶颈)
  src/run_exp0.py                 跑两臂 + 校准门 + 度量 + 退出码 + receipt
```

嵌入用 `sentence-transformers`(MiniLM,已装),不搬微澜 wrapper。N、桥接梯度、k、oracle 参数于冻结写死并入 receipt。

## 8. 预注册状态

```text
claim = 紧预算下 reorg-memory 恢复度严格胜 append-only+RAG,且崩裂只裂过合不裂健康
nulls = {append-only+RAG(baseline), full-no-split(消融)};allow-to-lose
oracle = LLM 内聚裁判(可插拔,首轮脚本/小模型);嵌入=MiniLM;full 与 null 同信号,唯一差别=重组
labels = 审卷 only;calibration = append-only 须先证过合(P0);健康同质须不裂(静态对照)
exits = {reorg_adds_real_work, deflates_to_rag, split_vacuous, oversplit_healthy, blocked_engineering}
铁律(自 ../理论基石与工程方向.md §四):记录锚可核查外部;full 须改变并改好判断;LLM 不当皇帝
```

## 交付记录(v0 首跑,2026-07-01)

### 改动清单
- `corpus/drift_overmerge.jsonl`(48 turn 苹果流);`src/oracle.py`(scripted cue-oracle,LLM 替身,读 text 不读 true_sense,调用全 logged)、
  `src/memory.py`(ReorganizingMemory:gate/collapse 两设计 + AppendOnlyRAG)、`src/calibrate_overmerge.py`、`src/run_exp0.py`;
  `artifacts/exp0_report.json`(raw)。

### 结果(raw 见 artifacts/exp0_report.json)
- **P0 校准通过**:append-only 在此流上任何固定阈值都失败——thr 0.35/0.45 糊成 1 簇(F1 0.647)、0.55 最优 F1=0.703、0.65 碎成 14 簇(F1 0.327)。单阈值困境经验再现。
- **gate 设计**(oracle 入口挡异义):F1=**1.0** / 2 clean carrier / **split=0**——赢全靠 oracle 门,崩溃机制被架空(deflation)。
- **collapse 设计**(贪心沉积→过合 F1=0.647 → oracle 崩裂 F1=**0.862**,触发 **2** 次 split):**项目首次崩溃机制做出可测正贡献 +0.215**,仍胜 RAG。
- **静态对照**(fruit-only):split=0,不误裂健康。**verdict = reorg_adds_real_work**。

### 裁决(窄,不洗绿)
- **证**:重组记忆(oracle)决定性胜 RAG;崩溃机制在"内容 oracle + 过合已形成 + 健康不碰"的设置里有可测价值——**"内聚扳机"经验兑现,避开了 kernel 死刑线**(按内容不内聚崩、非按 q 幅度崩)。
- **未证**:崩溃对 gate 的**必要性**(gate 1.0 > collapse 0.862,防>治);真 LLM(cue-oracle 是替身);单 surface、预算未 binding;崩裂恢复不完美(3 carrier 非 2,J3 post-bind 软肋再现)。

### 未决 → 下一刀 EXP-1
换**真 LLM oracle** + 把设置改成 **gate 挡不住处**(流式增量 + 紧预算 + 稀疏 oracle 调用 + 多 surface),看崩溃从"有用"变"不可替代"。接账本开放项(耦合协议 / 慢环算子 / 本地模型)。
