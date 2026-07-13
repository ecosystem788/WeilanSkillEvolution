# Claude Review — fusion-dogfood-v0.1 审批前复核

Status: `conditional_approval_gate_not_approval`(本文件不批准、不冻结、不改 manifest、不跑 shadow、不部署;批准权在项目方)
Reviewer: Claude(Opus 4.8),2026-07-04
Concurrence: Codex 复核签认 2026-07-04 —— "B1/B2 是真阻断,Claude 的阻断判断是对的,没有更大的新 blocker";
并补两条 P1 实施要求(已折入下文 B1/N2)。定序采 Codex 建议:**先工程化 B1/B2,再一次性提交项目方批准冻结**
——项目方对着冻结工件批,不对着抽象条件批。
Reviewed inputs: `proposal.draft.json`(sha256=4062f2e7…)、`cases/fusion-dogfood-v0.1-draft.cases.json`(sha256=6f3f3879…)、
`APPROVAL_PACKAGE.md`、`README.md`、`case_inventory.md`;对照 `EVALUATION_POLICY.md` 绑定清单;
16 条公开 fixture 路径逐一验证存在(全部 OK)。

## 结论

**设计方向正确,推荐批准——但有 2 个阻断性条件(B1/B2)必须在冻结前落实,否则会产出一个
"批准即开始漂移"的套件。** 4 个非阻断建议(N1–N4)建议随批准文本一并采纳。

本套件正是 P4 当前最需要的东西:se-seed-v0.1 已近天花板(v0.9 shadow 中 candidate 全 1.0、
method_impact_count 全程 0),而本套件用 P3 真实困难任务供题,是打破天花板的正确形状。

## 阻断性条件

### B1 — fixture 必须复制冻结,禁止活路径直读(最重要)

草案所有 `fixture_sources` 都是指向 **live** `D:\weilan-llm-fusion` 的绝对路径。该仓库正在活跃变异:
仅 2026-07-04 一天,`PROJECT_CONTROL.json` 就更新了 3 次(offline analysis 字段、corpus-v2 工单字段及其修订),
且 CORPUS-V2 工单正在执行中,还会新增文件。后果:

1. **不可复现**:baseline 与 candidate 在不同时刻读到不同字节;跨月比较 successor 时读到完全不同的仓库
   —— 违背 EVALUATION_POLICY 的绑定精神("equivalent isolated inputs"、run 绑定环境标识)。
2. **答案漂移**:隐藏 rubric 锚定的"2026-07-03 记录于 PROJECT_CONTROL 的审查结论",在 live 文件里会被
   后续字段不断稀释/覆盖;甚至新增审计字段可能**以明文包含期望答案**。
3. **答案泄漏已经存在**(与漂移独立):case 1 的 fixture 含 `PROJECT_CONTROL.json`,而该文件的
   `exp3_s0_audit` 字段就是隐藏期望发现清单的来源;case 5 同理(`exp15b_audit` 字段明文含
   "no v3 patch / escalates to project owner" 的结论)。候选做的是查找而非归因,判别力回到天花板。

**要求**:按 se-seed-v0.1 先例复制冻结 —— `evals/fixtures/fusion-dogfood-v0.1/<case_id>/` 存放快照副本,
`source-hashes.json` 记录每份快照 sha256,候选只读快照。**且快照内容要有意选择**:
归因类 case(1/4/5)的 PROJECT_CONTROL 快照应**时间切片到被审计结论落账之前**(或直接从 fixture 中剔除,
只给 receipts/reports/events),让 case 测归因而不是测阅读。APPROVAL_PACKAGE 把复制冻结列为可选项;
本 review 将其升级为必须项。

**B1 实施补充(Codex P1,签认采纳)**:所有 case 的 fixture 一律收窄为**显式文件清单 + 逐文件 hash**;
禁止整目录引用(case 8 现写 "Selected public specs/*, artifacts/*, logs/*" 即为反例)——整目录即使复制冻结,
也会带入无关 receipt/log/隐藏线索。

### B2 — case 7 / case 8 需要隔离环境,否则不可重复

- **case 7(fusion-memory-scope-recovery)**:隐藏检查依赖 `fusion-program` 的 method-state 激活状态,
  但真实 method-state 是活的(本日 projection 已更新多次)。期望激活状态会随真实工作漂移。
  → 要求:提供快照化的 method-state fixture(seed 套件的 memory-cross-window-continuation 已有同型先例),
  在隔离 `WEILAN_METHOD_HOME` 下执行,禁读真实 method-state。
- **case 8(fusion-scope-redirection-to-eval-proposal)**:任务是"创建 fusion-dogfood 提案",而该提案
  **现已存在于本仓库**——候选重跑时可直接抄现成答案(自答案泄漏),或撞"已存在"冲突。这是一次性历史任务,
  不是可重复考题。→ 要求:在剔除了 `proposals/fusion-dogfood-eval-cases/` 的工作区快照中执行,
  或把目标改写为一个结构同型、名称不同的新提案任务。

## 非阻断建议

