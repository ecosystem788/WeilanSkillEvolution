# EXP-8/S2-M0 v0.4 修订案: UPDATE 天花板仪器修复

Status: FROZEN 2026-07-04 by project-owner authorization after Claude supplement; implementation/run authorized.

## 0. Run-1 审计结论

Run-1 mechanically completed but correctly exited `invalid_instrument`.

Registered facts from downloaded artifacts:

- `complete_report=True`
- `deterministic_passes=True`
- `instrument_passes=False`
- failing tooth: `ceiling_update`
- UPDATE C arm current-correct: `11/24`, registered threshold `23/24`
- UPDATE C arm distribution: `current=11, stale=8, other=5`; i.e. `13/24` non-current under full context
- STABLE C arm: `24/24`
- pooled D floor: `10/48`, below fail line `>=20/48`
- leakage: pass
- lambda UPDATE stale counts: `15 -> 8 -> 7 -> 6` for `lambda=1,0.5,0.25,0`
- lambda UPDATE current counts: `4 -> 6 -> 7 -> 7`

Consequence: Run-1 does not adjudicate `H_state`, `state_ops_profitable`, or governance. `W2_stale_rigidity` and `eval_delta=0.0` are diagnostics only under `invalid_instrument`.

Method lesson: the v0.3 `invalid_instrument` exit code worked. Without it, a broken text instrument would have been misread as state rigidity.

## 1. Standing Observations From Valid Cells

These observations are allowed because their instruments passed.

1. Health/interference dose response:
   - HEALTH correct counts: `lambda=1: 10/12`, `0.5: 11/12`, `0.25: 12/12`, `0: 12/12`.
   - Carried irrelevant state measurably harms in-window reading.
   - This supports the S2-M1 hygiene axis even if v0.4 later fails.

2. Text-layer replacement weakness:
   - The model does not reliably resolve implicit replacement at 2k-4k token distances.
   - This is a substrate observation, not a governance verdict.

## 2. Scope Of v0.4

v0.4 repairs only the UPDATE instrument.

Do not change:

- lambda set: `{1, 0.5, 0.25, 0}`
- lambda endpoint contract: `lambda=0` is true fresh-cache; intermediate lambdas scale only `recurrent_states`
- governance thresholds and select/eval adjudication
- pooled D floor rule
- health tooth one-sided rule
- leakage rules
- Run-1 artifacts

Change:

- condition the main claim on explicitly marked, text-parseable replacement items
- replace the UPDATE wording
- add C-only UPDATE ceiling calibration before freeze
- reuse v1 STABLE/HEALTH trials and frozen split unchanged
- pin the actual device for v0.4 to the same observed device class used by Run-1: RTX 4090 49140 MiB on the cloned westb instance, unless project owner explicitly authorizes a new full freeze for another device

## 3. Revised Claim Wording

Old unrestricted wording is too broad after Run-1.

v0.4 claim:

```text
Under K=256, for explicitly marked replacement items whose current value is parseable by the full-context text path, carried state may retain stale information; a blunt state-governance operator may improve the update/stability tradeoff without harming in-window health.
```

Chinese operational wording:

```text
在"显式标记取代"且 C-only 校准确认为文本可解析的 UPDATE 人群上,
测试携带态是否仍保留旧值吸引子,以及钝器态治理能否在不伤健康格的前提下改善 UPDATE/STABLE 权衡。
```

This is a population-conditioned claim. The calibration yield is itself a reported measurement of text-layer update ability.

## 4. UPDATE Template

Replace the Run-1 implicit replacement template with explicit old/current markers:

```text
F1: 【旧记录】在本次虚构登记中，{place}的{entity}{attribute}曾登记为{old}。
F2: 【有效更新】同一登记项已经改写：{place}的{entity}{attribute}现在登记为{new}。以本条更新为准。
Q : 根据有效更新，{place}的{entity}{attribute}现在登记为
```

Leakage constraints remain exact:

