"""Read-only probe: do the existing wake_agent.ps1 source assertions pin the
cmd-owned byte redirection?  Mutate the source text IN MEMORY only.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "wake_agent.ps1").read_text(encoding="utf-8")

ASSERTS = [
    ("CREATE_SUSPENDED", lambda s: "CREATE_SUSPENDED" in s),
    ("AssignProcessToJobObject", lambda s: "AssignProcessToJobObject" in s),
    ("JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE", lambda s: "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE" in s),
    ("SetHandleInformation", lambda s: "SetHandleInformation" in s),
    ("utf8encoding($false, $true)", lambda s: "new-object system.text.utf8encoding($false, $true)" in s.lower()),
    ("--model claude-opus-5", lambda s: "--model claude-opus-5" in s),
    ("--effort high", lambda s: "--effort high" in s),
]

# The invariant under test: bytes must be redirected by cmd, never by PS 5.1.
REAL_LINE = '''    $commandLine = ('"{0}" /d /s /c "{1} 1>"{2}" 2>"{3}""' -f
        $env:ComSpec, $agentPayload, $outFile, $errFile)
    $contained = Start-ContainedCommand $commandLine'''
assert REAL_LINE in src, "source shape drifted; re-read wake_agent.ps1 before trusting this probe"

# Mutation: hand the redirection back to PowerShell (the exact shape that was
# proven corrupting in the Codex incident), keeping everything else intact.
MUTANT_LINE = '''    $contained = $null
    & claude -p $agentPayload 1> $outFile 2> $errFile
    $rc = $LASTEXITCODE'''
mutant = src.replace(REAL_LINE, MUTANT_LINE)
assert mutant != src

print("baseline (real source):")
for name, fn in ASSERTS:
    print(f"  {'PASS' if fn(src) else 'FAIL'}  {name}")
print("mutant (PowerShell-owned redirection, the corrupting shape):")
survivors = 0
for name, fn in ASSERTS:
    ok = fn(mutant)
    survivors += ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"\nassertions still green on the corrupting mutant: {survivors}/{len(ASSERTS)}")
print("cmd-owned redirection still present in mutant:",
      bool(re.search(r'ComSpec.*?/c', mutant, re.S)))