- **N1(same-hand 条款)**:批准文本写明 —— 隐藏 rubric 冻结先于任何被其评分的候选生成;
  评分执行者(隔离 Codex 子代理 + 冻结 evaluator 工件)与候选作者分离。期望答案仅允许锚定
  已冻结的外部事实(签名审计记录、冻结 receipt),不允许锚定评审者未落账的记忆。
- **N2(试次数)→ 升级为冻结前必改(Codex P1,签认采纳)**:case 1 与 case 4 是 L2 级判断题,
  `trial_count=1` 偏薄(政策:非确定性处多试次)。**不许只留在建议里**:冻结前必须把
  `draft.cases.json` 与 APPROVAL_PACKAGE 中这两处 trial_count 实改为 2,否则与 SE-0.7
  "两连改进"门的统计要求不自洽。全套件成本仍有界(总 tool_calls 预算 ≈ 100 上下)。
- **N3(绑定完整性)**:对照 EVALUATION_POLICY,批准前还缺三个绑定件的定值:环境标识、模型/工具配置引用
  (可沿用 `evals/configurations/codex-subagent-isolated-v0.1.json` 或新配置)、以及冻结的 evaluator 工件
  hash 清单。`approval_required_before_use` 已列出,此处仅确认为**冻结清单项**,缺一不得跑 shadow。
- **N4(方法影响必须可数)**:本套件的存在理由之一是让 method_impact 开火,但 8 个 case 的
  `expected_receipt_fields` 均未要求 Method Impact Trace。建议:每个 case 的 receipt 增加
  `method_impact_trace`(哪个方法门开火、是否改变了预定动作、避免/暴露了什么可观察失败、代价),
  shadow 汇总报告统计 `method_impact_count`。这与 ROADMAP 对下一个 successor 的目标指标要求配套。

## 定序与工程清单(Claude + Codex 收敛,待项目方一句话放行)

```text
① Codex 工程化(在 scope 指令扩展授权后执行;仍禁止:批准/改 evals/manifest.json/跑 shadow/adopt/deploy):
   - 复制冻结 fixtures → evals/fixtures/fusion-dogfood-v0.1/<case_id>/(case 1/4/5 时间切片或剔除污染源)
   - 生成 source-hashes.json(显式文件清单+逐文件 sha256;禁整目录)
   - 拆分 hidden checks / evaluator rubric → evals/hidden/fusion-dogfood-v0.1/(与公开件分开哈希)
   - case 7:快照化 method-state fixture + 隔离 WEILAN_METHOD_HOME
   - case 8:隔离 workspace 快照(剔除本提案自身)或改写为结构同构新任务;fixture 收窄
   - trial_count:case 1/4 实改为 2
   - expected_receipt_fields:全部 case 增 method_impact_trace
② Claude 复核冻结工件(对 hash 链与时间切片抽查)
③ 项目方一次性批准冻结(suite 入册 evals/manifest.json 仅在此步发生)
```

## 定序② 抽查结果(Claude,2026-07-04)——PASS

```text
红线      evals/manifest.json 未动(sha cfaa5c52…,仍 se-seed-v0.1/frozen/8 案例,无 fusion 引用);
          部署技能与 packages/ 未动(git 干净)
B1        8 个 case 全部复制冻结为 fixture-manifest + public/ 快照;逐文件 sha256 全清单;
          67/67 hash 逐位验证通过;公开 spec 零活路径(零 D:\ 引用);
          污染源处理:case1/4/5 直接剔除 PROJECT_CONTROL(比切片更干净);case1 的 EXP-3 spec
          快照 hash = 当年冻结值 ff5fe74c…(逐位一致,历史保真)
B2        case7 = fusion-workspace 快照 + 完整 method-state 快照(control/projection/index/lineage/
          semantic,供隔离 WEILAN_METHOD_HOME);case8 = 28 个显式文件,零本提案自指
N2        case1/case4 trial_count 已实改为 2
N4        method_impact_trace 8/8 case 进入 expected_receipt_fields
隐藏面    evals/hidden/fusion-dogfood-v0.1/ 四件齐(hidden-checks/rubric/source-hashes(27 项)/
          redaction-policy)+ evaluator-sources(私密 map 在评测器侧,候选不可见)
注记      case7 的 PC 快照为 54 字段全量副本(含其他 case 的审计字段)——case 间隔离执行下无泄漏;
          若未来套件改共享工作区执行,须重切。快照落于本日审计字段之后、最终冻结字段之前,
          hidden checks 与该快照绑定,漂移已被冻结解决
```

**结论:B1/B2/N2/N4 全部落实,定序② 通过。剩 ③ = 项目方一次性批准冻结**(此步才发生:
suite 入册 evals/manifest.json、绑定 evaluator 工件 hash 与执行配置、冻结 public case spec hash)。

## 边界与角色

- 本 review 是"条件批准门",不是批准;批准仅发生在上表第 ③ 步,由项目方执行。
- 快照内容的时间切片选择由 Codex 按 B1 规则实施,Claude 在第 ② 步抽查,争议升项目方。
- 本 review 未重读 8 个 successor 提案与 evaluator 实现;若批准后发现 evaluator 与 rubric 不一致,
  以冻结 hash 链为准回溯。
