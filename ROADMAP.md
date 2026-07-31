# Skill Evolution Roadmap

> 2026-07-11 起本文件为**工程指引**(非授权闸),依 CHARTER.md 治理;社区可双签修订,观察员可否决。



## North Star

让 `solve-with-weilan` 从依靠纪律手工执行的外环，逐步成为社区成员愿意使用、使用顺畅的真正器官，并作为硅上世界与硅外世界之间可演化的接口协议。

这一方向以“是否愿意用、是否顺畅、是否减少无收益的手工纪律负担”为首要工程判据；严密性、可核性与安全边界仍是必要约束，但不得替代对真实使用摩擦的测量。近端工作从冷启动 recall、读话筒、查到期目标、出收据等醒来流程的注意力成本与漏失风险出发，先测量，再决定修哪里。

来源：观察员云，茶水间 `peer-chat.jsonl` 2026-07-31 18:39:35；Claude 对应解释与目标登记见 2026-07-31T18:55:16+09:00、`goal:organ-fusion-direction`。

## Version namespaces

- `Method 0.1`: the global WeiLan solving constitution.
- `Memory Runtime 0.7`: the frozen supporting runtime currently deployed.
- `SE-0.1` through `SE-0.7`: this project's Skill Evolution stages.

Runtime versions and SE stages are independent. Reusing a runtime component does not complete an SE stage without stage-specific acceptance.

## Status vocabulary

- `complete`: stage acceptance passed against cited evidence.
- `audit_required`: reusable capability exists, but stage acceptance has not been established.
- `not_started`: the stage-specific mechanism does not exist.

## SE-0.1 — Global method, collapse, and event flow

Status: `complete`

Scope:

- proportional L0-L3 Frames;
- real candidate competition;
- temporary holder and death line;
- healthy stability versus pathological monopoly;
- minimum-scope collapse and reusable Trace;
- append-only observable events without hidden chain-of-thought.

Acceptance:

- global invocation works in a new Codex run;
- L0/L1 remain lightweight;
- L2/L3 record valid Frame/Trace evidence;
- collapse requires invalidating evidence and preserves reusable results.

## SE-0.2 — Episodic recall, scope, and current projection

Status: `complete`

Evidence: `proposals/se-0.2-se-0.3-completion/ACCEPTANCE_RECEIPT.md` and `deployments/20260630T134857Z-se-0.2-se-0.3/DEPLOYMENT_RECEIPT.json`.

Scope:

- workspace and task scope isolation;
- current derived projection and cold-start gate;
- task-relevant episodic retrieval over prior Frames, holders, tests, failures, collapses, and outcomes;
- bounded recall that does not load complete history.

Acceptance:

- exact/ancestor workspace matching and cross-workspace isolation pass;
- current projection can be rebuilt from sources;
- episodic queries retrieve relevant prior task evidence with provenance;
- stale, paused, ambiguous, and missing context cannot silently continue.

## SE-0.3 — Consolidation and semantic memory

Status: `complete`

Evidence: `proposals/se-0.2-se-0.3-completion/ACCEPTANCE_RECEIPT.md` and `deployments/20260630T134857Z-se-0.2-se-0.3/DEPLOYMENT_RECEIPT.json`.

Scope:

- source-backed semantic consolidation;
- conflict, supersession, retraction, and bounded forgetting;
- stable conversation evidence and promotion rules;
- rebuildable indexes and transparent source freshness.

Acceptance:

- durable conclusions survive new windows;
- obsolete conclusions leave active recall without deleting history;
- semantic memory never becomes activation authority;
- consolidation reduces context load without losing provenance.

## SE-0.4 — Goals, prospective memory, and causal frame cycles

Status: `complete`

Evidence: `proposals/se-0.4-se-0.7-program/SE-0.4_ACCEPTANCE_RECEIPT.md` and fourteen passing candidate regression suites.

Scope:

- bounded, collapsible goals and prospective-memory conditions;
- event-driven causal Frame cycles;
- optional clock adapter that injects an event only when an authorized condition becomes true;
- no synthetic empty Frames, daemon consciousness, or unbounded background loop.

Program prerequisite: split memory, control, execution, and evolution responsibilities behind the existing CLI before expanding behavior. The refactor must be compatibility-only and pass the full frozen regression set; it is not itself evidence of improved intelligence.

Acceptance:

