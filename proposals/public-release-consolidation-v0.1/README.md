# WeiLan Windows release candidate

This directory is a release candidate (RC, 发行候选), not a published release.
It provides an AI-operable bounded installer and documentation for mechanically
verifiable local and clean-machine acceptance. It does not authorize deployment,
adoption, publication, or any change to the selected license.

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
- The outward license is present in the repository and candidate payload; the
  exact license bytes remain bound to the frozen-candidate receipt.

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

## AI-operated acceptance boundary

An AI agent is the installation operator and receipt author. It must execute the
documented lifecycle without source edits, preserve stdout/stderr and elapsed
time, and compare the resulting hashes and machine-readable receipts with the
frozen candidate. The human observer is not a recurring installation tester.
Request the smallest observer check only for facts the agent cannot establish
from the child layer, such as host-visible UI, permissions, or subjective
experience.

Final clean-machine acceptance still requires a genuinely fresh Windows
environment that is not the development machine: fresh HOME and state, no
inherited PATH/configuration contamination, prerequisite and path discovery
from zero, and the complete install -> start -> status -> dashboard -> stop ->
uninstall lifecycle in at most ten minutes. The AI agent must retain the timed
receipt. A current-machine rehearsal cannot satisfy this gate.

## Local isolated rehearsal

Run this as a bounded local preflight before clean-machine acceptance:

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
