# Barrel-Fix v2 — Derivation Performance Patchset

Owner-authorized 修木桶 batch 2 (2026-07-07). Scope: the "fake cache" performance cluster —
freshness checks and source resolution whose cost equaled a full rebuild (audit findings
T3/T4/T5/T6/S8/T10). Base: deployed artifact `a1b0cd3d…` (barrel-fix v1).
Codex review round applied directly to this staging tree; Claude independent audit PASS.

## Changes (scripts/weilan_trace.py + references/memory-system.md)

1. **Per-derivation memo layer.** `derivation_memo_scope()` (ContextVar) memoizes scoped
   ledger loads (evidence, promotion, lifecycle, persistence-audit, semantic entries and
   dispositions), frame reads, id lookups, and `source_snapshot` resolution — once per
   read-only derivation. Applied via `@memoized_derivation` to 15 read-only entry points
   (recall, self-project, metabolic contract, governance reduce/show, semantic index
   build/freshness, episode index/search, projection rebuild, retention/conflicts/archive
   listings). Write commands are deliberately NOT scoped, so every write path re-reads
   fresh state (no stale read-after-write). Memoized snapshots are returned as deep copies
   so no caller can mutate the shared cache. Lookup memo keys include the workspace/scope
   hints so hinted and unhinted lookups never share cache entries.
2. **Tiered id lookup.** `find_evidence` / `find_semantic_memory` accept workspace/scope
   hints and search scoped directory → workspace directory → global scan, in that order.
   Wrong hints still resolve through the global tier; unhinted behavior is unchanged.
3. **Scoped frame indexing robustness.** `scoped_frame_paths` memoizes its scan per
   derivation and skips unreadable frame files with a stderr warning only when the first
   frame event proves the file belongs to a different workspace/scope. Current-scope or
   unowned corrupt frames still fail hard.
4. **Bounded listing output.** `evidence-show`, `governance-show`, `prospective-show`,
   `metabolic-transaction-show` gain `--limit` (default newest 20, `0` = unlimited) plus
   total counts and truncated flags; governance targets also cap `transition_history`.
   Transaction listings keep reducer (journal/chronological) order and truncate to the
   newest entries.

## Verification

- New `scripts/test_derivation_performance.py`: 11 regressions (single load per scope,
  warning replay, cross-command read-after-write safety, snapshot mutation safety, hinted
  lookup + global fallback, hinted/unhinted memo separation, foreign-corrupt-frame
  isolation, current-scope corrupt-frame hard failure, transaction listing order, two
  --limit contracts).
- Existing unresolved-conversation fixtures set an empty `WEILAN_CODEX_SESSIONS_HOME`
  so tests do not scan the live Codex session corpus before exercising opaque-source
  behavior.
- Full suite: all 18 test scripts PASS (16 pre-existing + durability + this file);
  independently re-run by Claude after the Codex review round.
- Output equivalence: on a clean copy of the real ledger, `memory-recall`, `self-project`,
  and `episode-search` outputs are byte-identical to the deployed version.
- Benchmark (final audited tree; real ledger + 20x foreign-workspace inflation of
  semantic/evidence planes, 593 files, best-of-N subprocess timing): memory-recall cold
  start 3.38s → 0.61s (**5.5x**), episode-search 1.93x, metabolic-contract 1.18x,
  governance-show parity (1.06x). Honest cost: `self-project` is ~90ms slower (0.54s →
  0.63s, 0.86x, reproducible best-of-7) — the memo layer's constant overhead outweighs
  its savings on this small-state command; accepted as the price of the scan-heavy wins.

## Known semantic deltas (intentional)

- A hinted id lookup that matches in a scoped tier no longer detects a duplicate of the
  same UUID in a *different* workspace (previously a global-uniqueness RuntimeError).
  UUID collision across workspaces is not a real state; global scans still detect
  duplicates when no hint tier matches.
- Show listings default to newest-20 with explicit truncation metadata (was: unbounded);
  transaction listings are journal-ordered instead of id-sorted.

Diff: `barrel-fix-v2.diff` (+699/-123; 9 file diffs including `weilan_trace.py`,
`memory-system.md`, the new derivation test, and test fixture isolation updates).
Candidate tree hash: `cf8553304505c33eea63f3febb310542d392fcb27657c7bd40581876c38da847`.
