# Authoritative Skill Evolution Roadmap

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

Status: `not_started`

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

Status: `not_started`

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

Status: `not_started`

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

Use the deployed SE-0.2/SE-0.3 release during one bounded long-horizon program, then implement SE-0.4 through SE-0.7 sequentially behind stage acceptance gates. Before SE-0.4 behavior expands, establish a compatibility-preserving runtime boundary so new capabilities do not continue accumulating in the monolithic CLI. SE-0.5 must add external real-task cases, method-impact and overhead evidence, and independent evaluation authority; self-referential Skill work alone cannot establish improvement.
