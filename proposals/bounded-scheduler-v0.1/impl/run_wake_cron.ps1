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

function Resolve-CheckoutRoot([string]$ScriptDir) {
    # Derive the checkout root from this script's own location instead of
    # hardcoding one machine's path.  The hardcoded form made the wrapper die at
    # Set-Location in every other clone -- including the hosted CI checkout under
    # D:\a\<repo>\<repo> -- so the cron capture regression could not be brought
    # within reach of CI at all (2026-07-27 coverage-debt finding, arm E).
    # Require the ancestor to carry this repository's markers, so a wrong root
    # fails loudly here rather than running the heartbeat from somewhere else.
    $dir = (Resolve-Path -LiteralPath $ScriptDir).Path
    while ($true) {
        $charter = Join-Path $dir "CHARTER.md"
        $impl = Join-Path $dir "proposals\bounded-scheduler-v0.1\impl"
        if ((Test-Path -LiteralPath $charter -PathType Leaf) -and
            (Test-Path -LiteralPath $impl -PathType Container)) {
            return $dir
        }
        $parent = Split-Path -Parent $dir
        if (-not $parent -or $parent -eq $dir) {
            throw ("run_wake_cron.ps1: cannot derive the checkout root from " +
                "'$ScriptDir' -- no ancestor carries CHARTER.md and " +
                "proposals\bounded-scheduler-v0.1\impl")
        }
        $dir = $parent
    }
}

$repo = Resolve-CheckoutRoot $here
if (-not $WakeScript) { $WakeScript = Join-Path $here "wake.py" }
if (-not $LogPath) { $LogPath = Join-Path $here "wake-cron.log" }
if (-not $WakeAgentScript) { $WakeAgentScript = Join-Path $here "wake_agent.ps1" }
$stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
$trace = if ($env:WEILAN_WAKE_AGENT_TEST_TRACE) { $env:WEILAN_WAKE_AGENT_TEST_TRACE } else { "C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py" }

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
        alerted = @($segment | Where-Object { $_ -match '\sALERT sentinel_failure_streak=' }).Count -gt 0
    }
}

