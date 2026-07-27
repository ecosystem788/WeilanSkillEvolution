import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
WAKE_CODEX = HERE.parent / "bounded-scheduler-v0.1" / "impl" / "wake_codex.ps1"
EMITTER = HERE / "emit_json.py"


def _record_native_utf8(tmp_path: Path, *, guarded: bool) -> str:
    output = tmp_path / ("guarded.jsonl" if guarded else "cp936.jsonl")
    body = [
        "$ErrorActionPreference = 'Stop'",
        "[Console]::OutputEncoding = [Text.Encoding]::GetEncoding(936)",
    ]
    if guarded:
        body.extend(
            [
                "$previousOutputEncoding = [Console]::OutputEncoding",
                "try {",
                "    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)",
                "    & python $args[0] 1> $args[1]",
                "} finally {",
                "    [Console]::OutputEncoding = $previousOutputEncoding",
                "}",
            ]
        )
    else:
        body.append("& python $args[0] 1> $args[1]")

    harness = tmp_path / ("guarded.ps1" if guarded else "cp936.ps1")
    harness.write_text("\n".join(body) + "\n", encoding="ascii")
    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
            str(EMITTER),
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return output.read_bytes().decode("utf-16")


def test_forced_cp936_control_is_red_and_utf8_guard_is_green(tmp_path):
    broken = _record_native_utf8(tmp_path, guarded=False)
    try:
        broken_row = json.loads(broken)
    except json.JSONDecodeError:
        broken_row = None
    assert broken_row is None or broken_row["item"]["text"] != "我会先"

    repaired = json.loads(_record_native_utf8(tmp_path, guarded=True))
    assert repaired["item"]["text"] == "我会先"


def test_wake_codex_binds_and_restores_utf8_console_encoding():
    source = WAKE_CODEX.read_text(encoding="utf-8")
    save = "$previousOutputEncoding = [Console]::OutputEncoding"
    bind = "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)"
    restore = "[Console]::OutputEncoding = $previousOutputEncoding"

    assert source.count(save) == 1
    assert source.count(bind) == 1
    assert source.count(restore) == 1
    assert source.index(save) < source.index(bind) < source.index("& codex exec")
    assert source.index("& codex exec") < source.rindex("finally {") < source.index(restore)
