# Barrel-Fix v1 — Ledger Durability Patchset

Owner-authorized direct deployment (修木桶 mode, 2026-07-07). Scope: six ledger-durability
short staves in the deployed solve-with-weilan skill, plus two P1 corrections from Codex review.

## Fixes

1. **Torn-tail self-healing (never truncate).** All three appenders
   (`weilan_trace.append_event`, `transaction.append_jsonl`, `runner.append_jsonl`) seal an
   unterminated trailing fragment before writing: the fragment's byte identity
   (offset, length, SHA-256, preview) goes to an append-only `<ledger>.torn` quarantine
   sidecar, then one newline isolates the fragment. Readers skip only (a) the unterminated
   final physical line and (b) terminated lines whose exact byte range is quarantined.
2. **Governance validate-before-append.** `append_governance_event` replays
   `records + [event]` under the lock before writing; a losing concurrent writer is rejected
   without persisting an invalid replay (mirrors the prospective writer).
3. **Promotion/consolidation fencing.** `evidence-promote` and `memory-consolidate` hold the
   workspace/scope `contract_fence`, closing the check-then-append race that could violate
   "one evidence fragment cannot be promoted twice" and permanently block frame close.
4. **Staging fencing.** `prepare_transaction` and `recover_transaction` stage pending
   envelopes under `staging_fence` (contract fence → transaction lock, same order as COMMIT),
   serializing participant-ledger appends against direct writers.
5. **Case-insensitive ledger identity.** Transaction/runner replay compares raw
   workspace/scope casefolded; a differently-cased `--scope` no longer wedges the journal.
6. **Blast-radius isolation.** A corrupt transaction journal no longer fails every frame and
   ledger read in the workspace: pending envelopes stay hidden (same conservative semantics
   as uncommitted) with one process-level stderr warning; per-envelope integrity failures
   remain hard errors.

## Codex review corrections (P1)

- Readers parse ledger bytes with **strict UTF-8 per line** (no `errors="replace"` laundering
  of terminated invalid-UTF-8 lines into committed data).
- Quarantine matching is **byte-range identity** (offset + length + SHA-256), never fragment
  text, so an unrelated identical-text bad line can never be silently suppressed.

## Verification (all green before deployment)

- `scripts/test_ledger_durability.py`: 11 regression tests (new), including the two Codex probes.
- All 16 pre-existing test scripts pass (`test_transaction.py` ~83s).
- CLI smoke: open → event → persistence-audit → close → validate → memory-recall, then a
  live torn tail injected into the frame file; validate/open/recall unaffected.
- Reference docs (`memory-system.md`, `transaction-system.md`) updated to match behavior.

Diff: `barrel-fix-v1.diff` (+277/−74; 4 files changed, 1 test file added).
