# wake_brief deployed-root false-zero audit v0.1

**Auditor:** Claude bounded wake episode.
**Time:** 2026-07-10 (UTC+9 evening).
**Status:** green-zone audit only. No deployed code, wake prompt, scheduler, or ledger changed.
**Builds on:** `wake-brief-runtime-cursor-permission-observation-v0.1.md` (Codex, 22:00). Same root cause, one severity Codex's note did not surface.

## What Codex found (write side)

Codex ran the deployed `wake_brief.py` and hit
`PermissionError … 'D:\CodexData\skills\solve-with-weilan\scripts\wake-cursor.json.tmp'`,
then correctly fell back to direct reads. Codex's framing: the failure is loud, safe, and
"degrades to the original direct-read path."

## What this audit adds (read side — the dangerous half)

For a wake process that *can* write to the deployed scripts dir, there is **no error**. My brief
this episode returned cleanly with `cursor_status: {"status": "incremental"}` — looks healthy —
but every delta was empty:

```
owner_inbox_delta: []      prospective_due: []
codex_replies_unreviewed: []      peer_chat_new: []
```

Yet the live `impl/peer-chat.jsonl` at that moment held the entire supervised-deployment
conversation (owner 21:42/21:54, Codex 22:00, the four-item read-only re-verification). The brief
saw none of it. This is a **silent false-zero**, not a graceful degradation: the tool reports
"nothing new" while real owner messages and peer chat exist.

The fallback discipline in the wake prompt only triggers on "`cursor_status` 异常或命令失败". Here
`cursor_status` is `incremental` — a healthy-looking value — so the fallback does **not** fire. A
wake that trusts step 1.5 ("一次拿到:话筒新消息…") would silently miss the owner. I only caught the
deployment conversation because wake-prompt step 2 makes me read `impl/` inbox/peer-chat directly as
a backstop.

## Root cause (single, unifying)

`wake_brief.py:331`:

```python
parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
```

`root` is the script's own directory. All file reads (`owner-inbox.jsonl`, `peer-chat.jsonl`,
`codex-inbox-replies.jsonl`) and the cursor write use `root / name` (lines 280, 286–297, 309). In
the `impl/` prototype the script lives beside those files, so the default is correct. **Deployment
copied only the script into a scripts dir that has none of the inbox/chat files** (verified: Glob
for `*inbox*` in the deployed dir returns nothing; `read_jsonl` returns `[]` on a missing file,
`wake_brief.py:25`). The `.claude` entry resolves via junction to the same deployed dir
(`Path(__file__).resolve().parent → D:\CodexData\skills\solve-with-weilan\scripts`), so both entry
points inherit the wrong root.

One cause, two symptoms:
- Codex's process can't write there → loud PermissionError → safe fallback.
- Claude's process can write there → no error → silent empty deltas → **no fallback**.

## Recommended fix direction (supersedes "move the cursor")

Moving only the cursor (Codex's minimal direction) fixes the write symptom but leaves the read side
still pointed at an empty dir. The unifying fix is to **derive `--root` from `--workspace`, not from
`__file__`**, so both reads and the cursor write land on the live, writable inbox dir. Concretely,
default `--root` to the workspace's bounded-scheduler impl anchor
(`<workspace>/proposals/bounded-scheduler-v0.1/impl`) when `--root` is not passed, or make the wake
prompt pass `--root` explicitly. Final choice is a spec decision for the supervised follow-up.

## Guard worth adding regardless of fix

Even after the root fix, a brief that reads a root where the expected inbox files are *absent*
should not present as `incremental`. Consider: if `owner-inbox.jsonl` / `peer-chat.jsonl` do not
exist under `root`, surface `cursor_status.status` as an abnormal value (e.g. `missing_sources`) so
the wake-prompt fallback fires instead of trusting a blind brief. This is the false-zero guard the
brief currently lacks (cf. sibling proposal `false-zero-guard-v0.1`).

## Boundary

Do not patch from an unattended wake. The deployed script and the wake-prompt contract are
project-owner surfaces (red). This audit is the reversible deliverable: diagnosis + fix direction +
guard recommendation. Source edits to the shared `wake_brief.py` should go through the two-sign
procedure; re-deployment and any wake-prompt change require the project owner in a supervised
session.
