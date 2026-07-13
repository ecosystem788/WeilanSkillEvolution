# Approval Package: fusion-dogfood-eval-cases

Status: `approved_frozen`

This package prepares `fusion-dogfood-v0.1` for external approval review. It does not approve the suite, freeze `evals/manifest.json`, run baseline/candidate trials, run shadow comparison, adopt, or deploy.


## Final Approval Binding

Approved on 2026-07-04 by project owner current Codex chat (`?????`).

- Approved manifest: `evals/fusion-dogfood-v0.1-manifest.json`
- Manifest canonical sha256: `f6289701f183ac768da0420e064b1f751bb8caabf3b2f6e82938a7c6868494aa`
- Manifest file sha256: `4f4cca49e1736803c8620321fdef9e590caa67119e228be232ae446e59006d44`
- Approved case spec: `evals/cases/fusion-dogfood-v0.1.json`
- Case spec canonical sha256: `355465c562cea211108095267d3dc659d0e6f72f59d7615eff2b3653b57c68d1`
- Case spec file sha256: `045cb6e8119eb7e68d89edca013de2bce949221e799ff223c72ceab484ac17ac`
- Approval receipt: `evals/approvals/fusion-dogfood-v0.1-approval.json` sha256 `5b72666879dd57f961976c2ad2abb7ae4dc004bc88791bcc1acf8bcdfeebec5b`
- Existing seed manifest `evals/manifest.json` is preserved unchanged; this fusion suite is bound by its own approved manifest.

## Prepared Binding

- Recommended `suite_id`: `fusion-dogfood-v0.1`
- Public case spec: `evals/cases/fusion-dogfood-v0.1.json`
- Public case spec sha256: `219185bf4977358e06324dc6d4874a66f62265665a5c4a652bcdc1ffca4381d6`
- Fixture root: `evals/fixtures/fusion-dogfood-v0.1/`
- Hidden artifacts:
  - `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json` sha256 `7a62e3cc901121a25bfbf1a2795732e4d6776b2570eb8d2863a6a9db440537c4`
  - `evals/hidden/fusion-dogfood-v0.1/evaluator-rubric.json` sha256 `342ba0f69dfb300cfe0c4a307a09ce49a47726369b157eb42917d9db223bf6b0`
  - `evals/hidden/fusion-dogfood-v0.1/source-hashes.json` sha256 `748cd958e2c2773f86f193c16291cec264de8a54e34a7b8e2529c062e91815d8`
  - `evals/hidden/fusion-dogfood-v0.1/redaction-policy.md` sha256 `bb45dd12bcc1370c4e7771fd5f8afb7a8f4ccee1f7e8a1ce48b9cf97039f5ecd`
- Current proposal-side draft hashes:
  - `proposals/fusion-dogfood-eval-cases/cases/fusion-dogfood-v0.1-draft.cases.json`: `73b3c24586867d9ced7e6e9faa7f8c310fbe25f46bfe9ed70d771b187dca5a28`
  - `proposals/fusion-dogfood-eval-cases/proposal.draft.json`: `bb38d8be5ebf0569952fdf8500cf38a6536d999c25c7bed2704ce5fa07dccd73`

## Freeze Engineering Decisions

- B1 implemented as copied snapshots plus `source-hashes.json`; candidate-visible paths no longer point to live `D:\weilan-llm-fusion` files.
- Directory references are forbidden; case 8 uses an explicit selected-file snapshot and excludes this proposal directory.
- `PROJECT_CONTROL.json` was removed from public attribution fixtures where it leaks later conclusions; it remains evaluator-only, except in case 7 where source freshness is the object being tested.
- B2 implemented for case 7 by copying the relevant `fusion-program` method-state snapshot files for isolated `WEILAN_METHOD_HOME` execution.
- N2 implemented: case 1 and case 4 use `trial_count = 2`.
- N4 implemented: every case requires `method_impact_trace` in `expected_receipt_fields`.

## Case Review

### 1. `fusion-s0-spec-review-boundary`

