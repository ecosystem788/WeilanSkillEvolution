import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wake  # noqa: E402


def _receipt():
    return SimpleNamespace(
        stop_reason="queue_exhausted",
        structure_events=1,
        queued_for_owner=[],
        receipt_hash=lambda: "a" * 64,
    )


def _trace_error(message="branch-head conflict"):
    return wake.TraceCommandError(
        ("open",),
        {"_rc": 2, "_stderr": message, "_raw": "", "trace_error": {"error": message}},
    )


def _wake_with_reasons(monkeypatch, tmp_path, *, fired=None, owner=0, handoffs=0):
    receipt = SimpleNamespace(
        crossed_irreversible_gate=True,
        to_json=lambda: json.dumps({"crossed_irreversible_gate": True}),
        receipt_hash=lambda: "b" * 64,
    )
    chat = tmp_path / "CHAT_EXPERIMENT"
    chat.touch()
    monkeypatch.setattr(wake, "CHAT_EXPERIMENT", chat)
    monkeypatch.setattr(wake, "PAUSED", tmp_path / "PAUSED")
    monkeypatch.setattr(wake, "read_ledger_state", lambda: {})
    monkeypatch.setattr(wake, "briefing", lambda recall: {"continuation_allowed": True})
    monkeypatch.setattr(wake, "build_wake_brief", lambda recall: {})
    monkeypatch.setattr(wake, "derive_work_queue", lambda recall: [])
    monkeypatch.setattr(wake, "run_episode", lambda queue: receipt)
    monkeypatch.setattr(
        wake, "check_prospective_clock", lambda write: {"fired": fired or []}
    )
    monkeypatch.setattr(wake, "owner_inbox_pending", lambda: owner)
    monkeypatch.setattr(wake, "codex_inbox_pending", lambda: handoffs)
    monkeypatch.setattr(wake, "escalation_decision", lambda: "due")
    return wake.wake(commit=True)


def test_escalation_reasons_chat_only(monkeypatch, tmp_path):
    report = _wake_with_reasons(monkeypatch, tmp_path)
    assert report["escalation_reasons"] == ["chat"]


def test_escalation_reasons_preserve_clock_and_chat(monkeypatch, tmp_path):
    report = _wake_with_reasons(
        monkeypatch, tmp_path, fired=[{"cycle": "READY"}]
    )
    assert report["escalation_reasons"] == ["clock", "chat"]


def test_codex_wake_reasons_chat_without_handoffs(monkeypatch, tmp_path):
    report = _wake_with_reasons(monkeypatch, tmp_path, handoffs=0)
    assert report["codex_wake_reasons"] == ["chat"]


def test_trace_rejects_nonzero_and_non_json(monkeypatch):
    def completed(rc, stdout):
        return SimpleNamespace(returncode=rc, stdout=stdout, stderr="boom")

    monkeypatch.setattr(wake.subprocess, "run", lambda *a, **k: completed(7, '{"error":"x"}'))
    with pytest.raises(wake.TraceCommandError) as nonzero:
        wake._trace("open")
    assert nonzero.value.result["_rc"] == 7

    monkeypatch.setattr(wake.subprocess, "run", lambda *a, **k: completed(0, "not-json"))
    with pytest.raises(wake.TraceCommandError) as invalid:
        wake._trace("open")
    assert invalid.value.result["_raw"] == "not-json"


def test_receipt_open_refreshes_once_to_a_new_closed_head(monkeypatch):
    calls = []
    heads = iter(["wf-old", "wf-new"])
    monkeypatch.setattr(wake, "_current_head", lambda: next(heads))

    def fake_trace(*args):
        calls.append(args)
        if args[0] == "open" and "wf-old" in args:
            raise _trace_error()
        if args[0] == "open":
            return {"frame_id": "wf-receipt"}
        return {"valid": True}

    monkeypatch.setattr(wake, "_trace", fake_trace)
    assert wake.emit_receipt_frame(_receipt(), {}) == "wf-receipt"
    assert [c[0] for c in calls].count("open") == 2
    assert ("validate", "--frame-id", "wf-new", "--require-closed") in calls


