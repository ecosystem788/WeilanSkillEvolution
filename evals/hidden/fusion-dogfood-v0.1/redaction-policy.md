# Redaction Policy: fusion-dogfood-v0.1

Status: approved_frozen

Candidate-visible bundles may include public prompts, public guardrails, budgets, scoring metric names, and copied public fixture snapshots only.

Do not expose private arm maps, option maps, answer keys, raw hidden answers, credentials, API keys, evaluator expected outputs, scoring keys, or evaluator-only trace classifications to candidates.

`PROJECT_CONTROL.json` is evaluator-only for attribution cases where it contains later conclusions. It is candidate-visible only for cases where source-freshness and method-state recovery are the task object.

All public source references must resolve to copied fixture paths under `evals/fixtures/fusion-dogfood-v0.1/<case_id>/`. Directory-wide references and live absolute source reads are forbidden.

Approval source: `evals/approvals/fusion-dogfood-v0.1-approval.json`
