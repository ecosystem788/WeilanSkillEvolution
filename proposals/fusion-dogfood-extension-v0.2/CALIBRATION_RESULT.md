# fusion-dogfood-v0.2 Baseline Calibration Result

Date: 2026-07-05
Baseline artifact: `49e656d2aa0fdd6e6b48989f30975a9e06f7bda11a57e143869698f5d2c5dcfe`
Record type: `calibration_not_evidence`

## Verdict

The redesigned v0.2 draft fails R2/R7 and must not be frozen.

Aggregate: `proposals/fusion-dogfood-extension-v0.2/calibration/baseline-49e656d2-20260705/aggregate.json`
Aggregate sha256: `da6c8b127c93ddeaf8d1f01e384f689aa6fdd479f8521d5edf661bbcfdacd205`

| Case | Trials | Mean | Status |
| --- | ---: | ---: | --- |
| `fusion-stale-baseline-binding-repair` | 2 | 0.9925 | `rejected_ceiling_saturation` |
| `fusion-budget-saturated-triage` | 2 | 0.9550 | `rejected_ceiling_saturation` |
| `fusion-targeted-deployment-risk` | 2 | 0.9725 | `rejected_ceiling_saturation` |

R2 requires every non-guardrail headroom case to calibrate below 0.85. None did.

R7 requires at least two calibrated non-guardrail cases below 0.95. Observed count: 0.

## Interpretation

The second-pass fixes removed the obvious fixture leaks, but the deployed baseline still solves the three headroom cases. The strongest current evidence is that this suite shape has little usable headroom for measuring successor improvement.

The guardrail case remains useful as a non-regression check, but it cannot contribute positive improvement evidence or R2/R7 headroom.

## Next Design Direction

Do not freeze this draft. Redesign or replace the headroom cases, with priority on cases where baseline calibration is expected below 0.80 to leave noise margin below the 0.85 R2 threshold.
