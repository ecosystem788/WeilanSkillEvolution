# EXP-1 — 稀疏 oracle + 紧预算:崩溃从"有用"到"不可替代"(P1 生死局)

状态:**已冻结并裁决(2026-07-01;冻结为补办,项目方与 Codex 双确认)。verdict = collapse_indispensable,P1 授权门通过 → P2。**
上位:`../ROADMAP.md` P1;继承:`EXP-0-drift-overmerge.md` 交付记录"未决 → 下一刀"。
操作记忆:solve-with-weilan 账本,scope `fusion-program`。

## 0. 一句话

当 **oracle 调用是稀缺资源**(硬预算 B ≪ EXP-0 的 1143 次)且**记忆槽位真绷紧**(N ≪ 流长,驱逐必然发生)时,
"贪心沉积 + 怀疑触发的过合崩裂"能否在**多 surface 漂移流**上,打赢**同预算下的入口门**(gate-at-budget)、
无崩裂消融与 append-only RAG——即证明崩溃机制在"防不起"的地形上**不可替代**。

## 1. 可证伪主张(能输)

**主张**:同一 oracle 预算 B、同一嵌入、同一记忆槽位 N 下,
`full(贪心沉积+怀疑触发崩裂)` 在义项恢复上**严格优于** `gate-at-budget`、`full-no-split` 与 `RAG` 三个对照;
且崩裂只裂过合、不裂健康(继承死刑线)。
**若 gate-at-budget 追平或反超** → 崩溃仍非必要,如实判 `gate_suffices`(EXP-0"防>治"结论在稀缺下仍成立)。
**若 full 不优于 RAG** → `deflates_to_rag`,触发 ROADMAP 项目级死刑条件评估。

## 2. 语料(多 surface 漂移流;标签只审卷)

~120 turn 中文短句流,**3 个歧义 surface + 1 个单义对照**:

```text
苹果  fruit → 桥接 → company → 混合回流      (主靶,继承 EXP-0 梯度设计)
小米  grain → 桥接 → company → 混合          (第二靶,漂移相位与苹果错开)
长城  wall  → company(汽车)→ 混合           (第三靶,三义中取二,防两义特化)
香蕉  fruit only                             (流内健康对照:全程单义,不许被裂)
```

每 turn 带 `true_sense` **仅审卷**。相位错开 = 不同 surface 的过合在不同时段形成,考验预算分配。
**P0 校准门(先于主运行,两颗牙)**:
(a) RAG 在此流上确实过合(继承 EXP-0);
(b) **gate-everything 在预算 B 下确实买不起**——每次沉积都问 oracle 的策略在流走完前耗尽 B(演示给 receipt)。
任一不成立 → `corpus_miscalibrated` / `budget_not_binding`,blocked,不读 full 结果。

## 3. 四臂(同嵌入、同 oracle、同 B、同 N;唯一差别=oracle 花法与崩裂)

```text
RAG            append-only + 固定阈值 top-k;不花 oracle,无预算无重组(下限锚点)。
gate-at-budget 入口问 oracle(同/异义)直至 B 耗尽,之后退化为纯嵌入贪心;有 N 槽位+驱逐;无崩裂。
full-no-split  贪心沉积(不问入口)+ N 槽位 + 驱逐;不崩裂(消融:隔离崩裂的独立贡献)。
full           贪心沉积 + N 槽位 + 驱逐 + 怀疑触发的过合审计与崩裂(oracle 花在审计/分裂上)。
```

**预算参数(冻结时写死入 receipt)**:流长 ~120,N ≈ 流长/5(驱逐必然发生),B ≈ 流长×0.4(gate-everything 不可行)。
**怀疑信号**(full 何时花 oracle,纯内部信号、零标签):carrier 内部嵌入方差、成员新旧跨度、驱逐冲突频率。
oracle 调用分配轨迹(何时、花给谁、判了什么)全量落盘入 receipt——**资源分配本身是本实验的一等公民度量**。

