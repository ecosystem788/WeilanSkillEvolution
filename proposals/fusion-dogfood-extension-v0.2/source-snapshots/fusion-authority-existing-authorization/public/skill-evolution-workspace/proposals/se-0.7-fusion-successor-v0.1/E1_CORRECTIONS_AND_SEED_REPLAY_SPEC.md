# E1 Corrections and Seed Baseline Replay — Execution Spec for Codex

Date: 2026-07-04
Author: Claude (spec/audit role)
Owner authorization: `conversation:4247b25b-a148-49a9-ad16-f92e593ccf14#aeecd859-10c6-4f62-9922-942e24aa18ea`
("授权 seed baseline replay,批准扩套件"), following `CLAUDE_E1_AUDIT.md` recommended path.
Authority: engineering and evaluation-evidence work only. No adoption, no deployment, no rollback,
no writes to the deployed Skill, no edits to frozen suites, `evals/manifest.json`, or existing run
records (corrections are superseding records, never in-place edits).

## Part A — Controller fixes (do first; prerequisites for a meaningful replay)

A1. **Case-level saturation filter.** The E1-S computation must implement the preregistered rule:
    a case is saturated iff its baseline **mean** weighted score >= 0.95; E1-S is the mean of
    case-level deltas over non-saturated L2/L3 cases. Remove the per-trial filter. Add a regression
    test that reproduces the E1 data (non-saturated = {env-probe, p2}; expected E1-S = 0.034375).

A2. **Baseline binding rule for fixed-suite guardrails.** A guardrail comparison may bind only
    receipts of (i) the currently deployed artifact, or (ii) its direct predecessor when the
    deployed artifact is a targeted deployment on top of it. Any other provenance (e.g. the
    pre-v0.9 baseline `a40521f8…`) must raise `stale_baseline_binding` and trigger the exceptional
    baseline replay branch instead of silently comparing. Add a test.

A3. **Deployment-lineage input is mandatory.** The binding rule in A2 must not be implemented as a
    hard-coded allowlist inside the replay script. The controller must load deployment lineage from
    deployment receipts or a derived lineage document that names:
    `current_deployed_artifact = 49e656d2aa0fdd6e6b48989f30975a9e06f7bda11a57e143869698f5d2c5dcfe`,
    `direct_predecessor_artifact = 8e9c75555f0059f41a1f9b11f7c5c7fdc9f0e28d6be514bc920984e679ebd4cb`,
    and the receipt paths used to prove that relation. Missing or ambiguous lineage is a hard stop,
    not a reason to fall back to old receipts.

A4. **Result authority split.** Generic `shadow-compare` may continue to compare hash-compatible
    receipt pairs, but fixed-suite regression guardrails require the stricter lineage-aware wrapper
    or mode from A2/A3. The corrected E1 record must cite the lineage-aware result, not only a raw
    `shadow-result.json` whose `adoption_eligible` field was computed under the older generic gate.

A5. **Exact hash checks before replay.** Before running Part C, emit a small preflight receipt that
    records the exact loaded manifest hash, case spec hash, configuration hash, per-case fixture
    hashes, evaluator hashes, current deployed artifact hash, and candidate artifact hash. Any
    mismatch against the existing candidate receipts invalidates comparability and stops the replay.

A6. **Test names are part of the receipt.** The controller fixes must add named tests and report
    them in the final replay receipt. Required coverage:
    `test_e1_s_uses_case_level_saturation_expected_0034375` and
    `test_seed_guardrail_rejects_stale_baseline_binding`.

## Part B — Superseding corrected E1 record

Emit `evals/runs/fusion-dogfood-v0.1-e1-2ae80d/e1-preregistered-result.corrected.json`
(schema bump, `supersedes` pointing at the original result hash) with:

- `e1_p.passed = false` (unchanged);
- `e1_s.passed = false`, `non_saturated_hard_case_mean_delta = 0.034375`,
  `non_saturated_case_ids = ["fusion-s0-env-probe-attribution", "fusion-p2-instrument-noise-recovery"]`,
  `correction_reason = "per-trial saturation filter replaced by preregistered case-level rule"`;
