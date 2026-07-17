# Operation card

All examples assume the candidate was installed to `C:\Weilan-RC`. Replace that
path with the exact install directory you chose.

| Goal | Command | Expected result |
|---|---|---|
| Check ownership and drift | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\status.ps1` | exit `0`, `state: healthy` |
| Start observable tick-only task | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\start.ps1 -TickOnly` | exit `0`, `status: running`; receipts append under `data\runtime` |
| Start configured bounded agent | Create `data\runtime\runtime.json` with `{"agent_command":["absolute-command", "arg"]}`, then run `start.ps1` | exit `0`; each task tick records `agent_invoked` or a bounded failure receipt |
| Open local dashboard | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\open-dashboard.ps1` | exit `0`, URL on `127.0.0.1` |
| Stop owned runtime | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\stop.ps1` | exit `0`, exact receipt-owned task and matching dashboard process stopped |
| Remove owned, unchanged files | `powershell -NoProfile -ExecutionPolicy Bypass -File C:\Weilan-RC\bin\uninstall.ps1` | exit `0`, `status: uninstalled` |

## Safety boundary

`start` without `-TickOnly` refuses unless `runtime.json` contains a valid
`agent_command`. `-TaskName` is a harness-only injection and accepts only the
`WeilanReleaseTest-` prefix; normal installs use their receipt-derived
`WeilanScheduler-<install_id>` name. Non-loopback dashboard exposure requires
an explicit acknowledgement and should be reviewed before use.

Uninstall removes only files listed in the install receipt whose hashes remain
unchanged. A changed owned file is preserved and reported as a conflict; resolve
it manually only after deciding whether its content must be retained.

## Suggested review sequence

1. Install to an empty directory.
2. Run `status` and confirm `healthy`.
3. Run `start -TickOnly`, then `status`; confirm a task and a recent tick.
4. Run `open-dashboard`; confirm HTTP 200 on the printed loopback URL.
5. Run `stop` twice; both calls must succeed.
6. Run `uninstall`, then repeat it and confirm `already_absent`.

Tick-only mode does not invoke an agent. A configured `agent_command` starts
one bounded episode per due tick; it does not create an unbounded Agent. This
sequence still does not substitute for a genuinely clean-machine review.
