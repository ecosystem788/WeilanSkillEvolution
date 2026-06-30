# SE-0.2 / SE-0.3 candidate acceptance receipt

Status: `candidate_complete_not_adopted`

This receipt establishes stage-specific capability in the isolated candidate. It does not change `ROADMAP.md`, authorize adoption, or deploy the candidate.

## Candidate identity

- Base commit: `d688092`
- Candidate path: `proposals/se-0.2-se-0.3-completion/candidate/solve-with-weilan`
- Candidate files: `29`
- Candidate aggregate SHA-256: `ac420fa67b468222d936fb876479323321f863585f36d2dfe305bd4caaaad7b1`
- Frozen runtime aggregate SHA-256: `89e5f32fa626efda074d9d01fb8714989a8f07fa416437465694c66f850eda1a`

## SE-0.2 evidence

- `projection-rebuild` deterministically derives the bounded current projection from control heads, scoped Frames, and active semantic memory.
- Deleting the projection cache and rebuilding restores an `ACTIVE` projection from authoritative sources.
- `episode-index` and `episode-search` retrieve scoped problems, candidates, holders, tests, observations, collapses, traces, and outcomes with `frame:<id>` provenance.
- Exact workspace/scope isolation and stale-index fallback are covered by `scripts/test_episode_memory.py`.
- Existing activation-state and ancestor-workspace behavior remain covered by `scripts/test_memory.py`.

## SE-0.3 evidence

- Direct `memory-consolidate` rejects `conversation:` and `evidence:` sources; chat-derived claims must pass capture and promotion.
- Conversation evidence resolves one exact Codex thread/turn and snapshots only public user/assistant messages by content hash.
- `--conflicts-with` and `memory-conflicts` preserve explicit unresolved disagreements without inventing semantic contradictions.
- `memory-retention-plan` is read-only. Append-only `memory-disposition` events remove dormant or retired entries from active recall without deleting history.
- Supersession, evidence retraction, source freshness, rebuildable indexes, and non-activation authority remain covered by existing regression tests.
- New integrity coverage is in `scripts/test_semantic_integrity.py`.

## Verification

- Candidate skill validation: passed with `quick_validate.py` under UTF-8 mode.
- Python compilation: all candidate scripts passed.
- New acceptance tests: `test_episode_memory.py`, `test_semantic_integrity.py` passed.
- Existing regression tests passed: conversation evidence, evidence lifecycle, frame lineage, governance, memory activation, metabolism, runner, semantic memory, transaction, and transition planner.
- Frozen snapshot verification: all 27 manifest paths match their recorded SHA-256.
- Deployed Skill verification: all 27 manifest paths match their recorded SHA-256.

## Boundary

- No deployed Skill file changed.
- No frozen baseline file changed.
- No authority document or evaluation policy changed.
- No SE-0.4-or-later behavior was added.
- Adoption and deployment remain explicitly unauthorized.