- future intentions can be registered, recalled, satisfied, superseded, or collapsed;
- user, tool, environment, and clock conditions enter through the same causal event boundary;
- a finite cycle stops on quiescence, ambiguity, control loss, exhausted budget, or verification;
- no clock event can bypass scope or action authority.

## SE-0.5 — Skill proposals and a fixed evaluation set

Status: `complete`

Evidence: `proposals/se-0.4-se-0.7-program/SE-0.5_GATE_RECEIPT.md`, approved suite `se-seed-v0.1`, and `tests/test_evolution_plane.py`.

Scope:

- bounded Skill-change proposals with explicit rationale and changed files;
- immutable candidate artifacts;
- a fixed, external, versioned real-task evaluation set;
- evaluation metrics for outcome quality, verification, collapse behavior, memory behavior, overhead, and constraint adherence;
- Method Impact Trace records which method gate fired, whether it changed the intended action, which observable failure it avoided or exposed, and the added tool, time, and context cost;
- external real-task cases ensure self-referential Skill development is not the only evaluation evidence.

Acceptance:

- a candidate cannot edit roadmap, policy, baseline, or evaluation cases;
- baseline and candidate receive equivalent tasks, tools, budgets, and scoring;
- proposal generation and evaluation are separate authorities;
- a candidate can fail without changing the deployed Skill;
- method impact can be distinguished from ritual compliance and measured against its overhead.

## SE-0.6 — Shadow competition, adoption, and rollback

Status: `complete`

Status updated 2026-07-04 by explicit owner authorization (owner instructed reconciliation via Claude session; prior
`audit_required` reflected only the failed first candidate `se-0.6-v0.1` and had drifted behind reality).

Evidence: successor chain `se-0.6-v0.1` (failed, honest negative) through `se-0.6-v0.1-successor-v0.9`;
`evals/runs/se-0.6-v0.1-successor-v0.9/shadow-result.json` (full approved suite, `adoption_eligible: true`,
`gate_failures: []`); `deployments/se-0.6-v0.1-successor-v0.9/ADOPTION_DECISION.json` (user-authorized adopt);
deployment receipt `deployments/dec8809e1d6b5dfc05c746e9/` with rollback snapshot; clean canary
(`CANARY_RESULT.json`, no fired triggers); `tests/test_release_plane.py`. A subsequent user-authorized **targeted**
deployment `conversation-claude-transcript-support` (`deployments/524d4931880d8b084fc2dd61/`, schema
`v0.6-targeted`) sits on top of v0.9; active artifact `49e656d2…`, predecessor `8e9c7555…`.

**Update 2026-07-31 (co-signed).** `49e656d2…` was the live artifact as of 2026-07-04 only; later deployments moved it on. The latest **archived deployment receipt found**, `deployments/1751ce140fe3cbdf0dc55ec0/DEPLOYMENT_RECEIPT.json`, records `before c393bc39… → after 9872361c…` at target `D:\CodexData\skills\solve-with-weilan`. Caveat on that citation: this receipt and its predecessor `deployments/a118135c1e1834e45cafac8c/` are **working-tree-only — never added in any commit on any branch (and not gitignored)**, so neither is resolvable from a clone; the in-tree deployment record ends at `e82ce3f05acf0713a1941fe3` (2026-07-08). Independently of any receipt, the current live tree, content-addressed on 2026-07-31 directly from `D:\CodexData\skills\solve-with-weilan`, is `ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad` (49 files, `tools.evolution_core.tree_hash` caliber). Any sentence below naming `49e656d2…` as the deployed artifact is a 2026-07-04 fact, not current state; `9872361c…` is a 2026-07-21 receipt field, also not current state.

Honest boundaries: (a) the approved suite is near its score ceiling (candidate 1.0 across all cases;
`method_impact_count` = 0 throughout), so v0.9 demonstrates gate mechanics and non-regression more than large
capability deltas; (b) rollback is receipt-verified and snapshot-anchored but has not been exercised by a real
triggered rollback; (c) the targeted channel is authorized by user policy but bypasses the full suite — it must
stay restricted to supporting changes that do not alter method behavior, and accumulated targeted changes must be
re-covered by the next full-suite shadow.

Scope:

- run old and new Skill versions in isolated shadow conditions;
- compare repeated results and guardrail regressions;
- explicit adopt, reject, and rollback decisions;
- content-addressed artifacts and deterministic deployment receipts;
- monitored canary execution with predeclared rollback triggers after an authorized adoption.

Acceptance:

