# SE-0.7 bounded evolution gate receipt

Status: `mechanism_accepted_real_evolution_run_pending`

## Completed mechanism

- Added a finite foreground evolution manifest with hard limits on steps, proposals, candidate generations, shadow comparisons, evaluation receipts, and deployments.
- The runner validates one externally supplied proposal, freezes one candidate, consumes pre-existing evaluation receipts, checks one shadow result, validates an external decision, and can perform an explicitly authorized deploy, canary, and rollback sequence.
- Decision and rollback files must live under declared external authority roots.
- Missing deployment permission stops before changing the target.
- Regression, invalid input, exhausted budget, rejection, missing authority, invalid canary evidence, and required rollback are terminal bounded outcomes.
- The runner writes one replayable receipt and exits; it has no scheduler, polling, timer, heartbeat, self-invocation, worker, or background Agent.
- `tests/test_bounded_evolution.py` passed a full temporary candidate-adopt-deploy-canary-rollback cycle, unauthorized deployment stop, budget rejection, and receipt replay.

## Real candidate manifest

`evals/evolution/se-0.7-v0.1-manifest.json` binds the current proposal, candidate, approved shadow plan, future receipt set, external decision roots, installed target, and eight-step ceiling.

## Remaining acceptance evidence

The real manifest cannot advance past shadow comparison until the `24` approved-suite receipts exist. It has no adoption authority and was not run with deployment enabled. Repeated held-out improvement and production guardrail evidence therefore do not yet exist.

SE-0.7 remains `audit_required` until at least one authorized real manifest completes from evidence through monitored outcome and repeated held-out runs show improvement without guardrail degradation.
