"""Regression tests for the run_wake_cron.ps1 pre-flight block (FINDING 9.4).

Covers the acceptance shapes from delegation 0fbbf8cd08fa plus the two
review-pinned invariants from the 2026-08-03T21:44:36 revision proposal:

- F1: --evidence must reach frame-abandon as parseable JSON (FORM C), so the
      abandon call can actually succeed in the one scenario that needs it.
- F2: validate --require-closed must emit "frame must be terminal" for an
      open frame, and run_wake_cron.ps1 must key its is_open decision on
      that same string (FINDING 9.4 gap 2 pinned as a measured invariant).
- P (proposal #2, peer-chat:3541+3542): the proxy visibility precheck must be
      fail-open with three distinguishable log codes, and the NO_PROXY list
      must be a single dot-sourced source. The hooks accept "0" (force fail)
      and "1" (force pass) so every case is hermetic -- the suite touches no
      live network.

The wrapper tests run run_wake_cron.ps1 under Windows PowerShell 5.1 with a
mocked head (WEILAN_WAKE_AGENT_TEST_ROOT/HEAD/HEAD_OPEN) and a fake trace
script (WEILAN_WAKE_AGENT_TEST_TRACE) so no live ledger state is touched.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WRAPPER = HERE / "run_wake_cron.ps1"
TRACE = Path(r"D:\CodexData\skills\solve-with-weilan\scripts\weilan_trace.py")


def _write_fake_wake(path, *, wake_rc=0):
    path.write_text(
        """import json, os, sys
from pathlib import Path
Path(os.environ['WAKE_MARKER']).write_text('woken', encoding='ascii')
if int(os.environ.get('WAKE_RC', '0')) != 0:
    sys.exit(int(os.environ['WAKE_RC']))
print(json.dumps({'committed_frame': 'wf-fixture-ok', 'receipt': {'crossed_irreversible_gate': False, 'stop_reason': 'fixture'}}))
""",
        encoding="utf-8",
    )


def _write_fake_trace(path, *, emits_stderr=False):
    stderr_line = (
        "sys.stderr.write('weilan_trace: some warning' + chr(10))\n"
        if emits_stderr
        else ""
    )
    path.write_text(
        """import json, os, sys
with open(os.environ['TRACE_OUT'], 'a', encoding='utf-8') as f:
    f.write(json.dumps(sys.argv[1:]) + chr(10))
"""
        + stderr_line
        + """sys.exit(int(os.environ.get('TRACE_RC', '0')))
