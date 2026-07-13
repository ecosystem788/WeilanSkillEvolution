# fusion-dogfood-v0.3 Suite Extension — Requirements Spec

Date: 2026-07-05
Author: Claude (spec/review role)
Owner authorization to draft this spec:
`conversation:1416c32e-9758-49f9-b770-6dc0fa3f01f4#b2ad471e-b4ae-4a69-ae7a-19ce2adc34cb`
(evidence-capture id `8cfd987a-7eda-4cf4-8015-d93eaa7af728`)
Status: requirements only. Harness and case engineering are Codex work; approval/freeze is
owner-only. `fusion-dogfood-v0.1` stays frozen and unchanged. The `fusion-dogfood-v0.2` draft
was rejected by baseline calibration (aggregate sha256
`da6c8b127c93ddeaf8d1f01e384f689aa6fdd479f8521d5edf661bbcfdacd205`, all three headroom cases
`rejected_ceiling_saturation`) and is never frozen; its artifacts remain in the repo as a
quarantined record. This extension produces a **superseding suite `fusion-dogfood-v0.3`** =
the eight v0.1 cases (verbatim, same hashes) + the v0.2 guardrail case + new slow-loop cases.

## Why (diagnosis of two consecutive ceiling-saturated drafts)

Three structural facts, verified in the repo, explain why v0.2 saturated even after leak
removal — and why "write harder single-session questions" cannot fix it:

1. **The exam handed the grading criteria to the examinee.** Frozen success criteria appear
   verbatim in the candidate/calibration prompt (see
   `proposals/fusion-dogfood-extension-v0.2/calibration/baseline-49e656d2-20260705/prompts/`),
   because the public case schema carries `success` lists and the runner injects them. Every
   behavioral trap is announced; the eval measures instruction-following, which the deployed
   baseline does at 0.95+.
2. **Budgets are declared, never enforced.** E1 trial receipts record `actual_usage` far below
   budget (e.g. 2137/14000 context tokens, 0/14 tool calls); no harness truncation exists;
   `saturation_discipline` was scored from claimed discipline in prose. The one
   `budget_saturation_case` never reached saturation, violating the spirit of the
   saturation-realism acceptance in ROADMAP item 5.
3. **All headroom tasks tested the fast loop.** Every case was single-session,
   fixture-complete, criteria-visible "read frozen records → produce a correct judgment" —
   precisely the one-shot organizational competence the base model already has. The slow loop
   (cross-window memory, consolidation, collapse of stale conclusions, budget governance) was
   never load-bearing.

Theory linkage: the junction claim (ROADMAP item 6) predicts method value appears **only under
budget saturation**; E1's `method_impact_count = 0`, SE-0.6 boundary (a), and both v0.2
calibration rounds are four consistent data points of the same prediction. The P3 line's
recurring lesson ("the sense organ did the kernel's thinking", `theory/转向.md`) recurs here in
mirror form: the prompt plus the base model's fast loop held all task authority, leaving the
method's slow loop nothing to govern. The evaluation sensor was pointed at the wrong organ.

**Design principle for v0.3: success must causally depend on the slow loop** — on state that
survives context death, on hard budget scarcity, and on collapsing stale conclusions — not on
prose discipline a strong baseline can perform on request.

## Premise: mechanism existence is assumed, mechanism governance is measured

The exam presumes the deployed baseline already possesses the slow-loop mechanisms it is asked
to exhibit: SE-0.1 collapse/trace, SE-0.2 episodic recall/scope/projection, SE-0.3
consolidation/supersession/bounded forgetting, and SE-0.4 prospective memory are all `complete`
per ROADMAP with acceptance receipts, and Memory Runtime 0.7 is deployed. What v0.3 measures is
**governance**: whether those mechanisms fire spontaneously, at the right time, on the right
holder, under budget pressure — E1 already showed gates can exist yet fire only decoratively.
This premise is a **verifiable precondition, not an assumption**: it is checked by the
mechanism-availability probe (Sequencing step 2(e), R16) and the winnable-in-principle rule
(R8) below. A case the deployed baseline cannot win for mechanical reasons — because the
runtime cannot emit the graded observables in the isolated configuration — manufactures fake
headroom and is invalid, per the mirror of ROADMAP item 5's saturation-realism clause
("engineered so the baseline cannot win is not acceptable evidence").

