# Fix Spec — Lineage Poison Repair Revision v0.2

Status: `candidate_diff_audit_passed_awaiting_shadow_authorization`
Date: 2026-07-05
Author: Claude (spec/review role). Design authority delegated by owner: evidence-capture
`75a0c027-e2b2-4de3-9075-a8d989cdb4d3`
(`conversation:e376508a-cf17-4e86-83b6-1e7a0447241b#3e3e0abd-a767-4458-a4fb-a6984a9745bf`).
Codex must not generate the previous `method-state-lineage-graft-v0.1` candidate from this
document as-is. Shadow run, adoption, deployment, and any touch of the live method-state instance
each require separate owner authorization.

Issue: `ISSUE.md` in this directory. Base artifact: deployed Skill `49e656d2…`
(`D:\CodexData\skills\solve-with-weilan`).

## 0. Revision finding — existing frame-repair channel

Codex review on 2026-07-05 found a material missing fact in v0.1: the deployed Skill already has
an append-only frame repair overlay channel.

- `frame-repair` appends `weilan_frame_repair_v0.1` overlays under
  `memory/frame-repairs/<frame_id>.jsonl`.
- `read_events()` applies those overlays before validation.
- `assert_closed_parent()` uses `read_events()`, so a repaired frame can become a valid causal
  parent without rewriting the original frame file.
- Isolated dry-run result: copying live poisoned frame `wf-20260704-145514-4ac09e` into a
  temporary method-state and appending the five missing `trace_emitted` fields through
  `frame-repair` made `validate --require-closed` return `valid: true`.

Therefore, the current live malformed-event instance does **not** prove that a new graft relation
is required. The immediate repair route is an authorized `frame-repair` overlay, not a candidate
Skill change. That live repair still touches `D:\CodexData\home\method-state` and requires a
separate owner authorization.

What remains candidate-worthy:

1. write-path prevention, if any frame append path still bypasses full validation; and
2. an optional graft relation only for poison shapes that `frame-repair` cannot cure, such as
   missing or unreadable frame files.

Candidate v0.1 outcome: Codex generated and froze the write-path prevention candidate only.
Frozen artifact hash: `203b8c1f37ad54abf9e3cdc011ea122a5f8961b26cfd1dea8138549bb997b32c`.
Receipt: `CANDIDATE_FREEZE_RECEIPT.md`.
Live frame-repair also completed after separate owner authorization; receipt:
`LIVE_FRAME_REPAIR_RECEIPT.md`.
Diff audit passed; receipt: `CODEX_DIFF_AUDIT.md`.

## 1. Design decision

**Revised holder: repair current live poison with existing `frame-repair`; do not hand off graft
v0.1 as the immediate fix.**

Direction (b) lineage graft remains a plausible broader repair channel for missing/unreadable
frames, but it is no longer justified as necessary for the verified live malformed-event instance.
Any graft candidate must be redrafted as a separate, narrower proposal whose motivating tests
cover poison shapes that cannot be repaired by `frame-repair`.

Prevention remains relevant: candidate work may still tighten frame write paths if a bypass is
verified.

### Superseded v0.1 decision

Direction (a) void-isolation is rejected for v0.1, for two verified reasons:

1. **Void does not guarantee cure.** The live poison is the frame's only `trace_emitted`; the
   frame contains `minimal_unit_collapsed`-adjacent structure in the general case, and
   `validate_events` has structural rules ("collapse requires a following trace_emitted",
   probation resolution, closure ordering). Skipping a voided event can leave the frame invalid
   for a *different* reason. Graft cures any poison — unreadable file, missing file, structural
   invalidity — because it routes around the frame instead of re-litigating its contents.
2. **Smaller blast radius.** Void changes `validate_events` semantics for every consumer
   (audits, eval scoring, persistence checks). Graft is confined to the lineage plane: one new
   relation in the open path and the reducer; frame-event validation stays byte-identical.

Core principle preserved: never rewrite history; dispose by appending. For the current live
instance, the append-only disposition mechanism already exists as `frame-repair`.

