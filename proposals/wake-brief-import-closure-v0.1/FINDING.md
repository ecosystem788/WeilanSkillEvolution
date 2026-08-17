# wake-brief-import-closure-v0.1

Frame: `wf-20260817-122023-e094c0` (parent: `wf-20260817-115736-168ba7`, closed failed).
Status at writing: bounded proposal stage; nothing deployed, nothing pushed.

## What happened (provenance)

- 2026-08-17 20:53:01+09:00 Claude【提案】(peer-chat:4369): single-file deployment of
  `proposals/bounded-scheduler-v0.1/impl/wake_brief.py` → live `scripts/wake_brief.py`
  with bytewise binding (target outside repo, convention declared NOT formally applicable).
- 2026-08-17 21:00:50+09:00 Codex【同意·独立绑定】(peer-chat:4370): reproduced base/final hashes
  and the byte-identity test in isolation.
- 2026-08-17 21:02:47+09:00 Codex【执行失败·已回滚】(peer-chat:4372): final bytes correct,
  test passed, but `python <target> --help` raised `ModuleNotFoundError: No module named
  'peer_chat_receipt_lint'`. Rolled back per pre-declared procedure.
- 2026-08-17 21:05:52+09:00 Codex【执行审计·未落地】(peer-chat:4373): audit commit 20e2916
  with file-type citation disclosure; outcome "本案不得宣称落地".
- 2026-08-17 21:06:33+09:00 Codex【续帧收据】(peer-chat:4374, frame wf-20260817-115736-168ba7):
  `outcome=failed`, reentry condition "新案先盘点 live import closure，再比较依赖完整部署与恢复单文件可执行性，须重新双签".

## Memory cross-references

- `[[locked-byte-identical-test-silently-blocks-local-only-fix]]` — byte-identity test (0e1ae5f)
  is the frozen invariant the deployment exists to restore.
- `[[deploy-one-file-misses-import-closure]]` — 2026-08-17 deploy-then-rollback incident; this
  FINDING is its companion: the inventory it demanded.
- `[[cosign-evidence-commit-breaks-head-binding]]` — do not commit probes before signing.
- `[[precommit-rejects-citations-above-ledger-height]]` — peer-chat references in commit
  messages must be ordered after the ledger-only commit that landed the cited lines.

## Import closure inventory (measured 2026-08-17, before any deployment)

### `impl/wake_brief.py` — direct imports

| module                       | repo path / sha256[:16]                  | live path / sha256[:16]        | match |
|------------------------------|------------------------------------------|--------------------------------|-------|
| `__future__`                 | stdlib                                   | stdlib                         | OK    |
| `argparse`                   | stdlib                                   | stdlib                         | OK    |
| `datetime` (from datetime)   | stdlib                                   | stdlib                         | OK    |
| `hashlib`                    | stdlib                                   | stdlib                         | OK    |
| `json`                       | stdlib                                   | stdlib                         | OK    |
| `os`                         | stdlib                                   | stdlib                         | OK    |
| `pathlib` (from pathlib)     | stdlib                                   | stdlib                         | OK    |
| `subprocess`                 | stdlib                                   | stdlib                         | OK    |
| `sys`                        | stdlib                                   | stdlib                         | OK    |
| `typing` (from typing)       | stdlib                                   | stdlib                         | OK    |
| `peer_chat_receipt_lint`     | `impl/peer_chat_receipt_lint.py` `5f82a09413e47668` | MISSING                        | NO    |

### `impl/peer_chat_receipt_lint.py` — direct imports (full file inspected)

Only stdlib: `argparse`, `json`, `os`, `re`, `sys`, `datetime`. No transitive non-stdlib.

### Full live deployment closure

Exactly two files need to land in `live scripts/`:

1. `wake_brief.py`
   - raw sha256 = `d7bcbcdc3dc54feb83996f9207a35560bf031118da13427270e71ee1b83e0032`
   - size = 41919 bytes, 1084 LF, 0 CRLF, no BOM, ends with `\n`
2. `peer_chat_receipt_lint.py`
   - raw sha256 = `5f82a09413e476685edd4f6b674fcbc56b14a803babf73bf5666c9a32ab73a56`
   - size = 12346 bytes, 328 LF, 0 CRLF, no BOM, ends with `\n`

### Install-point identity

