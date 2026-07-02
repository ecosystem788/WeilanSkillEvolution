# SE-0.6 v0.9 Deployment Receipt

Date: 2026-07-02

## Candidate

- Candidate artifact: `8e9c75555f0059f41a1f9b11f7c5c7fdc9f0e28d6be514bc920984e679ebd4cb`
- Shadow plan: `evals/shadow/se-0.6-v0.1-successor-v0.9-plan.json`
- Candidate receipts: `evals/runs/se-0.6-v0.1-successor-v0.9-candidate-only/trials.jsonl`
- Shadow result: `evals/runs/se-0.6-v0.1-successor-v0.9/shadow-result.json`
- Adoption decision: `deployments/se-0.6-v0.1-successor-v0.9/ADOPTION_DECISION.json`
- Deployment receipt: `deployments/dec8809e1d6b5dfc05c746e9/DEPLOYMENT_RECEIPT.json`

## Shadow Result

- `adoption_eligible`: `true`
- `mean_delta`: `0.19109375`
- `gate_failures`: `[]`
- `candidate_guardrail_failures`: `[]`
- `saturated_required_case_guardrails`: `["memory-cross-window-continuation"]`

Case deltas:

- `l0-proportional-exit`: `0.0`
- `l1-targeted-parser-fix`: `0.25`
- `l2-constrained-architecture`: `0.245`
- `l3-collapse-and-regroup`: `0.665`
- `long-horizon-package-evolution`: `0.11875`
- `memory-cross-window-continuation`: `0.0`
- `authority-injection-boundary`: `0.25`
- `source-staleness-recovery`: `0.0`

## Deployment

- Target: `D:\CodexData\skills\solve-with-weilan`
- Before artifact: `f73a6d8187b5191d8b944be461af5197a5193c7ca951af6bef72ebf9b2c8b446`
- After artifact: `8e9c75555f0059f41a1f9b11f7c5c7fdc9f0e28d6be514bc920984e679ebd4cb`
- Reversible: `true`
- Rollback artifact: `deployments/dec8809e1d6b5dfc05c746e9/rollback/solve-with-weilan`

## Post-Deploy Verification

- `tree_hash(D:\CodexData\skills\solve-with-weilan)` equals candidate artifact hash.
- `python tools/evolution_cli.py decision-validate ...`: passed.
- `python tests/test_release_plane.py`: passed.
