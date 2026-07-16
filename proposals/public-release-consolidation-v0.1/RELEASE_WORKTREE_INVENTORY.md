# Release worktree inventory — 2026-07-16 00:27 +09:00

Status: read-only classification of the current local tree. This inventory does
not authorize deletion, cleanup, adoption, deployment, publication, or changes
to `ROADMAP.md`, `ARCHITECTURE.md`, or `EVALUATION_POLICY.md`.

## Snapshot

- Branch: `codex/se-0.4-0.7-program`
- HEAD: `1a212a7c0d0937629a62481900b99a2b5e6b5824`
- Relative to `origin/main`: 28 commits ahead, 0 behind
- Tracked modifications: 23 files
- Untracked files reported by `git status --untracked-files=all`: 592
- Root `README.md` and `LICENSE` exist and are tracked. There is no root
  `setup.ps1`; the current setup entry is an untracked release candidate under
  this proposal.

Counts describe this instant only. Append-only ledgers, cursors, logs, and wake
receipts continue to move and must be re-inventoried before a release freeze.

## Tracked modifications

### Candidate runtime source and focused tests — 11

These are possible release inputs or validation code, not automatically
approved release source:

- `proposals/bounded-scheduler-v0.1/impl/launch_observe.py`
- `proposals/bounded-scheduler-v0.1/impl/observe.py`
- `proposals/bounded-scheduler-v0.1/impl/run_wake_cron.ps1`
- `proposals/bounded-scheduler-v0.1/impl/wake.py`
- `proposals/bounded-scheduler-v0.1/impl/wake_agent.ps1`
- `proposals/bounded-scheduler-v0.1/impl/wake_brief.py`
- `proposals/bounded-scheduler-v0.1/impl/test_launch_observe.py`
- `proposals/bounded-scheduler-v0.1/impl/test_observe.py`
- `proposals/bounded-scheduler-v0.1/impl/test_wake_sentinel.py`
- `proposals/mutual-aid-v0.1/peer_health_wake.py`
- `proposals/mutual-aid-v0.1/test_peer_health_wake.py`

### Coordination and replaceable current state — 7

These are live operational state or append-only community records. They are
evidence/state inputs, not files to copy blindly into a release payload:

- `proposals/bounded-scheduler-v0.1/impl/codex-inbox-processed.jsonl`
- `proposals/bounded-scheduler-v0.1/impl/codex-inbox-replies.jsonl`
- `proposals/bounded-scheduler-v0.1/impl/codex-inbox.jsonl`
- `proposals/bounded-scheduler-v0.1/impl/concurrent-receipts.jsonl`
- `proposals/bounded-scheduler-v0.1/impl/peer-chat.jsonl`
- `proposals/bounded-scheduler-v0.1/impl/wake-cursor.json`
- `proposals/bounded-scheduler-v0.1/impl/wake-cursor.prev.json`

### Local runtime output — 5

These are machine-local logs or run receipts and are not release source:

- `proposals/bounded-scheduler-v0.1/impl/observe-server.log`
- `proposals/bounded-scheduler-v0.1/impl/wake-agent-runs/2026-07-14T14-29-21.json`
- `proposals/bounded-scheduler-v0.1/impl/wake-agent.log`
- `proposals/bounded-scheduler-v0.1/impl/wake-codex.log`
- `proposals/bounded-scheduler-v0.1/impl/wake-cron.log`

## Untracked inventory

### Bounded scheduler operational trail — 568

- `wake-agent-runs/`: 550 run JSON/error files; local execution evidence.
- `tmp/`: 15 probes and message/argument fixtures; temporary validation
  material.
- Proposal root: 3 files — empty `PAUSED` sentinel, `chat_append.py`, and
  `test_wake_recovery.py`. The latter two require review before any release
  inclusion; the sentinel is host control state, not payload.

### Public-release candidate — 14

- `INSTALL_OWNERSHIP_RECEIPT.json`
- `OPERATION_CARD.md`
- `README.md`
- `RUNTIME_DEPLOYABILITY_RECEIPT.json`
- `TROUBLESHOOTING.md`
- `clean_home_rehearsal.py`
- `install-manifest.json`
- `release_candidate_hygiene.py`
- `release_installer.py`
- `setup.ps1`
- `test_clean_home_rehearsal.py`
- `test_release_candidate_hygiene.py`
- `test_release_installer.py`
- `verify_release_candidate.py`

The same proposal directory has 8 tracked evidence/source files. Therefore the
current proposal surface is 22 files, including 14 code-owned candidate files
that are currently untracked. The candidate hygiene scanner evaluates these 14
files plus the 47 manifest payload files, for a 61-file release surface.

### Other candidate or evidence groups — 17

- Parse diagnostic proposal: 3 files.
- Wake-brief EOL candidate/rollback: 3 files.
- Release-inclusion temporary inputs and hash lists under `tmp/`: 9 files.
- Unrelated `agent-output/` reports: 2 files.

These groups must remain outside the release candidate unless a later freeze
manifest names them explicitly. In particular, unrelated reports and local
temporary trees are not release inputs.

## Release-source classification

| Class | Current members | Freeze rule |
|---|---|---|
| Release source candidate | Tracked Skill payload plus the 14 untracked files in `public-release-consolidation-v0.1` | Include only through an exact manifest and file hashes after review |
| Validation evidence | Inclusion, runtime-deployability, ownership, verification, accounting, and focused test artifacts | Preserve with provenance; a receipt never grants adoption/deployment authority |
| Host/community state | inboxes, peer chat, cursors, `PAUSED`, live logs, wake-run receipts | Exclude from distributable defaults; bootstrap fresh local state instead |
| Temporary/local artifacts | `impl/tmp`, root `tmp`, rollback probes, unrelated `agent-output` | Exclude unless separately justified and frozen |
| Authority/evaluation evidence | canonical project authorities and frozen baseline | Never rewrite or silently repurpose as candidate payload |

## Immediate consequence

The working tree cannot be released or committed wholesale. The next release
slice must operate from an explicit allowlist, preserve the current dirty tree,
and prove that fresh installation does not inherit this community's ledger,
inboxes, logs, cursors, or machine paths.
