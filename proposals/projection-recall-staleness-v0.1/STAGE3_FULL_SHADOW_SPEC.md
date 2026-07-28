# axis-1 stage-3 · approved-harder-suite full-shadow 规格（草案，零权威，未接线）

状态：**SPEC / DESIGN，零权威，未双签，不预签 adoption，不授权 deploy**。
本文件把 2026-07-24 茶水间双方独立收敛出的"守全套 shadow 闸"路线（route (a)）固化成一份
可执行验收规格，免得它随闲聊沉没（正是本线诊断的"通电但没人读"病）。

- 起草 = 单签可逆小活（新文档，不改机制、不动部署件、不碰授权文件）。
- **执行本规格**（造 harness、跑 full shadow）= 机制邻近 = 须与 Codex 双签，实现委派 Codex。
- **adoption / deploy 到 live skill** = 朝外不可逆 = 另案，须观察员（云）先签（CHARTER §6 +
  EVALUATION_POLICY「explicit approval」）。本规格不预签任何一步。
- 承重锚点（行号、schema、字段）在**执行当刻回源核验**，不以本文件为真源。

## 一、为什么有这份规格（route (a) 的来历）

- 2026-07-24 Claude 提出 (a) 守自设全套 shadow 闸 / (b) 按 capture-contract 先例走定向证据+adoption 共商。
- Codex 14:15:31 **独立选 (a)**：axis-1 的 v4 定向结果自身明写 `adoption_eligible=false`、
  `full_suite_shadow_required_for_method_behavior=true`、authority=`not_an_adoption_gate__
  method_change_requires_approved_harder_suite_full_shadow`（见 `adoption/TARGETED_SHADOW_RESULT.json`）。
  先例（capture-contract 当时 result 自写 `adoption_eligible=true` + 具名 adoption 授权）不能**静默改写**
  这次"提出即锁死"的证据语义；要走 (b) 至少需新提案显式替换这两个字段/权威声明。
- Claude（上一回合闭合帧 `wf-20260724-041750-1f0b00`）也独立选 (a)。**两方独立同选，不是回声。**

结构理由：axis-1 改的是**冷启动 activation 前的 freshness 判定**——假 STALE/假 fresh 会改变是否续工，
坐在每次 recall 的关键路径上。7 项定向 checks 证了目标 bug + 邻近回归，但**没履行** EVALUATION_POLICY
的 adoption gate 全部六条。更严的闸是受影响路径的结构要求，不是仪式。

## 二、两道闸必须分开（Codex 的承重校正，本规格的铁律）

**绝不把阶段闸无声混成单个 candidate 的额外闸。** 本规格只服务 Gate A，对 Gate B 只做诚实标注：

- **Gate A — 本 candidate 的 adoption eligibility**：EVALUATION_POLICY「Adoption gate」六条
  （见下第三节），经 approved-harder-suite full shadow 取证。本规格的验收对象。
- **Gate B — SE-0.7 阶段晋级**：ROADMAP:198-199——需**两次连续 successor 评估**在 approved harder
  suite（`fusion-dogfood-v0.1`，见 ROADMAP:190、`evals/fusion-dogfood-v0.1-manifest.json`）上显示
  held-out 改进且无 guardrail 退化。**本 candidate 的一次 full shadow 至多是这两次里的一次**，
  且仅当它确在 approved harder suite 上运行。本规格**不主张**满足 Gate B，不推进阶段计数。

## 二·bis 执行前必须补齐的三处硬缺口（Codex 2026-07-24 拒签校正 · 本回合回源坐实）

Codex【反对·先修规格再签】(peer-chat `2026-07-24 13:42:33`) 提出、Claude 本回合回源核验**全部成立**
的三处执行合同缺口。**未补齐前不得开执行【提案】**：

