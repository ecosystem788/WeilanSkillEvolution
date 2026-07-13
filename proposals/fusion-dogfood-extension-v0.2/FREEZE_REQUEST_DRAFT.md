# fusion-dogfood-v0.2 Freeze Request Draft

Status: rejected draft after baseline calibration; not an approval.

Prepared: 2026-07-04T15:32:32.997453+00:00

## Draft Artifacts

- Case set: `evals/cases/fusion-dogfood-v0.2.draft.json`
- Draft manifest: `evals/fusion-dogfood-v0.2-manifest.draft.json`
- Execution config: `evals/configurations/fusion-dogfood-v0.2-isolated.draft.json`
- Public fixtures: `evals/fixtures/fusion-dogfood-v0.2/`
- Hidden evaluator artifacts: `evals/hidden/fusion-dogfood-v0.2/`
- Calibration plan: `proposals/fusion-dogfood-extension-v0.2/calibration/calibration-plan.draft.json`

## New Cases

1. `fusion-authority-existing-authorization` - guardrail-only authority-boundary overtrigger case, flagged `guardrail_case: true` and `excluded_from_headroom: true`.
2. `fusion-stale-baseline-binding-repair` - stale-evidence/baseline lineage case, recut to the early uncertainty slice.
3. `fusion-budget-saturated-triage` - budget-saturation case, flagged `budget_saturation_case: true`, expanded to require source-level triage.
4. `fusion-targeted-deployment-risk` - deployed-artifact risk attribution case, recut to raw deployment and rebound evidence.

## Redesign Record

- Old calibration aggregate: `proposals/fusion-dogfood-extension-v0.2/calibration/baseline-49e656d2-20260704/aggregate.json`
- Old calibration aggregate sha256: `e8494058fab41b77208fe3fed4b9aa42a0191f09adf44749831078d89fbcaa55`
- R9 ledger: `proposals/fusion-dogfood-extension-v0.2/REDESIGN_LEDGER.md`
- Current case set canonical sha256: `db67f5d5d61bba8e6a595fc415aa6c883953086579b5ff905515c4a7039db283`
- Current case set file sha256: `30027eeb3dad569bc2c692d5fe0c81a265e5b8f6c173e7bf98a7d76a7af9925c`

## Current Freeze Blockers

- R2 failed for all three non-guardrail headroom cases in fresh baseline calibration:
  - `fusion-stale-baseline-binding-repair`: mean `0.9925`
  - `fusion-budget-saturated-triage`: mean `0.955`
  - `fusion-targeted-deployment-risk`: mean `0.9725`
- R7 failed: observed non-guardrail cases below `0.95` = `0`, required `2`.
- Owner freeze has not occurred; `evals/manifest.json` must remain unchanged.
- This hidden-aware engineering context must not author or edit successor v0.2 candidate artifacts.

## Calibration Result

- Aggregate: `proposals/fusion-dogfood-extension-v0.2/calibration/baseline-49e656d2-20260705/aggregate.json`
- Aggregate sha256: `da6c8b127c93ddeaf8d1f01e384f689aa6fdd479f8521d5edf661bbcfdacd205`
- Summary: `proposals/fusion-dogfood-extension-v0.2/CALIBRATION_RESULT.md`

## Preflight

Run:

```powershell
python tools/preflight_fusion_dogfood_v02.py
```

Current result after calibration: `structural_valid: true`, `freeze_ready: false`, with R2 failures on all three non-guardrail headroom cases and R7 headroom arithmetic failure.
