# SE-0.6 Successor v0.7 Fix Receipt

Status: prepared; not deployed.

## Changed Artifact

- Candidate artifact: `747644bec5cdc48b1741d4026ac26b8096c1fc4a98bca3a72350fe9f0a8c44a1`
- Source candidate: `proposals/se-0.4-se-0.7-successor-v0.6/candidate/solve-with-weilan`
- Shadow plan: `evals/shadow/se-0.6-v0.1-successor-v0.7-plan.json`

## Fixes

1. Added explicit L3 recovery contract guidance to the candidate Skill:
   - preserve public compatibility columns and source-facing identifiers;
   - emit observable collapse/regroup events in the evaluator-compatible order;
   - write `recovery.json` using stable top-level keys from the public route and logs;
   - verify final databases through compatibility columns, not only internal IDs.

2. Updated external release comparison:
   - saturated required positive-delta cases become non-regression guardrails;
   - saturated cases do not synthesize positive delta;
   - unlisted fixed-case negative deltas now block adoption.

## Verification

- `python tests/test_release_plane.py`: passed.
- `python tests/test_evaluation_integrity.py`: passed.
- `python tests/test_bounded_evolution.py`: passed.
- `python tools/evolution_cli.py proposal-validate --proposal proposals/se-0.4-se-0.7-successor-v0.6/proposal.json`: passed.
- `python tools/evolution_cli.py shadow-validate --plan evals/shadow/se-0.6-v0.1-successor-v0.7-plan.json --manifest evals/manifest.json --case-set evals/cases/seed-v0.1.json`: passed.
- L3 contract smoke using the frozen scorer returned:
  - `outcome`: `1.0`
  - `collapse_quality`: `1.0`
  - `verification`: `1.0`
  - `trace_reuse`: `1.0`
  - guardrail failures: none

## Evaluation Status

Prepared 24 execution workspaces at:

`evals/multi-agent-runs/se-0.6-v0.1-successor-v0.7`

No adoption or deployment has occurred. The new candidate still requires 24 real baseline/candidate execution receipts and a fresh `shadow-result.json` with `adoption_eligible=true` before deployment is allowed.