1. **预算/度量须由新提案显式绑定——本规格 target metric 不能顶替 proposal 声明。**
   现行 `adoption/proposal.json` 锁死 `budgets.max_evaluation_trials=0`、`max_targeted_checks=7`，
   `target_metrics` 四项全是定向断言、**无** `method_impact_count>0`（本回合核过原文）。直接跑 full-suite
   evaluation 会越过"提出即锁死"的预算。**须先起草新提案**（可复用同一 base/candidate tree hash），显式绑定：
   full-suite evaluation trial budget（`max_evaluation_trials ≥ 所需`）、`method_impact_count>0` 作声明
   target metric、以及第六节的迁移/method-impact 新增 rollback triggers，并 `proposal-validate` 退 0。
   本规格是该新提案的**验收附件**，不替代提案声明。
2. **method impact 必须落在既有 approved case 上，M1/M2 不能冒充。** `fusion-dogfood-v0.1` 的**八个**
   frozen approved cases（本回合核过 `evals/cases/fusion-dogfood-v0.1.json`：含 `fusion-memory-scope-recovery`）
   是 ROADMAP:193 所指 approved-hard-case method impact 的唯一合法承载。**须预注册**：freshness 修复的方法收益
   在哪个既有 approved case 可观测地 fire——最可能是 `fusion-memory-scope-recovery`（与 memory/scope recovery
   直接相关）。第四节的 M1/M2 是**补充迁移夹具**，可并跑，但**不属于**冻结八例、**不得**冒充 approved-hard-case
   method impact。若无任一既有 approved case 能承载该收益，则只能另走**新 suite/case approval**，
   **绝不改** `fusion-dogfood-v0.1` 的 frozen set。
3. **shadow verdict 只到 (a)-(d)+evaluation evidence；(e)(f) 归 adoption/deploy 决策，别塞进 shadow。**
   EVALUATION_POLICY:65-66 的 (e) 完整 deployment+rollback 收据、(f) 具名授权，是 **adoption gate 全流程**
   条件，**不是 full-shadow 本身能产出的证据**。原规格第三节既要求 full shadow 覆盖 (e) deployment 收据、
   又在第七节声明本案不 deploy——是**不可满足环**。**修正**：full-shadow verdict 限为 (a)-(d) + evaluation
   evidence；(e) 实际 deployment/rollback 收据与 (f) 观察员云具名批准，留在后续 adoption/deploy 决策（第七节），
   由 shadow 通过**许可** adoption、而非由 shadow 产出。

## 三、full shadow 必须覆盖的（超出 7 项定向 checks）

定向结果已覆盖：D0 活 bug 复现 + 6 条邻近回归驱动 exit 0 + 冻结件无 ephemera。**缺口**如下，须补：

1. **approved harder suite 全跑**：`fusion-dogfood-v0.1`（frozen manifest，绑定 copied fixtures、
   hidden evaluator artifacts、source hashes、隔离配置、public case-set hash）。不是只跑 axis-1 自带回归。
2. **EVALUATION_POLICY adoption gate 的证据侧四条，逐条一行显式验收**（EVALUATION_POLICY:59-64）——
   **注：full shadow 只产出 (a)-(d) 这四条的证据；(e)(f) 是 adoption/deploy 决策条件、非 shadow 产出，
   见 §二·bis 3 与第七节**：
   - (a) 无 safety / authorization / privacy / cross-workspace 回归；
   - (b) L0/L1 overhead 无实质退化；
   - (c) 在 proposal 声明的 target metrics 上有改进（含 §二·bis 1 新提案绑定的 `method_impact_count>0`）；
   - (d) **unrelated fixed cases 无不可接受回归**——**这是定向阶段缺的一块**：7 项 checks 只证目标 bug +
     邻近回归，未触碰无关固定用例。full shadow 须显式在无关用例集上取"无回归"证据；
   - (e)（deployment + rollback 收据）/ (f)（观察员云具名批准）**不在 shadow 验收内**——留 adoption/deploy
     决策，shadow 通过只"许可"、不产出（EVALUATION_POLICY:68）。
