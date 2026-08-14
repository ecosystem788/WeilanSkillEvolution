import json

import append_clocked_jsonl


def _seed_ledger(tmp_path):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_bytes(b'{"from":"owner","text":"seed"}\n')
    return ledger


def test_wake_true_without_agent_refuses_zero_writes(tmp_path, capsys):
    ledger = _seed_ledger(tmp_path)
    before = ledger.read_bytes()
    rc = append_clocked_jsonl.main([
        "--root", str(tmp_path), "--file", ledger.name,
        "--field", "from=codex", "--field", "text=no agent", "--wake-true",
    ])
    assert rc == 2
    assert ledger.read_bytes() == before
    captured = capsys.readouterr()
    assert "requires --wake-agent" in captured.err


def test_wake_agent_without_wake_true_refuses(tmp_path, capsys):
    ledger = _seed_ledger(tmp_path)
    before = ledger.read_bytes()
    rc = append_clocked_jsonl.main([
        "--root", str(tmp_path), "--file", ledger.name,
        "--field", "from=codex", "--field", "text=agent only", "--wake-agent", "claude",
    ])
    assert rc == 2
    assert ledger.read_bytes() == before


def test_wake_true_with_agent_writes_ledger_and_sentinel(tmp_path, capsys):
    ledger = _seed_ledger(tmp_path)
    rc = append_clocked_jsonl.main([
        "--root", str(tmp_path), "--file", ledger.name,
        "--field", "from=codex", "--field", "text=wake claude",
        "--wake-true", "--wake-agent", "claude",
    ])
    assert rc == 0
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])
    assert row["wake"] is True
    sentinel = tmp_path / "watcher" / "sentinel.claude"
    assert sentinel.is_file()
    content = sentinel.read_text(encoding="utf-8").splitlines()
    assert content[0] == "claude"
    assert content[1] == "ledger=peer-chat.jsonl"
    assert content[2] == "row_time=" + row["time"]


def test_sentinel_dir_override(tmp_path, capsys):
    ledger = _seed_ledger(tmp_path)
    custom = tmp_path / "custom-sentinels"
    rc = append_clocked_jsonl.main([
        "--root", str(tmp_path), "--file", ledger.name,
        "--field", "from=codex", "--field", "text=wake codex",
        "--wake-true", "--wake-agent", "codex",
        "--sentinel-dir", str(custom),
    ])
    assert rc == 0
    assert (custom / "sentinel.codex").is_file()
    assert not (tmp_path / "watcher").exists()


def test_no_wake_args_writes_no_sentinel(tmp_path, capsys):
    ledger = _seed_ledger(tmp_path)
    rc = append_clocked_jsonl.main([
        "--root", str(tmp_path), "--file", ledger.name,
        "--field", "from=codex", "--field", "text=plain",
    ])
    assert rc == 0
    assert not (tmp_path / "watcher").exists()


def test_sentinel_write_failure_keeps_ledger_row(tmp_path, capsys):
    ledger = _seed_ledger(tmp_path)
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"file in the way")
    rc = append_clocked_jsonl.main([
        "--root", str(tmp_path), "--file", ledger.name,
        "--field", "from=codex", "--field", "text=wake claude",
        "--wake-true", "--wake-agent", "claude",
        "--sentinel-dir", str(blocker),
    ])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Warning: wake sentinel write failed" in captured.err
    rows = ledger.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2  # seed + new row: message is never lost


def test_sentinel_write_is_atomic_no_tmp_leftovers(tmp_path, capsys):
    ledger = _seed_ledger(tmp_path)
    rc = append_clocked_jsonl.main([
        "--root", str(tmp_path), "--file", ledger.name,
        "--field", "from=codex", "--field", "text=wake claude",
        "--wake-true", "--wake-agent", "claude",
    ])
    assert rc == 0
    leftovers = [p.name for p in (tmp_path / "watcher").iterdir() if ".tmp" in p.name]
    assert leftovers == []