def test_receipt_does_not_retry_when_refreshed_head_is_open(monkeypatch):
    heads = iter(["wf-old", "wf-new"])
    monkeypatch.setattr(wake, "_current_head", lambda: next(heads))
    opened = []

    def fake_trace(*args):
        if args[0] == "open":
            opened.append(args)
            raise _trace_error()
        if args[0] == "validate":
            raise _trace_error("frame is not closed")
        return {}

    monkeypatch.setattr(wake, "_trace", fake_trace)
    with pytest.raises(wake.FrameCommitFailure) as failure:
        wake.emit_receipt_frame(_receipt(), {})
    assert failure.value.stage == "refreshed_head_not_closed"
    assert len(opened) == 1


def test_main_prints_structured_failure_and_returns_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(wake, "wake", lambda commit=False: (_ for _ in ()).throw(
        wake.FrameCommitFailure("frame_open", {"rc": 2})
    ))
    monkeypatch.setattr(sys, "argv", ["wake.py", "--commit"])
    assert wake.main() == 3
    report = json.loads(capsys.readouterr().out)
    assert report["frame_commit_failure"] == {"stage": "frame_open", "rc": 2}


def test_cron_wrapper_failure_streak_alerts_once_and_success_resets(tmp_path):
    fake = tmp_path / "fake_wake.py"
    fake.write_text(
        """import json, os, sys
mode = os.environ['WAKE_FIXTURE_MODE']
if mode == 'native':
    print('native diagnostic', file=sys.stderr); raise SystemExit(7)
if mode == 'badjson': print('not-json'); raise SystemExit(0)
frame = None if mode == 'missing' else 'wf-fixture-ok'
print(json.dumps({'committed_frame': frame, 'receipt': {
    'crossed_irreversible_gate': False, 'stop_reason': 'fixture'}}))
""",
        encoding="utf-8",
    )
    log = tmp_path / "cron.log"
    wrapper = HERE / "run_wake_cron.ps1"

    def run(mode):
        env = {**os.environ, "WAKE_FIXTURE_MODE": mode}
        return subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper),
                "-WakeScript", str(fake), "-LogPath", str(log), "-NoEscalate",
            ],
            env=env, capture_output=True, text=True, timeout=30,
        )

    assert run("native").returncode == 7
    assert run("badjson").returncode == 1
    assert " ALERT " not in log.read_text(encoding="utf-8-sig")

    assert run("missing").returncode == 1
    assert log.read_text(encoding="utf-8-sig").count(" ALERT ") == 1
    assert run("badjson").returncode == 1
    assert log.read_text(encoding="utf-8-sig").count(" ALERT ") == 1

    assert run("success").returncode == 0
    assert run("missing").returncode == 1
    lines = log.read_text(encoding="utf-8-sig").splitlines()
    last_ok = max(i for i, line in enumerate(lines) if " wake ok " in line)
    assert sum(" ERROR " in line for line in lines[last_ok + 1:]) == 1
    assert sum(" ALERT " in line for line in lines[last_ok + 1:]) == 0


@pytest.mark.parametrize("codepage", [65001, 936])
def test_cron_wrapper_survives_cjk_report_on_any_console_codepage(tmp_path, codepage):
    # Live incident 2026-07-14T14:00:58: wake.py exited 0 with a valid UTF-8
    # report, but PowerShell 5.1's native 1>/2> redirection re-decoded the
    # bytes with the legacy codepage — a CJK char right before a closing
    # quote swallowed the quote and every healthy wake logged json_parse.
    # The capture path must be byte-faithful regardless of console codepage.
    fake = tmp_path / "fake_wake.py"
    fake.write_text(
        """import json
report = {
    'briefing': {'open_questions': ['\\u65b9\\u5411\\uff1a\\u5fae\\u6f9c\\u6001\\u52bf\\u611f\\u77e5' * 600]},
    'committed_frame': 'wf-fixture-ok',
    'receipt': {'crossed_irreversible_gate': False, 'stop_reason': '\\u9759\\u9ed8'},
}
print(json.dumps(report, ensure_ascii=False, indent=2))
""",
        encoding="utf-8",
    )
    log = tmp_path / "cron.log"
    wrapper = HERE / "run_wake_cron.ps1"
    inner = (
        f"chcp {codepage} >nul & powershell -NoProfile -ExecutionPolicy Bypass "
        f"-File {wrapper} -WakeScript {fake} -LogPath {log} -NoEscalate"
    )
    proc = subprocess.run(["cmd", "/c", inner], capture_output=True, timeout=60)
    log_text = log.read_text(encoding="utf-8-sig") if log.exists() else "(no log)"
    assert proc.returncode == 0, log_text
    assert " wake ok " in log_text and "静默" in log_text, log_text