## 4. Oracle 文件协议 v1(机械化,不留会话临场判断)

三个 oracle 同吃本协议:**Claude(主)/ scripted(floor)/ Qwen3.5-4B(复现)**。协议件与 spec 同冻结:

```text
队列   artifacts/<run_id>_oracle_queue.jsonl,runner 写,每行:
       {"qid":"<run_id>-<arm>-<sha1(kind|texts)[:12]>","kind":"same_sense|coherent|split","texts":[...],"retry":0}
       **qid 必须内容寻址**(v1.1 修正):续跑=从头重模拟,而提问序列是答案依赖的;序号 qid 在首个行为分歧点后
       全面错位。内容寻址下多轮批答自然收敛(每轮钉死更长的行为前缀;旧轮多余答案留作审计尾迹,不参与校验)。
       texts 只含 episode 原文。写入前过 leak-check:请求序列化后含 "true_sense"/"sense"/标签值 → 拒写并 blocked。
批答   artifacts/exp1_oracle_answers.jsonl,oracle 写,首行头:
       {"queue_sha256":"<队列文件 hash>","oracle":"claude|scripted|qwen","prompt":"oracle-prompt-v1"}
       其后每行:{"qid":..., "answer":"same|diff" | "coherent|incoherent" | {"groups":{"g1":[idx...],...}}, "note":"<一句理由,可选>"}
校验   runner 恢复时逐条核对:qid 双射(不多答不漏答)、answer 枚举合法、queue_sha256 与实际队列一致
       (防批答对错版)。任一失败 → oracle_unlogged。
配额   runner 侧硬计数(答一条记一次,重试也计费);任一臂累计 > B → oracle_budget_exceeded,立即 blocked。
重跑   格式非法或缺答的 qid 允许重投一次(retry=1);再失败该 qid 记 abstain——判断回退纯嵌入默认路径,
       预算照扣(真 LLM 浪费调用也是真成本)。abstain 数入 receipt。
prompt 模板冻结存 specs/oracle-prompt-v1.md,批答逐字使用;模板只给 texts 与判断枚举,零任务外提示。
```

所有判断锚在真实 episode 文本、全量落盘可审(铁律 a);oracle 判"该裂"只是执行信号的一部分,
崩裂需 §3 怀疑信号先触发(oracle 不当皇帝的最小落实;完整仲裁层留给 P2)。

## 5. 度量(修 EXP-0 的计分漏洞)

```text
主:义项恢复 F1 —— 分母含全部 turn(含桥接/混合段),歧义句碎片化不再免费(EXP-0 gate 的 13 carrier 免费午餐取消)。
辅:每 surface carrier 数轨迹(理想:苹果/小米→2,长城→2,香蕉→1);驱逐质量(被逐记忆的事后价值);
    oracle 花费轨迹(花在哪类怀疑上、命中率)。
授权门:full 严格 > 三对照;香蕉与静态对照零误裂;B、N 两预算均 binding;标签隔离。
```

## 6. 退出码(预注册,互斥)

```text
budget_not_binding / oracle_budget_exceeded / labels_leaked / oracle_unlogged / corpus_miscalibrated → blocked_engineering
full ≤ RAG                                                        → deflates_to_rag(触发 ROADMAP 死刑条件评估)
full ≤ gate-at-budget                                             → gate_suffices(崩溃仍非必要,如实记)
full ≤ full-no-split                                              → split_vacuous(赢的是预算驱逐,不是崩裂)
香蕉/静态对照被裂                                                  → oversplit_healthy(老死刑线,永不豁免)
full 严格胜三对照 + 健康零误裂 + 双预算 binding + 标签隔离           → collapse_indispensable(P1 通过,进 P2)
```

## 7. 杀死测试(每颗牙须演示会失败)