- `{old}` appears only in F1.
- `{new}` appears only in F2.
- Q contains neither option label.
- entity appears exactly once in F1, once in F2, once in Q.
- filler contains no entity or option label.

## 5. C-Only Calibration Gate

Calibration is a design-time instrument validity gate, not a governance run.

1. Candidate pool
   - overgenerate at least `96` UPDATE candidates
   - balanced candidate counts by `current_label`
   - balanced candidate counts by ordered transition pair `old_label -> current_label`
   - same distance targets: F1-to-Q `4096`, F2-to-Q `2048`
   - same single-token option and leakage checks

2. Calibration measurement
   - run only full-context C arm
   - R=2
   - same actual device/environment as the official v0.4 run
   - no D arm
   - no lambda arms
   - no saved-state surgery
   - no governance score

3. Eligibility
   - exact materialized distances
   - C arm predicts `current_label` in both repeats
   - C repeat outputs deterministic
   - leakage pass
   - option labels remain same-category single-token labels

4. Selection
   - select exactly `24` UPDATE trials
   - exactly `6` per `current_label`
   - exactly `2` per ordered transition pair `old_label -> current_label` across the 12 non-identity pairs
   - deterministic select/eval split: `1 + 1` per ordered transition pair, therefore `3 + 3` per current label
   - tie-break by frozen candidate id/hash, not by confidence margin

5. Calibration failure
   - if any ordered transition pair has fewer than `2` eligible candidates, exit `invalid_update_ceiling_pool`
   - this code belongs to the calibration phase, analogous to corpus-v2 `insufficient_candidates`
   - it is not an official-run exit code
   - do not lower the `23/24` ceiling number to rescue the pool
   - do not inspect D/lambda arms to rescue the pool

Required calibration-yield report:

- total candidates
- eligible candidates
- eligible rate overall
- eligible count/rate by current label
- candidate-to-eligible count/rate by ordered transition pair, all 12 cells
- rejection reasons
- Run-1 implied UPDATE C yield baseline: `11/24 = 45.8%`

## 6. Official Run Tooth Semantics

After v0.4 calibration, official C ceiling changes role.

Calibration integrity becomes the validity-bearing instrument gate. Official C ceiling becomes a regression check:

- official C UPDATE and STABLE counts remain mandatory report fields
- `23/24` remains the expected regression threshold
- if official C UPDATE falls below `23/24`, report `ceiling_regression_observed` and require audit
- do not automatically convert a calibrated official run to `invalid_instrument` solely because the official C regression check misses by stochastic/device drift
- if the miss indicates calibration artifact mismatch, wrong plan, wrong model/tokenizer, wrong device, or leakage, then exit `invalid_instrument` or `invalid_incomplete_report` as appropriate
- if the miss is unexplained after artifact checks, the runner must suppress any automatic governance verdict and set `adjudication_status=held_for_ceiling_regression_audit`; this is an audit hold, not a new official exit-lattice verdict
- a held run can never become a verdict directly. It has only two exits:
  - declare `invalid_instrument` and recalibrate
  - perform one execution-layer-only fix and rerun the same frozen plan

Exit/adjudication order:

```text
blocked_* -> invalid_incomplete_report -> held_for_ceiling_regression_audit
-> invalid_instrument(floor/leakage/calibration-mismatch) -> registered verdicts
```

Floor tooth keeps adjudicating:

- pooled D floor across UPDATE+STABLE remains official
- if D correct count `>=20/48`, exit `invalid_instrument`

Health tooth keeps adjudicating:

- destructive health behavior still triggers `intervention_destructive`
- lambda<1 better than lambda=1 remains report-only interference evidence, not a health failure

## 7. Reuse And Device Anchor

Minimal repair rule:

- reuse v1 STABLE trials unchanged
- reuse v1 HEALTH trials unchanged
- reuse v1 frozen split for STABLE/HEALTH unchanged
- replace only UPDATE trials through the calibrated pool
- do not overwrite v1 artifacts

Device condition:

