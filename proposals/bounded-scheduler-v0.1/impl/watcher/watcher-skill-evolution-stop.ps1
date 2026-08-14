# watcher-skill-evolution-stop.ps1 — stop the sentinel watcher (scope=skill-evolution)
param([string]$Scope = "skill-evolution")
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $here "watcher-$Scope.pid"

if (Test-Path $pidFile) {
    $oldPid = (Get-Content $pidFile -ErrorAction SilentlyContinue).Trim()
    if ($oldPid) {
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Write-Output "watcher-sentinel-$Scope stopped pid=$oldPid"
} else {
    Write-Output "watcher-sentinel-$Scope not running (no pid file)"
}
