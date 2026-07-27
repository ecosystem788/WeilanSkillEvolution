# Does the cp936 mis-decode merely mangle CJK, or does it also destroy JSON
# structure by swallowing adjacent ASCII? Verdict: can the recorded line be
# parsed back as JSON at all.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$emit = Join-Path $here "emit_json.py"
$a = Join-Path $here "probe-json-asis.jsonl"
& python $emit 1> $a
$prev = [Console]::OutputEncoding
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $b = Join-Path $here "probe-json-fixed.jsonl"
    & python $emit 1> $b
} finally { [Console]::OutputEncoding = $prev }
Write-Output "wrote $a and $b"
