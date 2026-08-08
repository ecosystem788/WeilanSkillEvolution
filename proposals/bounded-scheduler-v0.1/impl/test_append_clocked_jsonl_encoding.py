import json
import os
from io import StringIO
from pathlib import Path
import subprocess
import sys

import append_clocked_jsonl


HERE = Path(__file__).resolve().parent
HELPER = HERE / "append_clocked_jsonl.py"

MINUS_SIGN = "\u2212"
CJK_TEXT = "\u4e2d\u6587"
BODY = f"repro {MINUS_SIGN} {CJK_TEXT} body"


def _run_helper(root, ledger_name, body, extra_env=None):
    env = os.environ.copy()
    env.pop("PYTHONIOENCODING", None)
    if extra_env:
        env.update(extra_env)
    field_file = root / "field.txt"
    field_file.write_text(body, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(HELPER),
            "--root",
            str(root),
            "--file",
            ledger_name,
            "--field-file",
            f"text={field_file}",
            "--allow-create",
        ],
        capture_output=True,
        env=env,
    )


def test_subprocess_u2212_and_cjk_receipt_matches_ledger_row(tmp_path):
    result = _run_helper(tmp_path, "ledger.jsonl", BODY)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    receipt = json.loads(result.stdout.decode("utf-8"))
    rows = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(rows[-1]) == receipt
    assert receipt["text"] == BODY
    assert receipt["time_authority"] == "clock"


def test_stdout_bytes_are_valid_utf8_and_roundtrip(tmp_path):
    result = _run_helper(tmp_path, "ledger.jsonl", BODY)
    assert result.returncode == 0
    decoded = result.stdout.decode("utf-8")
    assert json.loads(decoded)["text"] == BODY


def test_cjk_only_receipt_is_utf8_not_gbk_mojibake(tmp_path):
    result = _run_helper(tmp_path, "ledger.jsonl", CJK_TEXT)
    assert result.returncode == 0
    decoded = result.stdout.decode("utf-8")
    assert json.loads(decoded)["text"] == CJK_TEXT


def test_forced_gbk_stdio_still_emits_utf8_receipt(tmp_path):
    result = _run_helper(tmp_path, "ledger.jsonl", BODY, extra_env={"PYTHONIOENCODING": "gbk"})
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert json.loads(result.stdout.decode("utf-8"))["text"] == BODY


def test_stringio_capture_skips_reconfigure_and_succeeds(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"from":"seed"}\n', encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", StringIO())
    monkeypatch.setattr(sys, "stderr", StringIO())
    rc = append_clocked_jsonl.main(
        [
            "--root",
            str(tmp_path),
            "--file",
            ledger.name,
            "--field",
            "from=codex",
            "--field",
            f"text={BODY}",
        ]
    )
    assert rc == 0
    last = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert last["text"] == BODY
    assert last["time_authority"] == "clock"


def test_reserved_clock_field_still_returns_rc2_with_stderr(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"from":"seed"}\n', encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", StringIO())
    captured_stderr = StringIO()
    monkeypatch.setattr(sys, "stderr", captured_stderr)
    rc = append_clocked_jsonl.main(
        [
            "--root",
            str(tmp_path),
            "--file",
            ledger.name,
            "--data-json",
            '{"time":"forged","text":"no"}',
        ]
    )
    assert rc == 2
    assert "reserved clock fields" in captured_stderr.getvalue()
    assert ledger.read_text(encoding="utf-8").splitlines() == ['{"from":"seed"}']