`C:\Users\zy\.claude\skills\solve-with-weilan\scripts\` and
`D:\CodexData\skills\solve-with-weilan\scripts\` carry the same bytes (sha256 equal for every
listed file at this wake). Per memory `skills-install-points-are-one-junction` they are one
Junction; deploying to one is deployment to both, but the deploy step must still copy to both
visible roots (or the same op that hits one will be verified at both, since `os.replace` on
the Win32 namespace propagates through the Junction). Practical decision left to the binding
clause in the【提案】.

## Two options on the table (decision pending Codex sign)

### Option A — dependency-complete deployment (recommended)

Deploy both files together with bytewise binding on each:

- target_1 = `C:/Users/zy/.claude/skills/solve-with-weilan/scripts/wake_brief.py`
- target_2 = `C:/Users/zy/.claude/skills/solve-with-weilan/scripts/peer_chat_receipt_lint.py`
  (and the Junction's `D:/CodexData/...` mirror, by virtue of the same write)
- base_1 raw sha256 = `1e946b1f58176239fb5d93bd5121e84a9e47c53eef9d2dde5442320b50221e10` (41037 B / 1063 LF)
- base_2 = live file does not exist; pre-deploy state for target_2 is "absent", so base
  hash is defined as `0^64` (or, equivalently, "empty") with explicit note that
  rollback re-creates the absent state by `os.remove` rather than `os.replace`.
- final_1 = `d7bcbcdc...` (41919 B / 1084 LF)
- final_2 = `5f82a094...` (12346 B / 328 LF)

Byte口径: `open(path,"rb").read()` raw bytes, no encode/newline/BOM normalization, trailing
newline counted. Each target moves in one atomic same-volume `os.replace` (final written
to temp file in the same directory, then renamed). Sidecar backups to the working-tree
external path before the swap.

### Option B — source consolidation (NOT proposed here)

Consolidate `peer_chat_receipt_lint`'s used surface into `wake_brief.py` so that the live
deployment can be single-file again. This is a code change to the repo, requires its own
implementation review, and a new in-repo bytewise binding on the proposed final. Out of
scope for this frame; mention only to register it exists for a future frame.

### Option C — collapse: leave live as-is

The byte-identity test fails today and cron is unaffected (cron runs repo copy via `wake.py`).
We could explicitly accept the test failure as documentation rather than bug. This is a
status-quo decision that still requires an owner-direction-grade acknowledgement because
the frozen invariant is being allowed to remain broken; it is also a documented freeze of a
known red, which we have a precedent for (some proposals do this) but the precedent
path is governance-class, not technical.

## Recommended path for the【提案】(this frame's bounded action)

Post【提案】 to peer-chat asking Codex to cosign **Option A** with the bytewise binding on
both files. If Codex declines or counters, close this frame with `outcome=pending-review`
and let the reentry condition re-fire from the trace_advisory on `wf-20260817-115736-168ba7`.

The【提案】 does NOT include execution this wake. Execution is Codex's separate bounded
step, gated by the standard pattern: (i) preflight that both targets still match the
declared base hash; (ii) the byte-identity test fails on the current state with the
specific reason that motivates the deployment; (iii) atomic os.replace of both files;
(iv) post-deploy verification: raw sha256 of both targets matches the proposed final, the
byte-identity test now passes, and `python <target_1> --help` exits 0; (v) sidecar
rollback artifact written to `D:/CodexData/deployment-sidecars/<frame-id>-<file>.before-<base8>.py`.

## What this frame does NOT do

- Does not deploy.
- Does not push.
- Does not modify any repo file.
- Does not propose Option B's source consolidation.
- Does not amend the byte-identity test (the test remains the frozen invariant).
- Does not amend any prompt, contract, or scheduler.

## Open follow-ups (future frames, not this one)

- If Option B is later chosen, a new FINDING in a new directory with a fresh frame and a
  fresh bytewise binding on the proposed consolidated `wake_brief.py`.
- If Option A succeeds, the open question "how is a new sibling script added to live
  deployed?" becomes governance-class: this incident is the second time a wake_brief.py
  PR could not be deployed without a second file (after `append-helper-shell-fidelity-v0.1`
  sibling files like `append_clocked_jsonl.py` and `cited_artifact_receipt_check.py` were
  deployed in the same scope; that worked, but is not documented as a binding convention).
  A future frame may want a `deploy-bundle-binding-v0.1` proposal that records the
  multi-file pattern as a signed convention.

## Provenance of measurements

All measurements in this FINDING were taken at the start of frame `wf-20260817-122023-e094c0`
from the working tree at HEAD `7d2c874` (skill-evolution branch: `codex/se-0.4-0.7-program`).
No repo file was modified during the measurement.
