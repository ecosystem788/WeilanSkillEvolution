# R9 pre-freeze concurrency and hard-kill finding

Date: 2026-07-17  
Target first measured: current checkout, whose frozen installer baseline is
`dba113205c95f2d96db02bab5f94e2fb00bbf632`.

This directory is deliberately outside the 62-file RC1 allowlist. The harness
loads `proposals/public-release-consolidation-v0.1/release_installer.py` from a
caller-selected checkout and drives it in separate Python processes. Hard-kill
cases use `os._exit`, so Python exception cleanup does not run.

Reproduce against a checkout root:

```powershell
$env:WEILAN_R9_RC_ROOT = '<checkout-root>'
python proposals/public-release-r9-fault-injection-v0.1/test_release_installer_r9_faults.py
```

## First discriminating run

Result: `Ran 4 tests in 6.137s` — `FAILED (failures=2)`.

- `test_hard_kill_during_payload_write_refuses_with_exact_conflict_and_preserves_unknown`: passed.
- `test_hard_kill_before_receipt_replace_recovers_and_preserves_unknown`: passed.
- `test_two_concurrent_installs_end_healthy`: failed. One installer raised
  `PermissionError: [WinError 5]` at the atomic receipt `os.replace`.
- `test_install_uninstall_race_never_leaves_receipt_without_payload`: failed.
  A deterministic real-process interleaving left a parseable `installed`
  receipt while `bin/install.ps1` was absent.

The second failure violates R9's allowed terminal states. Tests alone cannot
repair it because both `release_installer.py` and the existing installer test
file are inside the frozen surface. Execution therefore stopped at the inbox
death line and a dual-sign proposal was posted to `peer-chat.jsonl` at
`2026-07-17 10:22:46` for a narrow cross-process mutex repair, rerun, new
freeze, and R2/R13/R14 rebind. No frozen candidate byte was changed here.

## Clean frozen-RC replay

A detached temporary worktree at exactly
`dba113205c95f2d96db02bab5f94e2fb00bbf632` reran the same four tests:
`Ran 4 tests in 5.995s` — `FAILED (failures=1)`. The deterministic
install/uninstall half-ownership failure reproduced. The two-install race did
not fail on this scheduling sample, which is consistent with the first run's
intermittent `WinError 5`; it is not evidence that the race is absent. Both
hard-kill tests passed again.

The frozen checkout's own hygiene verifier reported `PASS`, 62 files, zero
findings, and tree
`794199af2ceaeb239b373bdca38a7e66bc5657a46f42e95487a0a4fbae89373f`.
The temporary worktree was removed after verification.
