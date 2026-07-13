import hashlib
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("compile_view.py")
SPEC = importlib.util.spec_from_file_location("compile_view", MODULE_PATH)
compile_view = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(compile_view)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def correction(raw: bytes, corrected: dict, reason: str = "repair") -> dict:
    return {
        "corrects": "human hint only",
        "reason": reason,
        "before_hash": compile_view.sha256_hex(raw),
        "after_hash": compile_view.sha256_hex(compile_view.canonical(corrected)),
        "corrected_json": corrected,
    }


def write_fixture(tmp_path: Path):
    raw = tmp_path / "peer-chat.jsonl"
    corrections = tmp_path / "peer-chat.corrections.jsonl"
    malformed_fixed = b'{"from":"claude",bad}'
    malformed_open = b'{"from":"owner"'
    semantic_raw = compile_view.canonical({"from": "codex", "text": "old"})
    raw.write_bytes(
        compile_view.canonical({"from": "owner", "text": "hello"})
        + b"\n"
        + malformed_fixed
        + b"\n"
        + malformed_open
        + b"\n"
        + semantic_raw
        + b"\n"
    )
    rows = [
        correction(malformed_fixed, {"from": "claude", "text": "fixed"}),
        correction(semantic_raw, {"from": "codex", "text": "new"}, "semantic"),
    ]
    corrections.write_bytes(b"".join(compile_view.canonical(row) + b"\n" for row in rows))
    return raw, corrections, malformed_fixed, malformed_open, semantic_raw


def parsed_lines(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_golden_strict_view_raw_unchanged_and_placeholder_parseable(tmp_path):
    raw, corrections, malformed_fixed, malformed_open, semantic_raw = write_fixture(tmp_path)
    view = tmp_path / "peer-chat.view.jsonl"
    rejections = tmp_path / "peer-chat.view.rejections.jsonl"
    raw_before, corrections_before = digest(raw), digest(corrections)

    result = compile_view.compile_view(raw, corrections, view, rejections)
    rows = parsed_lines(view)  # strict json.loads for every derived line

    assert result == {"applied": 2, "rejected": 0, "view_lines": 4}
    assert rows[1]["text"] == "fixed"
    assert rows[1]["_corrected_from"] == compile_view.sha256_hex(malformed_fixed)
    assert rows[3]["text"] == "new"
    assert rows[3]["_corrected_from"] == compile_view.sha256_hex(semantic_raw)
    assert rows[2] == {
        "_lineage": "unparseable",
        "before_hash": compile_view.sha256_hex(malformed_open),
        "raw_preserved": True,
        "source": f"{raw}:3",
    }
    assert digest(raw) == raw_before
    assert digest(corrections) == corrections_before


def test_before_hash_mismatch_is_rejected(tmp_path):
    raw, corrections, _, _, _ = write_fixture(tmp_path)
    bad = correction(b"not a raw line", {"text": "never"})
    corrections.write_bytes(compile_view.canonical(bad) + b"\n")
    view = tmp_path / "peer-chat.view.jsonl"
    rejected = tmp_path / "peer-chat.view.rejections.jsonl"

    result = compile_view.compile_view(raw, corrections, view, rejected)

    assert result["applied"] == 0
    assert parsed_lines(rejected)[0]["reason"] == "before_hash_not_found"
    assert parsed_lines(view)[1]["_lineage"] == "unparseable"


def test_after_hash_mismatch_is_rejected(tmp_path):
    raw, corrections, malformed_fixed, _, _ = write_fixture(tmp_path)
    bad = correction(malformed_fixed, {"text": "first"})
    bad["corrected_json"] = {"text": "tampered"}
    corrections.write_bytes(compile_view.canonical(bad) + b"\n")
    view = tmp_path / "peer-chat.view.jsonl"
    rejected = tmp_path / "peer-chat.view.rejections.jsonl"

    result = compile_view.compile_view(raw, corrections, view, rejected)

    assert result["applied"] == 0
    assert parsed_lines(rejected)[0]["reason"] == "after_hash_mismatch"
    assert parsed_lines(view)[1]["_lineage"] == "unparseable"


def test_repeated_compilation_is_byte_identical(tmp_path):
    raw, corrections, *_ = write_fixture(tmp_path)
    view = tmp_path / "peer-chat.view.jsonl"
    rejected = tmp_path / "peer-chat.view.rejections.jsonl"
    compile_view.compile_view(raw, corrections, view, rejected)
    first = (view.read_bytes(), rejected.read_bytes())

    compile_view.compile_view(raw, corrections, view, rejected)

    assert (view.read_bytes(), rejected.read_bytes()) == first


def test_malformed_correction_is_recorded_without_abort(tmp_path):
    raw, corrections, *_ = write_fixture(tmp_path)
    corrections.write_bytes(corrections.read_bytes() + b'{"broken"\n')
    view = tmp_path / "peer-chat.view.jsonl"
    rejected = tmp_path / "peer-chat.view.rejections.jsonl"

    result = compile_view.compile_view(raw, corrections, view, rejected)

    assert result["applied"] == 2
    assert result["rejected"] == 1
    assert parsed_lines(rejected)[0]["reason"] == "malformed_correction"
    assert len(parsed_lines(view)) == 4
