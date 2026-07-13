# Scorer Handoff — Claude-authored fusion-dogfood-v0.1 scorer for Codex review/run

Status: `scorer_authored_awaiting_codex_review_and_rescore`
Date: 2026-07-05
Author: Claude (evaluator side). Owner authorization: evidence-capture
`65f774cb-9439-45c8-b587-19777dec767c`
(`conversation:e376508a-cf17-4e86-83b6-1e7a0447241b#3e58b5ef-364b-42e9-a59d-fed6931ff63b`).
This restores authority separation: the previous run's scorer was authored by the candidate
author (Codex); scoring authorship now sits with the auditor side, execution with Codex.

## Resolution of the attribution-audit fork

The pending question was "local script deviates from frozen rubric" vs "rubric is
keyword-based". The answer is **neither: the frozen rubric is underspecified.**
`evals/hidden/fusion-dogfood-v0.1/evaluator-rubric.json` (hash verified against the approval
receipt) defines only dimension names, per-case weights, and guardrail zero-score conditions —
no per-dimension scoring procedure at all. The retired script implemented the weights faithfully
(recomputation reproduces both recorded regression deltas exactly) but had to invent the
measurement, and invented fragile literal-keyword fractions. The v0.1 freeze therefore bound the
weights but never bound the judgment. This is a suite-design defect to carry into
`fusion-dogfood-v0.2` requirements: a frozen rubric must specify per-dimension criteria
concretely enough that two independent implementations agree.

Additional finding: trial receipts record `grader_provenance.evaluator_artifact_hash =
b04c826e…`, which matches **no artifact on disk** (not the rubric file or its canonical form,
not hidden-checks, not the scoring script). Codex must explain and fix this provenance binding
in the receipt generator — a receipt hash an auditor cannot recompute is a broken binding.

## What was built

- `evals/hidden/scorers/fusion-dogfood-v0.1/scorer.py` — deterministic, stdlib-only,
  phrasing-robust scorer. Placed under `evals/hidden/` because it embeds hidden expected
  answers; candidate-authoring threads must not read it.
- `evals/hidden/scorers/fusion-dogfood-v0.1/test_scorer.py` — 10 tests, all passing, including
  phrasing-equivalence pairs that encode the retired scorer's exact failure mode (hyphenated vs
  spaced terms; positive-list vs negative-phrase authority statements must score identically)
  and a hash-tamper rejection test.

Scoring basis, in priority order: (1) structured receipt-field contract from the public case
spec (`expected_receipt_fields`); (2) expected answers from frozen `hidden-checks.json` for
content-accuracy dimensions; (3) multi-variant normalized concept checks for behavioral
dimensions; (4) frozen rubric weights, sha256-verified at load; (5) recorded guardrail failures
zero the case score. Overhead is computed from receipt budget vs actual usage instead of a
constant. Emitted breakdowns use check ids only — no hidden literals in output.

Smoke check run (parse coverage only, no scores): all 24 `mwp-shadow-20260705` outputs parse
with 6–35 structured fields; no low-coverage trial.

## Exposure declaration (read before treating any rescore as evidence)

The author read 6 of the 24 run outputs during the attribution audit before writing this
scorer. Mitigations: every check derives from the frozen rubric, frozen hidden checks, or the
public case spec, with the derivation visible in the code; phrasing-equivalence test fixtures
are synthetic; Codex review below is adversarial. Regardless of mitigation, a post-run-authored
scorer cannot produce adoption-grade evidence for that same run.

## Codex tasks (in order)

1. **Adversarial review** of `scorer.py` + `test_scorer.py`: check no criterion encodes
   run-specific tuning (every check must be justifiable from frozen/public sources alone);
   check no hidden literal can leak into scorer output; check determinism.
2. **Freeze**: record sha256 of both files in a scorer freeze receipt in this directory.
3. **Official rescore** of `shadow/runs/mwp-shadow-20260705` with
   `python evals/hidden/scorers/fusion-dogfood-v0.1/scorer.py --run-root <run> --out <run>/shadow-result.rescored.json`,
   emitted as a **superseding diagnostic record** (same pattern as the corrected E1 record).
   The original `shadow-result.json` and its gate outcome remain the recorded gate decision.
4. **Fix provenance**: explain `b04c826e…` and make `grader_provenance` bind recomputable
   hashes (scorer file hash + rubric hash) going forward.
5. **Retire** `shadow/score_fusion_shadow_run.py` for future runs (keep the file as history).

## Boundaries

- The rescored result is **diagnostic only**: it informs whether the candidate's failure signal
  survives honest measurement. It is not adoption evidence and does not change
  `shadow_failed_no_adoption`.
- If the owner later wants `method-state-write-path-prevention-v0.1` (`203b8c1f…`) adopted, the
  path is: this scorer frozen first, then a **fresh owner-authorized shadow run** scored by it.
- No change to the frozen rubric, hidden checks, manifest, or deployed Skill is authorized here.
- Requirement forwarded to `fusion-dogfood-v0.2`: rubric must bind per-dimension criteria
  (this scorer's check tables are the working template).
