import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wake  # noqa: E402


def _start_lock_owner(lock_path, ready_path, state_path=None):
    script = r"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import wake

wake.WAKE_COMMIT_LOCK = Path(sys.argv[2])
handle = wake._acquire_wake_commit_lock()
if sys.argv[4] != "-":
    Path(sys.argv[4]).write_text(json.dumps({
        "frame_id": "wf-orphan",
        "event_type": "frame_opened",
        "workspace": wake.WORKSPACE,
        "data": {
            "problem": wake.RECEIPT_PROBLEM,
            "success_criteria": "episode stop=quiescent structure=1",
            "causal": {
                "scope": wake.SCOPE,
                "branch_id": wake.BRANCH,
                "relation": "continue",
            },
        },
    }), encoding="utf-8")
Path(sys.argv[3]).write_text("ready", encoding="ascii")
try:
    time.sleep(300)
finally:
    wake._release_wake_commit_lock(handle)
"""
    proc = subprocess.Popen([
        sys.executable,
        "-c",
        script,
        str(HERE),
        str(lock_path),
        str(ready_path),
        str(state_path) if state_path is not None else "-",
    ])
    deadline = time.monotonic() + 10
    while not ready_path.exists() and proc.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert ready_path.exists(), f"lock owner did not become ready; rc={proc.poll()}"
    return proc


def _kill_process(proc):
    if proc.poll() is None:
        proc.kill()
    proc.wait(timeout=10)


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


def _wake_with_reasons(
    monkeypatch, tmp_path, *, fired=None, owner=0, handoffs=0, paused=False
):
    receipt = SimpleNamespace(
        crossed_irreversible_gate=True,
        to_json=lambda: json.dumps({"crossed_irreversible_gate": True}),
        receipt_hash=lambda: "b" * 64,
    )
    chat = tmp_path / "CHAT_EXPERIMENT"
    monkeypatch.setattr(wake, "CHAT_EXPERIMENT", chat)
    paused_path = tmp_path / "PAUSED"
    if paused:
        paused_path.touch()
    monkeypatch.setattr(wake, "PAUSED", paused_path)
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
    monkeypatch.setattr(wake, "escalation_decision", lambda *_: "due")
    return wake.wake(commit=True)


def test_permanent_tearoom_wakes_both_bodies_without_legacy_flag(monkeypatch, tmp_path):
    report = _wake_with_reasons(monkeypatch, tmp_path)
    assert report["chat_experiment"] is False
    assert report["tearoom_permanent"] is True
    assert report["escalation_reasons"] == ["chat"]
    assert report["codex_wake_reasons"] == ["chat"]
    assert report["codex_due"] is True


def test_escalation_reasons_preserve_clock_and_chat(monkeypatch, tmp_path):
    report = _wake_with_reasons(
        monkeypatch, tmp_path, fired=[{"cycle": "READY"}], owner=1
    )
    assert report["escalation_reasons"] == ["clock", "owner_inbox", "chat"]


def test_codex_handoff_priority_is_preserved(monkeypatch, tmp_path):
    report = _wake_with_reasons(monkeypatch, tmp_path, handoffs=1)
    assert report["codex_wake_reasons"] == ["handoffs", "chat"]


def test_paused_remains_a_hard_stop_for_codex(monkeypatch, tmp_path):
    report = _wake_with_reasons(monkeypatch, tmp_path, paused=True)
    assert "codex_due" not in report
    assert "codex_wake_reasons" not in report


def test_active_orphan_context_uses_latest_incident_event(monkeypatch, tmp_path):
    alerts = tmp_path / "peer-health-alerts.jsonl"
    rows = [
        {"incident_key": "old", "kind": "orphan_frame", "event": "raised", "parent_frame_id": "wf-head"},
        {"incident_key": "old", "kind": "orphan_frame", "event": "resolved", "parent_frame_id": "wf-head"},
        {"incident_key": "live", "kind": "orphan_frame", "event": "reopened", "parent_frame_id": "wf-head"},
    ]
    alerts.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    monkeypatch.setattr(wake, "PEER_HEALTH_ALERTS", alerts)
    monkeypatch.setattr(wake, "_current_head", lambda: "wf-head")
    assert wake._active_orphan_rescue_context() == {
        "orphan_head_frame_id": "wf-head",
        "incident_key": "live",
    }


def test_orphan_reason_and_context_cross_python_report(monkeypatch, tmp_path):
    context = {"orphan_head_frame_id": "wf-head", "incident_key": "orphan:wf-head"}
    monkeypatch.setattr(wake, "_active_orphan_rescue_context", lambda: context)
    report = _wake_with_reasons(monkeypatch, tmp_path)
    assert report["escalation_reasons"][0] == "orphan_rescue"
    assert report["rescue_context"] == context


def test_cron_passes_rescue_context_to_agent_stub(tmp_path):
    context = {"orphan_head_frame_id": "wf-orphan", "incident_key": "orphan:wf-orphan"}
    fake_wake = tmp_path / "fake_rescue_wake.py"
    fake_wake.write_text(
        "import json; print(json.dumps(" + repr({
            "committed_frame": "wf-fixture-ok",
            "receipt": {"crossed_irreversible_gate": False, "stop_reason": "fixture"},
            "escalation_due": True,
            "escalation_reasons": ["orphan_rescue"],
            "rescue_context": context,
        }) + "))",
        encoding="utf-8",
    )
    captured = tmp_path / "captured.json"
    agent = tmp_path / "agent_stub.ps1"
    agent.write_text(
        f'''param([string]$RescueContext)
[IO.File]::WriteAllText("{captured}", $RescueContext, (New-Object Text.UTF8Encoding($false)))
''',
        encoding="utf-8-sig",
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(HERE / "run_wake_cron.ps1"), "-WakeScript", str(fake_wake),
         "-LogPath", str(tmp_path / "cron.log"), "-WakeAgentScript", str(agent)],
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0
    import base64
    carried = base64.b64decode(captured.read_text(encoding="utf-8")).decode("utf-8")
    assert json.loads(carried) == context


@pytest.mark.parametrize("prompt_name", ["wake_prompt.md", "wake_prompt_codex.md"])
def test_prompts_describe_permanent_tearoom_with_layered_authority(prompt_name):
    text = (HERE / prompt_name).read_text(encoding="utf-8")
    assert "常态茶水间" in text
    assert "不由 `impl\\CHAT_EXPERIMENT` 旗文件开关" in text
    assert "具名证据或判断" in text
    assert "发言本身不自动授权行动" in text
    assert "行动授权只来自【提案】+【同意】的双签或观察员指令" in text
    assert "闲聊实验" not in text
    assert "等旗落" not in text
    assert "没有工作任务" not in text


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
    monkeypatch.setattr(wake, "_trace_events", lambda frame_id: [{
        "event_type": "frame_opened",
        "frame_id": frame_id,
        "workspace": wake.WORKSPACE,
        "data": {
            "problem": "a model-owned frame",
            "causal": {
                "scope": wake.SCOPE,
                "branch_id": wake.BRANCH,
                "relation": "continue",
            },
        },
    }])
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


def test_receipt_recovers_exact_work_free_scheduler_orphan(monkeypatch):
    heads = iter(["wf-orphan", "wf-orphan"])
    monkeypatch.setattr(wake, "_current_head", lambda: next(heads))
    monkeypatch.setattr(wake, "_trace_events", lambda frame_id: [{
        "event_type": "frame_opened",
        "frame_id": frame_id,
        "workspace": wake.WORKSPACE,
        "data": {
            "problem": wake.RECEIPT_PROBLEM,
            "success_criteria": "episode stop=quiescent structure=1",
            "causal": {
                "scope": wake.SCOPE,
                "branch_id": wake.BRANCH,
                "relation": "continue",
            },
        },
    }])
    calls = []
    audit_completed = set()

    def fake_trace(*args):
        calls.append(args)
        command = args[0]
        if command == "open" and "wf-orphan" in args and not audit_completed:
            raise _trace_error("causal parent must be closed")
        if command == "open":
            return {"frame_id": "wf-receipt"}
        if command == "persistence-audit-show":
            frame_id = args[-1]
            completed = ["round_end"] if frame_id in audit_completed else []
            return {"completed_triggers": completed}
        if command == "persistence-audit":
            audit_completed.add(args[args.index("--frame-id") + 1])
            return {"saved": True}
        return {"valid": True}

    monkeypatch.setattr(wake, "_trace", fake_trace)
    assert wake.emit_receipt_frame(_receipt(), {}) == "wf-receipt"
    close_calls = [call for call in calls if call[0] == "close"]
    orphan_close = next(call for call in close_calls if "wf-orphan" in call)
    new_close = next(call for call in close_calls if "wf-receipt" in call)
    assert orphan_close[orphan_close.index("--outcome") + 1] == "failed"
    assert new_close[new_close.index("--outcome") + 1] == "success"
    assert [call[0] for call in calls].count("open") == 2


def test_receipt_finalize_retries_one_transient_audit_lock_timeout(monkeypatch):
    calls = []
    audit_completed = False

    def fake_trace(*args):
        nonlocal audit_completed
        calls.append(args)
        if args[0] == "persistence-audit-show":
            return {"completed_triggers": ["round_end"] if audit_completed else []}
        if args[0] == "persistence-audit" and not audit_completed:
            if [call[0] for call in calls].count("persistence-audit") == 1:
                raise _trace_error("lock timeout on .workspace-contract.lock")
            audit_completed = True
            return {"saved": True}
        return {"valid": True}

    monkeypatch.setattr(wake, "_trace", fake_trace)
    monkeypatch.setattr(wake.time, "sleep", lambda seconds: None)
    wake._finalize_receipt_frame("wf-receipt", "success", "ok")
    assert [call[0] for call in calls].count("persistence-audit") == 2
    assert any(call[0] == "close" for call in calls)


def test_live_lock_owner_prevents_peer_from_entering_recovery(monkeypatch, tmp_path):
    lock_path = tmp_path / ".wake-commit.lock"
    ready_path = tmp_path / "ready"
    owner = _start_lock_owner(lock_path, ready_path)
    entered = []
    monkeypatch.setattr(wake, "WAKE_COMMIT_LOCK", lock_path)
    monkeypatch.setattr(wake, "_wake_once", lambda commit: entered.append(commit))
    try:
        with pytest.raises(wake.WakeCommitLockBusy):
            wake.wake(commit=True)
        assert entered == []
    finally:
        _kill_process(owner)


def test_killed_lock_owner_releases_lock_and_next_wake_recovers_orphan(
    monkeypatch, tmp_path
):
    lock_path = tmp_path / ".wake-commit.lock"
    ready_path = tmp_path / "ready"
    state_path = tmp_path / "opened-frame.json"
    owner = _start_lock_owner(lock_path, ready_path, state_path)
    _kill_process(owner)

    opened = json.loads(state_path.read_text(encoding="utf-8"))
    heads = iter(["wf-orphan", "wf-orphan"])
    calls = []
    audit_completed = set()
    monkeypatch.setattr(wake, "WAKE_COMMIT_LOCK", lock_path)
    monkeypatch.setattr(wake, "_current_head", lambda: next(heads))
    monkeypatch.setattr(wake, "_trace_events", lambda frame_id: [opened])

    def fake_trace(*args):
        calls.append(args)
        command = args[0]
        if command == "open" and "wf-orphan" in args and not audit_completed:
            raise _trace_error("causal parent must be closed")
        if command == "open":
            return {"frame_id": "wf-receipt"}
        if command == "persistence-audit-show":
            frame_id = args[-1]
            return {
                "completed_triggers": ["round_end"] if frame_id in audit_completed else []
            }
        if command == "persistence-audit":
            audit_completed.add(args[args.index("--frame-id") + 1])
            return {"saved": True}
        return {"valid": True}

    monkeypatch.setattr(wake, "_trace", fake_trace)
    monkeypatch.setattr(
        wake, "_wake_once", lambda commit: wake.emit_receipt_frame(_receipt(), {})
    )
    assert wake.wake(commit=True) == "wf-receipt"
    close_calls = [call for call in calls if call[0] == "close"]
    assert any("wf-orphan" in call for call in close_calls)
    assert any("wf-receipt" in call for call in close_calls)


def test_lock_loser_cli_exits_nonzero_before_any_ledger_access(tmp_path):
    lock_path = wake.WAKE_COMMIT_LOCK
    handle = wake._acquire_wake_commit_lock()
    try:
        proc = subprocess.run(
            [sys.executable, str(HERE / "wake.py"), "--commit"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    finally:
        wake._release_wake_commit_lock(handle)
    assert proc.returncode == 4
    report = json.loads(proc.stdout)
    assert report["wake_commit_lock_busy"]["reason"] == "busy"
    assert report["wake_commit_lock_busy"]["path"] == str(lock_path)


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


@pytest.mark.parametrize("codepage", [65001, 936])
def test_wake_agent_capture_is_utf8_on_any_console_codepage(tmp_path, codepage):
    wrapper_source = (HERE / "wake_agent.ps1").read_text(encoding="utf-8")
    assert "CREATE_SUSPENDED" in wrapper_source
    assert "AssignProcessToJobObject" in wrapper_source
    assert "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE" in wrapper_source
    assert "SetHandleInformation" in wrapper_source
    assert "new-object system.text.utf8encoding($false, $true)" in wrapper_source.lower()

    fake = tmp_path / "fake_claude.py"
    fake.write_text(
        """import json
