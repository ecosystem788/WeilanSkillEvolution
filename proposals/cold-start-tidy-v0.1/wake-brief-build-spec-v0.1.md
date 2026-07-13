# wake_brief build spec v0.1 — the buildable green half

**Author:** Claude (spec gradient). **Date:** 2026-07-10.
**Status:** zero-authority candidate / build contract. Reversible. Nothing here is wired in.
**Depends on:** [`cold-start-diagnostic-v0.1.md`](cold-start-diagnostic-v0.1.md) (the proposal half).
**Double-sign:** proposal Claude 2026-07-10 18:16:40 → 【同意】Codex 2026-07-10 18:16:48.
Codex's 【同意】 carried a cut (cursor integrity bits); this spec **accepts** that cut and
turns it into a build contract. Building is Codex's harness gradient.

This is the "苗圃产物" for the cold-start item: a concrete, testable contract so the build
is reviewable and the two red-zone lines stay pinned. It does not rewire the ritual.

---

## 1. Scope of the buildable half (green)

Two new files, both green (new, reversible, git-revertable), neither importing nor
modifying `weilan_trace.py` internals or the ledger:

1. `proposals/bounded-scheduler-v0.1/impl/wake_brief.py` — a **read-only** aggregator.
2. `proposals/bounded-scheduler-v0.1/impl/wake-cursor.json` — a per-scope tail cursor
   (written by `wake_brief.py`, read by the next wake). This is the ONLY file the tool
   writes, and it is a *convenience* marker, never an authority (see §4).

Out of scope (red — propose-and-queue only, restated from diagnostic §5):
- Editing either wake_prompt to point the ritual at `wake_brief.py`. Until the owner
  does this, the tool is *built and tested but unused* — the honest nursery outcome.
- Any `--brief` flag on `weilan_trace.py` / `memory-recall` itself. Wrap it, don't cage-edit it.

## 2. `wake_brief.py` I/O contract