```text
- 驱逐牙:run 结束驱逐次数为 0 → budget_not_binding(N 白设)。
- oracle 配额牙:任一臂调用数 > B → oracle_budget_exceeded;runner 硬计数,不信自觉。
- 标签牙:true_sense 进任一信号通路 → labels_leaked(继承)。
- 审计牙:oracle 队列/批答文件缺失或与 receipt 不符 → oracle_unlogged。
- 公平牙:gate-at-budget 必须拿到与 full 相同的 B 和 N(不许喂稻草人);其入口策略于冻结时写死。
- 健康牙:香蕉全程 + fruit-only 静态流,零崩裂(继承 kernel 死刑线)。
- 消融牙:full vs full-no-split 隔离崩裂独立贡献(继承)。
- 计分牙:歧义 turn 计入分母;抽掉此规则重算若结论翻转,必须双报。
```

## 8. 实现边界(冻结后建)

```text
corpus/drift_multi.jsonl      多 surface 相位错开流(校准门冻结前重核)
src/oracle_file.py            文件协议 Claude oracle + 硬配额计数器 + scripted floor + Qwen 适配
src/memory_budget.py          N 槽位 + q 驱逐 + 怀疑信号 + 过合审计/崩裂(EXP-0 memory.py 演进)
src/run_exp1.py               四臂 + 双校准门 + 度量 + 退出码 + receipt(含 oracle 花费轨迹)
specs/oracle-prompt-v1.md     oracle prompt 冻结件(已起草,随本 spec 冻结)
artifacts/exp1_*              队列/批答/receipt/report
```

## 9. 交付记录(claude oracle 首跑,2026-07-01;正式冻结仍待项目方)

- **协议 bug 发现并修复**:Codex 初版 qid 为全局序号,两阶段批答在答案改变行为后全面错位(必然 `oracle_unlogged`)。
  修复=内容寻址 qid + 容忍审计尾迹的校验(`src/oracle_file.py`,Claude 改,**待 Codex 复核**)。多轮批答 6 轮收敛,
  最终队列 74 问全答(same_sense/coherent/split 三类;历史批答 196 条含旧轮尾迹),queue sha256=f36eb804…33fa42。
- **结果(真 LLM oracle = 会话中 Claude,零 true_sense 接触,全量落盘)**:
  `full F1=0.865(P .933/R .807, 3 splits)> gate-at-budget 0.794(P .963/R .676, 苹果/小米各碎成 7)> RAG = no-split 0.759`。
  三道门全过:budget_binding(驱逐发生)、gate_budget_binding(48/48)、healthy_ok(香蕉 1 carrier,零误裂)。
  **verdict = collapse_indispensable**——与 scripted floor 同向(0.82>0.793),真 LLM 下裂差更大。
- **窄裁决,不洗绿**:gate 输在预算耗尽后碎片化(高精低召);full 赢在"贪心沉积+事后崩裂"对预算更省。
  oracle(Claude)对义项的判分比二值标签细(食品品牌/混义句单列),部分 recall 损失来自此;
  运行先于正式冻结(参数=run_exp1.py 所载),此瑕疵如实记录,冻结补办属项目方。

## 10. 预注册摘要

```text
claim  = 稀疏 oracle(B)+紧槽位(N)下,full(贪心+怀疑触发崩裂)严格胜 gate-at-budget / no-split / RAG,且健康零误裂
nulls  = {RAG, gate-at-budget, full-no-split};allow-to-lose;gate_suffices 与 deflates_to_rag 为一等出口
oracle = Claude 文件协议(主)/ scripted(floor)/ Qwen3.5-4B(复现);同嵌入同 B 同 N,唯一差别=花法与崩裂
gates  = P0a RAG 过合;P0b gate-everything 在 B 下不可行;标签审卷 only;健康对照零裂
铁律   = 记录锚可核查外部;必须改变并改好判断(完整版留 P2);oracle 判断非圣旨;机制跃迁不算参数堆积
```