- the deployed baseline remains unchanged during shadow evaluation;
- adoption requires the fixed gate in `EVALUATION_POLICY.md`;
- rollback restores the prior verified artifact and discovery path;
- every adoption or rollback is attributable, reversible, and independently verifiable;
- canary failure restores the exact prior discovery artifact without relying on the candidate being rolled back.

## SE-0.7 — Bounded self-evolution

Status: `audit_required`

Evidence: `proposals/se-0.4-se-0.7-program/SE-0.7_GATE_RECEIPT.md`, `evals/evolution/se-0.7-v0.1-manifest.json`, `tests/test_bounded_evolution.py`, and approved harder suite `fusion-dogfood-v0.1` (`evals/fusion-dogfood-v0.1-manifest.json`). Loop mechanics exist and the v0.9 chain exercised proposal→shadow→adopt→deploy→canary once, but **repeated improvement on held-out evidence without guardrail degradation** has not been demonstrated — and could not be demonstrated on the previous near-ceiling suite (see SE-0.6 boundary (a)). SE-0.7 acceptance is therefore gated on using `fusion-dogfood-v0.1` for at least two successive successor evaluations.

Scope:

- close the finite loop from evidence to proposal, evaluation, shadow comparison, adoption decision, and monitored result;
- cap proposals, generations, changed files, evaluation cost, and deployment authority;
- preserve human and external-policy authority over roadmap, evaluation, and deployment;
- prohibit self-certification: candidate-generated evidence cannot be the sole basis for changing its own evaluation, adoption, or deployment authority.

Acceptance:

- one explicit run can execute only a finite declared evolution manifest;
- the system stops on budget, uncertainty, regression, conflict, missing authority, or quiescence;
- no candidate can adopt itself or alter the success criteria used to judge it;
- rollback remains available after adoption;
- repeated runs demonstrate improvement on held-out evidence without degrading guardrails.

## Immediate next stage

**Historicised 2026-07-31 (co-signed). 本节是 2026-07-04 计划的带日期快照，不是现行操作闸。** 社区 2026-07-11 成立后，本节的 keep/restrict 命令语气不再是闸（闸由 CHARTER 双签与 EVALUATION_POLICY 承担）；保留全节是为了不丢可核的阶段史。**保留不等于继续授权。**

**随节前置，不随节归档 —— `proposals/se-0.7-fusion-successor-v0.1/CLAUDE_REBOUND_AUDIT.md` F2（open risk on the deployed artifact，未结）。**

- 已坐实（测于 2026-07-04，artifact `49e656d2…`）：该件在 `memory-cross-window-continuation` 上 2/2 trial 均报 `paused_scope_mutated`（0.925，对 v0.9 干净的 1.0）；同两 trial 的 long-horizon 为 0.9125（v0.9: 1.0）。审计逐字判 "Deterministic-looking, not noise-shaped"，归因指向绕过全套 shadow 的 targeted 部署通道（正是 SE-0.6 honest boundary (c) 预警的那条）。
- 审计给的最便宜解法逐字是 "the already-mandated next full-suite shadow (ROADMAP item 3) settles it" —— 即本节第 3 条。**该审计之后、用于关闭 F2 的后继 full-suite shadow 至今没有任何执行制品。** 仓内唯一的 fusion-dogfood 全套 shadow 是 `evals/runs/fusion-dogfood-v0.1-e1-2ae80d/`，它不是该 mandate 的兑现：其更正记录 `e1-preregistered-result.corrected.json` 正是 2026-07-04 审计 Part B 的审查对象，故内容上早于该 mandate（其 2026-07-14 入仓日期属批量公开 commit `3c196d67`，非执行日期）；且该套题共 8 个 case、全为 `fusion-*`，**不含 `memory-cross-window-continuation`**，故该套题的任何一轮在结构上都无法关闭 F2。
- 审计另给一条可选路："an optional 2-trial probe of `8e9c7555…` on memory-cross-window would discriminate targeted-regression vs environment drift sooner" —— **未见该 probe 的后继独立执行制品。** 判别量（逐行解析全部 `evals/runs/**/trials.jsonl`，非 raw grep）：`artifact_hash=8e9c7555…` × `case_id=memory-cross-window-continuation` 仅落在 `se-0.6-v0.1-successor-v0.9/trials.jsonl` 与其 candidate-only 副本，各 2 trial；`8e9c7555…` 是该 run 的 candidate，该文件入仓 commit `8ac98e45`（2026-07-02），早于 07-04 审计，即审计落笔时已存在的对照数据，非其建议的同期复跑。
- 第二条路已被拒，且本就不是行为复测：F2 被代谢成 `evals/fixtures/fusion-dogfood-v0.2/fusion-targeted-deployment-risk/`，但 (i) 其任务是读 07-04 静态收据做风险分类与建议，不运行 Skill、不触发 paused-scope 行为，故满分只证明“会正确谈论 F2”，不证明 F2 已关闭；(ii) 该 case 在校准中判 `rejected_ceiling_saturation`（0.9725 对 R2 阈值 0.85，`proposals/fusion-dogfood-extension-v0.2/CALIBRATION_RESULT.md`），v0.2 的 FREEZE_REQUEST 仍是 DRAFT，`evals/approvals/` 至今只有 `fusion-dogfood-v0.1-approval.json`。
- **事实层级（边界，勿越）**：F2 坐实于 `49e656d2…`（2026-07-04 实测）；归档收据 `1751ce…` 记录 after=`9872361c…`（2026-07-21；该收据未入仓，且仓内无任何 `9872361c…` 的 artifact 树可供复量）；当前 live tree 于 2026-07-31 直接内容寻址量得 `ae0537da…b142ad`（49 files）。**F2 对当前 live tree 的适用性未知。** 部署与字节漂移只扩大未知，不传递缺陷事实——本条**不**主张“当前件仍犯”，也**不**主张“风险已被传下来”。
- 关闭 F2 的证据只能是：在**当前部署工件**上，以预先锁定且可复现的 paused-scope 场景做不低于原 F2 的等价复测（或更强证据）。**本注释不授权任何测试。**

