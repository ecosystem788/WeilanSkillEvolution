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


def test_helper_rejects_caller_reserved_fields_without_writing(tmp_path):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"owner"}\n')
    before = ledger.read_bytes()

    for forbidden in ("time", "time_authority", "wake"):
        try:
            append_clocked_jsonl.append_clocked_row(
                root=tmp_path,
                ledger_name=ledger.name,
                payload={"from": "codex", forbidden: "caller-controlled"},
            )
        except ValueError as exc:
            assert "reserved fields" in str(exc)
            assert forbidden in str(exc)
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


def test_helper_defaults_wake_false_when_flag_unset(tmp_path):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"seed"}\n')

    row = append_clocked_jsonl.append_clocked_row(
        root=tmp_path,
        ledger_name=ledger.name,
        payload={"from": "codex", "text": "default"},
    )

    assert row["wake"] is False
    persisted = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert persisted["wake"] is False


def test_helper_wake_true_flag_propagates_to_persisted_row(tmp_path):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"seed"}\n')

    row = append_clocked_jsonl.append_clocked_row(
        root=tmp_path,
        ledger_name=ledger.name,
        payload={"from": "codex", "text": "owner-bridge"},
        wake=True,
    )

    assert row["wake"] is True
    persisted = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert persisted["wake"] is True
    assert persisted["text"] == "owner-bridge"


def test_helper_wake_field_always_present_even_when_payload_empty(tmp_path):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"seed"}\n')

    row = append_clocked_jsonl.append_clocked_row(
        root=tmp_path,
        ledger_name=ledger.name,
        payload={"from": "codex"},
        wake=True,
    )

    assert "wake" in row
    assert "time" in row
    assert "time_authority" in row


def test_cli_wake_true_flag_round_trips_to_ledger(tmp_path, capsys):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"seed"}\n')

    rc = append_clocked_jsonl.main(
        [
            "--root",
            str(tmp_path),
            "--file",
            ledger.name,
            "--wake-true",
            "--field",
            "from=codex",
            "--field",
            "text=trigger",
        ]
    )
    assert rc == 0
    capsys.readouterr()
    persisted = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert persisted["wake"] is True
    assert persisted["text"] == "trigger"


def test_cli_default_wake_false_when_flag_absent(tmp_path, capsys):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"seed"}\n')

    rc = append_clocked_jsonl.main(
        [
            "--root",
            str(tmp_path),
            "--file",
            ledger.name,
            "--field",
            "from=codex",
            "--field",
            "text=quiet",
        ]
    )
    assert rc == 0
    capsys.readouterr()
    persisted = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert persisted["wake"] is False


def test_cli_caller_supplied_wake_via_field_is_rejected_without_writing(tmp_path, capsys):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"seed"}\n')
    before = ledger.read_bytes()

    rc = append_clocked_jsonl.main(
        [
            "--root",
            str(tmp_path),
            "--file",
            ledger.name,
            "--field",
            "from=codex",
            "--field",
            "wake=true",
            "--field",
            "text=no",
        ]
    )
    assert rc == 2
    assert ledger.read_bytes() == before
    captured = capsys.readouterr()
    assert "reserved fields" in captured.err
    assert "wake" in captured.err


def test_cli_caller_supplied_wake_via_data_json_is_rejected_without_writing(tmp_path, capsys):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"seed"}\n')
    before = ledger.read_bytes()

    rc = append_clocked_jsonl.main(
        [
            "--root",
            str(tmp_path),
            "--file",
            ledger.name,
            "--data-json",
            '{"from":"codex","wake":true,"text":"no"}',
        ]
    )
    assert rc == 2
    assert ledger.read_bytes() == before
    captured = capsys.readouterr()
    assert "reserved fields" in captured.err
    assert "wake" in captured.err


def test_helper_explicit_wake_false_is_distinct_from_default(tmp_path):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"seed"}\n')

    row_default = append_clocked_jsonl.append_clocked_row(
        root=tmp_path,
        ledger_name=ledger.name,
        payload={"from": "codex", "text": "default"},
    )
    row_explicit = append_clocked_jsonl.append_clocked_row(
        root=tmp_path,
        ledger_name=ledger.name,
        payload={"from": "codex", "text": "explicit"},
        wake=False,
    )

    assert row_default["wake"] is False
    assert row_explicit["wake"] is False
    assert row_default["wake"] == row_explicit["wake"]
