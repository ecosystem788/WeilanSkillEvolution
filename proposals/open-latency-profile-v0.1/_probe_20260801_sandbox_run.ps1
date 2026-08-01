# Run one sandboxed `open` sample against a chosen skill tree.
# Usage: _sbx_run_0801.ps1 <skillRoot> <label> [profileOutPath]
param([string]$SkillRoot, [string]$Label, [string]$ProfileOut = "")

$sbx  = "D:\WeilanSkillEvolution\_sbx_0801"
$work = "$sbx\work"

robocopy "$sbx\pristine" $work /MIR /NFL /NDL /NJH /NJS /R:1 /W:1 | Out-Null
python D:\WeilanSkillEvolution\_sbx_prep_0801.py $work wf-20260801-134306-1c1731 wf-20260801-133458-441509 | Out-Null

$env:WEILAN_METHOD_HOME = $work
$trace = Join-Path $SkillRoot "scripts\weilan_trace.py"

$argv = @(
  $trace, "open", "--level", "L2",
  "--problem", "sandbox latency sample $Label",
  "--success", "sandbox latency sample $Label",
  "--workspace", "D:\WeilanSkillEvolution",
  "--scope", "skill-evolution",
  "--branch", "main",
  "--relation", "continue",
  "--parent", "wf-20260801-133458-441509"
)
if ($ProfileOut -ne "") { $argv = @("-m", "cProfile", "-o", $ProfileOut) + $argv }

$sw = [Diagnostics.Stopwatch]::StartNew()
& python @argv > "$sbx\_out_$Label.json" 2> "$sbx\_err_$Label.txt"
$rc = $LASTEXITCODE
$sw.Stop()

Remove-Item Env:\WEILAN_METHOD_HOME
[pscustomobject]@{ label = $Label; rc = $rc; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 3) } | ConvertTo-Json -Compress
