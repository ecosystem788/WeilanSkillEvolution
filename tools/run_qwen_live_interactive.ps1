param(
  [string]$Snapshot = "qwen3.7-plus-2026-05-26"
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Repo

Write-Host "Qwen live runner. Secrets are kept only in this PowerShell process."
Write-Host "Paste the OpenAI-compatible base URL, then the API key when prompted."
$BaseUrl = Read-Host "QWEN_BASE_URL"
$SecureKey = Read-Host "QWEN_API_KEY" -AsSecureString
$Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureKey)
try {
  $PlainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr)
}

$env:QWEN_BASE_URL = $BaseUrl
$env:QWEN_API_KEY = $PlainKey
$env:QWEN_MODEL_SNAPSHOT = $Snapshot

$OutRoot = Join-Path $Repo "v03runs\qwen-live-20260706"
New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null

python tools\qwen_v03_runner.py live-preflight `
  --output (Join-Path $OutRoot "LIVE_PREFLIGHT.json")
if ($LASTEXITCODE -ne 0) { throw "live-preflight failed" }

$Manifest = Get-Content "v03runs\cross-conflict-redesign-v2\CROSS_CONFLICT_V2_MANIFEST.json" | ConvertFrom-Json
$FixtureRoot = "v03runs\cross-conflict-redesign-v2\fixtures"
foreach ($Trial in $Manifest.trials) {
  $TrialRoot = Join-Path $OutRoot $Trial.trial_id
  New-Item -ItemType Directory -Force -Path $TrialRoot | Out-Null
  python tools\qwen_v03_runner.py run-trial `
    --arm $Trial.arm `
    --prompt-path $Trial.prompt `
    --fixture-root $FixtureRoot `
    --workspace-root $TrialRoot `
    --output (Join-Path $TrialRoot "telemetry.json") `
    --receipt-output (Join-Path $TrialRoot "receipt.json") `
    --tool-calls 5 `
    --context-tokens 4800
  if ($LASTEXITCODE -ne 0) { throw "trial failed: $($Trial.trial_id)" }
}

Remove-Item Env:\QWEN_API_KEY -ErrorAction SilentlyContinue
$PlainKey = $null

Write-Host "Qwen live run complete: $OutRoot"
Read-Host "Press Enter to close"
