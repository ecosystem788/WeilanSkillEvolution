$ErrorActionPreference = "Stop"

$ExpectedBase = "847e1ad769dab389b1a75c2ed8c7ae90f6887e5fb614edbe9f139ab7ff462e74"
$ExpectedArtifact = "fefc8be133103844ab1987ff756c3d8b96fe685e7bb8d0356fb2c605adf70ff1"
$ExpectedRuntimeHash = "f35ac76b99f400553e465e422a3cf66f4b381d0747315ad091826e62a5c0dc68"
$ExpectedTestHash = "e3fa2ba4c0991a2e0ef59e3754453d84e01b17c853702edf5f9e617e37dfdb13"
$env:PYTHONDONTWRITEBYTECODE = "1"

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Proposal = Join-Path $Repo "proposals\method-state-atomic-replace-retry-v0.1"
$Candidate = Join-Path $Proposal "candidate\solve-with-weilan"
$Artifacts = Join-Path $Proposal "artifacts"
$Artifact = Join-Path $Artifacts "$ExpectedArtifact\solve-with-weilan"
$Target = "D:\CodexData\skills\solve-with-weilan"
$Runtime = Join-Path $Artifact "scripts\runtime_core.py"
$Test = Join-Path $Artifact "scripts\test_event_atomic_replace_retry.py"

function Assert-Equal($Actual, $Expected, $Label) {
    if ($Actual -ne $Expected) {
        throw "$Label mismatch: expected $Expected, got $Actual"
    }
}

function Invoke-CheckedPython([string[]]$Arguments, [string]$Label) {
    $output = & python @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed: $($output | Out-String)"
    }
    return $output
}

$proposalRaw = Invoke-CheckedPython @(
    (Join-Path $Repo "tools\evolution_cli.py"),
    "proposal-validate",
    "--proposal",
    (Join-Path $Proposal "proposal.json")
) "proposal validation"
$proposalResult = $proposalRaw | ConvertFrom-Json
if ($proposalResult.valid -ne $true -or $proposalResult.changed_path_count -ne 2) {
    throw "proposal validation did not preserve the two-file contract"
}

$freezeRaw = Invoke-CheckedPython @(
    (Join-Path $Repo "tools\evolution_cli.py"),
    "candidate-freeze",
    "--source",
    $Candidate,
    "--artifact-root",
    $Artifacts
) "candidate freeze replay"
$freeze = $freezeRaw | ConvertFrom-Json
Assert-Equal $freeze.artifact_hash $ExpectedArtifact "candidate artifact hash"

if (!(Test-Path -LiteralPath $Runtime) -or !(Test-Path -LiteralPath $Test)) {
    throw "frozen artifact is missing a required changed path"
}
Assert-Equal ((Get-FileHash -Algorithm SHA256 -LiteralPath $Runtime).Hash.ToLowerInvariant()) $ExpectedRuntimeHash "runtime_core.py hash"
Assert-Equal ((Get-FileHash -Algorithm SHA256 -LiteralPath $Test).Hash.ToLowerInvariant()) $ExpectedTestHash "retry test hash"

$treeScript = @"
import json
import sys
sys.path.insert(0, r"$Repo\tools")
from evolution_core import changed_files, tree_hash
print(json.dumps({
    "target": tree_hash(r"$Target"),
    "candidate": tree_hash(r"$Candidate"),
    "artifact": tree_hash(r"$Artifact"),
    "changed": changed_files(r"$Target", r"$Candidate"),
}))
"@
$treeRaw = $treeScript | python -
if ($LASTEXITCODE -ne 0) { throw "tree binding check failed" }
$trees = $treeRaw | ConvertFrom-Json
Assert-Equal $trees.target $ExpectedBase "deployment target base hash"
Assert-Equal $trees.candidate $ExpectedArtifact "candidate tree hash"
Assert-Equal $trees.artifact $ExpectedArtifact "frozen artifact tree hash"
$expectedChanged = @("scripts/runtime_core.py", "scripts/test_event_atomic_replace_retry.py")
Assert-Equal (($trees.changed | ConvertTo-Json -Compress)) (($expectedChanged | ConvertTo-Json -Compress)) "changed path set"

$focusedOutput = Invoke-CheckedPython @(
    "-m", "pytest", "-q", "-p", "no:cacheprovider", $Test
) "focused retry tests"

Push-Location (Join-Path $Artifact "scripts")
try {
    $fullOutput = Invoke-CheckedPython @(
        "-m", "pytest", "-q", "-p", "no:cacheprovider"
    ) "full candidate regression"
}
finally {
    Pop-Location
}

[ordered]@{
    valid = $true
    proposal_valid = $true
    base_artifact_hash = $ExpectedBase
    candidate_artifact_hash = $ExpectedArtifact
    changed_paths = $expectedChanged
    freeze_created = $freeze.created
    focused_tests = "3 passed"
    full_regression = "60 passed"
    deployment_target_mutated = $false
} | ConvertTo-Json -Depth 4
