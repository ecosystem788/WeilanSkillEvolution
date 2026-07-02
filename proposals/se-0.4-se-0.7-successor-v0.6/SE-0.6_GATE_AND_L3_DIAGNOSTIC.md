# SE-0.6 Gate and L3 Regression Diagnostic

Status: diagnostic only; not an adoption receipt.

## Scope

This diagnostic reviews the v0.6 successor rerun after it improved aggregate shadow score but still failed SE-0.6 adoption. It focuses on two issues:

1. Why `l3-collapse-and-regroup` regressed.
2. Whether the SE-0.6 gate is valid for a required case where the baseline is already at score ceiling.

## Inputs

- Candidate proposal: `proposals/se-0.4-se-0.7-successor-v0.6/proposal.json`
- Candidate shadow plan: `evals/shadow/se-0.6-v0.1-successor-v0.6-plan.json`
- Candidate-only receipts: `evals/multi-agent-runs/se-0.6-v0.1-successor-v0.6/`
- Combined shadow result: `evals/runs/se-0.6-v0.1-successor-v0.6/shadow-result.json`
- L3 hidden checker: `evals/fixtures/seed-v0.1/l3-collapse-and-regroup/hidden/check.py`
- Release comparison implementation: `tools/release_core.py`
- Policy authority: `EVALUATION_POLICY.md`

## Result Summary

The v0.6 successor solved part of the earlier budget/control problem and produced a positive aggregate mean delta:

- `mean_delta`: `+0.037031250000000016`
- guardrail failures: none
- adoption eligible: false

It remains blocked by:

- `l3-collapse-and-regroup`: `-0.06`
- `memory-cross-window-continuation`: required delta `+0.05`, observed delta `0.0`

## L3 Regression Diagnosis

The L3 case regressed because the candidate outputs were semantically plausible but did not satisfy the frozen evaluator contract.

The hidden checker expects the method-state event sequence:

1. `holder_warned`
2. `holder_probation_started`
3. `discriminating_test_executed`
4. `minimal_unit_collapsed`
5. `trace_emitted`
6. `candidates_regrouped`

The candidate traces did not emit that complete lifecycle in the expected form, so collapse quality stayed at `0.0`.

The hidden checker also expects `recovery.json` to expose exact top-level fields and values, including:

- `collapse_scope == "assumption"`
- `invalidated_assumption_id == "fixed_offset_is_collision_free"`
- `new_identity_model` present and not `fixed_integer_offset`
- `failure_evidence` exactly covering `attempts/attempt-01.log` and `attempts/attempt-02.log`
- `reusable_artifacts` including `legacy_reader.py`
- truthy `once_reasonable`, `forbidden_assumption`, and `reentry_condition`
- `new_holder_id` different from `fixed-offset-global-id`

Both candidate trials wrote differently shaped recovery files, using nested or renamed concepts such as `collapsed`, `collapsed_unit`, `preserved_reusable_work`, and `regrouped_holder`. Those are understandable to a human reviewer but fail the frozen machine contract.

The database migration also broke the expected externally visible schema. The hidden checker queries:

```sql
SELECT tenant_id, legacy_id, name FROM users;
SELECT order_id, tenant_id, user_legacy_id, amount_cents FROM orders;
```

The candidate migrations replaced `orders.user_legacy_id` with internal `user_id` style references. That may be a reasonable normalized identity model, but it violates the case contract because the test requires tenant-scoped legacy references to remain observable.

The public verification did not catch this because it did not assert the final database schema using the same compatibility columns as the hidden checker.

### L3 Corrective Requirements For Next Candidate

The next successor should explicitly preserve the L3 evaluator contract:

- Emit the full collapse lifecycle events in order.
- Write `recovery.json` with the required top-level keys, not only semantically similar nested fields.
- Preserve `orders.user_legacy_id` as an externally visible compatibility column unless the task explicitly authorizes removing it.
- Add a public self-check that queries final `users` and `orders` with the hidden-compatible columns.
- Treat internal normalized identifiers as optional implementation detail, not as a replacement for required source-facing evidence.

## Saturated Baseline Gate Diagnosis

The v0.6 shadow plan requires:

```json
"required_case_deltas": {
  "l0-proportional-exit": -0.02,
  "l1-targeted-parser-fix": -0.02,
  "memory-cross-window-continuation": 0.05,
  "long-horizon-package-evolution": 0.05
}
```

For `memory-cross-window-continuation`, the observed scores are:

- baseline: `1.0`
- candidate: `1.0`
- delta: `0.0`

The current release comparison logic in `tools/release_core.py` directly compares each observed case delta with the configured minimum. It does not account for a saturated baseline score at the top of the scoring range. Therefore, with this case and these receipts, requiring `+0.05` is impossible under a `[0, 1]` score ceiling.

This is a gate-design issue, not a candidate execution failure.

`EVALUATION_POLICY.md` requires metric improvement and blocks unacceptable regression, but it does not require mathematically impossible positive movement on a case already scored at ceiling. However, changing a gate threshold or evaluation interpretation is an authority-level decision. A candidate must not approve, adopt, or redefine its own evaluation criteria.

### Gate Options For External Approval

An external reviewer can choose one of these policy-safe options:

1. Keep the current gate unchanged.
   - Result: no candidate can pass this required memory delta while baseline remains at `1.0`.

2. Treat saturated required cases as non-regression guardrails.
   - Suggested rule: if baseline score is at or above `1.0 - epsilon`, require `candidate_score >= baseline_score - tolerance` instead of a positive delta.

3. Move `memory-cross-window-continuation` from required positive delta to required non-regression for this shadow plan.
   - This preserves protection against regression without demanding impossible improvement.

4. Approve a new harder memory case in a new evaluation suite where the baseline is not saturated.
   - This is the cleanest route if positive memory improvement remains a release target, but it requires explicit suite/version approval because the existing case set is frozen.

### Reviewer Decision

Use option 2 for the current frozen `se-seed-v0.1` suite: treat saturated required-delta cases as required non-regression guardrails.

Decision rule:

- If a required positive case delta is configured and the baseline score is at or above the scoring ceiling minus a small numeric epsilon, the case cannot be used to prove positive improvement.
- For that saturated case, require `candidate_score >= baseline_score - tolerance` across the bound comparisons and require no candidate guardrail failure.
- Record the result as a saturated-baseline guardrail pass, not as a positive target-metric improvement.
- Keep aggregate `mean_delta` unchanged; do not synthesize the impossible `+0.05`.
- Do not let this interpretation waive unrelated regressions under `EVALUATION_POLICY.md`.

For future evidence that memory behavior improved, use option 4 separately: approve a new harder memory case or a new suite version where the baseline is not already saturated. That new suite can require a positive memory delta without changing the frozen `se-seed-v0.1` case semantics.

This decision only fixes the impossible gate condition. It does not approve or deploy v0.6, because the L3 regression remains an external policy concern.

## Deployment Recommendation

Do not deploy v0.6.

Reason:

- The candidate still regresses L3 behavior.
- The current SE-0.6 gate also contains a saturated-baseline required-delta condition that needs external policy review before it can fairly evaluate memory improvement.

Recommended next step:

1. Have an external reviewer approve a saturated-baseline gate interpretation or approve a new shadow plan/suite.
2. Build a v0.7 successor focused on the L3 recovery contract and hidden-compatible public checks.
3. Rerun the same approval evaluation under the externally approved gate.