Invocation (mirrors the recall command's args):
```
python wake_brief.py --workspace "D:\WeilanSkillEvolution" --scope "skill-evolution"
```

Emits **one** JSON object to stdout. Fields:

| field | source | semantics |
|-------|--------|-----------|
| `authority` | `weilan_trace.py memory-recall` | verbatim passthrough of `activation` + `control` + `freshness`, **every `source` ref kept**. The tool does NO authority judgment — it only co-locates. Step 1 stays the agent's call. |
| `owner_inbox_delta` | `owner-inbox.jsonl` − `owner-inbox-processed.jsonl` | **full text** of unprocessed owner messages (id set-difference), most-recent last. Empty list = nothing to answer. |
| `prospective_due` | `weilan_trace.py prospective-show` | only ACTIVE goals whose `not_before` has passed, each with its READY causal events. Drops the historical `causal_events` dump. |
| `codex_replies_unreviewed` | `codex-inbox-replies.jsonl` vs cursor | reply lines whose `reply_to` is past the review cursor. Surfaces the review gradient. |
| `peer_chat_new` | `peer-chat.jsonl` vs cursor | lines appended since the last wake cursor (tail, not whole file). |
| `sources` | all of the above | every ref the briefing was built from, so any load-bearing judgment can re-open the live source. **This is what keeps it lossless.** |
| `cursor_status` | §4 | `"incremental"` (cursor valid, tail-sliced) or `"full_rescan"` + `reason` (cursor missing/stale/failed integrity → whole-file read). Non-fatal; always reported. |

Hard properties:
- **Read-only except `wake-cursor.json`.** No ledger writes, no edits to any inbox/chat file.
- **Lossless.** Nothing dropped, only aggregated + de-duplicated + tail-sliced. Full commands
  and raw files remain available and unchanged; the tool just hands back a delta view *with
  source pointers*. Load-bearing judgment always re-opens the cited source.
- **Degrades safely.** If any sub-step fails (recall non-JSON, missing file, unreadable cursor),
  the tool reports it in-band and falls back to the fuller read, never to silent loss.

## 3. `wake-cursor.json` schema

```json
{
  "schema_version": "wake_cursor_v0.1",
  "scope": "skill-evolution",
  "files": {
    "peer-chat.jsonl":            { "byte_offset": 0, "line_count": 0, "file_size": 0, "content_tail_hash": "" },
    "codex-inbox-replies.jsonl":  { "byte_offset": 0, "line_count": 0, "file_size": 0, "content_tail_hash": "" }
  },
  "updated_at_utc": ""
}
```

Per tracked append-only file, the cursor stores the four integrity bits from Codex's
accepted cut (§4). `updated_at_utc` is written by the tool; do NOT read the machine clock
inside the module under test — accept it as a passed-in / stamped value so the module stays
deterministic and testable (same discipline the workflow scripts use).

## 4. Cursor integrity contract (Codex's accepted cut — the load-bearing half)

A cursor that only remembers "last-seen time" is unsafe: a JSONL file can be truncated,
rotated, or hand-repaired between wakes, and a naive offset would then skip the true tail.
So the cursor carries validation bits and the tool **verifies them before trusting the offset**:

Before incremental read of file `F`, given cursor entry `C` for `F`:
1. `size(F) < C.file_size`  → file shrank → **full rescan**, `reason="file_shrank"`.
2. `C.byte_offset > size(F)` → offset out of bounds → **full rescan**, `reason="offset_oob"`.
3. hash of `F[0 : C.byte_offset]` (or of the last-read prefix window) `!= C.content_tail_hash`
   → the already-read prefix changed underneath us → **full rescan**, `reason="prefix_mismatch"`.
4. `line_count` of `F[0 : C.byte_offset]` `!= C.line_count` → structural drift → **full rescan**,
   `reason="line_count_mismatch"`.
5. all four hold → **incremental**: emit only `F[C.byte_offset : ]`, then advance the cursor.

Rules:
- Any failure ⇒ read the whole file this wake AND set `cursor_status="full_rescan"` with the
  `reason`, so the agent is told the tail was rebuilt (never silently). Then rewrite a fresh
  valid cursor from the full read.
- Missing cursor file ⇒ treat as first wake ⇒ full read, `reason="no_cursor"`. No error.
- The cursor is a **convenience accelerator, not an authority**. Worst case a stale/corrupt
  cursor costs one full re-read — i.e. today's behavior. It can never cause lost information.
  That degradation-to-today is exactly what makes it safe to be cheap.

## 5. Acceptance tests (Codex to write, all offline, no production imports)

Build against in-memory / temp-file fixtures — do **not** import production `weilan_trace.py`
or touch the real ledger; stub `memory-recall` / `prospective-show` output with fixture JSON.

1. **Lossless aggregation** — given fixture recall + inbox + prospective + chat, the emitted
   briefing contains every unprocessed owner message's full text, every unreviewed reply, the
   chat tail, and a `sources` entry for each — no field silently dropped.
2. **8→1 read count** — one `wake_brief` call reproduces the content of the diagnostic's
   steps 2–8 (assert the delta sets match a hand-computed expectation).
3. **Incremental tail** — with a valid cursor, only lines appended after the offset appear in
   `peer_chat_new` / `codex_replies_unreviewed`; `cursor_status=="incremental"`.
4. **Fallback: no cursor** — missing cursor ⇒ full read, `cursor_status=="full_rescan"`,
   `reason=="no_cursor"`, and output equals the whole-file read.
5. **Fallback: each integrity failure** — one test per §4 reason (`file_shrank`, `offset_oob`,
   `prefix_mismatch`, `line_count_mismatch`): corrupt the fixture accordingly, assert full
   rescan + correct `reason` + no tail lost.
6. **Cursor advance** — after an incremental read, the rewritten cursor's bits validate on the
   next call against the unchanged file (idempotent second call yields empty deltas).

Acceptance: reply with (a) new file paths, (b) pytest output verbatim all-green, (c) a
one-line statement of what stays red (wake_prompt rewire; adoption). Do not cross red.

## 6. Session frictions log (owner directive 2026-07-10 18:10, `woke:false`)

> "当前任务也当测试任务，把过程里面没理顺的东西都记下来，回头再慢慢解决，毕竟把我们
> 三方都嵌入微澜，一起合作，是第一回实践。"

Frictions observed while running the three-party (owner + Claude + Codex) loop, logged
for later, not solved here:

- **F1 — inbox diff is hand-done every wake.** The owner/codex inbox id set-difference is
  recomputed by hand each cold-start though `wake.py` already computes it as a count. This
  spec's `wake_brief.py` is the fix-in-progress; noting it as the canonical example of
  "same delta computed twice."
- **F2 — peer-chat is re-read whole every wake.** Append-only, monotonically growing; the
  cursor (§3–4) targets this. Until adopted (red-zone prompt edit), the whole-file re-read
  remains the ritual — the payoff is gated on the owner's button, honestly.
- **F3 — prospective-show returns the full historical `causal_events` dump.** Grows without
  bound; only ACTIVE-due goals + their READY events are load-bearing at wake. `wake_brief`'s
  `prospective_due` filters this, but the raw command still returns everything — a future
  candidate might want a `--due-only` view (would be a red-zone `weilan_trace` change; queue).
- **F4 — two channels, no unified "since last wake" marker.** Owner speaks in the mic
  (authority) and in the tearoom (zero-authority); a wake must read both and keep the
  authority distinction. The briefing keeps them as separate fields on purpose; noting that
  the cursor covers tearoom/replies but the mic delta is already cheap (small files) so it is
  not cursored — a deliberate asymmetry to record, not a bug.
- **F5 — receipt discipline vs. chat rounds.** Chat-experiment rounds still owe a receipt; the
  boundary between "idle chat, short" and "sanctioned work thread" is judged per-round by the
  agent, not marked in the ledger. Worth a future explicit round-type tag so the receipt
  weight is legible rather than re-decided each wake.

None of F1–F5 authorizes a red-zone change. They are the "回头慢慢解决" backlog.

## 7. What this spec deliberately does NOT do

- Does not build anything — it is the contract Codex builds against.
- Does not touch `weilan_trace.py`, the ledger, either wake_prompt, or any authority surface.
- Does not adopt the tool into the ritual — that is the owner's red-zone button. Built-but-unused
  is the correct nursery outcome until then.
