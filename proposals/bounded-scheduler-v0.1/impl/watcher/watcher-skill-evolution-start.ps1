# watcher-skill-evolution-start.ps1 — start the sentinel watcher (scope=skill-evolution)
param([string]$Scope = "skill-evolution")
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$impl = Split-Path -Parent $here
$pidFile = Join-Path $here "watcher-$Scope.pid"
$log = Join-Path $impl "watcher.log"

if (Test-Path $pidFile) {
    $oldPid = (Get-Content $pidFile -ErrorAction SilentlyContinue).Trim()
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Output "watcher-sentinel-$Scope already running pid=$oldPid"
        exit 1
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

$proc = Start-Process -FilePath "python" -ArgumentList @(
    (Join-Path $here "watcher_sentinel.py"),
    "--sentinel-dir", $here,
    "--wake-script-dir", $impl,
    "--scope", $Scope,
    "--log", $log
) -WindowStyle Hidden -PassThru

Set-Content -Path $pidFile -Value $proc.Id -Encoding Ascii
Write-Output "watcher-sentinel-$Scope started pid=$($proc.Id) (log: $log)"
