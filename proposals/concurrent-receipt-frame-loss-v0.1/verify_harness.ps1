$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
python -m pytest (Join-Path $Here "test_concurrent_receipts.py") -q