""",
        encoding="utf-8",
    )


def _run_wrapper(tmp_path, *, head_open, trace_rc, emits_stderr=False,
                 proxy_port_open="1", proxy_endpoint_ok="1", wake_rc=0,
                 skip_proxy_precheck=False):
    wake = tmp_path / "fake_wake.py"
    marker = tmp_path / "wake.marker"
    trace = tmp_path / "fake_trace.py"
    trace_out = tmp_path / "trace.argv"
    log = tmp_path / "cron.log"
    _write_fake_wake(wake, wake_rc=wake_rc)
    _write_fake_trace(trace, emits_stderr=emits_stderr)
    env = {
        **os.environ,
        "WEILAN_WAKE_AGENT_TEST_TRACE": str(trace),
        "WEILAN_WAKE_AGENT_TEST_ROOT": str(tmp_path),
        "WEILAN_WAKE_AGENT_TEST_HEAD": "wf-fixture-preflight",
        "WEILAN_WAKE_AGENT_TEST_PROXY_PORT_OPEN": proxy_port_open,
        "WEILAN_WAKE_AGENT_TEST_PROXY_ENDPOINT_OK": proxy_endpoint_ok,
        "WAKE_MARKER": str(marker),
        "TRACE_OUT": str(trace_out),
        "TRACE_RC": str(trace_rc),
        "WAKE_RC": str(wake_rc),
    }
    if head_open:
        env["WEILAN_WAKE_AGENT_TEST_HEAD_OPEN"] = "1"
    args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(WRAPPER), "-WakeScript", str(wake),
            "-LogPath", str(log), "-NoEscalate"]
    if skip_proxy_precheck:
        args.append("-SkipProxyPrecheck")
    proc = subprocess.run(
        args, env=env, capture_output=True, text=True, timeout=60,
    )
    text = log.read_text(encoding="utf-8-sig") if log.exists() else ""
    trace_lines = trace_out.read_text(encoding="utf-8") if trace_out.exists() else ""
    return proc, text, trace_lines, marker


def _abandon_calls(trace_lines):
    calls = [json.loads(line) for line in trace_lines.splitlines() if line.strip()]
    return [c for c in calls if c and c[0] == "frame-abandon"]


def test_preflight_abandons_open_head_then_wakes(tmp_path):
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=True, trace_rc=0
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "wake must run after a successful abandon"
    assert "preflight: abandoned stale open head wf-fixture-preflight (silence >= 7200s)" in text
    assert " wake ok " in text

    calls = _abandon_calls(trace_lines)
    assert len(calls) == 1, trace_lines
    argv = calls[0]
    assert "--frame-id" in argv
    assert argv[argv.index("--frame-id") + 1] == "wf-fixture-preflight"
    assert "--silence-threshold-seconds" in argv
    assert argv[argv.index("--silence-threshold-seconds") + 1] == "7200"
    assert "--evidence" in argv
    evidence = json.loads(argv[argv.index("--evidence") + 1])
    assert evidence == {
        "alert_id": "preflight",
        "consecutive_count": 0,
        "source_ref": "run_wake_cron:preflight",
    }


def test_preflight_skips_wake_when_abandon_refused(tmp_path):
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=True, trace_rc=1
    )
    assert proc.returncode == 0, proc.stderr
    assert not marker.exists(), "wake must not run when abandon refuses"
    assert "preflight: open head wf-fixture-preflight, abandon refused (live or raced); skip wake" in text
    assert " wake ok " not in text
    assert len(_abandon_calls(trace_lines)) == 1


def test_preflight_closed_head_skips_abandon_and_wakes(tmp_path):
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=False, trace_rc=0
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "wake must run when the head is closed"
    assert "preflight:" not in text
    assert " wake ok " in text
    assert trace_lines.strip() == "", "frame-abandon must not be invoked for a closed head"


def test_validate_require_closed_pins_terminal_error_string(tmp_path):
    method_state = tmp_path / "method-state"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env = {**os.environ, "WEILAN_METHOD_HOME": str(method_state)}
    opened = subprocess.run(
        [sys.executable, "-X", "utf8", str(TRACE), "open",
         "--level", "L2", "--workspace", str(workspace),
         "--scope", "preflight-pin", "--branch", "main",
         "--relation", "root", "--problem", "F2 pin", "--success", "bounded"],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert opened.returncode == 0, opened.stderr
    frame_id = json.loads(opened.stdout)["frame_id"]

    validated = subprocess.run(
        [sys.executable, "-X", "utf8", str(TRACE), "validate",
         "--frame-id", frame_id, "--require-closed"],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert validated.returncode == 1
    payload = json.loads(validated.stdout)
    assert "frame must be terminal" in payload["errors"]

    # The wrapper's is_open decision keys on the same string; if either side
    # changes wording, this test fails instead of silently inerting the
    # pre-flight (FINDING 9.4 gap 2, measured not assumed).
    wrapper_source = WRAPPER.read_text(encoding="utf-8-sig")
    assert '-contains "frame must be terminal"' in wrapper_source

def test_preflight_stderr_noise_does_not_abort_when_abandon_succeeds(tmp_path):
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=True, trace_rc=0, emits_stderr=True
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "wake must run despite pre-flight stderr noise"
    assert "preflight: abandoned stale open head wf-fixture-preflight (silence >= 7200s)" in text
    assert "wrapper_exception" not in text
    assert len(_abandon_calls(trace_lines)) == 1


def test_preflight_stderr_noise_does_not_abort_when_abandon_refused(tmp_path):
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=True, trace_rc=1, emits_stderr=True
    )
    assert proc.returncode == 0, proc.stderr
    assert not marker.exists(), "wake must stay skipped when abandon refuses"
    assert "preflight: open head wf-fixture-preflight, abandon refused (live or raced); skip wake" in text
    assert "wrapper_exception" not in text
    assert len(_abandon_calls(trace_lines)) == 1


def test_preflight_probe_unavailable_is_logged_and_wake_proceeds(tmp_path):
    # Live branch (no TEST_ROOT/TEST_HEAD): the fake trace returns unparseable
    # stdout, so ConvertFrom-Json throws and Get-HeadAndOpenState catches.
    # The wrapper must log the unavailable probe (fail-open visible) instead of
    # silently proceeding as if the head were closed.
    wake = tmp_path / "fake_wake.py"
    marker = tmp_path / "wake.marker"
    trace = tmp_path / "fake_trace_badjson.py"
    log = tmp_path / "cron.log"
    _write_fake_wake(wake)
    trace.write_text(
        "import sys\nprint('this is not json')\nsys.exit(0)\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "WEILAN_WAKE_AGENT_TEST_TRACE": str(trace),
        "WEILAN_WAKE_AGENT_TEST_PROXY_PORT_OPEN": "1",
        "WEILAN_WAKE_AGENT_TEST_PROXY_ENDPOINT_OK": "1",
        "WAKE_MARKER": str(marker),
    }
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(WRAPPER), "-WakeScript", str(wake),
         "-LogPath", str(log), "-NoEscalate"],
        env=env, capture_output=True, text=True, timeout=60,
    )
    text = log.read_text(encoding="utf-8-sig") if log.exists() else ""
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "wake must proceed when the probe is unavailable"
    assert "preflight: head/open-state probe unavailable; wake proceeds without pre-flight" in text
    assert "wrapper_exception" not in text


def test_proxy_precheck_pass_keeps_wake_silent(tmp_path):
    # Port listening + endpoint reachable (simulated): no proxy_precheck line,
    # wake still runs, rc=0. Hermetic: the hooks force the outcome, so no live
    # network is touched.
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=False, trace_rc=0,
        proxy_port_open="1", proxy_endpoint_ok="1",
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "wake must run on a healthy proxy"
    assert "code=proxy_" not in text
    assert " wake ok " in text


def test_proxy_precheck_port_not_listening_is_fail_open(tmp_path):
    # P1 fails (port down): a distinguishable one-line ERROR, wake still runs
    # with rc=0 -- the precheck must not decide behavior (the fourth predicate
    # is deliberately left to the 乙 follow-up).
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=False, trace_rc=0, proxy_port_open="0",
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "fail-open: wake must still run when the port is down"
    assert "code=proxy_port_not_listening" in text
    assert " wake ok " in text


def test_proxy_precheck_endpoint_unreachable_is_fail_open(tmp_path):
    # P1 passes, P2 fails (the proxy arm cannot reach chatgpt.com): a
    # distinguishable one-line ERROR, wake still runs with rc=0.
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=False, trace_rc=0,
        proxy_port_open="1", proxy_endpoint_ok="0",
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "fail-open: wake must still run when the endpoint is unreachable"
    assert "code=proxy_endpoint_unreachable" in text
    assert " wake ok " in text


def test_proxy_precheck_skip_flag_is_rollback_switch(tmp_path):
    # -SkipProxyPrecheck: zero proxy_precheck lines even with the port down,
    # wake runs -- the soft rollback path for the precheck.
    proc, text, trace_lines, marker = _run_wrapper(
        tmp_path, head_open=False, trace_rc=0,
        proxy_port_open="0", skip_proxy_precheck=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert marker.exists(), "wake must run with the precheck skipped"
    assert "code=proxy_" not in text
    assert " wake ok " in text


def test_proxy_precheck_failure_streak_stacking(tmp_path):
    # Agree precision note (2): the precheck ERROR feeds the same failure
    # streak as a main failure, a succeeding wake truncates it, and a same-tick
    # double-fail stacks -- 2 double-fail ticks (4 ERROR lines) escalate where
    # a main-only run would need 3 ticks. The port is down every tick; the
    # wake main fails on ticks 1, 3 and 4 and succeeds on tick 2.
    wake = tmp_path / "fake_wake.py"
    marker = tmp_path / "wake.marker"
    trace = tmp_path / "fake_trace.py"
    trace_out = tmp_path / "trace.argv"
    log = tmp_path / "cron.log"

    def run_tick(wake_rc):
        _write_fake_wake(wake, wake_rc=wake_rc)
        _write_fake_trace(trace)
        env = {
            **os.environ,
            "WEILAN_WAKE_AGENT_TEST_TRACE": str(trace),
            "WEILAN_WAKE_AGENT_TEST_ROOT": str(tmp_path),
            "WEILAN_WAKE_AGENT_TEST_HEAD": "wf-fixture-preflight",
            "WEILAN_WAKE_AGENT_TEST_PROXY_PORT_OPEN": "0",
            "WAKE_MARKER": str(marker),
            "TRACE_OUT": str(trace_out),
            "TRACE_RC": "0",
            "WAKE_RC": str(wake_rc),
        }
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(WRAPPER), "-WakeScript", str(wake),
             "-LogPath", str(log), "-NoEscalate"],
            env=env, capture_output=True, text=True, timeout=60,
        )

    # Tick 1 (double-fail): 2 ERROR lines after the last wake ok, no ALERT yet.
    proc = run_tick(wake_rc=1)
    assert proc.returncode == 1, proc.stderr
    text = log.read_text(encoding="utf-8-sig")
    assert text.count("code=proxy_port_not_listening") == 1
    assert "ALERT" not in text

    # Tick 2 (precheck ERROR + main ok): the wake ok line truncates the streak.
    proc = run_tick(wake_rc=0)
    assert proc.returncode == 0, proc.stderr
    text = log.read_text(encoding="utf-8-sig")
    assert " wake ok " in text

    # Tick 3 (double-fail): 2 lines after the last wake ok, still no ALERT.
    proc = run_tick(wake_rc=1)
    assert proc.returncode == 1, proc.stderr
    text = log.read_text(encoding="utf-8-sig")
    assert "ALERT" not in text

    # Tick 4 (double-fail): 4 lines after the last wake ok -> ALERT. A main-only
    # run would need 3 failed ticks; the stacked precheck line escalates one
    # tick earlier. This pinned upgrade moment is the agree note's ask.
    proc = run_tick(wake_rc=1)
    assert proc.returncode == 1, proc.stderr
    text = log.read_text(encoding="utf-8-sig")
    assert "ALERT sentinel_failure_streak=4" in text


def test_proxy_single_source_of_truth_static():
    # 甲: one frozen NO_PROXY list in a dot-sourced file, three wake scripts
    # referencing it, zero inline copies left behind.
    proxy_file = HERE / "proxy-no-proxy.ps1"
    assert proxy_file.exists()
    frozen = (
        '$env:NO_PROXY = "localhost,127.0.0.1,::1,'
        "token-plan.cn-beijing.maas.aliyuncs.com,"
        "ws-s0l7d3yz7axp4uwz.cn-beijing.maas.aliyuncs.com,"
        'api.minimaxi.com,www.minimaxi.com,api.deepseek.com"'
    )
    assert proxy_file.read_text(encoding="utf-8-sig").strip() == frozen
    for name in ("run_wake_cron.ps1", "wake_agent.ps1", "wake_codex.ps1"):
        src = (HERE / name).read_text(encoding="utf-8-sig")
        assert "proxy-no-proxy.ps1" in src, name
        assert "api.deepseek.com" not in src, f"{name} still carries an inline NO_PROXY list"
