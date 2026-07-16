# Operation card

All examples assume the candidate was installed to `C:\Weilan-RC`. Replace that
path with the exact install directory you chose.

| Goal | Command | Expected result |
|---|---|---|
| Check ownership and drift | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\status.ps1` | exit `0`, `state: healthy` |
| Verify start entry only | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\start.ps1 -Smoke` | exit `0`, `runtime_activation_performed: false` |
| Verify dashboard entry only | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\open-dashboard.ps1 -Smoke` | exit `0`, no browser or server launched |
| Verify stop entry only | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\stop.ps1 -Smoke` | exit `0`, no host task changed |
| Remove owned, unchanged files | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\uninstall.ps1` | exit `0`, `status: uninstalled` |

## Safety boundary

Do not omit `-Smoke` from `start`, `stop`, or `open-dashboard` in this candidate.
The current expected result without it is an honest activation refusal (exit
`3`), because portable scheduler/dashboard wiring has not been accepted.

Uninstall removes only files listed in the install receipt whose hashes remain
unchanged. A changed owned file is preserved and reported as a conflict; resolve
it manually only after deciding whether its content must be retained.

## Suggested review sequence

1. Install to an empty directory.
2. Run `status` and confirm `healthy`.
3. Run all three `-Smoke` commands and confirm
   `runtime_activation_performed: false`.
4. Run `uninstall` and confirm `uninstalled`.
5. Run `uninstall` again and confirm `already_absent`.

This sequence validates proposal mechanics only. It does not start the
autonomous loop and does not substitute for a clean-machine review.