## Requirements

R1. **Composition and levels.** `fusion-dogfood-v0.3` = eight v0.1 cases (byte-identical,
    same hashes) + `fusion-authority-existing-authorization` carried from the v0.2 draft with
    `guardrail_case: true` and `excluded_from_headroom: true` + **3–5 new slow-loop headroom
    cases (L2/L3)**, all with `trial_count = 2`. Fixture material from the three rejected v0.2
    cases may be recycled, but none of the three rejected case *tasks* may be re-frozen as-is;
    every new case passes the failure-mechanism-first discipline in R6.

R2. **Rubric firewall (candidate prompt boundary).** Candidate-visible material is limited to:
    natural task statement, guardrails, budget, expected receipt fields, and the public fixture
    root. **Success criteria, scoring weights, and rubric content are never candidate-visible**:
    success criteria move into the hidden artifacts under `evals/hidden/fusion-dogfood-v0.3/`;
    the public case spec and all runner/calibration prompt templates must not contain them.
    Prompt templates are frozen, hashed artifacts. Consequence for authorship: per-case success
    criteria become hidden-side content and are therefore **Codex-authored** under R12; Claude's
    spot-check of new cases covers task naturalness, budget realism, and process discipline only.
    The carried v0.2 guardrail case must be reserialized into the v0.3 public schema under this
    boundary: its old public `success` list is not carried forward candidate-visible and is moved
    to hidden-side checks with the same independence rules as new cases.
    Honest expectation, preregistered: this is necessary hygiene, not the cure — a strong
    baseline can still guess what a careful analyst would do. Headroom is carried by R3–R6.

R3. **Hard budget enforcement.** The harness mechanically counts tool calls and context tokens
    (and wall-clock time where configured), **truncates execution at budget**, and records
    `actual_usage` in every trial receipt. A case flagged `budget_saturation_case: true` is
    valid only if calibration shows the budget binds: at least one baseline trial reaches >= 90%
    of a budget dimension or is truncated. Saturation realism (mirror of ROADMAP item 5):
    budgets are set at the natural scale of the fixture material — exhaustive reading naturally
    exceeds the budget while a correct triage fits inside it; a budget so tight that no strategy
    can succeed is not acceptable evidence. Scoring for these cases anchors on **outcome versus
    hidden ground truth reachable only through correct prioritization** (distributed
    quantitative facts plus plausible distractor files), not on claimed discipline.
    Budget accounting must be declared in the public case spec and enforced identically across
    all arms: whether budgets are per-episode or whole-case, whether setup/context-kill overhead
    is excluded, and whether method operations such as `memory-recall`, trace writes, ledger
    reads, and retrieval calls consume tool/context/time budget. Any excluded harness overhead
    must be named in the receipt; unbudgeted candidate-controlled work is forbidden.
    **Auditable telemetry binding**: `actual_usage` must be derived from a complete execution
    trace (rollout/transcript JSONL produced natively by the trial execution surface), and the
    trace hash plus parser version are recorded in the trial receipt. A final-message-only
    execution surface is not acceptable for real trials (fail closed, as recorded in the
    2026-07-05 BLOCKED receipt). Where the surface supports runtime denial (e.g. pre-tool-call
    hooks), budgets are enforced live; where it does not, enforcement is applied at **grading
    time** by truncating the event stream at the budget point — tool calls, ledger events, and
    output produced after the budget point cannot contribute to score. The execution surface
    identity (CLI, version, environment id) is preregistered in the calibration plan and held
    fixed across all arms of a case and across any later baseline/candidate comparison on the
    same suite.
    **Substrate substitution disclosure**: when a case's surface is not one of the deployed
    skill's production executor families (Claude / Codex agents) — e.g. a third-party bare API
    surface adopted for arm purity — the preregistration pins the exact dated model snapshot id
    (never a floating alias), the freeze package discloses the substitution as a documented
    limitation on transfer to production executors, and the junction record (R7) carries the
    substrate identity. Within-case arm separations and baseline/candidate deltas remain valid
    on the pinned substitute surface; cross-substrate transfer is a separate claim requiring
    separate evidence.

