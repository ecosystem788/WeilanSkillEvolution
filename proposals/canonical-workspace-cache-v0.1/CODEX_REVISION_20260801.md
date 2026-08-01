# Codex revision receipt — 2026-08-01

Scope: collect the behavioral-discriminator mislabel identified in
`CLAUDE_REVIEW_20260801.md`, re-freeze the proposal candidate, and do not deploy.

## Result

- Revised candidate hash:
  `8602bb0f4e243145c8bf2a7cb0ea7552edc7f19557f370bdae81a26708d93c1a`.
- Proposal validation: `valid: true`, `changed_path_count: 2`.
- Baseline with the revised test grafted: return code 1, one `FAILED` by
  `AssertionError`, one `SKIPPED`, and no `AttributeError`.
- Revised candidate: return code 0, two `PASSED`.
- Baseline-to-candidate artifact delta remains exactly
  `scripts/runtime_core.py` plus `scripts/test_canonical_workspace_cache.py`.
- Previous-to-revised candidate delta is exactly
  `scripts/test_canonical_workspace_cache.py`; `scripts/runtime_core.py` is
  byte-identical across those two candidate hashes.
- Both installed Skills still hash to the frozen baseline
  `ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad`.

## Full-suite reconciliation

At the time the original revision receipt was authored, the 600-second attempt had
not emitted a new receipt. A complete machine-readable result appeared afterward in
`_probe_suite_acceptance.out.json`, so the earlier statement that the file still
described `ec236760…` is superseded by the current on-disk evidence.

The current receipt binds candidate `8602bb0f…`: baseline collected 93 nodes with
92 passed and one failure; the revised candidate collected 95 nodes with 94 passed
and the same single failure. Candidate-only failures and baseline-only nodes are
empty. Claude independently corroborated those conclusions in
`_review2_20260801_claude_independent_suite.out.json` under a separate runner and
1500-second per-arm bound. The exact cause of the late appearance is not inferred
beyond the observed artifact ordering.

Only `test_same_expanded_path_is_resolved_once_per_process` is the behavioral
discriminator against a purpose-built no-cache sham. The explicit-clear/new-process
test pins the documented boundary but is not an independent caching discriminator.

This reconciliation closes the suite-evidence mismatch. It does not create a
shadow result, adoption authority, or deployment authority, and it changes no
candidate or installed Skill byte.
