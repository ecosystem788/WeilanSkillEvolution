# solve-with-weilan 简短说明书

## 这是什么

`solve-with-weilan` 是一个 Codex Skill（技能），用于把任务处理成可控的 Frame（框架）、Trace（轨迹）和 Evidence（证据）流程。它不是替代用户指令的“总控制器”，而是一个工作方法层：帮助 agent 按任务风险选择深度、保留关键过程证据、在失败时执行 collapse/regroup（坍缩与重组），并在结束时给出可验证 receipt（回执）。

当前部署版本是动态的：真源是 `deployments/` 下的 `DEPLOYMENT_RECEIPT.json`（当前部署目标：`D:\CodexData\skills\solve-with-weilan`）。哪一份最新不可按目录名或 mtime 判定——目录名是不可排序哈希，且部分收据无时间字段（2026-08-12 实测 13 份中 4 份缺，恰含最新的）；按 `git log --diff-filter=A` 的加入顺序判定。

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

下面这些提示词可以直接复制给 Codex。可以整组发送，也可以只发送某个模块。默认规则是：先自检、先报告，不要把自检变成修复或部署。

```text
【总控提示词】
请用 $solve-with-weilan 对当前工作区做一次模块化功能自检。

约束：
- 除非我另行授权，不要修改业务文件。
- 不要部署、不要回滚、不要推送 GitHub。
- 不要修改 frozen evaluator（冻结评测器）或 frozen evaluation set（冻结评测集）。
- 不要启动后台 runner（运行器）、scheduler（调度器）、timer（定时器）、heartbeat（心跳）或 daemon（守护进程）。
- 不要为了满足流程制造候选、Frame（框架）或 collapse（坍缩）事件。
- 发现问题后先报告，等待我授权再修。

输出：
- 先给总结论：OK / WARN / BLOCKED。
- 然后按模块列出检查结果。
- 每个模块写：结论、检查项、证据路径或命令、未做事项及原因。
```

### 模块 1：Activation / Memory Recall（激活与记忆召回）

```text
请只检查 activation / memory recall（激活与记忆召回）模块。

检查项：
1. 运行：
   python "D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py" memory-recall --workspace "<cwd>"
2. 报告 activation.state。
3. 说明当前状态应该如何处理：
   - ACTIVE：可以继续，但要先核对当前任务相关来源。
   - PAUSED：只报告暂停状态，不擅自继续。
   - CONFIRM_REQUIRED：需要用户明确方向。
   - STALE：先重建或刷新相关投影。
   - NO_CONTEXT：从干净状态开始。
4. 不要修改 memory-control（记忆控制），除非我明确要求暂停、恢复、停止或重定向 scope（范围）。

输出：
- 模块结论：OK / WARN / BLOCKED。
- activation.state。
- 证据命令和关键输出。
```

### 模块 2：Skill File / Script（技能文件与脚本）

```text
请只检查 Skill file / script（技能文件与脚本）模块。

检查项：
1. 检查 D:\CodexData\skills\solve-with-weilan\SKILL.md 是否存在。
2. 检查 D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py 是否存在并可运行。
3. 检查 SKILL.md 是否包含 L0/L1/L2/L3 深度规则。
4. 检查 SKILL.md 是否包含 memory-recall、memory-control、persistence-audit 等入口说明。

约束：
- 只读检查。
- 不要修改 deployed skill（已部署技能）。

输出：
- 模块结论：OK / WARN / BLOCKED。
- 每个文件或入口的检查结果。
- 证据路径或命令。
```

### 模块 3：Frame / Trace（框架与轨迹）

```text
请只检查 Frame / Trace（框架与轨迹）模块。

检查项：
1. 如果当前任务是 L0/L1，说明为什么不需要创建 Frame。
2. 如果当前任务达到 L2/L3，检查 lineage-show 或已有 Frame head（头部）是否可读。
3. 检查是否存在可继续的 parent Frame（父框架）或需要 clean start（干净开始）。
4. 确认不会记录隐藏思维链，只记录外部可验证事件。

约束：
- 不要为了形式强行创建 L2/L3 Frame。
- 如果确实需要创建临时自检 Frame，必须先说明原因、scope、parent、成功标准和关闭方式。

输出：
- 模块结论：OK / WARN / BLOCKED。
- 当前深度判断：L0 / L1 / L2 / L3。
- lineage 或 Frame 证据。
```

### 模块 4：Persistence Audit（持久化审计）

