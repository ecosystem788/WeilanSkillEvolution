# SE-0.6 shadow release gate receipt

Status: `mechanism_accepted_real_shadow_pending`

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

## Remaining acceptance evidence

The approved real-task suite has not been executed for these two artifacts. No real shadow result, adoption decision, deployment, canary result, or rollback event exists. The deployed Skill remains unchanged.

SE-0.6 remains `audit_required` until all `24` equivalent receipts exist and the fixed external gate evaluates them. Passing the gate would permit an adoption decision; it would not supply one.
