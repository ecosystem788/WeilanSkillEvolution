# Model-in-the-loop wake — what the real cron runs to let the agent LIVE one episode.
# One firing = one headless `claude -p` bounded autonomous episode against the live
# project + ledger, under the discipline in wake_prompt.md.
#
# 2026-07-11 CHARTER regime (owner decree, see CHARTER.md): full autonomy.
#   * --dangerously-skip-permissions: no tool whitelist, no sandbox, full machine use.
#   * Order comes from the constitution + dual-sign procedure in wake_prompt.md,
#     not from a technical cage. Observer (owner) retains veto + kill switches.
#
# Kill switches (observer's buttons):
#   HARD : Unregister-ScheduledTask -TaskName "WeilanBoundedSchedulerWake" -Confirm:$false
#   SOFT : create a file named  PAUSED  next to this script (shared with the heartbeat).
#
# Observability: full JSON transcript per run under wake-agent-runs\, one summary
# line per run in wake-agent.log, with head-before/after so you can see if it wrote.

$ErrorActionPreference = "Stop"
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo   = "D:\WeilanSkillEvolution"
$log    = Join-Path $here "wake-agent.log"
$runs   = Join-Path $here "wake-agent-runs"
$prompt = Join-Path $here "wake_prompt.md"
$trace  = "C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
$stamp  = Get-Date -Format "yyyy-MM-ddTHH-mm-ss"
if (-not (Test-Path $runs)) { New-Item -ItemType Directory -Path $runs | Out-Null }

# SOFT kill (shared sentinel with the pure-python heartbeat).
if (Test-Path (Join-Path $here "PAUSED")) {
    Add-Content -Path $log -Value "$stamp  SKIPPED (PAUSED)" -Encoding utf8
    exit 0
}

# Episode lock — owned HERE (both the mic and the heartbeat may spawn us;
# one episode at a time). A lock older than 30 min is a crashed episode's
# leftover and is taken over.
$lockFile = Join-Path $here "wake-agent.lock"
# Atomic acquire (create-if-absent). Closes the TOCTOU window between the old
# Test-Path check and the Set-Content write: when the mic and the heartbeat
# spawn us back-to-back, exactly one CreateNew wins. Guardrail: the write is
# wrapped in finally so a write fault never leaks the file handle.
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
    # Lock exists. Fresh (<30min) => another episode owns it, yield. Stale
    # (>=30min) => crashed leftover, take over. If the file vanished under us
    # (peer takeover) Get-Item would throw; treat "gone" as free and retry.
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

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"

# Ensure the local proxy is present even when invoked from a bare environment
# (Task Scheduler): claude is a Node app, ignores WinINET, and a direct
# connection to the API is geo-blocked (403). Idempotent if already set.
if (-not $env:HTTPS_PROXY) {
    $env:HTTP_PROXY  = "http://127.0.0.1:2080"
    $env:HTTPS_PROXY = "http://127.0.0.1:2080"
    $env:NO_PROXY    = "localhost,127.0.0.1,::1"
}

function Get-Head {
    try {
        $j = & python $trace lineage-show --workspace $repo --scope skill-evolution 2>$null | Out-String
        if ($j -match '"head_frame_id":\s*"([^"]+)"') { return $Matches[1] }
    } catch {}
    return "?"
}

$headBefore = Get-Head
$outFile = Join-Path $runs "$stamp.json"

$errFile = Join-Path $runs "$stamp.err.txt"
try {
    # Keep the child's UTF-8 streams as bytes until explicit decoding. PS 5.1
    # native redirection decodes through the console codepage and re-encodes as
    # UTF-16, which can corrupt CJK and even swallow adjacent JSON quotes.
    & cmd /c "claude -p `"现在醒来，执行这一回合的自主工作。照系统提示的纪律来。`" --append-system-prompt-file `"$prompt`" --dangerously-skip-permissions --output-format json 1>`"$outFile`" 2>`"$errFile`""
    $rc = $LASTEXITCODE
    $headAfter = Get-Head

    $cost = "?"; $turns = "?"; $ok = "?"
    try {
        $utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
        $transcript = [System.IO.File]::ReadAllText($outFile, $utf8Strict)
        $j = $transcript | ConvertFrom-Json
        $cost  = $j.total_cost_usd
        $turns = $j.num_turns
        $ok    = $j.subtype
    } catch {}

    $moved = if ($headBefore -ne $headAfter) { "ledger_advanced" } else { "ledger_unchanged" }
    Add-Content -Path $log -Value "$stamp  rc=$rc  $ok  turns=$turns  cost=`$$cost  $moved  head=$headAfter" -Encoding utf8
    exit $rc
}
catch {
    Add-Content -Path $log -Value "$stamp  ERROR $($_.Exception.Message)" -Encoding utf8
    exit 1
}
finally {
    Remove-Item -Path $lockFile -Force -ErrorAction SilentlyContinue
}