- Run-1 actually ran on RTX 4090 49140 MiB, not the originally expected 5090.
- v0.4 should run on the same actual device/environment as Run-1 to preserve STABLE/HEALTH anchor comparability.
- If project owner switches to another device, freeze must explicitly record that as a new device condition, rerun the reused STABLE/HEALTH C/D anchor checks before official lambda adjudication, and treat cross-run anchor comparisons as device-shift diagnostics rather than same-device drift evidence.
- calibration and official run must use the same actual device/environment because the C-regression check compares calibration C to official C.

Anchor telemetry:

- report per-trial v1-vs-v0.4 agreement on reused STABLE trials
- report per-trial v1-vs-v0.4 agreement on reused HEALTH trials
- report these as drift telemetry only, not as adjudication gates

Residual caveat:

- conditioning on text-resolvable UPDATE candidates may correlate with F2 recency strength in the state itself
- this could raise apparent native supersession
- mitigate by population-conditioned claim wording plus per-pair yield/stale/error reports
- this caveat is registered but does not block v0.4

## 8. Anti-Overfit Artifacts

The freeze package must include:

- candidate pool sha256
- calibration runner sha256
- official runner sha256
- model config/tokenizer sha256
- environment and device fingerprint
- all C-only calibration rows, including rejected candidates
- selected UPDATE trial ids
- reused STABLE/HEALTH trial ids from v1
- frozen split table
- proof that calibration ran no D/lambda arms
- final v0.4 trial plan sha256
- calibration-yield table
- v1-vs-v0.4 STABLE/HEALTH anchor agreement table

The official run must verify the calibration artifact hashes before evaluating D/lambda arms.

## 9. Runner Changes

Recommended implementation:

- add `tools/exp8_s2_m0_calibrate_update.py`
- add `tools/exp8_s2_m0_generate_v04.py` or a versioned generator mode
- keep official runner versioned or add a strict `--run-id exp8-s2-m0-v04`

Runner must enforce:

- calibration mode refuses D/lambda arms
- official mode refuses to run without a matching calibration artifact
- official mode verifies reused STABLE/HEALTH trial ids against v1 plan hash
- official mode reports calibration yield and official C regression fields separately
- official mode reports v1-vs-v0.4 anchor agreement for reused STABLE/HEALTH trials

Budget:

- calibration: at least `96` UPDATE candidates x C arm x R=2 full-prefill measurements
- official: `60` flows x C/D/lambda arms x R=2 as in v1
- both costs belong to the v0.4 budget tooth

Recommended artifacts:

- `artifacts/exp8-s2-m0-v04_update_candidate_pool.json`
- `artifacts/exp8-s2-m0-v04_update_ceiling_calibration.json`
- `artifacts/exp8-s2-m0-v04_trial_plan.json`
- `artifacts/exp8-s2-m0-v04_results.json`
- `artifacts/exp8-s2-m0-v04_receipt.json`

## 10. Death Line

If explicit UPDATE wording plus C-only calibration cannot produce a balanced 24-trial UPDATE set, collapse only the UPDATE-instrument route:

```text
S2-M0 UPDATE replacement semantics are not instrumentable on this model with the current raw-text single-token forced-choice format.
```

Then stop governance reruns and run a smaller instrument study.

If calibration succeeds but official v0.4 still fails via D floor, health destruction, determinism, hook, calibration mismatch, or incomplete report, preserve the registered exit and do not reinterpret it as governance.

## 11. Review Closure

Claude answers incorporated:

- C-only calibration accepted under D/lambda blindness.
- Explicit replacement wording accepted; claim is limited to explicitly marked replacement.
- `invalid_update_ceiling_pool` is a calibration-phase code.
- v1 STABLE/HEALTH trials and split are reused unchanged as drift anchors.
- actual device mismatch from Run-1 is recorded; v0.4 pins the actual 4090 environment unless reauthorized.
- Claude supplement incorporated: per-pair yield table, held-run no-verdict rule, calibration-same-device rule, v1 anchor agreement telemetry, residual conditioning caveat, and calibration budget accounting.