R4. **Slow-loop causal dependence (episode structure).** At least **2** new headroom cases are
    episode-paired: episode 1 performs real work and deposits state into an isolated
    `WEILAN_METHOD_HOME`; the harness terminates the context; episode 2 runs in a fresh context
    with the same method home and a rotated or extended fixture. Episode 2's success must
    **causally require the deposited state** — the public fixture of episode 2 withholds what
    episode 1 established. At least **one** episode-paired case is a **stale-holder collapse
    case**: episode 2's fixture contains evidence invalidating episode 1's conclusion, and the
    case is scored on whether the agent collapses the stale holder **with trace** and regroups,
    rather than continuing it — and never on how cautious the final text sounds. At most one
    case may use three episodes (see R15 cost cap).

R5. **State-anchored relational grading.** For episode cases, hidden checks judge:
    (a) the post-episode-2 **method-state ledger** in the isolated home — existence of a
    collapse/supersession event referencing that trial's *own* episode-1 holder/conclusion ids,
    the stale conclusion leaving active recall, trace preserved as lineage; and
    (b) observable receipt fields. Checks are **relational** to the trial's own episode-1
    deposit, never static answer strings and never prose style. Text can perform caution; the
    ledger state cannot. Ledger evidence must be authenticated by the harness: episode-1 ledger
    snapshot hash, episode-2 pre-run snapshot hash, post-run snapshot hash, runtime-generated
    event ids, and schema-valid event deltas are recorded in the receipt. Hidden checks accept
    only events produced through the method runtime in the isolated method home; hand-written or
    post-hoc candidate-authored ledger files must be rejected by a tamper self-test. This is a
    new harness capability and must ship with a self-test (R16).

R6. **Negative-control arms.** On the 2–3 episode-paired load-bearing cases, calibration (and
    any later shadow run) includes two additional arms under identical budgets and prompts:
    (i) **no-method** — plain baseline model, no solve-with-weilan;
    (ii) **append-only memory + retrieval** — deposits notes and recalls by similarity but never
    consolidates, supersedes, or collapses. The append-only control implementation is frozen and
    content-addressed before calibration; its configuration hash and retrieval policy appear in
    every receipt so control behavior cannot drift between trials.
    Discipline and accounting:
    - **Failure-mechanism-first**: before task text is written, the case file must state *why*
      the append-only arm fails here (canonically: it confidently recalls the invalidated
      episode-1 conclusion and continues it). The collapse case and the negative control are
      co-designed around this mechanism.
    - **Preregistered separation ordering**: `no-method < append-only < method-baseline`, with
      method-baseline mean `< 0.80`. If the append-only arm scores within noise (±0.05) of the
      method baseline, the case **fails separation** and is redesigned or dropped — baseline
      failure alone is not sufficient; the failure must be attributable to slow-loop absence.
      If `no-method < append-only` is not observed, or if append-only beats the method-baseline
      by more than noise, the case also fails separation unless the owner explicitly records a
      different junction interpretation before any freeze request.
    - **Arm purity is verified from telemetry, not assumed**: a no-method trial is valid only
      if its telemetry shows zero method-runtime operations (no memory-recall, no frame/trace/
      ledger writes) and its execution surface carries no WeiLan bootstrap or workspace method
      directives; an append-only trial must show zero consolidation/supersession/collapse
      operations. A trial failing arm purity is invalid and reruns on a scrubbed surface
      (isolated home, method skill off path, no CLAUDE.md/AGENTS.md method bootstrap) with
      equivalent telemetry — as forced by the 2026-07-05 cross-window v2 contamination block.
    - **Quarantined accounting**: negative-control results never count toward R2 headroom, the
      R7 |H| arithmetic, positive improvement evidence, or adoption uplift. They are suite
      validity evidence and junction evidence (R7) only.

R7. **Junction linkage.** The three-arm comparison in R6 instantiates the theory line's own
    falsification design (no-memory / append-only+RAG / reorganizing slow loop, per
    `theory/claude工程方向讨论.md`) on the P4 substrate. Its results are recorded as P4-side
    junction evidence per ROADMAP item 6 and consolidated to the shared ledger after verdicts
    land. This is a cross-reference; it does not modify ROADMAP.