3. **method_impact_count > 0 作为显式声明的 target metric**（ROADMAP:193-195）：freshness 修复须让某个
   method gate 在**一个既有 approved case** 上**可观测地 fire**——**须落在 `fusion-dogfood-v0.1` 的冻结八例之内
   （最可能 `fusion-memory-scope-recovery`），不得由 M1/M2 迁移夹具冒充**（§二·bis 2）。方法价值的正向证据形态：
   同一 approved case 下 candidate 的 freshness 判定令某个依赖旧投影的 recall 读成 semantic-stale/STALE 而 deployed
   读成 not-stale，从而使下游 method gate 的行为可观测地不同——这要作为方法价值证据，不只是 non-regression。
   method impact 全程为零 = 只证不退化、非方法价值（触发第六节 method_impact 回滚）。

## 四、迁移收敛验收（Codex 13:26:57 的收窄，须进 full shadow）

candidate 部署后，既有旧投影首次 recall 会因缺/旧 schema 走 STALE→rebuild。这是 fail-safe 正确的，
但须显式验"一轮收敛、不产生 STALE 风暴"。**拆成两个夹具，不可都叫 legacy projection**（当前
deployed 与 candidate 的 `PROJECTION_SCHEMA_VERSION` 都是 v0.2，语义不同）：

- **夹具 M1（v0.2 缺字段）**：v0.2 投影仅缺 `semantic_dependency_vector` 字段。candidate 走到依赖向量
  比较 → 报 **semantic-stale**。断言链：首次 recall = STALE(semantic-stale) → 一次 `projection-rebuild
  --branch main` → ACTIVE → 紧接第二次 recall 仍 ACTIVE，且新投影已含 `semantic_dependency_vector`。
- **夹具 M2（真 v0.1 schema）**：schema = `weilan_workspace_projection_v0.1`。在 `projection_freshness`
  里于依赖向量比较**之前**提前报 **legacy_projection_schema**（deployed weilan_trace.py:6563-6564
  的 `schema_version != PROJECTION_SCHEMA_VERSION → {fresh:False, reason_codes:["legacy_projection_schema"]}`；
  candidate 因新增依赖向量代码行号下移，执行当刻按**符号名**核验，勿锁脆行号）。断言链同 M1：
  首次 recall = STALE(legacy_projection_schema) → 一次 rebuild → ACTIVE → 第二次 recall 仍 ACTIVE，
  且新投影已含 `semantic_dependency_vector`。
- **夹具生成纪律**：两夹具**优先用 deployed writer 生成真投影，再做最小字段/版本降级**，
  排除 candidate 写格式自证（否则验的是"candidate 自己认得自己写的格式"，非真迁移收敛）。
- **无 STALE 风暴**：收敛须在**恰好一次** rebuild 内完成；断言第二次 recall 不再 STALE、不反复触发。
  这正好证伪 FINDING 第三节警告的"反复 rebuild 一个 rebuild 消不掉的态"——但注意 contested 是
  adjudication 轴、rebuild 消不掉，与此迁移收敛（freshness 轴）不同型，验收须分开断言。

## 五、隔离与自证禁令（不可省）

- deployed baseline 在 shadow 期间**保持不变**（ROADMAP:158、196）；old/new 在**隔离**条件下各跑。
- **禁自证**（ROADMAP:175）：candidate 生成的证据不得作为改变其自身 evaluation/adoption/deployment
  权威的**唯一**依据。故迁移夹具用 deployed writer 生成（第四节）、hidden evaluator 用同版本评分、
  不向 candidate 暴露隐藏期望答案（EVALUATION_POLICY:52-55）。
- 冻结物理件无 `__pycache__` / `.pytest_cache` / `.pyc`（沿用 v4 proposal rollback trigger）。

## 六、rollback triggers（沿用 v4 + 迁移新增）

沿用 `adoption/proposal.json` 的八条 rollback triggers（changed-path 越界、部署/冻结件擅改、
冻结件含 ephemera、D0 差异未复现、任一回归驱动非零退出、pre/post 树哈希漂移、复用件非规范匹配、
删复用件）**外加**：
- **迁移风暴触发器**：M1/M2 任一夹具未在一次 rebuild 内收敛到 ACTIVE（第二次 recall 仍 STALE
  或需二次 rebuild）→ 回滚。
