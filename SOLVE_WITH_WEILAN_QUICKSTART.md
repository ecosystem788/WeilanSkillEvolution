# solve-with-weilan 简短说明书

## 这是什么

`solve-with-weilan` 是一个 Codex Skill（技能），用于把任务处理成可控的 Frame（框架）、Trace（轨迹）和 Evidence（证据）流程。它不是替代用户指令的“总控制器”，而是一个工作方法层：帮助 agent 按任务风险选择深度、保留关键过程证据、在失败时执行 collapse/regroup（坍缩与重组），并在结束时给出可验证 receipt（回执）。

当前本地部署版本来自 SE-0.6 successor v0.9，部署目标是：

`D:\CodexData\skills\solve-with-weilan`

本地部署 receipt（回执）见：

`D:\WeilanSkillEvolution\deployments\dec8809e1d6b5dfc05c746e9\DEPLOYMENT_RECEIPT.json`

## 主要功能

1. **Proportional framing（按比例定框）**
   - L0：很小、低风险、一步能答的任务，直接处理。
   - L1：常规多步任务，窄范围检查、执行、验证，输出简短 receipt。
   - L2：有真实路线分歧、架构判断、成本或不确定性时，记录候选、holder（临时持有路线）和验证标准。
   - L3：长期、高影响或反复失败任务，记录 warning（警告）、probation（试用期）、collapse（坍缩）、trace（轨迹）、regroup（重组）生命周期。

2. **Memory recall/control（记忆召回与控制）**
   - 新工作窗口先执行 `memory-recall`，判断当前 scope（范围）是否 `ACTIVE`、`PAUSED`、`CONFIRM_REQUIRED`、`STALE` 或 `NO_CONTEXT`。
   - 明确的暂停、恢复、停止、范围重定向要写入 `memory-control`。
   - 普通“继续”不会自动解除 paused（已暂停）状态。

3. **Frame/Trace evidence（框架与轨迹证据）**
   - L2/L3 工作会保留可观察的 Frame/Trace 事件。
   - 记录的是外部可验证事件，不记录隐藏思维链。
   - 结束或切换重大路线前，需要做 Persistence Audit（持久化审计）。

4. **Collapse/regroup（坍缩与重组）**
   - 路线失败不等于必须坍缩。
   - 只有当 holder（临时路线）失去“继续治理任务的能力”时，才坍缩最小失效单元。
   - 坍缩后保留可复用结果、失败证据、禁用假设，并基于改变后的假设重组。

5. **Evidence promotion（证据提升）**
   - 对话、收据、测试结果等只有经过筛选和提升，才进入可持续使用的记忆。
   - 过期、撤回、替代、休眠、退役的证据不能继续作为 active recall（活跃召回）输入。

6. **Metabolic modules（代谢模块）**
   - 0.7a：提出一个候选状态转移计划，但不执行。
   - 0.7b：用显式 prepare/commit/abort 处理一次事务。
   - 0.7c：把一个被承认的转移具体落地，最多一次事务提交。
   - 0.7d：运行一个有限、前台、有边界的 manifest（清单），不能变成后台循环、定时器或 daemon（守护进程）。

7. **Skill Evolution（技能演化）外部治理**
   - 评测、冻结候选、adoption（采用）、deployment（部署）、rollback（回滚）属于 `D:\WeilanSkillEvolution` 的外部治理层。
   - candidate（候选）不能批准自己的评测，不能修改 frozen evaluator（冻结评测器），也不能自行授权部署。

## 怎么使用

每个任务默认先按 `$solve-with-weilan` 的深度规则处理：

```powershell
python "D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py" memory-recall --workspace "<cwd>"
```

然后按返回状态执行：

- `ACTIVE`：可以继续，但要先核对当前任务相关来源。
- `PAUSED`：只报告暂停状态，不擅自继续。
- `CONFIRM_REQUIRED`：需要用户明确方向。
- `STALE`：先重建或刷新相关投影。
- `NO_CONTEXT`：从干净状态开始。

