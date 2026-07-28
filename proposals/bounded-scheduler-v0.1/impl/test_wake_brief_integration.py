from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import wake as wake_mod  # noqa: E402


def _recall() -> dict:
    return {
        "activation": {"state": "ACTIVE", "continuation_allowed": True},
        "control": {},
        "freshness": {"fresh": True},
        "projection": {"source_snapshots": [{"ref": "frame:head"}]},
    }


def test_build_wake_brief_reuses_existing_recall() -> None:
    wake = importlib.reload(wake_mod)
    seen = {}

    def builder(**kwargs):
        seen.update(kwargs)
        return {"cursor_status": {"status": "incremental"}}

    recall = _recall()
    brief = wake.build_wake_brief(recall, updated_at_utc="2026-07-10T00:00:00+00:00", builder=builder)

    assert brief == {"cursor_status": {"status": "incremental"}}
    assert seen["root"] == wake.HERE
    assert seen["workspace"] == wake.WORKSPACE
    assert seen["scope"] == wake.SCOPE
    assert seen["recall_fixture"] is recall
    assert seen["updated_at_utc"] == "2026-07-10T00:00:00+00:00"
    assert seen["commit_cursor"] is False


def test_wake_report_surfaces_compact_brief(monkeypatch) -> None:
    wake = importlib.reload(wake_mod)
    compact = {
        "owner_inbox_delta": [{"id": "owner-1", "text": "接线"}],
        "cursor_status": {"status": "incremental"},
    }

    monkeypatch.setattr(wake, "read_ledger_state", _recall)
    monkeypatch.setattr(wake, "build_wake_brief", lambda recall: compact)
    monkeypatch.setattr(wake, "derive_work_queue", lambda recall: [])
    monkeypatch.setattr(wake, "check_prospective_clock", lambda write: {"clock_goals_checked": 0, "fired": []})
    monkeypatch.setattr(wake, "owner_inbox_pending", lambda: 0)
    monkeypatch.setattr(wake, "codex_inbox_pending", lambda: 0)

    report = wake.wake(commit=False)

    assert report["wake_brief"] == compact
    assert report["briefing"]["activation_state"] == "ACTIVE"
    assert report["receipt"]["structure_events"] == 0


def test_trigger_detection_does_not_consume_consumer_cursor(monkeypatch, tmp_path: Path) -> None:
    wake = importlib.reload(wake_mod)
    chat = {"from": "owner", "time": "2026-07-13 21:40:19", "text": "new message"}
    (tmp_path / "peer-chat.jsonl").write_text(
        json.dumps(chat, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (tmp_path / "codex-inbox-replies.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "CHAT_EXPERIMENT").write_text("", encoding="utf-8")

    monkeypatch.setattr(wake, "HERE", tmp_path)
    monkeypatch.setattr(wake, "CHAT_EXPERIMENT", tmp_path / "CHAT_EXPERIMENT")
    monkeypatch.setattr(wake, "read_ledger_state", _recall)
    monkeypatch.setattr(wake, "derive_work_queue", lambda recall: [])
    monkeypatch.setattr(wake, "emit_receipt_frame", lambda receipt, brief: "frame:test")
    monkeypatch.setattr(wake, "check_prospective_clock", lambda write: {"clock_goals_checked": 0, "fired": []})
    monkeypatch.setattr(wake, "owner_inbox_pending", lambda: 0)
    monkeypatch.setattr(wake, "codex_inbox_pending", lambda: 0)
    # Mirror the real arity (wake.py passes rescue_context since e21cefa); a
    # 0-arity double silently rotted here for five days while the sibling
    # sentinel suite got the same fix in that commit.
    monkeypatch.setattr(wake, "escalation_decision", lambda rescue_context=None: "due")

    first_detection = wake.wake(commit=True)
    second_detection = wake.wake(commit=True)

    assert first_detection["codex_due"] is True
    assert first_detection["wake_brief"]["peer_chat_new"] == [chat]
    assert second_detection["wake_brief"]["peer_chat_new"] == [chat]
    assert not (tmp_path / "wake-cursor.json").exists()

    consumer_brief = wake.wake_brief_mod.build_brief(
        root=tmp_path,
        workspace=wake.WORKSPACE,
        scope=wake.SCOPE,
        updated_at_utc="2026-07-13T13:15:00+00:00",
        recall_fixture=_recall(),
        prospective_fixture={"goals": []},
    )

    assert consumer_brief["peer_chat_new"] == [chat]
    assert (tmp_path / "wake-cursor.json").exists()