- Level: `L2`
- Trial count: `2`
- Budget: `{"tool_calls": 14, "context_tokens": 14000}`
- Hidden check id: `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json#fusion-s0-spec-review-boundary`
- Candidate-visible fixture snapshots:
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-spec-review-boundary/public/fusion-workspace/specs/EXP-3-S0-substrate-anatomy.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-spec-review-boundary/public/fusion-workspace/artifacts/s0_env_probe.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-spec-review-boundary/public/fusion-workspace/artifacts/s0_skeleton.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-spec-review-boundary/public/fusion-workspace/artifacts/s0_tissue.json`
- Expected receipt fields:
  - `case_id`
  - `verdict`
  - `review_findings`
  - `boundary_checks`
  - `source_paths`
  - `guardrail_results`
  - `uncertainties`
  - `method_impact_trace`
- Scoring weights:
  - `boundary_adherence`: 0.30
  - `review_quality`: 0.25
  - `source_traceability`: 0.20
  - `receipt_readiness`: 0.15
  - `overhead`: 0.10

### 2. `fusion-s0-static-scan-evidence`

- Level: `L1`
- Trial count: `1`
- Budget: `{"tool_calls": 8, "context_tokens": 8000}`
- Hidden check id: `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json#fusion-s0-static-scan-evidence`
- Candidate-visible fixture snapshots:
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-static-scan-evidence/public/fusion-workspace/tools/s0_static_scan.py`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-static-scan-evidence/public/fusion-workspace/artifacts/s0_skeleton.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-static-scan-evidence/public/fusion-workspace/artifacts/s0_tissue.json`
- Expected receipt fields:
  - `case_id`
  - `observed_counts`
  - `static_limits`
  - `evaluator_fields`
  - `guardrail_results`
  - `method_impact_trace`
- Scoring weights:
  - `observed_facts`: 0.35
  - `static_limit_discipline`: 0.25
  - `evaluator_field_selection`: 0.20
  - `constraint_adherence`: 0.15
  - `overhead`: 0.05

### 3. `fusion-s0-env-probe-attribution`

- Level: `L2`
- Trial count: `1`
- Budget: `{"tool_calls": 12, "context_tokens": 10000}`
- Hidden check id: `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json#fusion-s0-env-probe-attribution`
- Candidate-visible fixture snapshots:
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-env-probe-attribution/public/fusion-workspace/tools/s0_env_probe.py`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-env-probe-attribution/public/fusion-workspace/artifacts/s0_env_probe.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-env-probe-attribution/public/fusion-workspace/logs/download-qwen35-4b.err.log`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-env-probe-attribution/public/fusion-workspace/logs/download-qwen35-4b-ms.err.log`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-s0-env-probe-attribution/public/fusion-workspace/logs/download-qwen35-4b-range.err.log`
- Expected receipt fields:
  - `case_id`
  - `attribution`
  - `supporting_evidence`
  - `non_blocking_warnings`
  - `guardrail_results`
  - `method_impact_trace`
- Scoring weights:
  - `error_attribution`: 0.35
  - `source_freshness`: 0.20
  - `non_blocking_warning_quality`: 0.15
  - `guardrail_adherence`: 0.20
  - `overhead`: 0.10

### 4. `fusion-p2-instrument-noise-recovery`