常规使用方式：

- 小问题：直接答，最多做轻量验证。
- 普通改动：读最小相关文件，改最小范围，跑一个相关验证。
- 架构或多路线任务：明确候选、holder、death line（终止线），再执行。
- 反复失败或重大任务：进入 L3，记录坍缩与重组事件，最后做 Persistence Audit。

使用边界：

- 不能用它覆盖用户当前明确指令。
- 不能用它扩大任务范围或制造不必要工作。
- 不能让它自动部署、回滚、推送 GitHub 或修改 frozen evaluation set（冻结评测集）。
- 不能启动后台 runner（运行器）、scheduler（调度器）、timer（定时器）、heartbeat（心跳）或 daemon（守护进程）。

## 以后发给 Codex 的自检提示词

下面这段可以直接复制给 Codex，用来检查 `solve-with-weilan` 的相关模块和功能是否正常发挥作用：

```text
请用 $solve-with-weilan 对当前工作区做一次功能自检。除非我另行授权，不要修改业务文件、不要部署、不要回滚、不要推送 GitHub、不要修改 frozen evaluator（冻结评测器）或 frozen evaluation set（冻结评测集）。

目标：
检查 solve-with-weilan 的关键模块是否能正常发挥作用，并给出一份简短 receipt（回执）。

范围：
1. activation / memory recall（激活与记忆召回）
   - 运行：
     python "D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py" memory-recall --workspace "<cwd>"
   - 报告 activation.state，并按 ACTIVE / PAUSED / CONFIRM_REQUIRED / STALE / NO_CONTEXT 的规则处理。

2. Skill file（技能文件）与脚本可用性
   - 检查 D:\CodexData\skills\solve-with-weilan\SKILL.md 是否存在。
   - 检查 D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py 是否可运行。
   - 只做只读检查，不改 deployed skill（已部署技能）。

3. Frame / Trace（框架与轨迹）
   - 如果当前任务达到 L2/L3，检查 lineage-show 或已有 Frame 头部是否可读。
   - 不要为了形式强行创建 L2/L3 Frame。
   - 如果确实需要创建临时自检 Frame，必须说明原因、scope、parent、成功标准，并在结束前关闭和审计。

4. Persistence Audit（持久化审计）
   - 对任何本次新开的 L2/L3 Frame，运行 persistence-audit 或说明为什么本次不需要持久化。
   - 不记录隐藏思维链，只记录外部可验证事件。

5. Collapse / regroup（坍缩与重组）
   - 检查 SKILL.md 中 L3 contract（契约）是否仍要求固定事件顺序：
     holder_warned -> holder_probation_started -> discriminating_test_executed -> minimal_unit_collapsed -> trace_emitted -> candidates_regrouped
   - 检查 recovery.json contract（恢复文件契约）字段是否仍存在说明：
     collapse_scope, invalidated_assumption_id, new_identity_model, failure_evidence, reusable_artifacts, once_reasonable, forbidden_assumption, reentry_condition, new_holder_id

6. Metabolic modules（代谢模块）
   - 只读检查 0.7a / 0.7b / 0.7c / 0.7d 的入口说明是否存在。
   - 明确确认它们不能启动后台循环、定时器、守护进程或自我递归执行。

7. Skill Evolution local status（本地技能演化状态）
   - 如果当前工作区是 D:\WeilanSkillEvolution，检查 LOCAL_STATUS.md、最新 deployment receipt、canary result 和 adoption decision 是否存在。
   - 报告当前是否只是 local-only（仅本地）状态，不要尝试 GitHub 操作。

输出格式：
- 先给结论：OK / WARN / BLOCKED。
- 然后列 5 到 10 条检查项，每条包含：模块、结果、证据路径或命令。
- 最后列出没有做的检查和原因。

约束：
- 自检优先使用只读命令和临时测试。
- 不要把自检变成修复任务；发现问题后先报告，等待我授权再修改。
- 不要为了满足流程制造候选、Frame 或坍缩事件。
```
