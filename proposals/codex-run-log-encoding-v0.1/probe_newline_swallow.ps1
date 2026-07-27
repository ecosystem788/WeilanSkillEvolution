$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$emit = Join-Path $here "emit_two_rows.py"
& python $emit 1> (Join-Path $here "probe-two-asis.jsonl")
