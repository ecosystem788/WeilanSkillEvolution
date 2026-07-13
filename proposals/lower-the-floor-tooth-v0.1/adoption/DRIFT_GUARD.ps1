$ErrorActionPreference = "Stop"

$ExpectedArtifact = "9b2130988817076de547dffe3627d31501d4f62e584a2d00daf979c8db36a3c9"
$ExpectedTraceHash = "1ea27f9f0cccfa1d8271140449773d355756696c47d2eaea2c067ad56b3576bd"
$ExpectedTestHash = "4a66e83d871af2f49c80ab9df6970f03710a350fea9b850fa3fee498dbd89c62"
$env:PYTHONDONTWRITEBYTECODE = "1"

$Repo = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$Proposal = Join-Path $Repo "proposals\lower-the-floor-tooth-v0.1"
$Artifact = Join-Path $Proposal "artifacts\$ExpectedArtifact\solve-with-weilan"
$Trace = Join-Path $Artifact "scripts\weilan_trace.py"
$Test = Join-Path $Artifact "scripts\test_memory_note.py"

function Assert-Equal($Actual, $Expected, $Label) {
    if ($Actual -ne $Expected) {
        throw "$Label mismatch: expected $Expected, got $Actual"
    }
}

if (!(Test-Path $Trace)) {
    throw "missing memory-note command file: $Trace"
}
if (!(Test-Path $Test)) {
    throw "missing drift-guard test file: $Test"
}

Assert-Equal ((Get-FileHash -Algorithm SHA256 $Trace).Hash.ToLowerInvariant()) $ExpectedTraceHash "weilan_trace.py hash"
Assert-Equal ((Get-FileHash -Algorithm SHA256 $Test).Hash.ToLowerInvariant()) $ExpectedTestHash "test_memory_note.py hash"

$traceText = Get-Content -Raw $Trace
foreach ($needle in @("def command_memory_note", "def command_memory_note_fenced", "memory-note")) {
    if (!$traceText.Contains($needle)) {
        throw "memory-note command evidence missing: $needle"
    }
}

$testText = Get-Content -Raw $Test
foreach ($needle in @("reject_equivalence_full", "retry_no_duplicate", "manual_equivalence", "rejects_are_atomic")) {
    if (!$testText.Contains($needle)) {
        throw "drift-guard assertion missing: $needle"
    }
}

$freezeRaw = python (Join-Path $Repo "tools\evolution_cli.py") candidate-freeze --source (Join-Path $Proposal "candidate\solve-with-weilan") --artifact-root (Join-Path $Proposal "artifacts")
$freeze = $freezeRaw | ConvertFrom-Json
Assert-Equal $freeze.artifact_hash $ExpectedArtifact "candidate-freeze artifact hash"

$syntaxScript = @"
from pathlib import Path
for path in [r"$Trace", r"$Test"]:
    compile(Path(path).read_text(encoding="utf-8"), path, "exec")
"@
$syntaxScript | python -

$testRaw = python $Test --temp-parent (Join-Path $Repo "staging")
$result = $testRaw | ConvertFrom-Json
foreach ($field in @("valid", "reject_equivalence_full", "retry_no_duplicate", "manual_equivalence", "rejects_are_atomic")) {
    if ($result.$field -ne $true) {
        throw "drift-guard result field failed: $field"
    }
}

$summary = [ordered]@{
    valid = $true
    artifact_hash = $ExpectedArtifact
    command_file_hash = $ExpectedTraceHash
    drift_guard_test_hash = $ExpectedTestHash
    freeze_created = $freeze.created
    reject_equivalence_full = $result.reject_equivalence_full
    retry_no_duplicate = $result.retry_no_duplicate
    manual_equivalence = $result.manual_equivalence
    rejects_are_atomic = $result.rejects_are_atomic
}
$summary | ConvertTo-Json -Depth 4