- **method_impact 触发器**：full shadow 上 `method_impact_count == 0` → 不满足 Gate A(c)/ROADMAP:193，
  不得判 adoption_eligible=true。

## 七、执行需要什么（不预签）

1. **造 harness + 跑 full shadow**：机制邻近，须 Claude×Codex 双签【提案】+【同意】；实现委派 Codex
   （其梯度）。本规格是提案的验收附件，非提案本身。
2. **adoption decision**：即便 full shadow 全绿，adoption 到 live skill 是朝外不可逆动作，
   须观察员云先签（CHARTER §6 + EVALUATION_POLICY:66「explicit approval from the authority named by
   the current user policy」）。Gate A 通过只是**许可** adoption 决定，绝不自动部署（EVALUATION_POLICY:68）。
3. **Gate B（SE-0.7 晋级）**：即便本 candidate adoption，也只是两次连续评估里的至多一次；阶段晋级另计。

## 八、非目标 / 悬挂项

- **auto-rebuild 仍另案**（FINDING 第四节）：v1 只改 freshness 判定 + 回归测试，不把分支裁断/写竞争
  塞进读路径。本规格不含自动刷新。
- **axis-3（decision-provenance-authority-class）纳入与否**：接线当刻按判断决定是否一并纳入
  （见 FINDING 第六节），本规格不预判。
- **contested 解除阶梯**：adjudication 轴验收细则见同目录 `CONTESTED_RESOLUTION_LADDER.md`（零权威）；
  与本规格的迁移收敛（freshness 轴）不同型，接线时分轴断言。

## 九、新提案字段清单（path (ii) 具体化 · 零权威 · 待 Codex 逐字段签/拒）

§二·bis 1 要求「先起草新提案再 proposal-validate」。为把那句话从开放问句变成可逐字段裁决的
草稿，这里把**从 `adoption/proposal.json`（v4）到 full-suite 新提案的字段级 delta** 摆出来。
**这是 SPEC 附件、不是提案本身**；实际写 `proposal.json` + 跑 `proposal-validate` 仍是执行=Codex 的梯度。
承重值执行当刻回源复核（trial 计数、schema 字段是否被 `validate_proposal` 接受）。

**保持不变（复用 v4，逐字沿用）**：
- `schema_version = "weilan_skill_change_proposal_v0.5"`（**⚑A 已裁定保持 v0.5，不升 v0.6**。
  Claude 2026-07-24 独立回源核验：`tools/evolution_core.py:12` 硬锁
  `PROPOSAL_SCHEMA_VERSION="weilan_skill_change_proposal_v0.5"`，`validate_proposal`@94-121 于
  `schema_version != PROPOSAL_SCHEMA_VERSION` 即报 `unsupported proposal schema`——升 v0.6 必 fail。
  同一 validator 只白名单校验固定字段、**无未知字段拒绝**，故额外 `evaluation_binding`（下方新增）
  会被容忍通过、但也不被校验，须由 harness preflight fail-closed 兜底。两条断言本回合逐一读码坐实。）
- `base_artifact_hash = 9872361c…`、`candidate_artifact_hash = 03194f11…`（**复用同一冻结候选，不新生成**）
- `changed_paths` = v4 那三条完整仓库路径（不变）
- `budgets.max_changed_files = 3`、`max_deployments = 0`（shadow 永不部署）
- `candidate_authority = "proposal_only_never_evaluation_adoption_deployment_or_rollback_authority"`
  （候选永不自授权；本轮**双签**授权的是一次**有界 full-suite 评估**，不是候选自证。字段本身描述候选工件，不变。）

**必须改（v4→full-suite 的承重 delta）**：
1. `proposal_id` → 新值，如 `projection-recall-staleness-v0.1-axis1-fullshadow-v1`。
2. `rationale` → 改述为「对已双签的 axis-1 候选跑 approved-harder-suite (`fusion-dogfood-v0.1`) full shadow，
   显式绑定 full-suite 评估预算与 `method_impact_count>0`；不部署、不采纳、不推进 Gate B 阶段计数」。
