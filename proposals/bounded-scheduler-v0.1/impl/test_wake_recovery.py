import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wake  # noqa: E402


def _recall(state, allowed, reasons=None):
    return {
        "activation": {
            "state": state,
            "continuation_allowed": allowed,
            "reason_codes": reasons or [],
        }
    }


def test_stale_recall_rebuilds_once_and_recalls(monkeypatch):
    calls = []
    active = _recall("ACTIVE", True)

    def fake_trace(*args):
        calls.append(args)
        assert args[0] == "projection-rebuild"
        assert args[-2:] == ("--branch", "main")
        return {"rebuilt": True, "projection_id": "projection:new"}

    monkeypatch.setattr(wake, "_trace", fake_trace)
    monkeypatch.setattr(wake, "read_ledger_state", lambda: active)

    refreshed, recovery = wake.refresh_recall_if_stale(
        _recall("STALE", False, ["source_changed"])
    )

    assert refreshed is active
    assert len(calls) == 1
    assert recovery == {
        "attempted": True,
        "before_state": "STALE",
        "after_state": "ACTIVE",
        "reason_codes": ["source_changed"],
        "rebuilt": True,
        "projection_id": "projection:new",
        "continuation_allowed": True,
    }


def test_non_stale_recall_never_rebuilds(monkeypatch):
    monkeypatch.setattr(
        wake, "_trace", lambda *args: (_ for _ in ()).throw(AssertionError(args))
    )
    paused = _recall("PAUSED", False)
    refreshed, recovery = wake.refresh_recall_if_stale(paused)
    assert refreshed is paused
    assert recovery["attempted"] is False
    assert recovery["after_state"] == "PAUSED"


def test_cron_treats_fail_closed_abort_as_blocked_not_failure(tmp_path):
    fake = tmp_path / "fake_wake.py"
    fake.write_text(
        """import json
print(json.dumps({
    'aborted': 'continuation_not_allowed',
    'briefing': {'activation_state': 'PAUSED', 'continuation_allowed': False},
    'projection_recovery': {'attempted': False},
}))
""",
        encoding="utf-8",
    )
    log = tmp_path / "cron.log"
    wrapper = HERE / "run_wake_cron.ps1"
    proc = subprocess.run(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(wrapper), "-WakeScript", str(fake),
            "-LogPath", str(log), "-NoEscalate",
        ],
        env=os.environ.copy(), capture_output=True, text=True, timeout=30,
    )
    text = log.read_text(encoding="utf-8-sig")
    assert proc.returncode == 0
    assert " wake blocked " in text
    assert "state=PAUSED" in text
    assert " ERROR " not in text
    assert " ALERT " not in text
