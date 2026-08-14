# watcher-skill-evolution-status.ps1 — report watcher status (scope=skill-evolution)
param([string]$Scope = "skill-evolution")
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $here "watcher-$Scope.pid"

if (-not (Test-Path $pidFile)) {
    Write-Output "watcher-sentinel-$Scope: not running (no pid file)"
    exit 0
}
$oldPid = (Get-Content $pidFile -ErrorAction SilentlyContinue).Trim()
$proc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
if ($proc) {
    Write-Output "watcher-sentinel-$Scope: running pid=$oldPid started=$($proc.StartTime)"
    exit 0
}
Write-Output "watcher-sentinel-$Scope: pid file stale (pid=$oldPid not alive)"
exit 1
