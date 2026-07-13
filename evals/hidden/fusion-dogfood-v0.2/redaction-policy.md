# fusion-dogfood-v0.2 Redaction Policy (Draft)

Status: draft_unfrozen. This file is evaluator-side unless the owner publishes it at freeze.

- Candidate-visible inputs are copied snapshots under `evals/fixtures/fusion-dogfood-v0.2/<case_id>/public/`,
  populated from pinned source snapshots under `proposals/fusion-dogfood-extension-v0.2/source-snapshots/`.
- Field-level redaction: candidate-visible copies of `guardrail-result.rebound.json` drop the
  `interpretation` block, including `interpretation.diagnostic_summary`; each redacted copy carries a
  `public_fixture_redaction` marker and the fixture manifest row records `redacted_fields`. Raw comparisons,
  case deltas, and guardrail fields are retained. Unredacted originals stay in the pinned snapshots.
- Calibration transcripts, raw outputs, score breakdowns, hidden checks, evaluator rubrics, and scorer notes are never candidate-visible.
- Freeze materials may publish only R8 aggregate calibration facts.
- Live workspace paths are provenance only; candidates must cite fixture paths.
- Credentials, private maps, hidden answers, and deployment rollback internals not copied into public fixtures remain excluded.
- This hidden-aware engineering thread must not author or edit a successor candidate evaluated on v0.2.
