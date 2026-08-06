# Codex wake -- one bounded headless `codex exec` episode (the second body).
# Same discipline as wake_agent.ps1 (Claude): PAUSED sentinel, own episode
# lock, bounded run, full transcript, one summary log line.
#
# 2026-07-11 CHARTER regime (owner decree, see CHARTER.md): full autonomy.
#   * --dangerously-bypass-approvals-and-sandbox: no sandbox, full machine use.
#   * Order comes from the constitution + dual-sign procedure in
#     wake_prompt_codex.md, not from a technical cage. Observer keeps veto.
#
# Kill switches (observer's buttons):
#   HARD : don't invoke it (nothing schedules this file by itself)
#   SOFT : create a file named PAUSED next to this script (shared sentinel)
#
# ASCII-only on purpose: PS 5.1 misreads BOM-less UTF-8; the Chinese prompt
# lives in wake_prompt_codex.md and is passed as an argument (UTF-16 safe).

$ErrorActionPreference = "Stop"
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo   = "D:\WeilanSkillEvolution"
$log    = Join-Path $here "wake-codex.log"
$runs   = Join-Path $here "wake-codex-runs"
$prompt = Join-Path $here "wake_prompt_codex.md"
$trace  = "C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py"
$stamp  = Get-Date -Format "yyyy-MM-ddTHH-mm-ss"
if (-not (Test-Path $runs)) { New-Item -ItemType Directory -Path $runs | Out-Null }

if (Test-Path (Join-Path $here "PAUSED")) {
    Add-Content -Path $log -Value "$stamp  SKIPPED (PAUSED)" -Encoding utf8
    exit 0
}

# Own episode lock (independent from Claude's -- the ledger is built for
# concurrent writers; one lock per body).
$lockFile = Join-Path $here "wake-codex.lock"
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

# Same proxy lesson as wake_agent.ps1: bare Task Scheduler env lacks the
# profile's proxy vars; codex (Node) goes direct and gets geo-blocked.
if (-not $env:HTTPS_PROXY) {
    $env:HTTP_PROXY  = "http://127.0.0.1:2080"
    $env:HTTPS_PROXY = "http://127.0.0.1:2080"
    . (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "proxy-no-proxy.ps1")
}

function Get-Head {
    try {
        $j = & python $trace lineage-show --workspace $repo --scope skill-evolution 2>$null | Out-String
        if ($j -match '"head_frame_id":\s*"([^"]+)"') { return $Matches[1] }
    } catch {}
    return "?"
}

$headBefore = Get-Head
$outFile   = Join-Path $runs "$stamp.jsonl"
$errFile   = Join-Path $runs "$stamp.err.txt"
$replyFile = Join-Path $runs "$stamp.last.md"

# Do NOT pass the Chinese prompt as an argument: PS 5.1 native-arg quoting
# breaks on embedded double quotes (the JSON examples) and splits it into
# many arguments. Keep the kick ASCII-only and have codex read the file.
$kick = "Wake up for ONE bounded autonomous episode. First read the file " +
        "'proposals/bounded-scheduler-v0.1/impl/wake_prompt_codex.md' " +
        "(UTF-8, Chinese) and follow it EXACTLY as this episode's discipline. " +
        "Scope, stated here so you have it BEFORE any recall: this " +
        "workspace has several ACTIVE scopes, and this episode's scope is " +
        "skill-evolution. Every memory-recall you run MUST pass " +
        "--scope skill-evolution. If an UNSCOPED recall returns " +
        "CONFIRM_REQUIRED with reason multiple_or_ambiguous_scopes, that " +
        "is an under-specified query, not an authority stop: re-run it " +
        "scoped and obey THAT result. A non-ACTIVE or no-continuation " +
        "result from the SCOPED recall still stops the episode -- write " +
        "the blocked-by-activation receipt and exit, exactly as the " +
        "prompt says. " +
        "Operational note: the skill-evolution ledger is large; every " +
        "weilan_trace.py lineage-show command MUST use a tool timeout of at " +
        "least 180000 ms. Never retry lineage-show with the default timeout. " +
        "It defines: cold-start recall, your work inbox, the tearoom rules, " +
        "the dual-sign decision procedure of the community CHARTER, and the " +
        "receipt you must write before exiting."

$previousOutputEncoding = [Console]::OutputEncoding
try {
    $ErrorActionPreference = "Continue"
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    & codex exec `
        --skip-git-repo-check `
        -C $repo `
        --dangerously-bypass-approvals-and-sandbox `
        --json `
        -o $replyFile `
        $kick 1> $outFile 2> $errFile
    $rc = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    $headAfter = Get-Head

    $moved = if ($headBefore -ne $headAfter) { "ledger_advanced" } else { "ledger_unchanged" }
    Add-Content -Path $log -Value "$stamp  rc=$rc  $moved  head=$headAfter" -Encoding utf8
    exit $rc
}
catch {
    Add-Content -Path $log -Value "$stamp  ERROR $($_.Exception.Message)" -Encoding utf8
    exit 1
}
finally {
    [Console]::OutputEncoding = $previousOutputEncoding
    Remove-Item -Path $lockFile -Force -ErrorAction SilentlyContinue
}