function Get-CommitLockSkipEpoch {
    if (-not (Test-Path $LogPath)) { return 0 }
    $tail = @(Get-Content -Path $LogPath -Tail 400 -Encoding utf8)
    $slotPattern = '^(?<stamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})  '
    $terminalPattern = $slotPattern + '(wake ok|ERROR |wake blocked|SKIPPED \(PAUSED|ALERT consecutive_commit_lock_skips=)'
    $skipPattern = $slotPattern + 'wake skipped reason=commit_lock_busy$'
    $events = @()

    for ($i = 0; $i -lt $tail.Count; $i++) {
        if ($tail[$i] -match $terminalPattern) {
            $events += [pscustomobject]@{
                Stamp = $Matches['stamp']
                Position = $i
                Kind = 'terminal'
            }
            continue
        }
        if ($tail[$i] -match $skipPattern) {
            $events += [pscustomobject]@{
                Stamp = $Matches['stamp']
                Position = $i
                Kind = 'skip'
            }
        }
    }

    $ordered = @($events | Sort-Object Stamp, Position)
    $lastTerminal = -1
    for ($i = 0; $i -lt $ordered.Count; $i++) {
        if ($ordered[$i].Kind -eq 'terminal') { $lastTerminal = $i }
    }

    $skipStamps = @{}
    for ($i = $lastTerminal + 1; $i -lt $ordered.Count; $i++) {
        if ($ordered[$i].Kind -eq 'skip') {
            $skipStamps[$ordered[$i].Stamp] = $true
        }
    }
    return $skipStamps.Count
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

# Resolve lineage head and whether it is still open (for pre-flight).
# Mirrors wake_agent.ps1:139; honors test env vars for regression tests.
function Get-HeadAndOpenState {
    if ($env:WEILAN_WAKE_AGENT_TEST_ROOT -and $env:WEILAN_WAKE_AGENT_TEST_HEAD) {
        return [pscustomobject]@{
            head = $env:WEILAN_WAKE_AGENT_TEST_HEAD
            is_open = ($env:WEILAN_WAKE_AGENT_TEST_HEAD_OPEN -eq "1")
        }
    }
    $entryEap = $ErrorActionPreference
    try {
        # Local EAP=Continue keeps a chatty pre-flight probe from aborting the
        # wrapper (F3, 2026-08-04): under EAP=Stop a child stderr line turns
        # `& python ... 2>$null` into NativeCommandError.  Restore immediately;
        # the catch restores the entry value so Continue cannot leak onward.
        $ErrorActionPreference = "Continue"
        $raw = & python $trace lineage-show --workspace $repo --scope skill-evolution 2>$null | Out-String
        $ErrorActionPreference = $entryEap
        if ($LASTEXITCODE -ne 0) { return $null }
        $lineage = $raw | ConvertFrom-Json -ErrorAction Stop
        $head = [string]$lineage.branches.main.head_frame_id
        if ([string]::IsNullOrWhiteSpace($head)) { return $null }
        $ErrorActionPreference = "Continue"
        $validateRaw = & python $trace validate --frame-id $head --require-closed 2>$null | Out-String
        $ErrorActionPreference = $entryEap
        $validateRc = $LASTEXITCODE
        if ($validateRc -eq 0) { return [pscustomobject]@{ head=$head; is_open=$false } }
        $validate = $validateRaw | ConvertFrom-Json -ErrorAction Stop
        $isOpen = @($validate.errors) -contains "frame must be terminal"
        return [pscustomobject]@{ head=$head; is_open=$isOpen }
    } catch {
        $ErrorActionPreference = $entryEap
        Add-LogLine "$stamp  preflight: head/open-state probe unavailable; wake proceeds without pre-flight"
        return $null
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
$env:NO_PROXY    = "localhost,127.0.0.1,::1,token-plan.cn-beijing.maas.aliyuncs.com,ws-s0l7d3yz7axp4uwz.cn-beijing.maas.aliyuncs.com,api.minimaxi.com,www.minimaxi.com,api.deepseek.com"

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
    # --- pre-flight: abandon a stale open lineage head before wake (§9.4) ---
    # An open head blocks frame_open (§8.2 deadlock). frame-abandon's own gate
    # enforces silence >= 7200s and >= 3600s floor; pre-flight does not re-derive.
    $streak = Get-FailureStreak
    $headState = Get-HeadAndOpenState
    if ($headState -and $headState.is_open) {
        $ev = @{ alert_id = "preflight"; consecutive_count = [int]$streak.count;
                 source_ref = "run_wake_cron:preflight" } | ConvertTo-Json -Compress
        # Windows PowerShell 5.1 re-quotes native arguments on the command
        # line.  Escape the JSON quotes with backslashes so the argv parser
        # turns \" back into " (FORM C, verified by the 2026-08-03 review
        # probe): the delivered --evidence then parses with json.loads.
        $evArg = $ev -replace '"','\"'
        $savedEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & python $trace frame-abandon --frame-id $headState.head `
            --silence-threshold-seconds 7200 --evidence $evArg `
            --reason "pre-flight: cron abandoning a stale open lineage head before wake" 2>$null
        $ErrorActionPreference = $savedEap
        if ($LASTEXITCODE -ne 0) {
            # Abandon refused: live round holds head, or raced. Skip this tick
            # (exit 0 so the failure-streak counter does not advance).
            Add-LogLine "$stamp  preflight: open head $($headState.head), abandon refused (live or raced); skip wake"
            exit 0
        }
        Add-LogLine "$stamp  preflight: abandoned stale open head $($headState.head) (silence >= 7200s)"
    }
    # --- end pre-flight ---

    & cmd /c "python `"$WakeScript`" --commit 1>`"$stdoutPath`" 2>`"$stderrPath`""
    $nativeRc = $LASTEXITCODE
    $stdout = Get-Content -Raw -Encoding utf8 $stdoutPath
    $stderr = Get-Content -Raw -Encoding utf8 $stderrPath

    if ($nativeRc -eq 4) {
        Add-LogLine "$stamp  wake skipped reason=commit_lock_busy"
        $skipEpochCount = Get-CommitLockSkipEpoch
        if ($skipEpochCount -ge 20) {
            Add-LogLine "$stamp  ALERT consecutive_commit_lock_skips=$skipEpochCount action=log_only"
        }
        exit 0
    }

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
        if ($escalationReasons -contains "orphan_rescue") {
            $rescueJson = $report.rescue_context | ConvertTo-Json -Compress
            # Native PowerShell argument parsing strips JSON quotes.  Carry the
            # exact UTF-8 JSON bytes as base64; wake_agent accepts this form.
            $rescueB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($rescueJson))
            & powershell -NoProfile -ExecutionPolicy Bypass -File $WakeAgentScript -RescueContext $rescueB64
        } else {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $WakeAgentScript
        }
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
