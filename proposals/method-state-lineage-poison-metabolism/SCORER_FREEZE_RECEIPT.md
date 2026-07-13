# Fusion Dogfood v0.1 Scorer Freeze Receipt

Status: `diagnostic_rescore_complete_shadow_gate_unchanged`
Date: 2026-07-05
Reviewer / executor: Codex
Evaluator author: Claude, owner-authorized by evidence-capture
`65f774cb-9439-45c8-b587-19777dec767c`

## Scope

This receipt freezes the Claude-authored, hidden-aware diagnostic scorer for
`fusion-dogfood-v0.1` and records Codex's review, provenance fix, and diagnostic
rescore of `mwp-shadow-20260705`.

This is not an adoption decision. The original shadow gate remains
`shadow_failed_no_adoption`; adoption-grade evidence requires a fresh
owner-authorized shadow using the pre-frozen scorer.

## Frozen Hashes

- Scorer:
  `evals/hidden/scorers/fusion-dogfood-v0.1/scorer.py`
  `428f64899d1c153b37d6f1e33d8df51da8323d094d876884c30698f76c21bf59`
- Scorer tests:
  `evals/hidden/scorers/fusion-dogfood-v0.1/test_scorer.py`
  `951f666abcdca0197be435dad16fe242debcac9603cfee7cf7460472bc4963c5`
- Frozen rubric:
  `evals/hidden/fusion-dogfood-v0.1/evaluator-rubric.json`
  `e8f59038ae21881f462c125b70879a096800267c5cd7bd33c01c2441d8f1c743`
- Frozen hidden checks:
  `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json`
  `a11a7dc8457b67ce74882d621b4ea128b164be2b9a2619306bd0d0a731ff2d3c`
- Diagnostic rescore result:
  `proposals/method-state-lineage-poison-metabolism/shadow/runs/mwp-shadow-20260705/shadow-result.rescored.json`
  `c6c2ce2ffaea6ce5eefc09f9eaf4b89a54f88cfc6fe287694feee39f9f758b60`
- Retired historical keyword scorer:
  `proposals/method-state-lineage-poison-metabolism/shadow/score_fusion_shadow_run.py`
  `e5b8dcf8360836f1effe46c3310290f63e02e0ade891aef77d09ac6096fc874b`

## Review Results

- `python -m pytest evals/hidden/scorers/fusion-dogfood-v0.1/test_scorer.py -q`
  passed: `11 passed`.
- `python -m py_compile evals/hidden/scorers/fusion-dogfood-v0.1/scorer.py proposals/method-state-lineage-poison-metabolism/shadow/score_fusion_shadow_run.py`
  passed.
- Extraction smoke on the existing run parsed all 24 outputs.
- No concrete `mwp-*` execution ids appear in scorer criteria or tests.
- Exact hidden-literal scan of the diagnostic output found only the public suite id
  `fusion-dogfood-v0.1`, not hidden expected answers.
- Output provenance now includes recomputable hashes for the scorer file, rubric,
  and hidden-checks file.

## Diagnostic Rescore

Command:

```powershell
python evals\hidden\scorers\fusion-dogfood-v0.1\scorer.py --run-root proposals\method-state-lineage-poison-metabolism\shadow\runs\mwp-shadow-20260705 --out proposals\method-state-lineage-poison-metabolism\shadow\runs\mwp-shadow-20260705\shadow-result.rescored.json
```

Result summary:

- `diagnostic_only`: `true`
- `gate_effect`: `none_original_shadow_failed_no_adoption_unchanged`
- `mean_delta`: `0.096875`

Case deltas:

- `fusion-s0-spec-review-boundary`: `0.125`
- `fusion-s0-static-scan-evidence`: `0.441667`
- `fusion-s0-env-probe-attribution`: `0.166667`
- `fusion-p2-instrument-noise-recovery`: `0.041667`
- `fusion-exp15-merge-error-attribution`: `-0.033334`
- `fusion-hidden-evidence-boundary`: `0.0`
- `fusion-memory-scope-recovery`: `0.033334`
- `fusion-scope-redirection-to-eval-proposal`: `0.0`

## Provenance Finding

The old receipt field `grader_provenance.evaluator_artifact_hash =
b04c826e84a6bc37b3a71325fcdc93733ea942b284dff70cf831a9f34163256d`
comes from `evals/shadow/fusion-dogfood-v0.1-e1-2ae80d-plan.json` as the
per-case evaluator hash for `fusion-s0-spec-review-boundary`. It does not match
the current on-disk hashes of the scorer, rubric, hidden checks, whole hidden
checks object, or that case's hidden-check object.

Going forward, the diagnostic scorer records a recomputable `grader_provenance`
object with:

- `scorer_path` and `scorer_sha256`
- `rubric_path` and `rubric_sha256`
- `hidden_checks_path` and `hidden_checks_sha256`

## Retirement

`proposals/method-state-lineage-poison-metabolism/shadow/score_fusion_shadow_run.py`
is retained for historical reproduction only and now emits a retirement warning
when run. Future diagnostic scoring for this suite should use the frozen hidden
scorer recorded above.
