import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import append_clocked_jsonl


HERE = Path(__file__).resolve().parent


def test_helper_owns_clock_fields_and_preserves_existing_bytes(tmp_path):
    ledger = tmp_path / "peer-chat.jsonl"
    existing = b'{"from":"owner","text":"existing"}\n'
    ledger.write_bytes(existing)
    observed = datetime(2026, 7, 26, 9, 4, 29, tzinfo=timezone(timedelta(hours=9)))

    row = append_clocked_jsonl.append_clocked_row(
        root=tmp_path,
        ledger_name=ledger.name,
        payload={"from": "codex", "text": "clocked"},
        now=observed,
    )

    assert ledger.read_bytes().startswith(existing)
    assert row["time"] == "2026-07-26T09:04:29+09:00"
    assert row["time_authority"] == "clock"
    assert json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1]) == row


def test_helper_rejects_caller_clock_fields_without_writing(tmp_path):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"owner"}\n')
    before = ledger.read_bytes()

    for forbidden in ("time", "time_authority"):
        try:
            append_clocked_jsonl.append_clocked_row(
                root=tmp_path,
                ledger_name=ledger.name,
                payload={"from": "codex", forbidden: "caller-controlled"},
            )
        except ValueError as exc:
            assert "reserved clock fields" in str(exc)
        else:
            raise AssertionError(f"{forbidden} should have been rejected")
        assert ledger.read_bytes() == before


def test_cli_rejects_non_object_and_reserved_fields_without_partial_file(tmp_path, capsys):
    assert (
        append_clocked_jsonl.main(
            ["--root", str(tmp_path), "--file", "new.jsonl", "--data-json", "[]"]
        )
        == 2
    )
    assert not (tmp_path / "new.jsonl").exists()
    capsys.readouterr()

    assert (
        append_clocked_jsonl.main(
            [
                "--root",
                str(tmp_path),
                "--file",
                "new.jsonl",
                "--data-json",
                '{"time":"guessed","text":"no"}',
            ]
        )
        == 2
    )
    assert not (tmp_path / "new.jsonl").exists()


def test_cli_refuses_missing_ledger_without_allow_create(tmp_path, capsys):
    assert (
        append_clocked_jsonl.main(
            [
                "--root",
                str(tmp_path),
                "--file",
                "new.jsonl",
                "--field",
                "from=codex",
                "--field",
                "text=no opt-in",
            ]
        )
        == 2
    )
    assert not (tmp_path / "new.jsonl").exists()
    captured = capsys.readouterr()
    assert "refuse to create new ledger file" in captured.err


def test_cli_creates_missing_ledger_with_allow_create(tmp_path, capsys):
    assert (
        append_clocked_jsonl.main(
            [
                "--root",
                str(tmp_path),
                "--file",
                "new.jsonl",
                "--allow-create",
                "--field",
                "from=codex",
                "--field",
                "text=created",
            ]
        )
        == 0
    )
    rows = [
        json.loads(line)
        for line in (tmp_path / "new.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 1
    assert rows[0]["from"] == "codex"
    assert rows[0]["text"] == "created"
    assert rows[0]["time_authority"] == "clock"
    capsys.readouterr()


def test_cli_fields_are_powershell_safe_and_still_reserve_clock_fields(tmp_path, capsys):
    assert (
        append_clocked_jsonl.main(
            [
                "--root",
                str(tmp_path),
                "--file",
                "new.jsonl",
                "--allow-create",
                "--field",
                "from=codex",
                "--field",
                "text=value=keeps equals",
            ]
        )
        == 0
    )
    row = json.loads((tmp_path / "new.jsonl").read_text(encoding="utf-8"))
    assert row["from"] == "codex"
    assert row["text"] == "value=keeps equals"
    assert row["time_authority"] == "clock"
    capsys.readouterr()

    before = (tmp_path / "new.jsonl").read_bytes()
    assert (
        append_clocked_jsonl.main(
            [
                "--root",
                str(tmp_path),
                "--file",
                "new.jsonl",
                "--field",
                "time=guessed",
            ]
        )
        == 2
    )
    assert (tmp_path / "new.jsonl").read_bytes() == before


def test_helper_refuses_nested_target_and_unterminated_history(tmp_path):
    for name in ("../outside.jsonl", "nested/ledger.jsonl", "ledger.txt"):
        try:
            append_clocked_jsonl.append_clocked_row(
                root=tmp_path,
                ledger_name=name,
                payload={"text": "no"},
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"{name} should have been rejected")

    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"unterminated":true}')
    before = ledger.read_bytes()
    try:
        append_clocked_jsonl.append_clocked_row(
            root=tmp_path,
            ledger_name=ledger.name,
            payload={"text": "no"},
        )
    except ValueError as exc:
        assert "unterminated line" in str(exc)
    else:
        raise AssertionError("unterminated history should have been rejected")
    assert ledger.read_bytes() == before


def test_both_wake_prompts_route_agent_appends_through_helper():
    for name in ("wake_prompt.md", "wake_prompt_codex.md"):
        text = (HERE / name).read_text(encoding="utf-8")
        assert "append_clocked_jsonl.py" in text
        assert "调用方不得传 `time` / `time_authority`" in text
