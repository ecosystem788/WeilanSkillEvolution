# Barrel-Fix v3 — Skill Depollution + Remaining Robustness Staves

Owner-authorized 修木桶 batch 3 (2026-07-07). Two halves: (A) delete evaluation-fixture
overfitting from the skill's instruction surface (owner decision: delete outright, not
quarantine — a quarantined reference would be the renamed-holder revival the constitution
forbids); (B) the remaining small engineering staves from the original audits.
Base: deployed artifact `cf855330…` (barrel-fix v2).

## A. Instruction depollution (SKILL.md 179 → 164 lines; memory-system.md trimmed)

Deleted outright (pure fixture corpses): the `parcel-route-evolution` exact-scope rule;
the 16-call L2 contract block; the event-ingestion store API paragraph
(`open_store`/`ingest_batch`/64-event batches); `recovery.json` exact key lists and
`attempts/attempt-01.log` literals; `latency_p95_ms`-style example keys; the route-planning
cost-formula paragraph; the literal `STALE` token + SHA-256 receipt protocol; the
12/14/40-call numeric budget contracts (also in memory-system.md).

Kept and generalized: budget discipline (front-load, batch, reserve for verification,
divide multi-stage budgets evenly, stop after passing verification); preserve caller keys
and values exactly; reuse the task's named scope; make staleness observable; untrusted-data
validation; CLI `main(argv)` conventions; machine-shaped trace artifacts; regroup under a
genuinely changed assumption.

Accepted consequence (recorded, not a surprise): frozen-suite cases that those clauses
were written for (se-seed v0.1 / fusion-dogfood v0.1) may score lower on replay; that
measures memorization, not a real capability regression. fusion-dogfood v0.1 is already
saturated (|H| = 1) and awaiting the v0.2 extension.

## B. Engineering fixes

1. **archive-plan fails closed** (`weilan_trace.py`): reference-ledger corruption warnings
   are collected, and any corruption blocks the eligibility list entirely (exit 1,
   `planning_blocked`); an unreadable frame shard is listed as blocked, never eligible.
2. **Typed conflicts** (`transaction.py`, `runner.py`, `weilan_trace.py`): new
   `ContractConflict(ValueError)` raised for `idempotency_conflict`,
   `contract_head_changed`, and prepared-contract mismatch; the runner classifies stops by
   exception type first, message tokens as fallback — rewording can no longer terminalize
   a retryable conflict as `INVALID_EVENT`.
3. **Resumed-claim control gate** (`runner.py`): when a resumed materialization is
   rejected before any durable write (`NOT_STARTED`) and the contract status is
   paused/blocked, the run stops with the true reason (`CONTROL_BLOCKED` etc.) instead of
   a false terminal `INVALID_EVENT`.
4. **Windows lock timeout** (`runtime_core.py`, `transaction.py`): contended fences retry
   to a configurable deadline (`WEILAN_LOCK_TIMEOUT_S`, default 120s) and then raise
   "lock timeout on <name>; another weilan session holds it" instead of bare EACCES.
5. **Atomic replace retry** (`runtime_core.py`): `write_json_atomic` retries `os.replace`
   through transient Windows share-violation `PermissionError`; post-commit derived-view
   refresh failures no longer report a durable commit as a failed command
   (`refresh_deferred` marker instead).
6. **Legacy `open` canonicalizes the workspace** before writing the frame event, so frame
   identity and fences are stable across CWDs; removed the dead `ACTIVATION_STATES`.
7. **No corpus-wide conversation fallback**: session resolution requires the thread id in
   the session filename; the rglob-everything fallback is gone (worst-case latency bounded).

## Verification

- New `scripts/test_v3_robustness.py`: 8 regressions (fail-closed archive plan ×2,
  resumed-claim pause reason, reworded-conflict classification, legacy-open
  canonicalization, no-fallback conversation resolution, contended-lock timeout,
  atomic-replace retry).
- Full suite: all 19 test scripts PASS.
- Fixture-token scan over SKILL.md + references/: clean.
- `memory-recall` on a clean real-ledger copy: byte-identical to deployed v2.

Diff: `barrel-fix-v3.diff` (+176/−52; SKILL.md, memory-system.md, weilan_trace.py,
transaction.py, runner.py, runtime_core.py, plus the new robustness test file).
Candidate tree hash: `bc787ade263a82dc054d0d92724b4ecc106c3b2c949fb62588a97fee70704c85`.