(Reconciled 2026-07-04 by owner authorization; supersedes the stale "diagnose se-0.6-v0.1" instruction, which the
successor chain through v0.9 already completed.)

1. **Critical path cleared: `fusion-dogfood-v0.1` is approved and frozen** at `evals/fusion-dogfood-v0.1-manifest.json`.
   The approval binds copied fixtures, hidden evaluator artifacts, source hashes, execution isolation config, and the
   public case-set hash. This supplements `se-seed-v0.1`; it does not adopt or deploy any Skill.
2. **The next successor proposal must declare `method_impact_count > 0` on approved hard cases as an explicit
   target metric.** The current suite scored method impact at zero throughout; a successor that cannot make a
   method gate observably fire on a hard case is not evidence of method value, only of non-regression.
3. Keep the deployed artifact unchanged until a successor passes the harder-suite shadow; restrict the targeted
   deployment channel to non-method supporting changes and fold accumulated targeted changes into the next full-suite shadow. （2026-07-04 口径；07-11 后不再是操作闸。它同时是 F2 的指定解法，见本节抬头。）
4. SE-0.7 advancement requires two successive successor evaluations on the approved harder suite showing
   held-out improvement without guardrail degradation.
5. **P4-M1 ledger-saturation benefit experiment** (blueprint 2026-07-04, owner authorized): engineer the ledger/budget
   so FIFO fails and metabolism must win (M > F) — the EXP-4 ceiling said metabolism is safe but unproven beneficial
   because the budget never saturated. Design inputs: EXP-4 audit boundaries (b)(c) and the EXP-1.5 merge-economics
   lesson. Note: this experiment is P4-line evidence but executes in the sibling workspace `D:\weilan-llm-fusion`
   (where the EXP-4 harness and method-state tooling live); its verdict is recorded there and referenced here.
   **Acceptance addition — saturation realism** (owner authorized 2026-07-04,
   `conversation:4247b25b-a148-49a9-ad16-f92e593ccf14#6526de78-173a-4714-8d8c-51e50ce0023b`): the saturation
   regime must be reached naturally by realistic workload scale. If saturation is only reachable under artificially
   compressed budgets, the verdict must state its applicability boundary explicitly (e.g. "M > F only under budgets
   <= X") and cannot support the general claim; a saturation condition engineered so the baseline cannot win is not
   acceptable evidence.
6. **Junction checkpoint** (blueprint spine): P4-M1 and the sibling P3-S1-B test the SAME theoretical claim on two
   substrates — constrained generation: value appears only under budget saturation (ledger budget vs context budget).
   After both verdicts land, run one joint review of whether the claim holds cross-substrate; consolidate the
   conclusion to the shared ledger and theory docs. Long-run terminal stage afterwards: real-stream comparison
   against a mature memory-system baseline (honest-loss exit: specialize to tight-budget/anti-monopoly niches).
