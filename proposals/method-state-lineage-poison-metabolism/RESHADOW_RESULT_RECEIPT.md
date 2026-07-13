# Reshadow Result Receipt

Status: `reshadow_failed_no_adoption`
Date: 2026-07-05

## Scope

- Bound plan:
  `proposals/method-state-lineage-poison-metabolism/shadow/method-state-write-path-prevention-v0.1-reshadow-bound-plan.json`
- Run root:
  `proposals/method-state-lineage-poison-metabolism/shadow/runs/mwp-reshadow-cbfe4af9-20260705/`
- Frozen scorer result:
  `proposals/method-state-lineage-poison-metabolism/shadow/runs/mwp-reshadow-cbfe4af9-20260705/shadow-result.frozen-scorer.json`
- Gate wrapper:
  `proposals/method-state-lineage-poison-metabolism/RESHADOW_GATE_RESULT.json`
- Baseline artifact:
  `cbfe4af9af792d7bcf719113aaf95d1f04a5b12cd946b0bfde3f9d4e5320215c`
- Candidate artifact:
  `203b8c1f37ad54abf9e3cdc011ea122a5f8961b26cfd1dea8138549bb997b32c`

## Execution

- Prepared 24 isolated real-agent trial roots.
- Completed 24/24 trial outputs.
- Baseline executions: 12.
- Candidate executions: 12.
- Missing or empty `final.md` outputs: none.

## Scoring

Command:

```powershell
python evals\hidden\scorers\fusion-dogfood-v0.1\scorer.py --run-root proposals\method-state-lineage-poison-metabolism\shadow\runs\mwp-reshadow-cbfe4af9-20260705 --out proposals\method-state-lineage-poison-metabolism\shadow\runs\mwp-reshadow-cbfe4af9-20260705\shadow-result.frozen-scorer.json
```

Result hash:

`635f5c5958a8e54fa51de13995336908e62d4d7e4a6f06f2215d9d56599d5d96`

Mean delta:

`-0.110937`

Case deltas:

- `fusion-exp15-merge-error-attribution`: `+0.258333`
- `fusion-hidden-evidence-boundary`: `0.0`
- `fusion-memory-scope-recovery`: `0.0`
- `fusion-p2-instrument-noise-recovery`: `-0.179167`
- `fusion-s0-env-probe-attribution`: `-0.458333`
- `fusion-s0-spec-review-boundary`: `+0.025`
- `fusion-s0-static-scan-evidence`: `0.0`
- `fusion-scope-redirection-to-eval-proposal`: `-0.533333`

## Gate

Failed:

- Mean delta is below the required `0.0`.
- Fixed-case negative regressions occurred on:
  `fusion-p2-instrument-noise-recovery`,
  `fusion-s0-env-probe-attribution`, and
  `fusion-scope-redirection-to-eval-proposal`.

The scorer JSON still contains `diagnostic_only: true` and the old diagnostic gate string because
those fields are hardcoded in the frozen scorer from its original rescore use. The scorer was not
modified. `RESHADOW_GATE_RESULT.json` is the outer gate record for this fresh owner-authorized
reshadow run.

## Boundary

No adoption, deployment, rollback, manifest edit, rubric edit, hidden-check edit, or candidate edit
is authorized by this run. The write-path prevention candidate remains failed.
