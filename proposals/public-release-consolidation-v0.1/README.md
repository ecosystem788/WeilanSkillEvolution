# WeiLan Windows release candidate

This directory is a release candidate (RC, 发行候选), not a published release.
It provides a bounded installer proposal and documentation for an isolated local
rehearsal. It does not authorize deployment, adoption, publication, or a license
choice.

## Current runtime

- `install`, `status`, and `uninstall` operate on an explicitly selected install
  directory.
- `start -TickOnly` registers one per-user Scheduled Task with an observable
  tick receipt. Without `-TickOnly`, `data/runtime/runtime.json` must contain a
  nonempty `agent_command` argv array; silent heartbeat-only activation is
  refused.
- `open-dashboard` starts a GET-only viewer on `127.0.0.1`. A non-loopback
  bind requires both `-Bind` and `-AcknowledgeNetworkExposure`.
- `status`, `stop`, and `uninstall` use the task/pid ownership receipts. They
  never search by a broad task-name pattern when deleting.
- The outward license and notices are still pending independent approval. No
  license is selected or activated by this candidate documentation.

## Prerequisites

- Windows PowerShell 5.1 or newer.
- Python 3 available as `python` on `PATH`.
- Codex CLI available as `codex` on `PATH`.
- Claude Code CLI available as `claude` on `PATH`. Availability is checked; the
  rehearsal does not call the Claude API and therefore does not consume quota.
- A complete `WeilanSkillEvolution` checkout containing the manifest-declared
  Skill payload.

## One install command

From the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\proposals\public-release-consolidation-v0.1\setup.ps1 -InstallRoot C:\Weilan-RC
```

The command prints JSON. Continue only when `status` is `installed`. Then use
the generated scripts under `C:\Weilan-RC\bin`; see [OPERATION_CARD.md](OPERATION_CARD.md).

## Local isolated rehearsal

Run this before asking for clean-machine acceptance:

```powershell
python .\proposals\public-release-consolidation-v0.1\clean_home_rehearsal.py
```

The rehearsal creates a temporary `HOME`, `USERPROFILE`, `CODEX_HOME`,
`WEILAN_METHOD_HOME`, and install root; exercises the non-activating smoke
surface and uninstall; then removes the temporary tree. The separate portable
runtime acceptance uses a test-unique `WeilanReleaseTest-*` task and removes it
in the same test.

**This is a clean-HOME rehearsal on the current machine. It is not evidence of
a genuinely clean Windows account or clean machine, and it cannot close the
clean-machine/time acceptance gate.**

For recovery and exit-code meanings, see
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).