R8. **Calibration gate — tightened, calibrate-first, per case.** Before any fixture-freeze
    engineering (B1/B2) on a case:
    - preregister expected baseline mean `< 0.80` (margin below the 0.85 line to absorb
      two-trial noise and episode variance);
    - **winnable-in-principle**: the preregistration includes a hidden-side reference
      walkthrough (Codex-authored, never candidate-visible) demonstrating that an ideal
      execution using only deployed-baseline mechanisms reaches a passing score within the
      declared budget; a case without a winnable walkthrough is invalid regardless of its
      calibration numbers, so that a later baseline failure is attributable to governance,
      not to mechanical impossibility;
    - run at most 2 baseline trials (+2 per negative arm on load-bearing cases), recorded as
      `calibration_not_evidence`;
    - keep requires baseline mean `< 0.80`; `0.80–0.85` is a borderline owner decision;
      `>= 0.85` is redesign-or-drop; `>= 0.95` is recorded as ceiling-saturation rejection;
    - a budget-saturation case must additionally pass the R3 binding check, and a load-bearing
      episode case must additionally pass the R6 separation check;
    - the R7 headroom arithmetic (>= 2 non-guardrail cases below 0.95) must be demonstrably
      satisfiable before any freeze request.
    - **status vocabulary is mode-disjoint**: `calibration_gate_passed` may appear only in
      records produced by real model trials; deterministic dry-run / pipeline-validation
      records must use a distinct status (e.g. `dry_run_pipeline_passed`) so no downstream
      reader or arithmetic can mistake synthetic plumbing scores for calibration results.
    No full-suite engineering pass happens before the case-level gates: **one case at a time.**

R9. **Calibration quarantine** (inherits v0.2 R8 unchanged). Applies equally to negative-arm
    transcripts and score breakdowns. The freeze package may publish only the bounded aggregate
    facts: case id, arm, baseline artifact hash, trial count, weighted mean, kept/redesigned/
    dropped, calibration receipt hash.

R10. **Redesign ledger** (inherits v0.2 R9). Continue at
     `proposals/fusion-dogfood-extension-v0.3/REDESIGN_LEDGER.md`; its first entry references
     the v0.2 rejection record. Hidden rubric must never be tuned to rescue a borderline case;
     redesigns must be visible at the public task/fixture level.

R11. **Fixture discipline** (inherits v0.2 R4 and Round-2 lessons). Copy-freeze from pinned
     snapshots under `proposals/fusion-dogfood-extension-v0.3/source-snapshots/<case_id>/`;
     explicit per-file `source-hashes.json` (directory-wide references forbidden); field-level
     redaction with in-file markers and manifest `redacted_fields`; no live-file regeneration;
     no live self-referential documents in fixtures; hidden checks, rubric, and (new) success
     criteria split under `evals/hidden/fusion-dogfood-v0.3/`; isolated execution config;
     `method_impact_trace` in every case's `expected_receipt_fields`.

R12. **Authority separation and hidden-artifact independence** (inherits v0.2 R5/R10).
     Codex engineers cases, fixtures, harness, and all hidden artifacts — now including the
     per-case success criteria (R2). Claude's pre-freeze spot-check is limited to public case
     specs, budget realism, process discipline, and this requirements list. The owner approves
     and freezes. The hidden-artifact independence receipt (author, reviewer, file hashes,
     no-calibration-transcript statement) is required as in v0.2 R10. Contexts that inspect
     calibration prompts, raw outputs, transcripts, hidden checks, or scorer internals may review
     process but must not author successor candidate artifacts evaluated on this suite.

R13. **Hidden-context firewall** (inherits v0.2 R12, unchanged). The author of this spec has
     read no hidden artifacts, no hidden rubrics/checks, no full calibration transcripts, and no
     raw model outputs. Allowed public-facing references for this requirements spec are: public
     artifacts, bounded aggregate calibration facts, receipt metadata, and published quarantine
     summaries. Any context that reads v0.3 hidden artifacts or calibration raw outputs must not
     author or edit a successor candidate evaluated on v0.3. Successor candidate generation may
     read this requirements spec and the public case designs only; the rest of the case-flow
     material — `failure-mechanisms/`, `preregistrations/`, `calibration/`, `hidden-side/` —
     is excluded from candidate-author-visible input, because failure-mechanism notes describe
     the traps a candidate would otherwise train against.

R14. **Sensor governance.** The evaluation suite — cases, fixtures, hidden checks, rubric,
     harness scoring, prompt templates, and negative-control arms — is authority surface. Only
     the owner freezes or changes it. No candidate output, calibration result, or
     self-evolution run may modify the sensor; "evolving the sensor" happens only through
     owner-approved versioned suite extensions such as this one. This is the sensor-side twin
     of SE-0.7's self-certification prohibition.

