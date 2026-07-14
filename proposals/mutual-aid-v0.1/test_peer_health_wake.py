import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from peer_health_wake import main, run_check


NOW = datetime(2026, 7, 12, 2, tzinfo=timezone.utc)  # 11:00 UTC+9


def append(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def fixture(root: Path, activity_time="2026-07-12 10:55:00", replied=False):
    append(root / "peer-chat.jsonl", {"from": "codex", "time": activity_time, "text": "alive"})
    append(root / "codex-inbox.jsonl", {"id": "job-a", "from": "claude"})
    if replied:
        append(
            root / "codex-inbox-replies.jsonl",
            {"reply_to": "job-a", "from": "codex", "time": activity_time, "text": "done"},
        )


def alerts(root):
    path = root / "peer-health-alerts.jsonl"
    return [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_real_shape_fresh_activity_does_not_raise(tmp_path):
    fixture(tmp_path)
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_small_future_activity_is_fresh_end_to_end(tmp_path):
    future_local = (NOW + timedelta(minutes=5)).astimezone(
        timezone(timedelta(hours=9))
    ).strftime("%Y-%m-%d %H:%M:%S")
    fixture(tmp_path, activity_time=future_local)
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_silent_pending_raises_once_and_is_idempotent(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    first = run_check(root=tmp_path, now=NOW)
    assert len(first) == 1 and first[0]["event"] == "raised"
    assert first[0]["raised_by"] == "claude" and first[0]["peer"] == "codex"
    assert first[0]["status"] == "suspected"
    assert first[0]["silence"]["source_ref"] and first[0]["backlog"]["source_ref"]
    assert run_check(root=tmp_path, now=NOW) == []
    assert len(alerts(tmp_path)) == 1


def test_reply_clears_backlog_and_resolves_once(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    run_check(root=tmp_path, now=NOW)
    append(
        tmp_path / "codex-inbox-replies.jsonl",
        {"reply_to": "job-a", "from": "codex", "time": "2026-07-12 10:58:00", "text": "done"},
    )
    resolved = run_check(root=tmp_path, now=NOW)
    assert len(resolved) == 1 and resolved[0]["event"] == "resolved"
    assert run_check(root=tmp_path, now=NOW) == []


def test_malformed_or_missing_relevant_time_fails_safe_whole_round(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    append(tmp_path / "peer-chat.jsonl", {"from": "codex", "time": "not-a-time", "text": "newer bad"})
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []

    tmp_path.joinpath("peer-chat.jsonl").write_text(
        json.dumps({"from": "codex", "text": "missing time"}) + "\n", encoding="utf-8"
    )
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_malformed_json_row_is_visible_without_discarding_good_anchor(tmp_path):
    fixture(tmp_path)
    with (tmp_path / "peer-chat.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(r'{"from":"claude","text":"D:\bad\escape"}' + "\n")

    result = run_check(root=tmp_path, now=NOW)

    assert result == []
    assert result.activity_anchor == {
        "time_utc": "2026-07-12T01:55:00+00:00",
        "source_ref": "peer-chat.jsonl:1@2026-07-12 10:55:00 (codex activity)",
    }
    assert len(result.parse_errors) == 1
    assert result.parse_errors[0]["source"] == "peer-chat.jsonl:2"


def test_whole_file_read_failure_is_visible_in_cli(tmp_path, monkeypatch, capsys):
    fixture(tmp_path)
    original = Path.read_text

    def unreadable(path, *args, **kwargs):
        if path.name == "peer-chat.jsonl":
            raise PermissionError("test unreadable file")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    assert main(["--root", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["check"] == "skipped"
    assert report["appended"] == []
    assert report["skipped"]["source"] == "peer-chat.jsonl"
    assert "PermissionError" in report["skipped"]["reason"]


def test_authority_surfaces_are_byte_identical(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    protected = [tmp_path / "owner-inbox.jsonl", tmp_path / "activation.state", tmp_path / "codex-inbox.jsonl"]
    for path in protected[:2]:
        path.write_bytes((path.name + "\n").encode())
    before = {path: path.read_bytes() for path in protected}
    run_check(root=tmp_path, now=NOW)
    assert {path: path.read_bytes() for path in protected} == before