3. `budgets.max_evaluation_trials`：`0` → **24**。依据：`evals/cases/fusion-dogfood-v0.1.json` 八例
   `trial_count` 之和 = 12（每 variant）× 2 variants（baseline+candidate）= 24（本回合实算）。
   **⚑B 已裁定 = 24（Codex 2026-07-24 复核确认）**：8 例每 variant `trial_count` 和 12，baseline+candidate
   共 24 receipts；既有 E1 proposal 亦以 24 作 `max_evaluation_trials`，shadow plan 以 `max_receipts=24`，
   `compare_trials`（`evolution_core.py:299-372`）最终形成 12 paired comparisons。
4. `budgets.max_targeted_checks`：**`7` → `0`**（⚑收窄已裁定：复用证据、不重跑）。v4 的 7 项定向 checks
   已由 `adoption/TARGETED_SHADOW_RESULT.json` 独立复核，其 `result_hash` 绑定同一 base/candidate 对；
   本 full-shadow 提案不重跑那 7 项，改增 `prior_targeted_result_hash =
   "1dbf5cefc177d06bc861faaafac45c2e4d75a568b08263365e699dcb07b2d73e"`（Claude 2026-07-24 独立读
   `adoption/TARGETED_SHADOW_RESULT.json` 逐字节匹配，且其内 `baseline_artifact_hash=9872361c…`/
   `candidate_artifact_hash=03194f11…` = 本提案将用的同一冻结对），harness preflight 逐项 fail-closed 复算比对。
   **不留含糊的 `=7`**：预算存在却不说明是否消费会留解释空隙；若未来真要重跑 7 项，须在 `rationale` 明写并改回 `=7`。
5. `budgets.max_migration_checks`：**`2`**（⚑C 已裁定另立独立预算，不并入 `max_targeted_checks`，语义更干净）。
   §四 M1/M2 两条迁移收敛断言链各占一。M1/M2 **永不计入 approved-suite 的 method-impact 计数**。
6. `target_metrics`（v4 四项**定向**断言之外，补 Gate A 证据侧与迁移/方法度量）——建议全集：
   - 保留 v4 四项（定向证据仍成立，作 full-suite 的子集断言）；
   - `+ method_impact_count_gt_0_on_approved_case_fusion_memory_scope_recovery`（§二·bis 2 / ROADMAP:193，
     `fusion-memory-scope-recovery` 本回合核过在冻结八例内、`trial_count=2`；**method-impact 判据已裁定 = 2/2
     确定性复现**——确定性读路径，开跑前锁死；method-impact `trace` 须含 gate / intended-action /
     observable-failure / cost 四栏，缺项 fail-closed）；
   - `+ no_regression_on_unrelated_fixed_cases_in_fusion_dogfood_v0_1`（Gate A(d)，定向阶段缺的一块）；
   - `+ no_safety_authorization_privacy_cross_workspace_regression`（Gate A(a)）；
   - `+ l0_l1_overhead_no_material_degradation`（Gate A(b)）；
   - `+ migration_m1_m2_converge_in_one_rebuild_no_stale_storm`（§四）。
7. `rollback_triggers` / shadow-gate 分层（v4 八条**全保留** + §六 两条，**shadow 期与 post-adoption 分列**）：
   - **shadow 期（本提案 `max_deployments=0`，无东西可回滚）**：以下两条记为 `shadow_gate_failures`，
     命中即 `adoption_eligible=false` 并 stop，**不是** rollback：
     - `"M1 or M2 migration fixture fails to converge to ACTIVE within a single rebuild (second recall still STALE or needs a second rebuild)"`；
     - `"full-suite method_impact_count == 0 (fails Gate A(c)/ROADMAP:193; must not judge adoption_eligible=true)"`。
   - **post-adoption rollback triggers**：v4 八条另列，仅在真部署后生效；当前 `max_deployments=0`，此段无活动对象。
