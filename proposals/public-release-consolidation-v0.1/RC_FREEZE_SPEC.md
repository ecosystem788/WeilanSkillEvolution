# RC freeze specification v2 — dual-signed (2026-07-17)

Status: DUAL-SIGNED / Claude 【提案】 2026-07-17 01:03:27 + Codex 【同意】
2026-07-17 01:12:11. This v2 supersedes the checkout-byte assumption that
failed at Codex receipt 2026-07-17 00:56:44 while preserving the failed
`aa68fa6` commit as forensic evidence. This document defines the
procedure that closes R14 ("freeze the exact candidate and rerun all checks
without byte drift") and clears the R13 freeze-time-rebind condition in
`RELEASE_ACCEPTANCE_MATRIX.md`. The v2 freeze executes only under the cited
dual-sign in `peer-chat.jsonl`.

## What "freeze" means here

Pin the exact 62-file release surface (14 proposal-allowlist files +
48 `skill/solve-with-weilan` payload files, as enumerated by
`release_candidate_hygiene.expected_candidate_paths`) into a single local git
commit, then prove that the *committed* tree — not the dirty working tree —
passes every existing check with byte-identical hashes.

Freeze is NOT: push, tag-on-remote, adoption, deployment, or publication.
R16 remains BLOCKED BY POLICY (owner veto 2026-07-16 20:04:36: no push until
the release is complete and separately authorized). Freeze is a local,
reversible commit.

## Preconditions (all currently satisfied — verify again at execution)

1. R13 landed and cross-verified: root `LICENSE` and payload
   `skill/solve-with-weilan/LICENSE` both sha256
   `0193cdbacc8174c2af478e8de69bd919a6b36edd7fbd039bd82d83e280aed4e1`.
2. Hygiene: PASS, 62 files, 0 missing, 0 findings, tree_sha256
   `2898e5a76f334a96a7df6d730478baf4eb7bd715d40d7a3746aaafa46a893f49`
   (receipts: `tmp/r13-license-hygiene.json`,
   `tmp/codex-r13-independent-hygiene.json`).
3. Test suite: 26 passed + 9 subtests, reproduced independently by both
   members on 2026-07-17.
4. No open revision proposal against any of the 62 files.
5. Every one of the 62 candidate paths plus the five release evidence paths
   listed in Step 1 is covered by an explicit `eol=lf` Git attribute. Verify
   all 67 paths with `git check-attr eol` before creating the freeze commit.
   Root `LICENSE`, payload `LICENSE`, and `setup.ps1` are covered by the
   repository rules `LICENSE text eol=lf` and `*.ps1 text eol=lf`.

## Procedure

### Step 1 — enumerate and stage exactly the release surface

Run `expected_candidate_paths` (or `release_candidate_hygiene.py`) to get the
current 62-path allowlist. `git add` exactly those 62 paths, plus the
release evidence documents that describe the candidate
(`RELEASE_ACCEPTANCE_MATRIX.md`, `R2_INDEPENDENT_REVIEW.md`,
`LICENSE_DECISION_PACKET_PROPOSAL.md`, `RC_FREEZE_SPEC.md`, root `LICENSE`).
Nothing else: no ledgers, inboxes, chats, cursors, logs, wake runs, `tmp/`,
`wake-agent-runs/`, `agent-output/` (per `RELEASE_WORKTREE_INVENTORY.md`
freeze rules). Coordination-trail files continue to be preserved by the usual
separate trail commits, never in the freeze commit.

### Step 2 — freeze commit

One new local commit after the preserved failed `aa68fa6` forensic anchor,
containing only `.gitattributes` and this specification, message
`release: pin RC1 checkout bytes to LF`. Record
`freeze_commit` = commit sha, `freeze_git_tree` = `git rev-parse HEAD^{tree}`.
No push.

### Step 3 — zero-drift verification from the frozen anchor

In a temporary `git worktree add <tmpdir> <freeze_commit>` checkout:

1. Re-run `git check-attr eol` for the same 62 candidate paths plus five
   evidence paths from inside the checkout; every path must report `eol: lf`.
2. Run `release_candidate_hygiene.py --repo-root <tmpdir>` → must report
   PASS, 62 files, 0 missing, 0 findings, and tree_sha256 exactly
   `2898e5a7…` (byte identity with the working tree at freeze time).
3. Run the full 26-test candidate suite from the checkout → 26 passed
   (+9 subtests).
4. Re-verify both LICENSE copies hash to `0193cdba…`.

Any mismatch = freeze FAILED: remove the worktree, leave the commit for
forensics, report in peer-chat, do not update the matrix.

### Step 4 — bind receipts (separate follow-up commit)

Write `FREEZE_RECEIPT.json` next to this spec:
`{schema: weilan_rc_freeze_receipt_v0.1, freeze_commit, freeze_git_tree,
hygiene_tree_sha256, license_sha256, test_summary, verification_worktree
evidence paths, dual_sign: {proposal_time, consent_time}, executed_at}`.
Then update `RELEASE_ACCEPTANCE_MATRIX.md`: R2 rebound to the frozen tree,
R13 → `PASS (bound to freeze commit <sha>)`, R14 → `PASS for frozen RC1`.
Receipt + matrix update go in a second commit (`release: bind RC1 freeze
receipt`) — the freeze commit must not contain its own receipt (self-hash).

### Step 5 — drift rule (standing, part of this dual-sign)

After freeze, any byte change to any of the 62 files invalidates R13/R14 for
the release line: the change requires a new freeze (repeat Steps 1–4, new
receipt, old receipt preserved). Signatures never survive drift.

## Rollback

Local commits only: `git revert` (or reset before anything builds on top),
delete `FREEZE_RECEIPT.json` via a revert commit, matrix rows return to their
pre-freeze text. Nothing leaves the machine, so rollback is complete.

## What freeze does not close

R8 (real dashboard smoke), R9 (concurrency/power-loss fault injection on the
frozen RC), R11 (unfamiliar-reviewer run), R12 (genuinely clean Windows
≤10-minute run), R15 (independent final audit), R16 (publication — owner
authorization required). These proceed against the frozen RC afterwards.
