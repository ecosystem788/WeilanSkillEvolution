# Cold-start diagnostic v0.1 — "lossless but lighter"

**Author:** Claude (spec/audit gradient)
**Date:** 2026-07-10
**Status:** zero-authority candidate / draft. Reversible. Nothing here is wired in.
**Owner directive (tearoom 2026-07-10 18:03, `woke:false`):** "把你们的冷启动流程梳理
一下吧，看看怎么能既不丢失信息，又能够负担轻一点。这个记到下一个事情吧。"
Both peers recorded it as the item *after* the witness thread closes. The witness
thread's reversible surface is now closed (append-order prototype landed; remaining
defenses are red-zone/schema), so this opens that queued item with a diagnostic —
not an implementation.

---

## 1. What "cold-start" actually is today

Every wake the agent (Claude or Codex) runs the same opening ritual, defined in the
wake prompt + `CLAUDE.md`. Measured against the current prompt, one cold-start
performs **~8 distinct reads before any work begins**:

| # | Step | Source | Cost | Kind |
|---|------|--------|------|------|
| 1 | `memory-recall` | `weilan_trace.py memory-recall` | large JSON (projection + full `source_snapshots` + full `decisions` list + control + freshness) | **load-bearing** authority check |
| 2 | Read owner-inbox | `owner-inbox.jsonl` | full file | mechanical delta |
| 3 | Read owner-inbox-processed | `owner-inbox-processed.jsonl` | full file | mechanical delta |
| 3b| Diff 2 vs 3 by hand | (in-head) | id set-difference | mechanical |
| 4 | `prospective-show` | `weilan_trace.py prospective-show` | full JSON incl. **entire growing `causal_events` history** | mostly noise |
| 5 | Read current goal | projection `focus`/`next_action` + recent unclosed frame | re-parse of #1 | derived |
| 6 | Read peer-chat | `peer-chat.jsonl` | **entire file, re-read every wake** | mechanical delta |
| 7 | Read codex-inbox | `codex-inbox.jsonl` | full file | mechanical delta |
| 8 | Read codex-inbox-replies | `codex-inbox-replies.jsonl` | full file | mechanical delta (review gradient) |

Then work; then a 3-step receipt (`open` → `persistence-audit` → `close`).

## 2. The load-bearing vs. the mechanical

Exactly **one** of these is genuinely load-bearing and must stay in the agent's own
judgment: **step 1's authority check** — `activation.state`, `continuation_allowed`,
the control directive, and freshness. The 真源纪律 says the projection is
`derived_projection_verify_against_current_sources`; the agent must look at this and
decide whether it is even allowed to continue. That judgment cannot be delegated to a
wrapper. Keep it exactly as is.

Everything else (steps 2–8) is **mechanical delta-gathering**: "what changed since my
last wake?" — new owner messages, due prospective goals, new peer-chat lines,
unreviewed codex replies. None of it needs judgment to *collect*; it needs judgment
only to *act on*. Today the agent collects it by hand, reading 6 full files and one
oversized JSON, most of whose bytes are unchanged since last wake.

## 3. The redundancy already sitting in the repo

`wake.py` (the machine heartbeat) **already computes almost all of these signals**:
`briefing()` returns `activation_state`, `continuation_allowed`, `head_frame`,
`focus`, `next_action`, `open_questions`, `control_directive_present`;
`owner_inbox_pending()` and `codex_inbox_pending()` compute the id set-differences;
`check_prospective_clock()` filters to ACTIVE clock goals whose `not_before` has
passed. The heartbeat does the diffing — then throws away everything but a **count**.
The agent then re-derives the same diffs from raw files by hand.

So the waste is not "too much information." It is **the same delta computed twice**
(once by the heartbeat as a count, once by the agent as content) and **full re-reads
of files that are append-only** (peer-chat, both inboxes, replies) where only the tail
since the last wake is new.

## 4. Proposed lossless-lightening: one read-only `wake-brief` wrapper

A **new, independent, read-only** helper (green-zone) that the agent runs **once** at
cold-start in place of steps 2–8. It does no judgment and writes nothing; it only
aggregates what the agent would otherwise gather by hand, and emits one consolidated
briefing containing **content, not just counts**:

```
python wake_brief.py --workspace ... --scope ...
```

Emits (single JSON):
- **`authority`** — verbatim passthrough of `memory-recall`'s `activation` + `control`
  + `freshness` blocks, with every `source` ref included so the agent can still verify
  against live sources. (Step 1 stays the agent's call; the wrapper just co-locates it.)
- **`owner_inbox_delta`** — the *full text* of unprocessed owner messages (inbox ids −
  processed ids), not a count. Empty list = nothing to answer.
- **`prospective_due`** — only ACTIVE goals whose `not_before` has passed **and** their
  READY causal events; drops the entire historical `causal_events` dump.
- **`codex_replies_unreviewed`** — reply lines whose `reply_to` is not yet marked
  reviewed (needs a small review-cursor, see §6). This is the review gradient surfaced.
- **`peer_chat_new`** — peer-chat lines appended since the last wake cursor (§6), so the
  agent reads the tail, not the whole growing file.
- **`sources`** — every ref the briefing was built from, so any load-bearing judgment
  can re-open the live source. **This is what keeps it lossless.**

### Why this is lossless

Nothing is dropped — only **aggregated and de-duplicated**. The full commands
(`memory-recall`, `prospective-show`) and raw files remain available and unchanged;
the wrapper just calls them and hands back a tail-sliced, delta-only view *with source
pointers*. Any time the agent's judgment is load-bearing, it re-opens the cited source.
The lightening is real (8 reads → 1 call; no full re-reads of append-only files; no
historical causal-event dump); the information is not.

## 5. The green/red boundary (hard)

- **GREEN — buildable by us under the self-modification clause (double-sign):**
  - `wake_brief.py` as a **new** independent script. It only *calls* existing read-only
    commands and *reads* existing files. It does **not** import, modify, or wrap the
    internals of `weilan_trace.py`, and it writes nothing to the ledger.
  - A per-scope **cursor file** (§6) — a new file, green.
- **RED — owner's button, propose-and-queue only:**
  - **Editing the wake prompt** to point the agent at `wake_brief.py`. The two
    wake_prompt texts are explicitly red zone ("不改自己的笼子"). Until the owner edits
    the prompt, the wrapper is *available* but the ritual still says read-by-hand — so
    the wrapper only pays off once the owner adopts it. This diagnostic proposes; it
    does not rewire.
  - Any `--brief` flag **on `weilan_trace.py` / `memory-recall` itself** — that is the
    caged tool. Do not touch it; wrap it instead.

## 6. The one new mechanism needed: a wake cursor

To read "peer-chat since last wake" and "codex replies not yet reviewed" without
re-reading whole files, the wrapper needs a tiny **cursor file** per scope, e.g.
`impl/wake-cursor.json`: last-seen peer-chat line time, last-reviewed codex-reply
id. Green (new file, reversible). Note the honest caveat: a cursor is a *convenience*
tail-marker, **not** an authority — if it is ever stale or missing, the wrapper falls
back to reading the whole file, so a lost cursor degrades to today's behavior, never
to lost information. That fallback is what makes the cursor safe to be cheap.

## 7. What this diagnostic deliberately does NOT claim

- It does not touch `weilan_trace.py`, the ledger, the wake prompt, or any authority
  surface. Draft only; fully reversible.
- It does not delegate implementation yet. `wake_brief.py` is Codex's harness gradient;
  before it is built it should go through the double-sign clause (proposal → the other
  peer's explicit 【同意】 → build → verify → commit). This file is the proposal half.
- The payoff is **conditional on a red-zone step** (owner editing the wake prompt to
  adopt the wrapper). Building the wrapper without that step produces a correct,
  tested, *unused* tool. That is honest and fine — it is the nursery pattern: produce
  the artifact, let the owner decide adoption at the red boundary.

## 8. Recommended next step (single, reversible)

Post this direction to the tearoom for Codex's double-review. If Codex signs 【同意】,
the buildable green half is: prototype `wake_brief.py` + `wake-cursor.json` as an
independent module with tests, proving the 8-reads→1-call aggregation is lossless
(every source ref preserved, cursor fallback safe). Adoption into the actual ritual
stays queued for the owner's button.
