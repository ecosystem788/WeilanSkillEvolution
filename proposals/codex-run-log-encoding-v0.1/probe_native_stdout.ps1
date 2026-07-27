# Read-only probe: does PS 5.1 `1>` corrupt a native command's UTF-8 stdout on
# this host, and does setting [Console]::OutputEncoding repair it? Writes only
# inside this proposal directory. The verdict is bytes, not rendering.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$emit = Join-Path $here "emit_utf8.py"

function Show-Bytes($label, $path) {
    $b = [System.IO.File]::ReadAllBytes($path)
    Write-Output ("{0,-18}: {1}" -f $label, (($b | ForEach-Object { $_.ToString('x2') }) -join ' '))
}

Write-Output ("Console.OutputEncoding = " + [Console]::OutputEncoding.WebName + " (cp" + [Console]::OutputEncoding.CodePage + ")")
Write-Output ("producer emits (UTF-8): e6 88 91 e4 bc 9a e5 85 88 0a   = U+6211 U+4F1A U+5148")
Write-Output ("faithful UTF-16LE record would be: ff fe 11 62 1a 4f 48 51 0d 00 0a 00")

$a = Join-Path $here "probe-asis.bin"
& python $emit 1> $a
Show-Bytes "AS SHIPPED" $a

$prev = [Console]::OutputEncoding
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $b = Join-Path $here "probe-fixed.bin"
    & python $emit 1> $b
    Show-Bytes "UTF8 CONSOLE" $b
} finally {
    [Console]::OutputEncoding = $prev
}
