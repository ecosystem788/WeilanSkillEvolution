param(
    [Parameter(Mandatory=$true)][string]$InstallRoot,
    [string]$Receipt
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$manager = Join-Path $PSScriptRoot 'release_installer.py'
$manifest = Join-Path $PSScriptRoot 'install-manifest.json'
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    [ordered]@{
        schema = 'weilan_release_preflight_v0.1'
        status = 'blocked'
        issues = @(
            [ordered]@{
                code = 'prerequisite_python_missing'
                message = "Required command 'python' was not found on PATH."
                hint = "Install Python 3 and ensure 'python' is available on PATH."
            }
        )
        discoveries = [ordered]@{ commands = [ordered]@{ python = $null }; skill_payloads = @() }
    } | ConvertTo-Json -Depth 5
    exit 4
}
$argsList = @(
    $manager, 'install',
    '--repo-root', $repoRoot,
    '--install-root', [IO.Path]::GetFullPath($InstallRoot),
    '--manifest', $manifest
)
if ($Receipt) { $argsList += @('--receipt', [IO.Path]::GetFullPath($Receipt)) }
& python @argsList
exit $LASTEXITCODE
