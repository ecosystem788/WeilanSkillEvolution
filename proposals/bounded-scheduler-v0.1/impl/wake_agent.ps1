# Model-in-the-loop wake: one bounded Claude episode, contained as one OS tree.
param([string]$RescueContext = "")

$ErrorActionPreference = "Stop"
$scriptHome = Split-Path -Parent $MyInvocation.MyCommand.Path
$here = if ($env:WEILAN_WAKE_AGENT_TEST_ROOT) { $env:WEILAN_WAKE_AGENT_TEST_ROOT } else { $scriptHome }
$repo = if ($env:WEILAN_WAKE_AGENT_TEST_REPO) { $env:WEILAN_WAKE_AGENT_TEST_REPO } else { "D:\WeilanSkillEvolution" }
$log = Join-Path $here "wake-agent.log"
$runs = Join-Path $here "wake-agent-runs"
$prompt = Join-Path $scriptHome "wake_prompt.md"
$trace = if ($env:WEILAN_WAKE_AGENT_TEST_TRACE) { $env:WEILAN_WAKE_AGENT_TEST_TRACE } else { "C:/Users/zy/.claude/skills/solve-with-weilan/scripts/weilan_trace.py" }
$alerts = Join-Path $here "peer-health-alerts.jsonl"
$lockFile = Join-Path $here "wake-agent.lock"
$stamp = Get-Date -Format "yyyy-MM-ddTHH-mm-ss"
$lockSchema = "weilan_wake_agent_lock_v0.3"
$containmentVersion = "windows_job_kill_on_close_v1"
if (-not (Test-Path $here)) { New-Item -ItemType Directory -Path $here | Out-Null }
if (-not (Test-Path $runs)) { New-Item -ItemType Directory -Path $runs | Out-Null }

if (Test-Path (Join-Path $here "PAUSED")) {
    Add-Content -Path $log -Value "$stamp  SKIPPED (PAUSED)" -Encoding utf8
    exit 0
}

