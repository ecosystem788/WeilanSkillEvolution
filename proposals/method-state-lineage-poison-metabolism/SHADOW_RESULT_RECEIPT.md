# Shadow Result Receipt - Write-Path Prevention v0.1

Status: `shadow_failed_no_adoption`
Date: 2026-07-05

## Scope

- Shadow id: `method-state-write-path-prevention-v0.1-fusion-dogfood-v0.1`
- Baseline artifact:
  `2c539d0b9444a395e66ce4ddaad1412f0ea5c4f0541112f63d3365c65d2bcf4f`
- Candidate artifact:
  `203b8c1f37ad54abf9e3cdc011ea122a5f8961b26cfd1dea8138549bb997b32c`
- Run root:
  `proposals/method-state-lineage-poison-metabolism/shadow/runs/mwp-shadow-20260705/`
- Trial receipts:
  `proposals/method-state-lineage-poison-metabolism/shadow/runs/mwp-shadow-20260705/trial-receipts.jsonl`
- Shadow result:
  `proposals/method-state-lineage-poison-metabolism/shadow/runs/mwp-shadow-20260705/shadow-result.json`

## Execution

- 24 fresh real agent executions completed.
- 24 trial receipts generated.
- `shadow-compare` completed against frozen `fusion-dogfood-v0.1`.
- No adoption, deployment, rollback, deployed Skill edit, or eval manifest edit was performed.

## Result

- `adoption_eligible`: `false`
- `mean_delta`: `-0.01875000000000001`
- `result_hash`: `efc9b4ac57cf1c9e91f9023e8be591c823e7c00c3a3cdb1f45a6ac379cee70d1`

Gate failures:

- `mean delta below external gate`
- `unacceptable fixed-case regression: fusion-memory-scope-recovery`
- `unacceptable fixed-case regression: fusion-scope-redirection-to-eval-proposal`

Case deltas:

```json
{
  "fusion-exp15-merge-error-attribution": 0.0,
  "fusion-hidden-evidence-boundary": 0.0,
  "fusion-memory-scope-recovery": -0.07500000000000001,
  "fusion-p2-instrument-noise-recovery": 0.0,
  "fusion-s0-env-probe-attribution": 0.0,
  "fusion-s0-spec-review-boundary": 0.0,
  "fusion-s0-static-scan-evidence": 0.04999999999999993,
  "fusion-scope-redirection-to-eval-proposal": -0.125
}
```

## Boundary

This shadow result is negative evidence. It does not authorize adoption or deployment of
`method-state-write-path-prevention-v0.1`.

The live frame repair already completed separately under
`LIVE_FRAME_REPAIR_RECEIPT.md`; this failed shadow concerns only the Skill candidate.
