from __future__ import annotations

import importlib.util
import json
from pathlib import Path


HELPER_PATH = (
    Path(__file__).parents[1]
    / "bounded-scheduler-v0.1"
    / "impl"
    / "append_clocked_jsonl.py"
)
SPEC = importlib.util.spec_from_file_location("append_clocked_jsonl", HELPER_PATH)
assert SPEC and SPEC.loader
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


HAZARDS = [
    r"ledger at D:\CodexData\home\config.toml end",
    "the span `peer-chat.jsonl` end",
    "read $CODEX_HOME end",
    "read $env:CODEX_HOME end",
    "it's fine end",
    'he said "fine" end',
    r"core D:\CodexData\home ; span `peer-chat.jsonl` ; $CODEX_HOME end",
]


def read_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_field_file(tmp_path: Path, name: str, value: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(value)
    return path


def test_field_file_preserves_exact_text_and_mixes_with_field(tmp_path: Path) -> None:
    ledger = "ledger.jsonl"
    for index, intended in enumerate(HAZARDS):
        source = write_field_file(tmp_path, f"field-{index}.txt", intended.encode("utf-8"))
        argv = [
            "--root",
            str(tmp_path),
            "--file",
            ledger,
        ]
        if index == 0:
            argv.append("--allow-create")
        argv.extend(
            [
                "--field",
                f"from=test-{index}",
                "--field-file",
                f"text={source}",
            ]
        )
        rc = HELPER.main(argv)
        assert rc == 0

    rows = read_rows(tmp_path / ledger)
    assert [row["text"] for row in rows] == HAZARDS
    assert [row["from"] for row in rows] == [f"test-{i}" for i in range(len(HAZARDS))]
    assert all(row["time_authority"] == "clock" for row in rows)


def test_field_file_rejects_invalid_inputs_without_append(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    valid = write_field_file(tmp_path, "valid.txt", b"valid")
    invalid_utf8 = write_field_file(tmp_path, "invalid-utf8.bin", b"\xff")
    bom = write_field_file(tmp_path, "bom.txt", b"\xef\xbb\xbfvalue")
    nul = write_field_file(tmp_path, "nul.txt", b"before\x00after")
    directory = tmp_path / "directory"
    directory.mkdir()

    cases = [
        ["--field-file", f"text={tmp_path / 'missing.txt'}"],
        ["--field-file", f"text={directory}"],
        ["--field-file", f"text={invalid_utf8}"],
        ["--field-file", f"text={bom}"],
        ["--field-file", f"text={nul}"],
        ["--field", "text=old", "--field-file", f"text={valid}"],
    ]
    for extra in cases:
        assert (
            HELPER.main(["--root", str(tmp_path), "--file", ledger.name, *extra])
            == 2
        )
        assert not ledger.exists()


def test_field_file_consumption_happens_only_after_success(tmp_path: Path) -> None:
    source = write_field_file(tmp_path, "consume.txt", b"consume me")
    assert (
        HELPER.main(
            [
                "--root",
                str(tmp_path),
                "--file",
                "ledger.jsonl",
                "--allow-create",
                "--field-file",
                f"text={source}",
                "--consume-field-file",
            ]
        )
        == 0
    )
    assert not source.exists()
    assert read_rows(tmp_path / "ledger.jsonl")[0]["text"] == "consume me"


def test_old_field_path_still_works(tmp_path: Path) -> None:
    assert (
        HELPER.main(
            [
                "--root",
                str(tmp_path),
                "--file",
                "ledger.jsonl",
                "--allow-create",
                "--field",
                "text=old path",
            ]
        )
        == 0
    )
    assert read_rows(tmp_path / "ledger.jsonl")[0]["text"] == "old path"
