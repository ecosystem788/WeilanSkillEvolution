param(
    [string]$WakeScript,
    [string]$LogPath,
    [string]$WakeAgentScript,
    [switch]$NoEscalate
)

# Unattended heartbeat wrapper — what the real cron (Windows Task Scheduler) runs.
# One firing = one bounded wake episode against the LIVE ledger, committed.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = "D:\WeilanSkillEvolution"
if (-not $WakeScript) { $WakeScript = Join-Path $here "wake.py" }
if (-not $LogPath) { $LogPath = Join-Path $here "wake-cron.log" }
if (-not $WakeAgentScript) { $WakeAgentScript = Join-Path $here "wake_agent.ps1" }
$stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"

function Add-LogLine([string]$Value) {
    Add-Content -Path $LogPath -Value $Value -Encoding utf8
}

function Get-Diagnostic([string]$Stderr, [string]$Stdout) {
    $diagnostic = if ($Stderr) { $Stderr } else { $Stdout }
    $bytes = [Text.Encoding]::UTF8.GetBytes($diagnostic)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $hash = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
    $preview = ($diagnostic -replace '[\r\n]+', ' ').Trim()
    if ($preview.Length -gt 240) { $preview = $preview.Substring(0, 240) }
    return @{ hash = $hash; preview = $preview }
}

function Get-FailureStreak {
    if (-not (Test-Path $LogPath)) { return @{ count = 0; alerted = $false } }
    $tail = @(Get-Content -Path $LogPath -Tail 400 -Encoding utf8)
    $lastHealthy = -1
    for ($i = 0; $i -lt $tail.Count; $i++) {
        if ($tail[$i] -match '\swake ok\s') { $lastHealthy = $i }
    }
    $segment = if ($lastHealthy -lt ($tail.Count - 1)) {
        @($tail[($lastHealthy + 1)..($tail.Count - 1)])
    } else { @() }
    return @{
        count = @($segment | Where-Object { $_ -match '\sERROR\s' }).Count
        alerted = @($segment | Where-Object { $_ -match '\sALERT\s' }).Count -gt 0
    }
}

function Register-Failure([string]$Stage, [int]$NativeRc, [string]$Stderr, [string]$Stdout) {
    $diag = Get-Diagnostic $Stderr $Stdout
    Add-LogLine "$stamp  ERROR rc=$NativeRc stage=$Stage diag_sha256=$($diag.hash) stderr=$($diag.preview)"
    $streak = Get-FailureStreak
    if ($streak.count -ge 3 -and -not $streak.alerted) {
        Add-LogLine "$stamp  ALERT sentinel_failure_streak=$($streak.count) action=wake_agent"
        if (-not $NoEscalate) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $WakeAgentScript
            Add-LogLine "$stamp  alert wake_agent done rc=$LASTEXITCODE"
        }
    }
}

# SOFT kill: presence of a PAUSED sentinel halts firings without unregistering.
if (Test-Path (Join-Path $here "PAUSED")) {
    Add-LogLine "$stamp  SKIPPED (PAUSED sentinel present)"
    exit 0
}

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
$env:HTTP_PROXY  = "http://127.0.0.1:2080"
$env:HTTPS_PROXY = "http://127.0.0.1:2080"
$env:NO_PROXY    = "localhost,127.0.0.1,::1"

$stdoutPath = [IO.Path]::GetTempFileName()
$stderrPath = [IO.Path]::GetTempFileName()
try {
    # Capture the child's streams via cmd so the bytes reach the temp files
    # untouched. PowerShell 5.1's own 1>/2> on a native command decodes the
    # child's UTF-8 output with the legacy console codepage and re-encodes it
    # as UTF-16 — a mangled multibyte char can swallow an adjacent JSON quote
    # (live incident 2026-07-14T14:00:58 json_parse on a healthy rc=0 wake).
    # cmd-level redirection is byte-faithful, keeps native stderr away from
    # NativeCommandError under EAP=Stop, and propagates the child's exit code.
    & cmd /c "python `"$WakeScript`" --commit 1>`"$stdoutPath`" 2>`"$stderrPath`""
    $nativeRc = $LASTEXITCODE
    $stdout = Get-Content -Raw -Encoding utf8 $stdoutPath
    $stderr = Get-Content -Raw -Encoding utf8 $stderrPath

    if ($nativeRc -ne 0) {
        Register-Failure "native_exit" $nativeRc $stderr $stdout
        exit $nativeRc
    }

    try {
        $report = $stdout | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Register-Failure "json_parse" 0 $stderr $stdout
        exit 1
    }

    # A fail-closed activation gate is a valid bounded outcome, not a corrupt
    # receipt.  Keep it observable without feeding the failure-streak alert
    # (which would otherwise wake only Claude and leave Codex unreachable).
    $aborted = [string]$report.aborted
    if (-not [string]::IsNullOrWhiteSpace($aborted)) {
        if ($aborted -eq "continuation_not_allowed") {
            $activationState = [string]$report.briefing.activation_state
            Add-LogLine "$stamp  wake blocked  reason=$aborted  state=$activationState"
            exit 0
        }
        Register-Failure "aborted" 0 $stderr $stdout
        exit 1
    }

    $frame = [string]$report.committed_frame
    if ($frame -notmatch '^wf-[A-Za-z0-9-]+$') {
        Register-Failure "receipt_validate" 0 $stderr $stdout
        exit 1
    }
    if ($report.receipt.crossed_irreversible_gate -eq $true) {
        Register-Failure "kernel_gate" 2 $stderr $stdout
        exit 2
    }

    $stop = [string]$report.receipt.stop_reason
    Add-LogLine "$stamp  wake ok  stop=$stop  frame=$frame"

    if ($report.escalation_due -eq $true -and -not $NoEscalate) {
        $escalationReasons = @($report.escalation_reasons | Where-Object {
            -not [string]::IsNullOrWhiteSpace([string]$_)
        })
        $escalationReasonText = if ($escalationReasons.Count -gt 0) {
            $escalationReasons -join ","
        } else { "unknown" }
        Add-LogLine "$stamp  escalating: reasons=$escalationReasonText -> model episode"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $WakeAgentScript
        Add-LogLine "$stamp  escalation done rc=$LASTEXITCODE"
    }

    if ($report.codex_due -eq $true -and -not $NoEscalate) {
        $codexReasons = @($report.codex_wake_reasons | Where-Object {
            -not [string]::IsNullOrWhiteSpace([string]$_)
        })
        $codexReasonText = if ($codexReasons.Count -gt 0) {
            $codexReasons -join ","
        } else { "unknown" }
        Add-LogLine "$stamp  waking codex: reasons=$codexReasonText"
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here "wake_codex.ps1")
        Add-LogLine "$stamp  codex wake done rc=$LASTEXITCODE"
    }
    exit 0
} catch {
    Register-Failure "wrapper_exception" 1 $_.Exception.Message ""
    exit 1
} finally {
    Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
}
