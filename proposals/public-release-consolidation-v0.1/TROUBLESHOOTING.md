# Troubleshooting

Once argument parsing and PowerShell policy/parameter binding succeed, the
installer and generated entry points print machine-readable JSON for handled
results. Earlier shell or argument failures may be plain text. Preserve the
complete stdout and stderr when asking another Codex window or an independent
reviewer to audit a failure.

| Exit/status | Meaning | Safe next action |
|---|---|---|
| setup exit `4`, `prerequisite_python_missing` | `python` is unavailable on `PATH` | Install Python 3, open a new shell, and rerun setup |
| installer exit `1`, `error` | A handled filesystem or JSON operation failed | Preserve stdout/stderr and inspect the reported operation; do not assume rollback completed after a process kill or power loss |
| install exit `2`, `preflight_failed` | A required command, manifest, repository root, or payload is missing/invalid | Follow each JSON `hint`; no target files should have been written |
| install exit `2`, `conflict` | The target already contains a different file at an owned path | Choose a new empty install directory or preserve and inspect the conflicting file |
| status exit `2`, `state: drifted` | An installed owned file is missing or changed | Review `missing` and `drifted`; do not overwrite evidence blindly |
| entry exit `2`, `installation_not_healthy` | Runtime action was attempted on an absent or drifted install | Restore/reinstall into an empty target, then rerun status |
| start exit `1`, missing `agent_command` | Agent mode was requested without an explicit argv configuration | Add `data/runtime/runtime.json`, or use `-TickOnly` for an observable no-agent task |
| start exit `1`, invalid `-TaskName` | Test task injection did not use `WeilanReleaseTest-` | Omit `-TaskName` in product use; harnesses must use a unique admitted name |
| dashboard exit `1`, acknowledgement required | A non-loopback bind was requested without the second exposure acknowledgement | Prefer loopback; otherwise review exposure and pass `-AcknowledgeNetworkExposure` explicitly |
| uninstall exit `2`, `runtime_residue` | The exact owned task or dashboard process could not be proven stopped | Preserve task/pid receipts and inspect the reported residue; do not delete by name pattern |
| uninstall exit `2`, `conflict` | At least one owned path changed after install | The changed path is preserved; save it, review it, then remove it manually only if intended |
| uninstall `already_absent` | No ownership receipt exists | The installer has no verified ownership set to remove; inspect the target manually if the receipt may have been deleted |

## Rehearsal-specific failures

`clean_home_rehearsal.py` returns exit `0` only when every bounded step passes,
uninstall reports success, and the temporary state roots stay inside the
rehearsal directory. A nonzero result is a failed local rehearsal, not proof
that a clean machine would fail.

The script intentionally keeps no installed runtime after completion. Use
`--receipt <path>` to retain its JSON receipt outside the temporary directory.
The receipt is labeled `LOCAL_CLEAN_HOME_ONLY` and must not be relabeled as a
clean-machine acceptance result.

## Escalation boundaries

Stop and obtain the required independent approval before changing or merging
scheduler/wake/dashboard contracts, selecting the outward license, adopting
the deployed Skill, or pushing/tagging/publishing a release. The signed v0.7
contract authorizes only the receipt-owned portable runtime described here.
