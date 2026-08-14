# watcher-skill-evolution-autostart-unregister.ps1
# Remove the logon-triggered autostart task. Does not stop a running watcher.
param([string]$Scope = "skill-evolution")
$ErrorActionPreference = "Stop"
$taskName = "WeilanWatcherAutostart-$Scope"
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if (-not $existing) { Write-Output "no such scheduled task: $taskName"; exit 0 }
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Output "unregistered scheduled task: $taskName"
