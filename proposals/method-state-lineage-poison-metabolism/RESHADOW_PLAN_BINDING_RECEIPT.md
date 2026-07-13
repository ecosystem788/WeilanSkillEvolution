# Reshadow Plan Binding Receipt

Status: `bound_awaiting_real_agent_execution`
Date: 2026-07-05

## Scope

- Preregistration: `proposals/method-state-lineage-poison-metabolism/RESHADOW_PREREG.md`
- Bound plan:
  `proposals/method-state-lineage-poison-metabolism/shadow/method-state-write-path-prevention-v0.1-reshadow-bound-plan.json`
- Suite: `fusion-dogfood-v0.1`
- Baseline artifact:
  `cbfe4af9af792d7bcf719113aaf95d1f04a5b12cd946b0bfde3f9d4e5320215c`
- Candidate artifact:
  `203b8c1f37ad54abf9e3cdc011ea122a5f8961b26cfd1dea8138549bb997b32c`
- Frozen scorer:
  `428f64899d1c153b37d6f1e33d8df51da8323d094d876884c30698f76c21bf59`
- UTF-8 targeted deployment receipt:
  `deployments/cbfe4af9af792d7bcf719113/DEPLOYMENT_RECEIPT.json`

## Binding Checks

- The deployed Skill at `D:\CodexData\skills\solve-with-weilan` was rehashed as
  `cbfe4af9af792d7bcf719113aaf95d1f04a5b12cd946b0bfde3f9d4e5320215c`.
- The rollback snapshot for the immediately previous deployed artifact rehashes as
  `2c539d0b9444a395e66ce4ddaad1412f0ea5c4f0541112f63d3365c65d2bcf4f`.
- The old failed shadow plan remains unchanged for historical reproducibility.
- The bound plan uses the frozen scorer as the scoring authority. The legacy per-case
  evaluator hashes are not reused as scoring authority.

## Boundary

This binding authorizes only fresh shadow execution and frozen-scorer scoring under the
current user instruction. It grants no adoption, deployment, rollback, manifest edit,
rubric edit, or candidate edit authority.
