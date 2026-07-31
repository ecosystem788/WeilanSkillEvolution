# Codex independent review — current proposal rejected at its own contract boundary

Review target: `find-frame-index-v0.1`, frozen baseline
`ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad` and candidate
`794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b`.

## Verdict

The candidate is not eligible to advance under the current `proposal.json`. This is a
proposal-contract rejection, not a rejection of indexing as a direction and not an
adoption or deployment decision.

## Independently reproduced

- `proposal-validate`: `valid: true`, `changed_path_count: 2`.
- Both frozen artifact hashes reproduced with `candidate-freeze` (`created: false`).
- Tree diff: only `scripts/weilan_trace.py` changed and
  `scripts/test_find_frame_index.py` was added; nothing removed.
- Equivalence probe: 8/9 scenarios equivalent. The sole divergence is
  `foreign_second_file_after_first_lookup`.
- In that scenario the baseline's second lookup raises `RuntimeError`; the candidate
  returns the already indexed path.
- The ten new candidate tests pass (`10 passed`).
- The pre-existing `test_slow_loop.py::test_promotion_gate_rejects_on_full_budget`
  fails in both frozen trees with the same `invalid_or_incomplete_marker` error.

The attempted chained full-suite/performance rerun was terminated after exceeding the
README's combined rough runtime without emitting a receipt. It is not used as evidence
for this verdict.

## Contract collision

The proposal rationale says the table keeps the result identical to what a
same-moment glob would return. Its rollback triggers include:

> find_frame returns a path the same-moment glob would not have returned

The disclosed divergent scenario does exactly that: the same-moment baseline glob sees
two live matches and raises, while the candidate returns one path. Disclosure makes the
difference observable; it does not neutralize the proposal's own rollback trigger. The
candidate comment that the glob version does not make this guarantee is contradicted by
the frozen baseline behavior reproduced by the proposal's own probe.

## Re-entry

A successor may re-enter by either:

1. preserving the current contract with evidence that foreign writes cannot make an
   already indexed id ambiguous (or with an implementation that detects that ambiguity),
   while retaining the measured speedup; or
2. explicitly weakening the contract and rewriting the conflicting rollback trigger,
   with independent evidence that delayed duplicate-id detection is acceptable for
   lineage integrity.

No deployed Skill, adoption state, shadow result, or evaluation authority was changed.
