# fusion-dogfood-eval-cases

Status: `approved_frozen`

This proposal defines an external dogfood eval suite derived from the real `D:\weilan-llm-fusion` run history. It is prepared for approval review, but it is approved and frozen through `evals/fusion-dogfood-v0.1-manifest.json`; the legacy seed manifest at `evals/manifest.json` is preserved unchanged.

## Authority Boundary

- This proposal does not modify the deployed Skill at `D:\CodexData\skills\solve-with-weilan`.
- This proposal does not modify the frozen manifest at `D:\WeilanSkillEvolution\evals\manifest.json`.
- This proposal does not approve, shadow-run, adopt, rollback, or deploy any candidate.
- Candidate-visible source material is copied under `evals/fixtures/fusion-dogfood-v0.1/<case_id>/`; live source paths and directory-wide references are forbidden.
- Hidden evaluator checks, private maps, answer logs, expected outputs, and evaluator rubrics are under `evals/hidden/fusion-dogfood-v0.1/` and must not be exposed to candidates.

## Prepared Artifacts

- `cases/fusion-dogfood-v0.1-draft.cases.json`: proposal-side draft, synchronized to frozen fixture paths.
- `D:\WeilanSkillEvolution\evals\cases\fusion-dogfood-v0.1.json`: public case spec prepared for approval review, status `prepared_not_approved`.
- `D:\WeilanSkillEvolution\evals\fixtures\fusion-dogfood-v0.1\`: copied candidate-visible fixture snapshots.
- `D:\WeilanSkillEvolution\evals\hidden\fusion-dogfood-v0.1\hidden-checks.json`: hidden checks.
- `D:\WeilanSkillEvolution\evals\hidden\fusion-dogfood-v0.1\evaluator-rubric.json`: evaluator rubric.
- `D:\WeilanSkillEvolution\evals\hidden\fusion-dogfood-v0.1\source-hashes.json`: explicit file hash manifest.
- `D:\WeilanSkillEvolution\evals\hidden\fusion-dogfood-v0.1\redaction-policy.md`: hidden-material redaction policy.

## Case Set

1. `fusion-s0-spec-review-boundary`
2. `fusion-s0-static-scan-evidence`
3. `fusion-s0-env-probe-attribution`
4. `fusion-p2-instrument-noise-recovery`
5. `fusion-exp15-merge-error-attribution`
6. `fusion-hidden-evidence-boundary`
7. `fusion-memory-scope-recovery`
8. `fusion-scope-redirection-to-eval-proposal`

## Approval Needed

Before use, an external authority must approve the suite id, public case spec, fixture hashes, hidden evaluator artifacts, budgets, trial counts, and scoring version. Only after that approval may a future manifest bind these artifacts.

## Final Approval

Approved manifest: `evals/fusion-dogfood-v0.1-manifest.json`

Manifest canonical sha256: `f6289701f183ac768da0420e064b1f751bb8caabf3b2f6e82938a7c6868494aa`

Approval receipt: `evals/approvals/fusion-dogfood-v0.1-approval.json`