```text
请只检查 Persistence Audit（持久化审计）模块。

检查项：
1. 检查 persistence-audit 和 persistence-audit-show 是否在脚本入口中可用。
2. 如果本轮没有新开 L2/L3 Frame，说明为什么不需要审计。
3. 如果本轮新开了 L2/L3 Frame，检查是否有 promoted evidence（已提升证据）或明确 non-persistence reason（不持久化理由）。
4. 确认 active recall（活跃召回）不会使用撤回、过期、替代、休眠或退役证据。

输出：
- 模块结论：OK / WARN / BLOCKED。
- 审计是否需要执行。
- 证据路径或命令。
```

### 模块 5：Collapse / Regroup（坍缩与重组）

```text
请只检查 Collapse / Regroup（坍缩与重组）模块。

检查项：
1. 检查 SKILL.md 中是否仍要求 L3 lifecycle（生命周期）事件顺序：
   holder_warned -> holder_probation_started -> discriminating_test_executed -> minimal_unit_collapsed -> trace_emitted -> candidates_regrouped
2. 检查 recovery.json contract（恢复文件契约）字段是否仍存在说明：
   collapse_scope, invalidated_assumption_id, new_identity_model, failure_evidence, reusable_artifacts, once_reasonable, forbidden_assumption, reentry_condition, new_holder_id
3. 确认 collapse（坍缩）不是因为“失败一次”或“路线变强”，而是因为 holder（临时路线）失去治理能力。
4. 确认 regroup（重组）必须基于改变后的假设，而不是旧路线改名。

约束：
- 只检查契约和说明，不制造 collapse 事件。

输出：
- 模块结论：OK / WARN / BLOCKED。
- 事件顺序检查结果。
- recovery.json 字段契约检查结果。
```

### 模块 6：Metabolic Modules（代谢模块）

```text
请只检查 Metabolic modules（代谢模块）。

检查项：
1. 检查 0.7a metabolic proposal（代谢提案）入口说明是否存在。
2. 检查 0.7b transaction（事务）入口说明是否存在。
3. 检查 0.7c transition materialization（转移物化）入口说明是否存在。
4. 检查 0.7d finite runner（有限运行器）入口说明是否存在。
5. 明确确认这些模块不能启动后台循环、定时器、守护进程或自我递归执行。

约束：
- 只读检查。
- 不执行 metabolic transaction（代谢事务）或 runner（运行器）。

输出：
- 模块结论：OK / WARN / BLOCKED。
- 0.7a / 0.7b / 0.7c / 0.7d 分项结果。
- 证据路径或命令。
```

### 模块 7：Skill Evolution Local Status（本地技能演化状态）

```text
请只检查 Skill Evolution local status（本地技能演化状态）。

适用条件：
- 当前工作区是 D:\WeilanSkillEvolution 时执行。

检查项：
1. 检查 LOCAL_STATUS.md 是否存在。
2. 检查最新 deployment receipt（部署回执）是否存在。
3. 检查 adoption decision（采用决策）是否存在。
4. 检查 canary result（金丝雀结果）是否存在。
5. 报告当前是否是 local-only（仅本地）状态。

约束：
- 不要尝试 GitHub 操作。
- 不要创建 release、PR、tag 或 remote push。
- 不要把 local-only 状态说成已经开源或远端发布。

输出：
- 模块结论：OK / WARN / BLOCKED。
- 当前本地部署状态。
- 证据路径。
```

### 汇总输出格式

```text
请按这个格式输出自检结果：

总结果：OK / WARN / BLOCKED

模块结果：
1. Activation / Memory Recall（激活与记忆召回）：OK / WARN / BLOCKED
   证据：
   未做：
2. Skill File / Script（技能文件与脚本）：OK / WARN / BLOCKED
   证据：
   未做：
3. Frame / Trace（框架与轨迹）：OK / WARN / BLOCKED
   证据：
   未做：
4. Persistence Audit（持久化审计）：OK / WARN / BLOCKED
   证据：
   未做：
5. Collapse / Regroup（坍缩与重组）：OK / WARN / BLOCKED
   证据：
   未做：
6. Metabolic Modules（代谢模块）：OK / WARN / BLOCKED
   证据：
   未做：
7. Skill Evolution Local Status（本地技能演化状态）：OK / WARN / BLOCKED
   证据：
   未做：

结论：
- 能否继续正常使用 solve-with-weilan：
- 是否需要用户授权修复：
- 最小下一步建议：
```
