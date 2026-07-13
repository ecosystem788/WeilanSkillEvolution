# Verification harness for wake-lock-atomic-acquire-v0.1.
# Contains the EXACT patched lock block from wake_agent.ps1 / wake_codex.ps1,
# parameterised by lockFile/log/stamp so the three lock states plus a real
# concurrency race can be exercised as child processes. Not a live wake entry.
param(
    [string]$lockFile,
    [string]$log,
    [string]$stamp
)
$ErrorActionPreference = "Stop"

# ---- BEGIN patched block (verbatim from the two live entries) ----
function Acquire-EpisodeLock {
    param($path, $content)
    $fs = $null; $sw = $null
    try {
        $fs = [System.IO.File]::Open($path,
            [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::None)
        $sw = New-Object System.IO.StreamWriter($fs)
        $sw.Write($content); $sw.Flush()
    } finally {
        if ($sw) { $sw.Dispose() }
        if ($fs) { $fs.Dispose() }
    }
}
$acquired = $false
try {
    Acquire-EpisodeLock $lockFile $stamp
    $acquired = $true
} catch [System.IO.IOException] {
    $stale = $true
    try {
        $lockAge = (Get-Date) - (Get-Item $lockFile -ErrorAction Stop).LastWriteTime
        $stale = ($lockAge.TotalMinutes -ge 30)
    } catch { $stale = $true }
    if (-not $stale) {
        Add-Content -Path $log -Value "$stamp  SKIPPED (episode already running)" -Encoding utf8
        exit 0
    }
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
    try {
        Acquire-EpisodeLock $lockFile $stamp
        $acquired = $true
    } catch {
        Add-Content -Path $log -Value "$stamp  SKIPPED (lost takeover race)" -Encoding utf8
        exit 0
    }
}
if (-not $acquired) { exit 0 }
# ---- END patched block ----

Add-Content -Path $log -Value "$stamp  ACQUIRED (continued into episode)" -Encoding utf8
exit 0