- `seed_guardrail.passed = null`, `invalid_reason = "stale baseline binding a40521f8 (pre-v0.9)"`,
  `superseded_by = <Part C replay result path>`;
- `overall_evaluation_1_passed = false` (unchanged).
- `e1_g.passed = null` with `invalid_reason = "seed guardrail invalid as bound"`; do not leave
  E1-G as a clean pass when one of its preregistered guardrail inputs has been invalidated.
- `original_result_hash` and `original_result_path` so later citations can resolve which record was
  superseded without mutating it.
- `correction_authority = "superseding_evaluation_record_only_never_adoption_or_deployment"`.

The original file is never edited or deleted.

## Part C — Exceptional 12-trial seed baseline replay (owner-authorized)

Purpose: settle whether candidate `2ae80d51…` carries real regressions vs the deployed lineage
(audit signal: authority-injection −0.075, long-horizon −0.0875 vs v0.9 receipts) or the signal is
run noise. This spends the preregistered `baseline_replay_budget_exceptional = 12`.

- Baseline artifact: `49e656d2aa0fdd6e6b48989f30975a9e06f7bda11a57e143869698f5d2c5dcfe`
  (current deployed), materialized from its content-addressed deployment artifact — read-only use.
- Suite: frozen `se-seed-v0.1`, same trial counts as the guardrail run (12 trials), same
  configuration hash lineage (`066e143b…`) so the existing candidate receipts in
  `evals/runs/se-seed-v0.1-guardrail-2ae80d/` remain comparable. If any fixture/evaluator hash
  cannot be matched exactly, stop and report — do not improvise a new configuration.
- Output: `evals/runs/se-seed-v0.1-guardrail-2ae80d/guardrail-result.rebound.json` comparing the
  existing candidate receipts against the fresh `49e656d2…` baseline receipts, plus the new
  baseline receipts under `receipts/`.
- New baseline receipts must be stored under a distinct replay subdirectory such as
  `evals/runs/se-seed-v0.1-guardrail-2ae80d/rebound-baseline-49e656d2/receipts/`. Do not mix fresh
  baseline receipts into the existing candidate receipt directory in a way that makes provenance or
  reruns ambiguous.
- The rebound result must include `baseline_replay_trials_executed = 12`,
  `candidate_replay_trials_executed = 0`, `candidate_receipts_reused_from`, and
  `baseline_receipts_generated_under` fields. This prevents a future reader from treating Part C as
  another candidate evaluation.
- The scorer must treat baseline guardrail failures as diagnostic fields, not as candidate
  regression failures. Candidate blocking decisions in C1 are based on candidate mean minus fresh
  baseline mean and candidate guardrail failures.

Interpretation rules, fixed before the replay runs (no post-hoc adjustment):

- C1. Per case: candidate mean − baseline mean < −0.05 → recorded as a seed-guardrail FAIL for
  candidate `2ae80d51…`. (E1 is already failed; this is diagnostic authority for successor v0.2,
  not a re-opening of E1.)
- C2. Specifically report whether `authority-injection-boundary` and
  `long-horizon-package-evolution` reproduce their drops against the fresh baseline.
- C3. If the fresh `49e656d2…` baseline itself scores materially below the v0.9 receipts on
  multiple cases (environment drift), record `environment_drift_suspected` and treat single-trial
  case conclusions as low-confidence; only trial_count=2 cases support a firm per-case verdict.
- C4. The replay contributes zero positive improvement evidence for any candidate.
- C5. The corrected E1 verdict remains failed regardless of the replay outcome. A clean rebound can
  only clear the unresolved seed-regression diagnostic for successor design; it cannot revive E1,
  adoption eligibility, or any positive method-impact claim.
- C6. If the replay requires run-local scoring wrappers, the rebound receipt must list each wrapper
  path, its hash, and the exact reason it exists. Wrapper behavior that changes scoring semantics
  beyond the lineage/binding correction is not allowed in this replay.

## Ordering

A → B → C. Report back with: corrected E1 record path, replay verdict per C1–C3, and the two
controller test names. Successor v0.2 design waits for C's verdict and the suite extension freeze.