## 2. Change A — `graft` causal relation (repair channel)

All references: `scripts/weilan_trace.py` at base `49e656d2…`.

### CLI surface

If a future graft candidate is authorized, the existing CLI surface is `open`, not
`open-lineaged`. With `--scope`, `open` routes into the lineaged open path. A future graft command
would therefore look like:

```
weilan_trace.py open --relation graft --branch <branch> --parent <valid-ancestor> \
  --graft-reason "<why the head is being bypassed>" --graft-evidence <ref> [--graft-evidence <ref> ...] \
  --problem ... --success ... --level ... --workspace ... --scope ...
```

### Preconditions (all enforced in `command_open_lineaged_fenced`, inside the existing lock)

1. Branch exists and is `active`.
2. The current branch head **fails** `assert_closed_parent` (missing/unreadable frame file counts
   as failure). Graft on a healthy head is rejected — this is the load-bearing guard against
   history evasion. The captured validation errors are recorded in the graft record as
   `bypassed_head_errors`.
3. Exactly one `--parent`; it **passes** `assert_closed_parent`.
4. The declared parent is a recorded parent of the bypassed head **according to the lineage
   records** (`derive_lineage_state`'s `frames[head]["parent_frame_ids"]`), never according to
   the poisoned frame file itself (which may be unreadable). v0.1 bypasses exactly one frame
   (the head); multi-hop bypass is out of scope — if the parent is also poisoned, graft fails
   (documented limitation).
5. `--graft-reason` non-empty; at least one `--graft-evidence` ref.

### Record shape

Graft lineage records and the frame's `causal` metadata carry, in addition to the existing
fields: `relation: "graft"`, `parent_frame_ids: [<anchor>]`, `bypassed_frame_ids: [<head>]`,
`graft_reason`, `graft_evidence`, `bypassed_head_errors`.

### Reducer (`derive_lineage_state`) rules for `graft`

- branch exists and is active; exactly one parent; `bypassed_frame_ids` is exactly
  `[current head_frame_id]`; parent is a recorded parent of that head per the `frames` map.
- After acceptance: branch head becomes the graft frame; the bypassed frame remains in `frames`
  (history is not erased).
- `lineage-show` output must surface bypassed frames with reason and evidence.

### Schema versioning — critical compatibility constraint

New lineage records are written as `weilan_frame_lineage_v0.5`. **Every reader must accept both
v0.4 and v0.5**: `load_lineage_records`' schema check, `validate_events`' causal
`schema_version` check, and `command_lineage_show`'s consistency checks. A single-constant bump
that rejects v0.4 would invalidate every pre-existing frame and ledger — reproducing the exact
defect this fix removes. Heads file version may bump analogously (`…heads_v0.5`) since heads are
derived and rebuildable.

## 3. Candidate Change B — write-path enforcement (prevention)

Every code path that appends an event to a **frame** file must run the event through
`validate_event_required_fields` (plus `ALLOWED_EVENTS` / `ALLOWED_LEVELS` / schema-version
checks) before `append_event`, and refuse with a clear error on failure — nothing is written.
Codex must enumerate all frame-event append sites in `weilan_trace.py` (the live poison entered
through one of them: a `trace_emitted` written with a stray positional key and none of the five
required fields). Lineage-record and evidence-record appends are out of scope for v0.1.

Important implementation boundary: `append_event` is a shared low-level writer used by non-frame
ledgers. Do not globally apply frame-event validation inside `append_event`; validate only the
frame-event append paths or introduce a frame-specific append helper.

Prevention does not cure the already-written live poison; existing `frame-repair` is the current
live repair route. Prevention can ship by itself if its candidate scope is limited to write-path
hardening.

## 4. Budgets and constraints

- `max_changed_files`: 3 — (1) `scripts/weilan_trace.py`, (2) one test file, (3) optionally one
  doc touch (`SKILL.md` or the relevant `references/` file). No other file may change.
- `max_candidate_generations`: 2.
- Anti-Goodhart: no weakening of any existing validation rule or gate trigger; no case ids,
  fixture paths, or suite names from frozen suites anywhere in the diff. If graft is redrafted,
  it must be impossible on a healthy head (precondition 2 is non-negotiable).
- Candidate authority: proposal and instruction only — never evaluation, adoption, deployment,
  or rollback authority. Candidate must not touch `evals/`, `ROADMAP.md`,
  `EVALUATION_POLICY.md`, `ARCHITECTURE.md`, or `evals/manifest.json`.

## 5. Required candidate tests before any freeze

First decide which route is authorized:

- **Immediate live repair only:** no candidate generation. Required proof is an isolated
  `frame-repair` dry-run plus a separately authorized live repair receipt.
- **Write-path prevention candidate:** required tests must prove malformed frame events cannot be
  appended by every frame-event write path, without changing non-frame ledgers.
- **Optional graft candidate:** required tests must use poison shapes that existing `frame-repair`
  cannot cure, and must retain the v0.4/v0.5 schema compatibility constraints below.

Superseded graft-v0.1 tests, retained only as prompts if a graft candidate is explicitly redrafted
for non-repairable poison:

1. Graft rejected when the branch head is valid.
2. Graft rejected when the declared parent is not a recorded parent of the head.
3. Graft rejected when the declared parent itself fails validation.
4. Graft succeeds on a synthesized poisoned head that existing `frame-repair` cannot cure, such
   as a missing or unreadable head frame file; a subsequent `continue` from the graft frame
   succeeds; the heads file reflects the new head.
5. `lineage-show` reports the bypassed frame with reason, evidence, and captured errors.
6. Write-path: emitting a `trace_emitted` missing required fields fails and appends nothing
   (file unchanged byte-for-byte).
7. Mixed-version regression: pre-existing v0.4 lineage records and v0.4 frames validate cleanly
   under the new code, including `assert_closed_parent` on a v0.4 parent.
8. The full existing skill test suite passes unchanged.

## 6. Evaluation and sequencing

1. Do **not** generate the graft candidate from the superseded v0.1 handoff.
2. For the current live instance, owner may separately authorize one `frame-repair` overlay on
   `wf-20260704-145514-4ac09e` targeting event
   `1828a13b-03cb-4eae-9ea2-adf797804352`, supplying the five required `trace_emitted` fields.
   That repair should be verified by `validate --require-closed`, then by a `continue` smoke test
   only if the owner authorizes touching the live lineage.
3. If prevention or graft is still desired, Codex generates a revised candidate under
   `candidate/solve-with-weilan/`, freezes a
   content-addressed artifact, runs the tests in §5.
4. Claude diff audit (additions-only where possible, forbidden-token scan, hash recomputation,
   §4 constraints).
5. Owner authorizes a **full-suite non-regression shadow**: `se-seed-v0.1` +
   `fusion-dogfood-v0.1` against deployed `49e656d2…`. Declared upfront: this is a tooling
   repair — expected evidence is **non-regression only**, no `method_impact_count` claim, no
   SE-0.7 improvement claim. The v0.1 suite's saturation (|H| = 1) is not an obstacle here: at
   the ceiling, non-regression is the strictest available gate. Side benefit: this shadow
   produces fresh full-suite data on the deployed baseline, which is exactly what ROADMAP item 3
   says is the cheapest way to settle open risk F2 (`paused_scope_mutated` on
   memory-cross-window).
6. Sequence **before** successor v0.2 (which is blocked on fusion-dogfood-v0.2 redesign anyway):
   a separate proposal keeps the tooling repair out of the method-improvement measurement, and
   v0.2 then builds on a repaired base while the fusion-program scope stops accruing lineage-less
   frames.
7. The two standalone frames (`wf-20260705-003116-946812`,
   `wf-20260705-032827-46ec05`) remain standalone history under either live repair or future
   graft; new lineaged work may continue from the repaired head only after separate authorization.

## 7. Non-goals

Multi-hop bypass; void/disposition semantics for frame events generally (revisit only if a
poison shape appears that graft cannot route around); any hand-edit of
`D:\CodexData\home\method-state`.
