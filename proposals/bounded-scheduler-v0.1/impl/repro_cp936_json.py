# Known-answer control for the byte-faithful capture fix (2026-07-14).
# Rebuilds the PRE-FIX wrapper (PowerShell-native 1>/2> redirection) and runs
# the same CJK fixture the regression test uses: it must FAIL on the old code
# for the new test to count as a real detector. Read-only wrt the live system.
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CURRENT = HERE / "run_wake_cron.ps1"

OLD_BLOCK = """    $savedErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & python $WakeScript --commit 1> $stdoutPath 2> $stderrPath
    $nativeRc = $LASTEXITCODE
    $ErrorActionPreference = $savedErrorActionPreference"""

FAKE_BODY = """import json
report = {
    'briefing': {'open_questions': ['\\u65b9\\u5411\\uff1a\\u5fae\\u6f9c\\u6001\\u52bf\\u611f\\u77e5' * 600]},
    'committed_frame': 'wf-fixture-ok',
    'receipt': {'crossed_irreversible_gate': False, 'stop_reason': '\\u9759\\u9ed8'},
}
print(json.dumps(report, ensure_ascii=False, indent=2))
"""

cur = CURRENT.read_text(encoding="utf-8")
start = cur.index("    # Capture the child")
end = cur.index("    $nativeRc = $LASTEXITCODE") + len("    $nativeRc = $LASTEXITCODE")
old_text = cur[:start] + OLD_BLOCK + cur[end:]

tmp = pathlib.Path(tempfile.mkdtemp(prefix="oldwrap-"))
oldwrap = tmp / "run_wake_cron_old.ps1"
oldwrap.write_text(old_text, encoding="utf-8")
fake = tmp / "fake_wake.py"
fake.write_text(FAKE_BODY, encoding="utf-8")

for cp in (65001, 936):
    log = tmp / f"cron-{cp}.log"
    inner = (
        f"chcp {cp} >nul & powershell -NoProfile -ExecutionPolicy Bypass "
        f"-File {oldwrap} -WakeScript {fake} -LogPath {log} -NoEscalate"
    )
    proc = subprocess.run(["cmd", "/c", inner], capture_output=True, timeout=60)
    txt = log.read_text(encoding="utf-8-sig", errors="replace") if log.exists() else "(no log)"
    would_pass = proc.returncode == 0 and " wake ok " in txt and "静默" in txt
    print(f"OLD capture code cp={cp}: rc={proc.returncode} regression_test_would_pass={would_pass}")
    print("   ", txt.strip()[:220])
