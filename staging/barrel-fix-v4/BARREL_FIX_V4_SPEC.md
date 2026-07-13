# Barrel-Fix v4 — Memory 0.8 Slow-Loop Dynamics (Conservation + Reorganization)

Owner-authorized 修木桶 batch 4 (2026-07-07). This is the first mechanism batch: it
implements the theory's center — 受限生成 (bounded generation) — at the method plane.
Per the owner's direction this skips the SE pipeline; correctness is guarded by
Claude↔Codex cross-review instead. Base: barrel-fix-v3 staging (`bc787ade…`, in Codex
review at build time; rebase before deployment if v3 lands amended).

## What the theory demanded and what was missing

《元寂计划》: memory capacity is a finite budget; adding one must take from another —
"真正的零和". 《claude工程方向》: the slow loop's one missing action is bounded-budget
reorganization (merge redundant / split over-mixed / decay). The deployed skill had an
append-only semantic set with an advisory-only retention plan: every entry was an
immortal oligarch. This batch makes conservation binding and gives the LLM (the cohesion
judge, by design) the ledger operations it lacked.

## Mechanism (weilan_trace.py, ~+320 lines)

1. **Binding budget（守恒）.** Per-scope `max_active` head in a new append-only ledger
   `memory/semantic-budgets/workspaces/<wk>/<sk>.jsonl` (`memory-budget-set`, default 100,
   env override `WEILAN_SEMANTIC_BUDGET_DEFAULT`). `enforce_semantic_budget` guards every
   active-set-growing write: consolidate, promote, split, reactivation. At full budget the
   write must name `--displace <memory-id>`; displacement appends a dormant disposition
   (`displaced_by_budget:<new-id>`) — reversible, never deletion (痕迹不灭). Entries the
   same write supersedes count as leaving (a correction at full budget needs no
   displacement). Rejections list the oldest unprotected candidates; `constraint`,
   `open_question`, `critical`-tagged are never suggested (explicit displacement may still
   name them). Entry-first ordering: a crash between entry and displacement leaves a
   visible over-budget state that blocks the next admission — self-signaling, no loss.
2. **memory-merge（合并冗余）.** N≥2 active inputs → one entry superseding all of them,
   inheriting the union of sources — including `evidence:` refs, which do NOT re-pass the
   Promotion Gate (restructuring preserves grounding; the original promotion audit chain
   stays intact through lineage). Records `reorganization: {kind: merge, from: [...]}`.
   Merged summary must have lexical grounding in the inputs. Net active change ≤ −1.
3. **memory-split（崩裂过合）.** One active parent → ≥2 grounded parts. Only the final
   part supersedes the parent, so an interrupted split never deactivates the parent before
   every part is durable. Net growth charges the budget (displacement supported).
4. **Lifecycle closure.** Reorganization entries die with any inherited terminal
   `evidence:` source, exactly like promotion-backed entries (`active_semantic_entries` +
   index dependency state both extended) — no way to launder revoked evidence through a
   merge.
5. **retention-plan** defaults to the scope budget and reports the budget head.

Boundary discipline: no timer, no background loop, no automatic transition — every
dynamic is an explicit foreground command; the LLM judges, the ledger enforces lineage,
budget, and grounding. Authority files, frozen suites, and eval tooling untouched.

## Deployment impact

Real-ledger check: the busiest scope (`skill-evolution`) has 7 active entries against the
default budget of 100 — deployment changes nothing until a scope's budget is deliberately
tightened. The zero-sum experiment the theory demands (does reorganizing memory beat
append-only under a tight budget?) becomes runnable by setting a small budget on a real
working scope.

## Verification

- New `scripts/test_slow_loop.py`: 9 regressions (binding budget + displacement zero-sum,
  supersede-as-leaving, merge lineage/sources/grounding/net-shrink, split grounding +
  final-part parent flip + budget charge, ungrounded-part rejection, reactivation gate,
  merged-entry death on evidence withdrawal, promotion-gate budget rejection with no
  semantic write, append-only budget history).
- Full suite: all 20 test scripts (result recorded below).
- Docs: memory-system.md gains "Conservation and reorganization (Memory 0.8)"; SKILL.md
  gains the budget-response discipline (merge first, displace explicitly, never displace
  constraints silently).

## Codex review round 1 (both P1s fixed)

- P1-1 reactivation race: `command_memory_disposition` now runs entirely inside the
  workspace/scope `contract_fence` (reload, budget check, dispositions, index rebuild in
  one atomic section); regression asserts the fence is held.
- P1-2 budget fail-open: strict `load_semantic_budget_records` fails closed on any bad
  line, wrong schema, workspace/scope identity mismatch, or invalid `max_active` — for
  admission, retention-plan, and budget-set alike. Unterminated torn tails still heal via
  the v1 durability layer (crash damage is not corruption). Four regressions cover both
  Codex probes, forged-identity records, and the torn-tail balance.

## Result record

- Full suite: all 20 test scripts PASS (fullsuite-v4b.log, after the Codex review-round P1 fixes).
- Diff vs v3 base: +459/-8 (barrel-fix-v4-vs-v3.diff).
- Candidate tree hash: `4554ee3e1f7d12354358588cb83a79b342f0c6f3f77ccf35842bed5f4ed6e43f`.
