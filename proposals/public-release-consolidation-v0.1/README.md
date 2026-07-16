# WeiLan Windows release candidate

This directory is a release candidate (RC, 发行候选), not a published release.
It provides a bounded installer proposal and documentation for an isolated local
rehearsal. It does not authorize deployment, adoption, publication, or a license
choice.

## Current boundary

- `install`, `status`, and `uninstall` operate on an explicitly selected install
  directory.
- `start`, `stop`, and `open-dashboard` currently support only `-Smoke`. The
  smoke path checks the installed entry points without starting a scheduler,
  dashboard, or autonomous loop.
- Calling those three entries without `-Smoke` is expected to refuse activation
  with exit code `3` while machine-specific runtime wiring remains unresolved.
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
`WEILAN_METHOD_HOME`, and install root; exercises install, status, the three
non-activating smoke entries, and uninstall; then removes the temporary tree.
It never connects a real Task Scheduler task or dashboard.

**This is a clean-HOME rehearsal on the current machine. It is not evidence of
a genuinely clean Windows account or clean machine, and it cannot close the
clean-machine/time acceptance gate.**

For recovery and exit-code meanings, see
[TROUBLESHOOTING.md](TROUBLESHOOTING.md).

