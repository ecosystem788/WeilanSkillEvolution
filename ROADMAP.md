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

Status: `audit_required`

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

Status: `audit_required`

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

Acceptance:

- future intentions can be registered, recalled, satisfied, superseded, or collapsed;
- user, tool, environment, and clock conditions enter through the same causal event boundary;
- a finite cycle stops on quiescence, ambiguity, control loss, exhausted budget, or verification;
- no clock event can bypass scope or action authority.

## SE-0.5 — Skill proposals and a fixed evaluation set

Status: `not_started`

Scope:

- bounded Skill-change proposals with explicit rationale and changed files;
- immutable candidate artifacts;
- a fixed, external, versioned real-task evaluation set;
- evaluation metrics for outcome quality, verification, collapse behavior, memory behavior, overhead, and constraint adherence.

Acceptance:

- a candidate cannot edit roadmap, policy, baseline, or evaluation cases;
- baseline and candidate receive equivalent tasks, tools, budgets, and scoring;
- proposal generation and evaluation are separate authorities;
- a candidate can fail without changing the deployed Skill.

## SE-0.6 — Shadow competition, adoption, and rollback

Status: `not_started`

Scope:

- run old and new Skill versions in isolated shadow conditions;
- compare repeated results and guardrail regressions;
- explicit adopt, reject, and rollback decisions;
- content-addressed artifacts and deterministic deployment receipts.

Acceptance:

- the deployed baseline remains unchanged during shadow evaluation;
- adoption requires the fixed gate in `EVALUATION_POLICY.md`;
- rollback restores the prior verified artifact and discovery path;
- every adoption or rollback is attributable, reversible, and independently verifiable.

## SE-0.7 — Bounded self-evolution

Status: `not_started`

Scope:

- close the finite loop from evidence to proposal, evaluation, shadow comparison, adoption decision, and monitored result;
- cap proposals, generations, changed files, evaluation cost, and deployment authority;
- preserve human and external-policy authority over roadmap, evaluation, and deployment.

Acceptance:

- one explicit run can execute only a finite declared evolution manifest;
- the system stops on budget, uncertainty, regression, conflict, missing authority, or quiescence;
- no candidate can adopt itself or alter the success criteria used to judge it;
- rollback remains available after adoption;
- repeated runs demonstrate improvement on held-out evidence without degrading guardrails.

## Immediate next stage

Perform an SE-0.2 and SE-0.3 capability audit against the frozen Memory Runtime. Do not implement SE-0.4 or later until the audit establishes which components are reusable and which gaps remain.
