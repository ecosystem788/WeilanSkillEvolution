# Preregistration — Adoption-grade re-shadow of write-path prevention v0.1

Status: `executed_failed_no_adoption`
Date: 2026-07-05
Author: Claude (spec/audit role). Execution: Codex, only after explicit owner authorization.

Bound plan: `proposals/method-state-lineage-poison-metabolism/shadow/method-state-write-path-prevention-v0.1-reshadow-bound-plan.json`
Binding receipt: `proposals/method-state-lineage-poison-metabolism/RESHADOW_PLAN_BINDING_RECEIPT.md`
Result receipt: `proposals/method-state-lineage-poison-metabolism/RESHADOW_RESULT_RECEIPT.md`
Gate result: `proposals/method-state-lineage-poison-metabolism/RESHADOW_GATE_RESULT.json`

## Purpose

Give candidate `method-state-write-path-prevention-v0.1` (frozen artifact `203b8c1f…`) a gate
result that carries adoption meaning. The prior run's gate outcome
(`shadow_failed_no_adoption`) was produced by a scorer authored post-hoc by the candidate
author and found to measure phrasing, not behavior; the diagnostic rescore under the frozen
honest scorer shows no blocking regression but is preregistered here as **inadmissible for
adoption** (post-run scorer authorship, auditor output exposure, n = 1–2).

## Preregistered commitments (bound before execution)

1. **Scorer is frozen first**: `evals/hidden/scorers/fusion-dogfood-v0.1/scorer.py`
   sha256 `428f64899d1c153b37d6f1e33d8df51da8323d094d876884c30698f76c21bf59`
   (`SCORER_FREEZE_RECEIPT.md`), with rubric `e8f59038…` and hidden-checks `a11a7dc8…`.
   The run plan must embed these hashes; any mismatch at scoring time voids the run.
2. **Candidate**: `203b8c1f…` exactly as frozen (`CANDIDATE_FREEZE_RECEIPT.md`). No
   re-authoring: the candidate predates hidden exposure in its authoring context; any edit
   would require a fresh blind context and a new proposal.
3. **Baseline**: the currently deployed artifact, re-hashed from
   `D:\CodexData\skills\solve-with-weilan` at plan-binding time. The expected `2c539d0b…`
   changed because the owner authorized and Codex deployed the targeted UTF-8 console-output
   support fix first. The bound baseline is now
   `cbfe4af9af792d7bcf719113aaf95d1f04a5b12cd946b0bfde3f9d4e5320215c`, with rollback
   snapshot `2c539d0b9444a395e66ce4ddaad1412f0ea5c4f0541112f63d3365c65d2bcf4f`.
4. **Suite and structure**: frozen `fusion-dogfood-v0.1`, fresh 24 real executions (same
   4×2 + 4×1 per-arm structure), plus whatever guardrail replay `EVALUATION_POLICY.md`'s fixed
   gate requires, with the seed guardrail bound to the same fresh baseline hash.
5. **Gate**: the fixed gate in `EVALUATION_POLICY.md`, scored solely by the frozen scorer.
   No post-hoc scoring appeals of any kind — phrasing-artifact arguments were spent on the
   previous run and are preregistered away here; scores are final as computed.
6. **Effect-size discipline**: the diagnostic `mean_delta 0.096875` (and the +0.44
   single-trial case) must not be cited as an expected effect or used to interpret this run's
   result. This run's numbers stand alone.
7. **Authority**: this run grants no adoption, deployment, or rollback authority. Its result
   goes to owner decision with a Claude audit first.

## Dual purpose (declared so the evidence can be reused honestly)

The current deployed artifact `cbfe4af9…` carries accumulated targeted-channel changes
(transcript-support, frame-repair, and UTF-8 console output) that have never been covered by a full-suite shadow.
ROADMAP item 3 requires exactly that re-coverage. This run's baseline arm provides it for
`fusion-dogfood-v0.1` regardless of the candidate outcome.

## What the owner is asked to authorize

One item: execution of this preregistered run by Codex. Nothing else — adoption remains a
separate decision on the audited result.