print(json.dumps({
    'subtype': 'success', 'num_turns': 2, 'total_cost_usd': 0.25,
    'result': '\u65b9\u5411\uff1a\u5fae\u6f9c\u6001\u52bf\u611f\u77e5' * 600,
}, ensure_ascii=False))
""",
        encoding="utf-8",
    )
    fake_cmd = tmp_path / "claude.cmd"
    fake_cmd.write_text(
        f'@echo off\r\n"{sys.executable}" "{fake}" %*\r\n', encoding="ascii"
    )
    transcript = tmp_path / "transcript.json"
    errors = tmp_path / "transcript.err.txt"
    fixture = tmp_path / "capture.ps1"
    fixture.write_text(
        f'''$ErrorActionPreference = "Stop"
$outFile = "{transcript}"
$errFile = "{errors}"
$prompt = "{tmp_path / 'wake_prompt.md'}"
& cmd /c "claude -p `"现在醒来，执行这一回合的自主工作。照系统提示的纪律来。`" --append-system-prompt-file `"$prompt`" --dangerously-skip-permissions --output-format json 1>`"$outFile`" 2>`"$errFile`""
if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
$utf8Strict = New-Object System.Text.UTF8Encoding($false, $true)
$text = [System.IO.File]::ReadAllText($outFile, $utf8Strict)
$null = $text | ConvertFrom-Json
''',
        encoding="utf-8-sig",
    )
    inner = (
        f'chcp {codepage} >nul & powershell -NoProfile -ExecutionPolicy Bypass '
        f'-File {fixture}'
    )
    env = {**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        ["cmd", "/c", inner], env=env, capture_output=True, timeout=60
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    raw = transcript.read_bytes()
    assert not raw.startswith((b"\xff\xfe", b"\xfe\xff"))
    parsed = json.loads(raw.decode("utf-8", errors="strict"))
    assert parsed["result"].startswith("方向：微澜态势感知")


def _job_fixture(tmp_path, *, head="wf-orphan"):
    trace = tmp_path / "fake_trace.py"
    trace.write_text(
        f'''import json, sys
cmd = sys.argv[1]
if cmd == "lineage-show":
    print(json.dumps({{"branches": {{"main": {{"head_frame_id": "{head}"}}}}}}))
    raise SystemExit(0)
if cmd == "validate":
    print(json.dumps({{"valid": False, "errors": ["frame must be closed"]}}))
    raise SystemExit(1)
raise SystemExit(2)
''',
        encoding="utf-8",
    )
    marker = tmp_path / "stub-started.txt"
    stub = tmp_path / "stub_agent.py"
    stub.write_text(
        '''import json, pathlib, sys
pathlib.Path(sys.argv[1]).write_text(str(__import__("os").getpid()), encoding="ascii")
print(json.dumps({"subtype":"success","num_turns":1,"total_cost_usd":0,"result":"方向：微澜态势感知"}, ensure_ascii=False))
''',
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "WEILAN_WAKE_AGENT_TEST_ROOT": str(tmp_path),
        "WEILAN_WAKE_AGENT_TEST_REPO": str(tmp_path),
        "WEILAN_WAKE_AGENT_TEST_TRACE": str(trace),
        "WEILAN_WAKE_AGENT_TEST_HEAD": head,
        "WEILAN_WAKE_AGENT_TEST_HEAD_OPEN": "1",
        "WEILAN_WAKE_AGENT_TEST_COMMAND": f'"{sys.executable}" "{stub}" "{marker}"',
    }
    return env, marker


def _lock_record(owner_pid, owner_started_at):
    return {
        "schema_version": "weilan_wake_agent_lock_v0.3",
        "owner_pid": owner_pid,
        "owner_started_at": owner_started_at,
        "containment_version": "windows_job_kill_on_close_v1",
        "job_handle_inheritable": False,
        "breakaway_allowed": False,
        "acquired_at": "2026-07-23T00:00:00Z",
    }


def _prepare_rescue(tmp_path, lock, *, head="wf-orphan", incident="orphan:wf-orphan"):
    (tmp_path / "wake-agent.lock").write_text(json.dumps(lock), encoding="utf-8")
    alert = {
        "event": "raised", "kind": "orphan_frame", "incident_key": incident,
        "parent_frame_id": head,
    }
    (tmp_path / "peer-health-alerts.jsonl").write_text(
        json.dumps(alert) + "\n", encoding="utf-8"
    )
    return json.dumps({"orphan_head_frame_id": head, "incident_key": incident})


def _run_job_agent(env, rescue=None, timeout=30):
    command = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(HERE / "wake_agent.ps1"),
    ]
    if rescue is not None:
        command += ["-RescueContext", rescue]
    return subprocess.run(command, env=env, capture_output=True, timeout=timeout)


def _started_at(pid):
    return subprocess.check_output(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-Process -Id {pid}).StartTime.ToUniversalTime().ToString('o')"],
        text=True,
    ).strip()


def test_job_rescue_dead_correlated_owner_starts_stub_and_preserves_utf8(tmp_path):
    env, marker = _job_fixture(tmp_path)
    rescue = _prepare_rescue(tmp_path, _lock_record(999999, "2026-01-01T00:00:00Z"))
    proc = _run_job_agent(env, rescue)
    assert proc.returncode == 0, (tmp_path / "wake-agent.log").read_text(encoding="utf-8-sig")
    assert marker.exists()
    transcript = next((tmp_path / "wake-agent-runs").glob("*.json"))
    raw = transcript.read_bytes()
    assert json.loads(raw.decode("utf-8", errors="strict"))["result"].startswith("方向：")


def test_job_rescue_live_owner_and_head_mismatch_fail_closed(tmp_path):
    env, marker = _job_fixture(tmp_path)
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        live = _lock_record(sleeper.pid, _started_at(sleeper.pid))
        rescue = _prepare_rescue(tmp_path, live)
        assert _run_job_agent(env, rescue).returncode == 0
        assert not marker.exists()

        (tmp_path / "wake-agent.lock").write_text(
            json.dumps(_lock_record(999999, "2026-01-01T00:00:00Z")), encoding="utf-8"
        )
        wrong_head = json.dumps({
            "orphan_head_frame_id": "wf-other", "incident_key": "orphan:wf-orphan"
        })
        assert _run_job_agent(env, wrong_head).returncode == 0
        assert not marker.exists()
    finally:
        sleeper.terminate()
        sleeper.wait(timeout=10)


def test_job_no_alert_fresh_lock_and_assign_failure_do_not_start(tmp_path):
    env, marker = _job_fixture(tmp_path)
    (tmp_path / "wake-agent.lock").write_text(
        json.dumps(_lock_record(999999, "2026-01-01T00:00:00Z")), encoding="utf-8"
    )
    assert _run_job_agent(env).returncode == 0
    assert not marker.exists()

    (tmp_path / "wake-agent.lock").unlink()
    env["WEILAN_WAKE_AGENT_FORCE_ASSIGN_FAILURE"] = "1"
    assert _run_job_agent(env).returncode == 1
    assert not marker.exists()
    assert not (tmp_path / "wake-agent.lock").exists()


def test_killing_wrapper_kills_job_contained_stub(tmp_path):
    env, marker = _job_fixture(tmp_path)
    sleeper_stub = tmp_path / "sleeping_stub.py"
    sleeper_stub.write_text(
        '''import os, pathlib, sys, time
pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding="ascii")
time.sleep(120)
''',
        encoding="utf-8",
    )
    env["WEILAN_WAKE_AGENT_TEST_COMMAND"] = (
        f'"{sys.executable}" "{sleeper_stub}" "{marker}"'
    )
    wrapper = subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(HERE / "wake_agent.ps1")],
        env=env,
    )
    try:
        deadline = time.time() + 20
        while time.time() < deadline and not marker.exists():
            time.sleep(0.1)
        assert marker.exists(), "contained stub never started"
        child_pid = int(marker.read_text(encoding="ascii"))
        wrapper.kill()
        wrapper.wait(timeout=10)
        deadline = time.time() + 10
        while time.time() < deadline:
            alive = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"if(Get-Process -Id {child_pid} -ErrorAction SilentlyContinue){{exit 0}}else{{exit 1}}"],
                capture_output=True,
            ).returncode == 0
            if not alive:
                break
            time.sleep(0.2)
        assert not alive, "Job-contained stub survived owner termination"
    finally:
        if wrapper.poll() is None:
            wrapper.kill()
            wrapper.wait(timeout=10)


def test_real_task_scheduler_host_allows_nested_job(tmp_path):
    env, marker = _job_fixture(tmp_path)
    result = tmp_path / "scheduled-result.txt"
    wrapper = tmp_path / "scheduled_probe.ps1"

    def ps(value):
        return str(value).replace("'", "''")

    assignments = "\n".join(
        f"$env:{key} = '{ps(value)}'"
        for key, value in env.items()
        if key.startswith("WEILAN_WAKE_AGENT_")
    )
    wrapper.write_text(
        assignments
        + f"\n& powershell -NoProfile -ExecutionPolicy Bypass -File '{ps(HERE / 'wake_agent.ps1')}'\n"
        + f"[IO.File]::WriteAllText('{ps(result)}', [string]$LASTEXITCODE)\n",
        encoding="utf-8-sig",
    )
    task = f"WeilanV3NestedJobProbe-{os.getpid()}-{int(time.time())}"
    task_command = (
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{wrapper}"'
    )
    try:
        created = subprocess.run(
            ["schtasks", "/Create", "/TN", task, "/TR", task_command,
             "/SC", "ONCE", "/ST", "23:59", "/RL", "LIMITED", "/F"],
            capture_output=True,
            timeout=30,
        )
        assert created.returncode == 0, created.stderr.decode(errors="replace")
        started = subprocess.run(
            ["schtasks", "/Run", "/TN", task], capture_output=True, timeout=30
        )
        assert started.returncode == 0, started.stderr.decode(errors="replace")
        deadline = time.time() + 60
        while time.time() < deadline and not result.exists():
            time.sleep(0.25)
        assert result.exists(), "Task Scheduler nested-job probe did not finish"
        assert result.read_text(encoding="utf-8").strip() == "0"
        assert marker.exists(), "scheduled nested Job never launched its stub"
    finally:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", task, "/F"],
            capture_output=True,
            timeout=30,
        )