if (-not ("WeiLanJobNativeV3" -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class WeiLanJobNativeV3 {
    public const UInt32 CREATE_SUSPENDED = 0x00000004;
    public const UInt32 CREATE_NO_WINDOW = 0x08000000;
    public const UInt32 JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    public const UInt32 HANDLE_FLAG_INHERIT = 0x00000001;
    public const UInt32 INFINITE = 0xffffffff;

    [StructLayout(LayoutKind.Sequential)]
    public struct SECURITY_ATTRIBUTES {
        public Int32 nLength; public IntPtr lpSecurityDescriptor; public Int32 bInheritHandle;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct STARTUPINFO {
        public Int32 cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public Int32 dwX; public Int32 dwY; public Int32 dwXSize; public Int32 dwYSize;
        public Int32 dwXCountChars; public Int32 dwYCountChars; public Int32 dwFillAttribute;
        public Int32 dwFlags; public Int16 wShowWindow; public Int16 cbReserved2;
        public IntPtr lpReserved2; public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {
        public IntPtr hProcess; public IntPtr hThread; public Int32 dwProcessId; public Int32 dwThreadId;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public Int64 PerProcessUserTimeLimit; public Int64 PerJobUserTimeLimit; public UInt32 LimitFlags;
        public UIntPtr MinimumWorkingSetSize; public UIntPtr MaximumWorkingSetSize;
        public UInt32 ActiveProcessLimit; public UIntPtr Affinity; public UInt32 PriorityClass; public UInt32 SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS {
        public UInt64 ReadOperationCount; public UInt64 WriteOperationCount; public UInt64 OtherOperationCount;
        public UInt64 ReadTransferCount; public UInt64 WriteTransferCount; public UInt64 OtherTransferCount;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation; public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit; public UIntPtr JobMemoryLimit; public UIntPtr PeakProcessMemoryUsed; public UIntPtr PeakJobMemoryUsed;
    }

    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern IntPtr CreateJobObject(IntPtr attrs, string name);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool SetInformationJobObject(IntPtr job, Int32 infoClass, IntPtr info, UInt32 length);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool SetHandleInformation(IntPtr handle, UInt32 mask, UInt32 flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool CreateProcess(string app, StringBuilder commandLine, IntPtr processAttrs, IntPtr threadAttrs,
        bool inheritHandles, UInt32 flags, IntPtr environment, string currentDirectory, ref STARTUPINFO startupInfo,
        out PROCESS_INFORMATION processInformation);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern UInt32 ResumeThread(IntPtr thread);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool TerminateProcess(IntPtr process, UInt32 exitCode);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern UInt32 WaitForSingleObject(IntPtr handle, UInt32 milliseconds);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool GetExitCodeProcess(IntPtr process, out UInt32 exitCode);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool CloseHandle(IntPtr handle);
}
'@
}

function Get-OwnerStartedAt {
    return (Get-Process -Id $PID -ErrorAction Stop).StartTime.ToUniversalTime().ToString("o")
}

function New-LockRecord([string]$containment) {
    return [ordered]@{
        schema_version = $lockSchema
        owner_pid = $PID
        owner_started_at = Get-OwnerStartedAt
        containment_version = $containment
        job_handle_inheritable = $false
        breakaway_allowed = $false
        acquired_at = (Get-Date).ToUniversalTime().ToString("o")
    }
}

function Acquire-EpisodeLock([string]$path) {
    $content = (New-LockRecord "pending") | ConvertTo-Json -Compress
    $fs = $null; $sw = $null
    try {
        $fs = [System.IO.File]::Open($path, [System.IO.FileMode]::CreateNew,
            [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $sw = New-Object System.IO.StreamWriter($fs, (New-Object System.Text.UTF8Encoding($false)))
        $sw.Write($content); $sw.Flush()
    } finally {
        if ($sw) { $sw.Dispose() }
        if ($fs) { $fs.Dispose() }
    }
}

function Update-EpisodeLock([string]$containment) {
    $tmp = "$lockFile.$PID.tmp"
    $backup = "$lockFile.$PID.bak"
    [System.IO.File]::WriteAllText($tmp, ((New-LockRecord $containment) | ConvertTo-Json -Compress),
        (New-Object System.Text.UTF8Encoding($false)))
    try { [System.IO.File]::Replace($tmp, $lockFile, $backup) }
    finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
    }
}

function Get-HeadAndOpenState {
    if ($env:WEILAN_WAKE_AGENT_TEST_ROOT -and $env:WEILAN_WAKE_AGENT_TEST_HEAD) {
        return [pscustomobject]@{
            head = $env:WEILAN_WAKE_AGENT_TEST_HEAD
            is_open = ($env:WEILAN_WAKE_AGENT_TEST_HEAD_OPEN -eq "1")
        }
    }
    try {
        $raw = & python $trace lineage-show --workspace $repo --scope skill-evolution 2>$null | Out-String
        if ($LASTEXITCODE -ne 0) { return $null }
        $lineage = $raw | ConvertFrom-Json -ErrorAction Stop
        $head = [string]$lineage.branches.main.head_frame_id
        if ([string]::IsNullOrWhiteSpace($head)) { return $null }
        $validateRaw = & python $trace validate --frame-id $head --require-closed 2>$null | Out-String
        $validateRc = $LASTEXITCODE
        if ($validateRc -eq 0) { return [pscustomobject]@{ head=$head; is_open=$false } }
        $validate = $validateRaw | ConvertFrom-Json -ErrorAction Stop
        $isOpen = @($validate.errors) -contains "frame must be closed"
        return [pscustomobject]@{ head=$head; is_open=$isOpen }
    } catch { return $null }
}

function Test-ActiveOrphanAlert([string]$incident, [string]$head) {
    try {
        if (-not (Test-Path -LiteralPath $alerts)) { return $false }
        $latest = $null
        foreach ($line in [System.IO.File]::ReadAllLines($alerts, [System.Text.Encoding]::UTF8)) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $row = $line | ConvertFrom-Json -ErrorAction Stop
            if ([string]$row.incident_key -eq $incident) { $latest = $row }
        }
        return ($null -ne $latest -and [string]$latest.kind -eq "orphan_frame" -and
            @("raised", "reopened") -contains [string]$latest.event -and
            [string]$latest.parent_frame_id -eq $head)
    } catch { return $false }
}

function Test-OwnerDead($record) {
    try {
        $ownerPid = [int]$record.owner_pid
        if ($ownerPid -le 0 -or [string]::IsNullOrWhiteSpace([string]$record.owner_started_at)) { return $false }
        $process = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
        if ($null -eq $process) { return $true }
        $actual = $process.StartTime.ToUniversalTime().ToString("o")
        return $actual -ne [string]$record.owner_started_at
    } catch { return $false }
}

function Test-RescueTakeover {
    if ([string]::IsNullOrWhiteSpace($RescueContext)) { return $false }
    try {
        $contextJson = if ($RescueContext.TrimStart().StartsWith("{")) {
            $RescueContext
        } else {
            [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($RescueContext))
        }
        $context = $contextJson | ConvertFrom-Json -ErrorAction Stop
        $head = [string]$context.orphan_head_frame_id
        $incident = [string]$context.incident_key
        if ([string]::IsNullOrWhiteSpace($head) -or [string]::IsNullOrWhiteSpace($incident)) { return $false }
        $headState = Get-HeadAndOpenState
        if ($null -eq $headState -or -not $headState.is_open -or $headState.head -ne $head) { return $false }
        if (-not (Test-ActiveOrphanAlert $incident $head)) { return $false }
        $record = [System.IO.File]::ReadAllText($lockFile, [System.Text.Encoding]::UTF8) | ConvertFrom-Json -ErrorAction Stop
        if ([string]$record.schema_version -ne $lockSchema -or
            [string]$record.containment_version -ne $containmentVersion -or
            $record.job_handle_inheritable -ne $false -or $record.breakaway_allowed -ne $false) { return $false }
        return Test-OwnerDead $record
    } catch { return $false }
}

# Serialize initial acquire and rescue validation/remove/reacquire as one local
# critical section.  The Job handle itself is never inherited by cmd/claude.
$gate = New-Object System.Threading.Mutex($false, "Local\WeilanWakeAgentV3Acquire")
$gateHeld = $false; $acquired = $false; $skipReason = $null
try {
    try { $gateHeld = $gate.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $gateHeld = $true }
    if (-not $gateHeld) { $skipReason = "acquire critical section busy" }
    elseif (-not (Test-Path -LiteralPath $lockFile)) {
        try { Acquire-EpisodeLock $lockFile; $acquired = $true } catch { $skipReason = "lost acquire race" }
    } else {
        $stale = $false
        try { $stale = (((Get-Date) - (Get-Item $lockFile -ErrorAction Stop).LastWriteTime).TotalMinutes -ge 30) }
        catch { $skipReason = "lock unreadable" }
        $rescueAllowed = $false
        if (-not $stale -and -not $skipReason) { $rescueAllowed = Test-RescueTakeover }
        if ($stale -or $rescueAllowed) {
            Remove-Item -LiteralPath $lockFile -Force -ErrorAction SilentlyContinue
            try { Acquire-EpisodeLock $lockFile; $acquired = $true } catch { $skipReason = "lost takeover race" }
        } elseif (-not $skipReason) { $skipReason = "episode already running or rescue proof failed" }
    }
} finally {
    if ($gateHeld) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
if (-not $acquired) {
    Add-Content -Path $log -Value "$stamp  SKIPPED ($skipReason)" -Encoding utf8
    exit 0
}

Set-Location $repo
$env:PYTHONIOENCODING = "utf-8"
if (-not $env:HTTPS_PROXY) {
    $env:HTTP_PROXY = "http://127.0.0.1:2080"
    $env:HTTPS_PROXY = "http://127.0.0.1:2080"
    $env:NO_PROXY = "localhost,127.0.0.1,::1,token-plan.cn-beijing.maas.aliyuncs.com,ws-s0l7d3yz7axp4uwz.cn-beijing.maas.aliyuncs.com,api.minimaxi.com,www.minimaxi.com,api.deepseek.com"
}

function Get-Head {
    $state = Get-HeadAndOpenState
    if ($null -ne $state) { return $state.head }
    return "?"
}

function Start-ContainedCommand([string]$commandLine) {
    $job = [WeiLanJobNativeV3]::CreateJobObject([IntPtr]::Zero, $null)
    if ($job -eq [IntPtr]::Zero) { throw "CreateJobObject failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
    $pi = New-Object WeiLanJobNativeV3+PROCESS_INFORMATION
    try {
        if (-not [WeiLanJobNativeV3]::SetHandleInformation($job,
            [WeiLanJobNativeV3]::HANDLE_FLAG_INHERIT, 0)) {
            throw "SetHandleInformation failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
        }
        $limits = New-Object WeiLanJobNativeV3+JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        # Nested structs are value types: mutate a copy, then assign it back,
        # otherwise PowerShell changes only the boxed temporary and the Job
        # silently receives LimitFlags=0.
        $basic = $limits.BasicLimitInformation
        $basic.LimitFlags = [WeiLanJobNativeV3]::JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        $limits.BasicLimitInformation = $basic
        $size = [Runtime.InteropServices.Marshal]::SizeOf($limits)
        $ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal($size)
        try {
            [Runtime.InteropServices.Marshal]::StructureToPtr($limits, $ptr, $false)
            if (-not [WeiLanJobNativeV3]::SetInformationJobObject($job, 9, $ptr, $size)) {
                throw "SetInformationJobObject failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
            }
        } finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($ptr) }

        $si = New-Object WeiLanJobNativeV3+STARTUPINFO
        $si.cb = [Runtime.InteropServices.Marshal]::SizeOf($si)
        $buffer = New-Object System.Text.StringBuilder($commandLine)
        $flags = [WeiLanJobNativeV3]::CREATE_SUSPENDED -bor [WeiLanJobNativeV3]::CREATE_NO_WINDOW
        if (-not [WeiLanJobNativeV3]::CreateProcess($env:ComSpec, $buffer, [IntPtr]::Zero, [IntPtr]::Zero,
            $false, $flags, [IntPtr]::Zero, $repo, [ref]$si, [ref]$pi)) {
            throw "CreateProcess failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error()) cwd=$repo command=$commandLine"
        }
        $assignOk = if ($env:WEILAN_WAKE_AGENT_TEST_ROOT -and $env:WEILAN_WAKE_AGENT_FORCE_ASSIGN_FAILURE -eq "1") {
            $false
        } else { [WeiLanJobNativeV3]::AssignProcessToJobObject($job, $pi.hProcess) }
        if (-not $assignOk) {
            $null = [WeiLanJobNativeV3]::TerminateProcess($pi.hProcess, 125)
            throw "AssignProcessToJobObject failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
        }
        Update-EpisodeLock $containmentVersion
        if ([WeiLanJobNativeV3]::ResumeThread($pi.hThread) -eq 0xffffffff) {
            $null = [WeiLanJobNativeV3]::TerminateProcess($pi.hProcess, 126)
            throw "ResumeThread failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
        }
        return [pscustomobject]@{ Job=$job; Process=$pi.hProcess; Thread=$pi.hThread; Pid=$pi.dwProcessId }
    } catch {
        if ($pi.hThread -ne [IntPtr]::Zero) { $null = [WeiLanJobNativeV3]::CloseHandle($pi.hThread) }
        if ($pi.hProcess -ne [IntPtr]::Zero) { $null = [WeiLanJobNativeV3]::CloseHandle($pi.hProcess) }
        $null = [WeiLanJobNativeV3]::CloseHandle($job)
        throw
    }
}

$headBefore = Get-Head
$outFile = Join-Path $runs "$stamp.json"
$errFile = Join-Path $runs "$stamp.err.txt"
$contained = $null
try {
    $agentPayload = if ($env:WEILAN_WAKE_AGENT_TEST_COMMAND) {
        $env:WEILAN_WAKE_AGENT_TEST_COMMAND
    } else {
        $wakeText = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(
            "546w5Zyo6YaS5p2l77yM5omn6KGM6L+Z5LiA5Zue5ZCI55qE6Ieq5Li75bel5L2c44CC54Wn57O757uf5o+Q56S655qE57qq5b6L5p2l44CC"))
        'claude -p "{0}" --append-system-prompt-file "{1}" --effort high --dangerously-skip-permissions --output-format json' -f $wakeText, $prompt
    }
    # cmd owns byte redirection; PowerShell 5.1 never decodes native output.
    $commandLine = ('"{0}" /d /s /c "{1} 1>"{2}" 2>"{3}""' -f
        $env:ComSpec, $agentPayload, $outFile, $errFile)
    $contained = Start-ContainedCommand $commandLine
    $wait = [WeiLanJobNativeV3]::WaitForSingleObject($contained.Process, [WeiLanJobNativeV3]::INFINITE)
    if ($wait -ne 0) { throw "WaitForSingleObject failed: $wait" }
    [uint32]$exitCode = 1
    if (-not [WeiLanJobNativeV3]::GetExitCodeProcess($contained.Process, [ref]$exitCode)) {
        throw "GetExitCodeProcess failed: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
    }
    $rc = [int]$exitCode
    $headAfter = Get-Head
    $cost = "?"; $turns = "?"; $ok = "?"
    try {
        $utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
        $transcript = [System.IO.File]::ReadAllText($outFile, $utf8Strict)
        $j = $transcript | ConvertFrom-Json
        $cost = $j.total_cost_usd; $turns = $j.num_turns; $ok = $j.subtype
    } catch {}
    $moved = if ($headBefore -ne $headAfter) { "ledger_advanced" } else { "ledger_unchanged" }
    Add-Content -Path $log -Value "$stamp  rc=$rc  $ok  turns=$turns  cost=`$$cost  $moved  head=$headAfter containment=$containmentVersion" -Encoding utf8
    exit $rc
} catch {
    Add-Content -Path $log -Value "$stamp  ERROR $($_.Exception.Message)" -Encoding utf8
    exit 1
} finally {
    if ($null -ne $contained) {
        if ($contained.Thread -ne [IntPtr]::Zero) { $null = [WeiLanJobNativeV3]::CloseHandle($contained.Thread) }
        if ($contained.Process -ne [IntPtr]::Zero) { $null = [WeiLanJobNativeV3]::CloseHandle($contained.Process) }
        if ($contained.Job -ne [IntPtr]::Zero) { $null = [WeiLanJobNativeV3]::CloseHandle($contained.Job) }
    }
    Remove-Item -LiteralPath $lockFile -Force -ErrorAction SilentlyContinue
}
