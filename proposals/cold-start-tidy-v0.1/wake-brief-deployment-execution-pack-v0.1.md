# wake_brief deployment execution pack v0.1

Status: proposal-side preparation only. This pack does not deploy, adopt, edit wake prompts, change Task Scheduler, or touch `D:\CodexData\skills\solve-with-weilan`.

## Exact artifact

- Source: `proposals/bounded-scheduler-v0.1/impl/wake_brief.py`
- Proposed deployed copy: `D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py`
- Current verified fact: deployed `scripts\` has no `wake*` file, so copying the artifact alone creates no runtime effect.

## Required owner button

Real cold-start relief requires both steps:

1. Adopt/copy `wake_brief.py` into the deployed skill scripts directory.
2. Add a red-zone wake_prompt or harness instruction that invokes it before the long manual ledger reads.

Step 2 is the real connection. Without it, the copied file is inert.

## Read-only readiness command

Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File proposals/cold-start-tidy-v0.1/verify-wake-brief-deployment-readiness.ps1
```

JSON form:

```powershell
powershell -ExecutionPolicy Bypass -File proposals/cold-start-tidy-v0.1/verify-wake-brief-deployment-readiness.ps1 -Json
```

The verifier only reads files and runs tests. It reports the source hash, proposed target, whether a target already exists, deployed wake-file inventory, and pytest output.

## Verification before pressing deploy

Use the readiness script, then require all of these to hold:

- `pytest_exit_code = 0`.
- `source_sha256` is recorded in the deployment receipt.
- `target_exists = false`, or if true, `target_sha256` is recorded as the rollback predecessor.
- `deployed_skill_wake_files` is understood before adding a new deployed wake helper.
- The prompt/harness edit is a single owner-approved change with an obvious revert.

## Verification after owner connects it

Run:

```powershell
python D:\CodexData\skills\solve-with-weilan\scripts\wake_brief.py --workspace "D:\WeilanSkillEvolution" --scope "skill-evolution"
```

Check:

- Output JSON includes `authority`, `owner_inbox_delta`, `prospective_due`, `peer_chat_new`, `codex_replies_unreviewed`, `sources`, and `cursor_status`.
- First run from a missing cursor performs `full_rescan`.
- Second run performs `incremental`.
- `authority.activation` and `authority.control` agree with direct `memory-recall`.

## Rollback

- If `wake_brief.py` was newly copied into deployed skill scripts, delete only that copied file.
- If it replaced an existing target, restore the recorded predecessor hash from backup before reuse.
- Revert the single wake_prompt/harness instruction that called `wake_brief`.
- Re-run direct `memory-recall` and confirm the old wake path still starts from the normal activation gate.

## Red-zone boundary

This pack is preparation. It intentionally leaves the actual copy and prompt/harness connection to the owner-approved deployment action.
