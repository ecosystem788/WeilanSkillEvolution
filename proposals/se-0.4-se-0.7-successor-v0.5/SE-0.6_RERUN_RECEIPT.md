# SE-0.6 Rerun Receipt - Successor v0.5

## Status

- Proposal: `se-0.4-se-0.7-successor-v0.5`
- Candidate artifact hash: `40fad7acd65abb499419143bd35f6ab829873200c68311a582fc89fcb20e153d`
- Shadow plan: `evals/shadow/se-0.6-v0.1-successor-v0.5-plan.json`
- Run root: `evals/multi-agent-runs/se-0.6-v0.1-successor-v0.5`
- Result: `invalid_for_adoption`
- Deployment: `not_deployed`

## What changed from v0.4

v0.5 kept the functional contract fixes from v0.4 and tightened the remaining budget/continuity guidance:

- batched source reads under hard tool budgets;
- batched sequential `weilan_trace.py` operations when intermediate output is not needed;
- one strong verification instead of repeated smoke checks;
- exact `parcel-route-evolution` scope for parcel routing long-horizon work;
- 12-call stage target and 14-call death line for three-stage, 40-call long-horizon runs.

## Validation Completed

- `proposal-validate`: passed.
- `shadow-validate`: passed; expected receipt count remains 24.
- `tests/test_evaluation_integrity.py`: passed.
- `tests/test_release_plane.py`: passed.
- Evaluation run preparation: passed; 24 executions prepared.

## Candidate Execution Evidence

The rerun was stopped early because a hard budget violation was observed in candidate execution evidence. Under the approved SE-0.6 gate, any candidate budget overrun invalidates the candidate for adoption.

Observed completed candidate stages:

| execution | case | budget | observed task calls | status |
| --- | --- | ---: | ---: | --- |
| `se06-01-3f840b` | `l0-proportional-exit` | 0 | 0 | within budget |
| `se06-04-3ec3d8` | `l1-targeted-parser-fix` | 12 | 10 | within budget |
| `se06-06-60bd46` | `l2-constrained-architecture` trial 1 | 16 | 11 | within budget |
| `se06-08-5686e2` | `l2-constrained-architecture` trial 2 | 16 | 17 | over budget |
| `se06-09-241696` | `l3-collapse-and-regroup` trial 1 | 24 | 13 | within budget |

Primary invalidating evidence:

- `evals/multi-agent-runs/se-0.6-v0.1-successor-v0.5/trials/se06-08-5686e2/telemetry.json`
- `task_tool_calls=17`
- declared budget: `tool_calls=16`

## Deployment Opinion

Do not deploy v0.5.

The candidate is directionally better than v0.4 in some executions, especially L2 trial 1, but it still fails the fixed hard-budget gate. Because adoption requires valid approved shadow evidence, this early budget failure is enough to stop the run. The deployed baseline at `D:\CodexData\skills\solve-with-weilan` must remain unchanged.

## Next Successor Guidance

The next candidate should make the budget constraint operational rather than advisory. The most likely useful change is an explicit pre-edit call ledger:

- before first edit, write down remaining tool budget;
- if a case has a 16-call budget, forbid separate JSON-format checks when tests already validate artifacts;
- for L2 architecture cases, require one combined read command and one combined verification command;
- make final receipts omit extra explanatory sections when budget is tight.

This is a candidate-design issue, not a release-plane issue.