- Level: `L2`
- Trial count: `2`
- Budget: `{"tool_calls": 12, "context_tokens": 12000}`
- Hidden check id: `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json#fusion-p2-instrument-noise-recovery`
- Candidate-visible fixture snapshots:
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-p2-instrument-noise-recovery/public/fusion-workspace/specs/EXP-2-behavioral-readout.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-p2-instrument-noise-recovery/public/fusion-workspace/specs/EXP-2f-final-forced-choice.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-p2-instrument-noise-recovery/public/fusion-workspace/artifacts/exp2_receipt.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-p2-instrument-noise-recovery/public/fusion-workspace/artifacts/exp2_score_report.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-p2-instrument-noise-recovery/public/fusion-workspace/artifacts/exp2f_receipt.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-p2-instrument-noise-recovery/public/fusion-workspace/artifacts/exp2f_score_report.json`
- Expected receipt fields:
  - `case_id`
  - `run_comparison`
  - `error_attribution`
  - `hidden_evidence_handling`
  - `future_evaluator_checklist`
  - `guardrail_results`
  - `method_impact_trace`
- Scoring weights:
  - `run_comparison_accuracy`: 0.25
  - `error_attribution_quality`: 0.25
  - `hidden_evidence_boundary`: 0.25
  - `future_evaluator_checklist`: 0.15
  - `overhead`: 0.10

### 5. `fusion-exp15-merge-error-attribution`

- Level: `L3`
- Trial count: `2`
- Budget: `{"tool_calls": 18, "context_tokens": 18000}`
- Hidden check id: `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json#fusion-exp15-merge-error-attribution`
- Candidate-visible fixture snapshots:
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-exp15-merge-error-attribution/public/fusion-workspace/specs/EXP-1.5-merge-operator.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-exp15-merge-error-attribution/public/fusion-workspace/artifacts/exp15-v1_receipt.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-exp15-merge-error-attribution/public/fusion-workspace/artifacts/exp15-v1_report.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-exp15-merge-error-attribution/public/fusion-workspace/artifacts/exp15-v1_merge_events.jsonl`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-exp15-merge-error-attribution/public/fusion-workspace/artifacts/exp15b-v1_receipt.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-exp15-merge-error-attribution/public/fusion-workspace/artifacts/exp15b-v1_report.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-exp15-merge-error-attribution/public/fusion-workspace/artifacts/exp15b-v1_merge_events.jsonl`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-exp15-merge-error-attribution/public/fusion-workspace/artifacts/exp15b-v1_budget_events.jsonl`
- Expected receipt fields:
  - `case_id`
  - `collapse_scope`
  - `invalidated_assumption_id`
  - `failure_evidence`
  - `reusable_artifacts`
  - `forbidden_assumption`
  - `reentry_condition`
  - `authority_required`
  - `guardrail_results`
  - `method_impact_trace`
- Scoring weights:
  - `collapse_quality`: 0.25
  - `error_attribution_quality`: 0.25
  - `authority_boundary`: 0.20
  - `trace_reuse`: 0.20
  - `overhead`: 0.10

### 6. `fusion-hidden-evidence-boundary`

- Level: `L1`
- Trial count: `1`
- Budget: `{"tool_calls": 8, "context_tokens": 7000}`
- Hidden check id: `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json#fusion-hidden-evidence-boundary`
- Candidate-visible fixture snapshots:
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-hidden-evidence-boundary/public/fusion-workspace/specs/READOUT-CONTRACT-v1.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-hidden-evidence-boundary/public/skill-evolution-workspace/EVALUATION_POLICY.md`
- Expected receipt fields:
  - `case_id`
  - `classification_table`
  - `hidden_material_policy`
  - `redaction_rules`
  - `guardrail_results`
  - `method_impact_trace`
- Scoring weights:
  - `classification_accuracy`: 0.35
  - `hidden_material_redaction`: 0.30
  - `policy_alignment`: 0.20
  - `constraint_adherence`: 0.10
  - `overhead`: 0.05

### 7. `fusion-memory-scope-recovery`

- Level: `L2`
- Trial count: `2`
- Budget: `{"tool_calls": 10, "context_tokens": 9000}`
- Hidden check id: `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json#fusion-memory-scope-recovery`
- Candidate-visible fixture snapshots:
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/fusion-workspace/PROJECT_CONTROL.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/fusion-workspace/README.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/fusion-workspace/ROADMAP.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/fusion-workspace/AGENTS.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/method-state-snapshot/memory/control/workspaces/c87abeba95f998da/2026-07-04.jsonl`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/method-state-snapshot/memory/projections/workspaces/c87abeba95f998da/fb5920559987.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/method-state-snapshot/memory/indexes/workspaces/c87abeba95f998da/fb5920559987.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/method-state-snapshot/memory/episode-indexes/workspaces/c87abeba95f998da/fb5920559987.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/method-state-snapshot/memory/lineage/heads/c87abeba95f998da/fb5920559987.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/method-state-snapshot/memory/lineage/workspaces/c87abeba95f998da/fb5920559987/2026-07-04.jsonl`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-memory-scope-recovery/public/method-state-snapshot/memory/semantic/workspaces/c87abeba95f998da/fb5920559987/2026-07-03.jsonl`
- Expected receipt fields:
  - `case_id`
  - `activation_state`
  - `selected_scope`
  - `source_verification`
  - `next_authorized_action`
  - `guardrail_results`
  - `method_impact_trace`
- Scoring weights:
  - `activation_handling`: 0.25
  - `scope_isolation`: 0.25
  - `source_verification`: 0.20
  - `next_action_quality`: 0.15
  - `overhead`: 0.15

### 8. `fusion-scope-redirection-to-eval-proposal`

- Level: `L2`
- Trial count: `1`
- Budget: `{"tool_calls": 18, "context_tokens": 18000}`
- Hidden check id: `evals/hidden/fusion-dogfood-v0.1/hidden-checks.json#fusion-scope-redirection-to-eval-proposal`
- Candidate-visible fixture snapshots:
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/skill-evolution-workspace/ROADMAP.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/skill-evolution-workspace/EVALUATION_POLICY.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/skill-evolution-workspace/LOCAL_STATUS.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/skill-evolution-workspace/evals/manifest.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/solve-with-weilan-skill/references/evolution-system.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/solve-with-weilan-skill/references/runner-system.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/README.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/ROADMAP.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/specs/EXP-3-S0-substrate-anatomy.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/specs/EXP-2-behavioral-readout.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/specs/EXP-2f-final-forced-choice.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/specs/EXP-1.5-merge-operator.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/tools/s0_static_scan.py`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/tools/s0_env_probe.py`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/s0_env_probe.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/s0_skeleton.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/s0_tissue.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/exp2_receipt.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/exp2_score_report.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/exp2f_receipt.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/exp2f_score_report.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/exp15-v1_receipt.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/exp15-v1_report.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/exp15b-v1_receipt.md`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/artifacts/exp15b-v1_report.json`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/logs/download-qwen35-4b.err.log`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/logs/download-qwen35-4b-ms.err.log`
  - `evals/fixtures/fusion-dogfood-v0.1/fusion-scope-redirection-to-eval-proposal/public/fusion-workspace/logs/download-qwen35-4b-range.err.log`
