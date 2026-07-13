# Barrel-Fix v5 - Making the Collapse Gate Live (M3 + M4)

Owner-authorized barrel batch 5 (2026-07-07). Mechanism batch 2: the collapse
gate existed but did not fire in practice (`method_impact_count = 0` in E1)
because pressure was always a manual act, and nothing mechanically confronted a
re-entering candidate with its collapsed ancestors. Both halves are
read-only/advisory: mechanism surfaces evidence, the LLM and the owner keep all
authority. Base: deployed v4
(`4554ee3e1f7d12354358588cb83a79b342f0c6f3f77ccf35842bed5f4ed6e43f`).

## M3 - governance-pressure-derive

`governance-pressure-derive --workspace <cwd> --scope <scope>` is a read-only
derivation over the scope's own evidence; it records nothing.

- Two or more failed/blocked episodes whose tokens overlap an
  ACTIVE/WARNED/PROBATION target suggest a `contradiction` pressure. Three or
  more upgrade the suggested strength to `strong`; evidence is the failing
  `frame:` refs.
- A target whose registered source snapshots no longer match their sources
  suggests `staleness`.
- Failed/blocked episodes matching no registered target are informational
  `unregistered_risk` suggestions inviting `governance-target-register`, not
  pressure.

Recordable suggestions carry a direct `governance-pressure-record` command with
real `--required-change` and `--frame-id` values. If the scope has no usable
causal frame or a stale source ref is no longer valid governance evidence, the
suggestion is still shown with `recordable: false` and a blocking reason instead
of a fake command template. Re-running derive after an active matching pressure
is recorded does not keep emitting the same suggestion.

Exit 2 signals suggestions exist. No timer, no loop, no auto-transition:
derivation is a projection and pressure recording remains explicit.

## M4 - Re-entry trace advisories

`collapse_trace_registry` collects every collapse trace in the scope from both
planes: frame `trace_emitted` events (via the episode index, memoized) and
governance `collapse_trace` records. `matching_forbidden_traces` does
token-overlap matching, including Chinese bigrams, between candidate text and
each `forbidden_assumption`.

Surfaced three ways:

- `trace-check --text "..."`: standalone read-only check, exit 2 on match.
- `candidate_admitted`, `holder_selected`, and `route_reentered` events:
  advisories appear in the command JSON output automatically.
- Lineaged `open`: problem/success text is checked at frame open.

If the advisory registry cannot be built because the scope's governance trace
plane is invalid, standalone `trace-check` fails visibly. Event/open hooks still
preserve the main command but add `trace_advisory_error` to the command JSON
instead of silently returning no advisory.

Advisory-only by design for this first round: the constitution's re-entry rule
(declared new evidence, not a rename) stays a judgment; the mechanism guarantees
the trace is seen. SKILL.md states that silently ignoring an advisory is a
method violation. Hard blocking with a `--reentry-evidence` override is deferred
until false-positive rates are observed in real use.

## Codex Review Fixes

Round 1 audit found four issues and this candidate now covers them:

- Production close outcomes are `failed`/`blocked`; derive now recognizes
  production `failed` outcomes (with legacy `failure` tolerated) and tests use
  `failed` by default.
- Active matching pressures suppress duplicate derive suggestions.
- Staleness suggestions emit `ready_command` only when command execution is
  actually possible; deleted source refs are reported as non-recordable.
- `memory-merge` may inherit `evidence:` refs from input memories, but explicit
  `--source evidence:` or `--source conversation:` injection is rejected.

Round 2 hardening then tightened three non-blocking review findings:

- Explicit `conversation:`/`evidence:` source injection is rejected
  case-insensitively for both `memory-consolidate` and `memory-merge`.
- Advisory hook failures are observable as `trace_advisory_error` while still
  never blocking or authorizing the primary command.
- The pressure-derive docstring now matches the intended contract: only
  recordable suggestions carry `ready_command`.

## Verification

- `scripts/test_gate_liveness.py`: 10 regressions covering trace-check
  match/miss, event/open advisories, governance-plane trace registry,
  contradiction derive with real `failed` outcomes, ready command execution,
  duplicate suppression after pressure record, recordable and non-recordable
  staleness, orphan-failure informational output, no-write invariants, and
  observable non-blocking hook errors for invalid governance trace registries.
- `scripts/test_slow_loop.py`: 15 regressions including merge source inheritance
  and case-insensitive explicit evidence/conversation source injection
  rejection.
- Full suite: all 21 test scripts PASS after Codex round 2 hardening, and again
  after the Claude audit-round fix (fullsuite-v5b.log).
- Diff vs deployed v4: +429/-19 in modified files plus the new
  `test_gate_liveness.py` (`barrel-fix-v5.diff`).
- Candidate tree hash (official `tools/evolution_core.tree_hash`, SHA-256):
  `2e3db4f5519f95f7d468442864336ca72b6b58851c3f6dea62018df872791b47`.
  An earlier spec revision recorded a 40-hex non-official hash; deployment receipts
  must use the official tree hash above.

## Claude audit round (post Codex round 2)

- Verified all four Codex round-1 fixes and the round-2 hardening at source level;
  confirmed the production outcome-enum catch was P1-grade (the original derive
  matched an outcome value the CLI never emits).
- Found and fixed one derivation-liveness defect: a contradiction suggestion
  suppressed by an already-recorded active pressure used `continue`, skipping the
  same target's staleness derivation. Restructured control flow; regression
  `test_suppressed_contradiction_does_not_hide_staleness` locks it (gate-liveness
  suite now 11 tests; mechanism suites 26/26).
- Observation (non-blocking): suggestion evidence is capped at 4 refs, so a 5th
  new failure does not resurface a covered contradiction; acceptable because the
  recorded pressure already carries sufficient evidence.