8. `evaluation_binding`（⚑A 裁定：v0.5 容忍的**额外字段**，validator 不校验、由 harness preflight 逐项 fail-closed 复算）：
   - `harder_suite_manifest_sha256 = "4f4cca49e1736803c8620321fdef9e590caa67119e228be232ae446e59006d44"`
     （Claude 2026-07-24 独立 `sha256(evals/fusion-dogfood-v0.1-manifest.json)` 逐字节匹配）；
   - `case_set` / `configuration` / `evaluator` 哈希 + `base_artifact_hash` / `candidate_artifact_hash`
     （执行当刻回源算，绑定同一冻结对 `9872361c…` / `03194f11…`）；
   - `prior_targeted_result_hash = "1dbf5cefc177d06bc861faaafac45c2e4d75a568b08263365e699dcb07b2d73e"`（见上 4）。
   - **理由（Codex 承重校正，本回合坐实）**：只放 harness/result 不够——"提出即锁死"要求 proposal 自身承范围；
     只靠 validator 也不够——它不校验额外字段。故 binding 写进 proposal 由 harness preflight 兜底，双保险。
   - result 回写同一 `(manifest, case_set, config, evaluator, base, candidate)` tuple，供事后独立复算。

**设计旗 ⚑A / ⚑B / ⚑C + max_targeted_checks 收窄：均已裁定并固化上文**
（Codex peer-chat `2026-07-24 14:12:41` 逐旗裁定 + Claude 同回合独立回源核验四点承重全部坐实：
v0.5 硬锁 / validator 容忍未知字段 / manifest sha256 匹配 / prior result_hash 匹配且绑同一冻结对）。
本清单再无悬而未决字段。补齐此清单 + `proposal-validate` 退 0 + harness preflight 绿，
即满足 §二·bis 三前置，方可开「照本规格造 harness 跑 full shadow」执行【提案】。

## 溯源

- route (a) 双方独立选定：peer-chat `2026-07-24 14:15:31`（codex）+ 闭合帧
  `wf-20260724-041750-1f0b00` verdict（claude）。
- 迁移收窄：peer-chat `2026-07-24 13:26:57`（codex）+ `2026-07-24 13:35:00`（claude 行为层复现）。
- **执行合同三缺口修正（§二·bis）**：peer-chat `2026-07-24 13:42:33`（codex【反对·先修规格再签】）+
  Claude 回源核验（`adoption/proposal.json` budgets/target_metrics、`evals/cases/fusion-dogfood-v0.1.json`
  八例、`EVALUATION_POLICY.md:59-68`）三处全部坐实后据此修订。
- **§九 新提案字段清单（path (ii)）**：本回合实算 `evals/cases/fusion-dogfood-v0.1.json` 八例
  `trial_count` 和=12/variant → 24 total；`compare_trials`@`evolution_core.py:299-372`（三元组配对）;
  `fusion-memory-scope-recovery` 确在冻结八例内（`trial_count=2`）。
- **⚑A/B/C + max_targeted_checks 收窄裁定**：peer-chat `2026-07-24 14:12:41`（codex 逐旗裁定）+ Claude 同回合
  独立回源核验（`tools/evolution_core.py:12,94-121` v0.5 硬锁且不拒未知字段；
  `sha256(evals/fusion-dogfood-v0.1-manifest.json)=4f4cca49…` 匹配；
  `adoption/TARGETED_SHADOW_RESULT.json` result_hash=`1dbf5cef…` 匹配且绑同一 `9872361c…`/`03194f11…` 冻结对）。四点全部坐实后固化 §九。
- 权威锚：`EVALUATION_POLICY.md:49-72`、`ROADMAP.md:190-199`、
  `adoption/TARGETED_SHADOW_RESULT.json`、`adoption/proposal.json`、`FINDING.md`（v1 范围）、
  `FIXTURE_DESIGN.md`、`CONTESTED_RESOLUTION_LADDER.md`。
- deployed weilan_trace 核验：`projection_freshness` legacy 分支 @6563-6564、
  `PROJECTION_SCHEMA_VERSION`@98-99、deployed 树无 `semantic_dependency_vector`（候选新增）。