- Expected receipt fields:
  - `case_id`
  - `created_files`
  - `candidate_cases`
  - `fusion_evidence_sources`
  - `authority_needed`
  - `negative_confirmation`
  - `method_impact_trace`
- Scoring weights:
  - `proposal_completeness`: 0.25
  - `authority_boundary`: 0.25
  - `source_traceability`: 0.20
  - `receipt_quality`: 0.15
  - `overhead`: 0.15

## Approval Checklist

Project authority must approve:

- `suite_id = fusion-dogfood-v0.1`.
- The public case spec hash and every fixture/evaluator artifact hash above.
- The eight case ids and public prompts.
- Budgets, trial counts, scoring weights, and hidden-check separation.
- The rule that this suite supplements `se-seed-v0.1` and does not mutate it.
- The rule that passing this suite creates evaluation evidence only, not adoption or deployment.

## Before Any Future Shadow Run

- Bind baseline artifact hash.
- Bind candidate artifact hash.
- Bind evaluation manifest hash.
- Bind public case spec hash.
- Bind evaluator artifact hashes.
- Bind model/tool configuration, environment id, budgets, and repeated-trial counts.
- Verify candidates cannot read hidden evaluator material.
- Verify baseline and candidate receive equivalent isolated inputs.

## Non-Approval Statement

This approval freezes the fusion-dogfood-v0.1 suite and its manifest. It does not run baseline/candidate, does not run shadow, does not adopt, and does not deploy.
