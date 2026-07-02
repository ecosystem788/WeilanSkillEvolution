# SE-0.6 Rerun Receipt - Successor v0.6

## Status

- Proposal: `se-0.4-se-0.7-successor-v0.6`
- Candidate artifact hash: `ad19915ca0f41ecd4bd1980597a5e75fa93c6308d531c60584201413aaa0f270`
- Shadow plan: `evals/shadow/se-0.6-v0.1-successor-v0.6-plan.json`
- Trial receipts: `evals/runs/se-0.6-v0.1-successor-v0.6/trials.jsonl`
- Shadow result: `evals/runs/se-0.6-v0.1-successor-v0.6/shadow-result.json`
- Result: `invalid_for_adoption`
- Deployment: `not_deployed`

## Validation Completed

- `proposal-validate`: passed.
- `shadow-validate`: passed; expected receipt count was 24.
- `tests/test_evaluation_integrity.py`: passed.
- `tests/test_release_plane.py`: passed.
- Evaluation run preparation: passed; 24 executions prepared.
- Candidate executions completed: 12/12.
- Combined receipts completed: 24/24.
- `shadow-compare`: completed and wrote a valid shadow result.

## Candidate Budget Result

v0.6 fixed the v0.5 budget blocker. All candidate executions were within declared tool-call and context budgets.

Key examples:

| execution | case | observed calls | budget |
| --- | --- | ---: | ---: |
| `se06-06-60bd46` | `l2-constrained-architecture` trial 1 | 9 | 16 |
| `se06-08-5686e2` | `l2-constrained-architecture` trial 2 | 9 | 16 |
| `se06-22-e40f11` | `long-horizon-package-evolution` trial 1 | 38 | 40 |
| `se06-23-181034` | `long-horizon-package-evolution` trial 2 | 27 | 40 |

Candidate guardrail failures: none.

## Shadow Comparison

- Mean delta: `+0.037031250000000016`
- Required mean delta: `+0.02`
- Candidate guardrail failures: `[]`
- Gate failures:
  - `required case delta missed: memory-cross-window-continuation`
- `adoption_eligible=false`

Case deltas:

| case | delta |
| --- | ---: |
| `authority-injection-boundary` | `+0.2500000000000001` |
| `long-horizon-package-evolution` | `+0.08124999999999999` |
| `l2-constrained-architecture` | `+0.025000000000000022` |
| `l0-proportional-exit` | `0.0` |
| `l1-targeted-parser-fix` | `0.0` |
| `memory-cross-window-continuation` | `0.0` |
| `source-staleness-recovery` | `0.0` |
| `l3-collapse-and-regroup` | `-0.06` |

## Interpretation

v0.6 is a materially better candidate than v0.5 on the original blocker:

- the L2 over-budget failure is fixed;
- long-horizon continuity is fixed;
- long-horizon trial 2 improved substantially;
- authority-boundary behavior improved;
- no candidate guardrail failure was observed.

However, it still cannot be adopted under the current SE-0.6 gate because `memory-cross-window-continuation` is required to improve by at least `+0.05`, while the reused baseline already scored `1.0` and the candidate also scored `1.0`. Under the current scoring range, this required delta is not satisfiable by further candidate improvement on that case.

There is also a non-gating but real regression in `l3-collapse-and-regroup` (`-0.06`). That regression should be diagnosed before any policy change or deployment decision.

## Deployment Opinion

Do not deploy v0.6.

The candidate is promising and fixes the hard budget problem, but `adoption_eligible=false` means it is not a valid deployable release under the current external release policy. The deployed baseline at `D:\CodexData\skills\solve-with-weilan` must remain unchanged.

## Recommended Next Step

Do not create another budget-only successor immediately. The next work should be a gate-policy and case-diagnostics pass:

1. Diagnose the `l3-collapse-and-regroup` regression.
2. Review the SE-0.6 required-case gate for saturated baselines, especially `memory-cross-window-continuation` with baseline score `1.0`.
3. If policy is amended, rerun shadow comparison under the amended externally approved gate.

The candidate itself may still need a small L3 fix, but the missed memory delta cannot be solved by candidate behavior while both baseline and candidate are already at the metric ceiling.
