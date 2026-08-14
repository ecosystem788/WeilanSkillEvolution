# watcher-skill-evolution-autostart-register.ps1
# Register a logon-triggered scheduled task that starts the sentinel watcher.
# Authorized by observer directive (peer-chat 2026-08-14 20:47:08 JST: "好的，做成开机自启吧").
# Reversible: run watcher-skill-evolution-autostart-unregister.ps1 to remove.
param([string]$Scope = "skill-evolution")
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $here "watcher-$Scope-start.ps1"
if (-not (Test-Path $startScript)) { throw "start script not found: $startScript" }

$taskName = "WeilanWatcherAutostart-$Scope"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument (
    "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startScript`" -Scope $Scope"
)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Output "registered scheduled task: $taskName (AtLogOn, user=$env:USERNAME)"
