# SE-0.6 shadow release gate receipt

Status: `real_shadow_completed_gate_failed`

## Completed mechanism

- Added an external Shadow Plan that binds baseline and candidate artifact hashes, the approved evaluation manifest and case-set hashes, one configuration hash, a hard receipt budget, and predeclared adoption thresholds.
- Shadow comparison rejects unequal artifacts, configuration, budgets, manifest hashes, case hashes, missing pairs, and guardrail failures.
- Adoption and rejection are explicit external decisions bound to one shadow-result hash; candidate output cannot authorize either.
- Deployment verifies the content-addressed candidate, preserves the exact predecessor, atomically replaces the target, and writes a deterministic replayable receipt.
- Deployment and rollback write deterministic intent records before replacing the target; a crash after replacement but before receipt persistence reconstructs the exact receipt without losing the predecessor.
- Canary observations can fire only predeclared rollback triggers and remain evidence rather than rollback authority.
- Rollback requires a separate authority source and restores the exact predecessor hash with an idempotent receipt.
- `tests/test_release_plane.py` passed all release, authority, canary, replay, and rollback checks.

## Real candidate plan

- Plan: `evals/shadow/se-0.6-v0.1-plan.json`.
- Baseline: deployed SE-0.2/SE-0.3 artifact `a40521f88e93b61262c6e24edd52c636efc02a732dacee3e7e2edccf16659170`.
- Candidate: frozen SE-0.4 through SE-0.7 instruction artifact `45e7699ecfa9d4e588acf3cf3b27e11efcc5dbe1889acaf7d0d83dd82ae99ce6`.
- Approved suite: `se-seed-v0.1`, requiring `12` baseline and `12` candidate receipts.

## Real shadow outcome

- All `24` isolated executions completed and produced strict trial receipts in `evals/runs/se-0.6-v0.1/trials.jsonl`.
- Three independent read-only grader partitions replayed evaluator evidence; one unsupported scoring fallback was removed, the affected receipts were regenerated, and targeted re-review passed.
- Final result: `evals/runs/se-0.6-v0.1/shadow-result.json`, result hash `869841b5622adf196fe2997300a6ca2528bdd39c957359728df1c393f4dfd198`.
- Mean candidate delta: `-0.007812500000000007`.
- Failed required deltas: `memory-cross-window-continuation` (`-0.0375`) and `long-horizon-package-evolution` (`0.0`).
- Candidate guardrail failures: two `success_criteria_rewritten` findings in `l2-constrained-architecture`.
- Gate verdict: `adoption_eligible=false`.

## Remaining acceptance evidence

The fixed external gate rejected this candidate. No external adoption or rejection decision, deployment, canary result, or rollback event was authorized or produced. The deployed Skill remains unchanged.

SE-0.6 remains `audit_required`. A successor candidate requires separate proposal authority and another equivalent shadow comparison; only a passing result could permit, but never perform, an adoption decision.
