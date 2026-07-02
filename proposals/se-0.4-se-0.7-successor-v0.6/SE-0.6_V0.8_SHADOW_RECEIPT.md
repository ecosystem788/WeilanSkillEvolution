# SE-0.6 v0.8 Shadow Receipt

Date: 2026-07-02

## Candidate

- Candidate artifact: `a1550c1b72f6292a20c3642eca5c0ecae88ab39ff0607c54724cca50afe6f581`
- Shadow plan: `evals/shadow/se-0.6-v0.1-successor-v0.8-plan.json`
- Candidate receipts: `evals/runs/se-0.6-v0.1-successor-v0.8-candidate-only/trials.jsonl`
- Combined shadow receipts: `evals/runs/se-0.6-v0.1-successor-v0.8/trials.jsonl`
- Shadow result: `evals/runs/se-0.6-v0.1-successor-v0.8/shadow-result.json`

## Result

Do not deploy v0.8.

The L3 collapse/regroup regression is fixed against the frozen evaluator contract:

- `l3-collapse-and-regroup` case delta: `+0.635`
- Candidate L3 guardrail failures: none
- Candidate L3 trial scores: `0.94`, `1.00`

The saturated baseline gate issue is also handled as a non-regression guardrail:

- `memory-cross-window-continuation` baseline: `1.0`
- `memory-cross-window-continuation` candidate: `1.0`
- `saturated_required_case_guardrails`: `["memory-cross-window-continuation"]`

However, the full shadow result is not adoption eligible:

- `adoption_eligible`: `false`
- `gate_failures`: `["unacceptable fixed-case regression: l2-constrained-architecture"]`
- `l2-constrained-architecture` case delta: `-0.03`

## Deployment Decision

No deployment was performed. The explicit deploy-if-clean authorization is not sufficient to override a failed shadow gate.