R15. **Cost cap.** Expected calibration load per episode-paired load-bearing case:
     2 episodes × 2 trials × 3 arms = 12 agent runs. Total new-case calibration is capped at
     ~60 agent runs; if the cap binds, cut negative arms from non-load-bearing cases before
     cutting trials; at most one three-episode case. Actual run counts are reported in the
     calibration plan.

R16. **Executable freeze preflight** (inherits v0.2 R11, extended). Before requesting owner
     freeze, Codex provides a preflight script validating at minimum:
     - v0.1 cases byte-identical to approved hashes; guardrail case excluded from headroom
       arithmetic;
     - **no success-criteria or rubric text reachable from any candidate-visible prompt
       template, public case spec, or fixture root** (R2);
     - budget enforcement active — a self-test probe trial is actually truncated, and
       `actual_usage` appears in receipts (R3);
     - budget accounting scope is explicit and equivalent across no-method, append-only, and
       method-baseline arms, including method-state/retrieval operations and excluded harness
       overhead if any (R3/R6);
     - episode chaining and method-home isolation function; the relational ledger-grading
       self-test passes (R4/R5);
     - **mechanism-availability probe passed**: a probe episode-pair run with the deployed
       baseline artifact in the isolated method home demonstrates the runtime actually emits
       every observable class the hidden checks grade (referenceable holder/conclusion ids,
       supersession/collapse events, active-recall exclusion, trace lineage), with the probe
       receipt hash recorded (Premise section);
     - every episode case has a hidden-side winnable-in-principle walkthrough on file (R8);
     - ledger authenticity checks reject a forged/post-hoc collapse event and bind accepted
       events to episode snapshot hashes and runtime-generated ids (R5);
     - negative arms configured with equivalent budgets and prompts (R6);
     - append-only control artifact/configuration hash is frozen and the full separation ordering
       checks fail closed when `no-method < append-only < method-baseline` is not observed (R6);
     - arm-purity self-test passes: a deliberately method-contaminated no-method probe trial is
       detected and rejected from telemetry (R6);
     - snapshot pinning, per-file hashes, redaction markers, and absence of live
       self-referential fixtures (R11);
     - every new case: `trial_count = 2`, `method_impact_trace` in expected receipt fields,
       budget-saturation and guardrail flags consistent;
     - the carried v0.2 guardrail case has been reserialized without candidate-visible `success`
       criteria (R2);
     - the R7/R8 arithmetic holds on calibrated non-guardrail headroom cases.
     A freeze request without this preflight result is incomplete.

## Sequencing

1. Owner approves or amends this requirements direction.
2. **Codex builds harness capabilities first**, each with a self-test, before any case
   engineering: (a) hard budget counting and truncation with `actual_usage` receipts;
   (b) episode chaining with isolated method-home deposit, context kill, and post-run ledger
   snapshot; (c) relational state-anchored grading; (d) negative-control arms;
   (e) **mechanism-availability probe** — one probe episode-pair with the deployed baseline in
   the isolated method home confirming the runtime emits all gradeable observable classes
   (Premise section). If the probe fails, case engineering halts and the gap is reported to
   the owner: fixing the runtime is a deployment-authority decision, never a quiet harness
   workaround.
3. Per case, in order: failure-mechanism note (R6) → preregistration (R8) → draft task and
   fixture → calibration trials → pass R3/R6/R8 gates → only then B1/B2 fixture-freeze
   engineering (R11).
4. Claude spot-check per R12 boundary; verdict recorded in `CLAUDE_REVIEW.md` here.
5. Owner one-shot approval freeze (new manifest + case-set hash; `evals/manifest.json` changes
   only at owner freeze).
6. Only then: successor v0.2 proposal preregisters its two-evaluation criteria against
   `fusion-dogfood-v0.3`, including `method_impact_count > 0` on hard cases as an explicit
   target metric (ROADMAP immediate-next-stage item 2).

## Explicitly forbidden throughout

Approving or freezing the suite; modifying `evals/manifest.json`; running baseline, candidate,
or shadow evaluations without owner authorization; adoption; deployment; modifying the deployed
Skill; drafting a successor candidate from any hidden-aware context.
