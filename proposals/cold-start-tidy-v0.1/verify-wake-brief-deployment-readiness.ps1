param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path,
    [string]$SkillRoot = "D:\CodexData\skills\solve-with-weilan",
    [switch]$Json
)

$ErrorActionPreference = "Stop"

function Get-FileSha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$implRoot = Join-Path $RepoRoot "proposals\bounded-scheduler-v0.1\impl"
$source = Join-Path $implRoot "wake_brief.py"
$target = Join-Path $SkillRoot "scripts\wake_brief.py"
$skillScripts = Join-Path $SkillRoot "scripts"
$tests = @(
    "proposals/bounded-scheduler-v0.1/impl/test_bounded_scheduler.py",
    "proposals/bounded-scheduler-v0.1/impl/test_window.py",
    "proposals/bounded-scheduler-v0.1/impl/test_wake_brief.py",
    "proposals/bounded-scheduler-v0.1/impl/test_wake_brief_integration.py"
)

if (-not (Test-Path -LiteralPath $source)) {
    throw "Missing wake_brief source: $source"
}
if (-not (Test-Path -LiteralPath $skillScripts)) {
    throw "Missing deployed skill scripts directory: $skillScripts"
}

$wakeFiles = Get-ChildItem -LiteralPath $skillScripts -Filter "wake*" -File -ErrorAction Stop |
    Select-Object -ExpandProperty FullName

$pytestArgs = @("-m", "pytest") + $tests + @("-q")
$pytest = & python @pytestArgs 2>&1
$pytestExit = $LASTEXITCODE

$report = [ordered]@{
    schema_version = "wake_brief_deployment_readiness_v0.1"
    generated_at_utc = [DateTimeOffset]::UtcNow.ToString("o")
    repo_root = $RepoRoot
    source_artifact = $source
    source_sha256 = Get-FileSha256 $source
    target_artifact = $target
    target_exists = Test-Path -LiteralPath $target
    target_sha256 = Get-FileSha256 $target
    deployed_skill_wake_files = @($wakeFiles)
    tests = $tests
    pytest_exit_code = $pytestExit
    pytest_output = ($pytest -join "`n")
    owner_manual_steps_required = @(
        "copy source_artifact to target_artifact only after explicit owner adoption",
        "add one red-zone wake_prompt/harness instruction that invokes wake_brief before manual long-ledger reads",
        "run the verification checklist in wake-brief-deployment-execution-pack-v0.1.md",
        "rollback by removing target_artifact if it was newly added and reverting the prompt/harness edit"
    )
    crossed_irreversible_gate = $false
}

if ($Json) {
    $report | ConvertTo-Json -Depth 6
} else {
    "wake_brief deployment readiness"
    "source: $($report.source_artifact)"
    "source_sha256: $($report.source_sha256)"
    "target: $($report.target_artifact)"
    "target_exists: $($report.target_exists)"
    "deployed_skill_wake_files: $(@($wakeFiles).Count)"
    "pytest_exit_code: $pytestExit"
    $report.pytest_output
    "crossed_irreversible_gate: false"
}

exit $pytestExit
