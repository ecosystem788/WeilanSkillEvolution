from __future__ import annotations

import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WAKE_IMPL = ROOT / "proposals" / "bounded-scheduler-v0.1" / "impl"
PEER_IMPL = ROOT / "proposals" / "mutual-aid-v0.1"
for module_dir in (WAKE_IMPL, PEER_IMPL):
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

import wake_brief  # noqa: E402
from peer_health_wake import _rows  # noqa: E402


CORE = {
    "source",
    "line",
    "reason_code",
    "detail",
    "raw_text",
    "raw_bytes_sha256",
    "byte_offset",
}


def _diagnostics_from_peer(path: Path) -> list[dict]:
    errors: list[dict] = []
    _rows(path, parse_errors=errors)
    return errors


def _assert_core(diag: dict) -> None:
    assert CORE <= diag.keys()
    assert isinstance(diag["source"], str) and f":{diag['line']}" not in diag["source"]
    assert isinstance(diag["line"], int)
    assert diag["reason_code"] in {"invalid_json", "not_object", "decode_failure"}
    assert isinstance(diag["detail"], str)
    assert diag["raw_text"] is None or isinstance(diag["raw_text"], str)
    assert len(diag["raw_bytes_sha256"]) == 64
    assert isinstance(diag["byte_offset"], int)


def test_three_readers_share_core_identity_and_incremental_absolute_coordinates(tmp_path: Path) -> None:
    good = b'{"ok":true}\n'
    bad = b'{"text":"D:\\bad\\escape"}\n'
    path = tmp_path / "fixture.jsonl"
    path.write_bytes(good + bad)

    full = wake_brief.read_jsonl(path)[1]
    bytes_full = wake_brief._jsonl_from_bytes(path, path.read_bytes())[1]
    peer = _diagnostics_from_peer(path)[0]
    incremental = wake_brief._jsonl_from_bytes(
        path,
        bad,
        start_line=wake_brief._line_count(good),
        start_byte=len(good),
    )[0]

    for diag in (full, bytes_full, peer, incremental):
        _assert_core(diag)
    identity = ("source", "line", "reason_code", "raw_bytes_sha256", "byte_offset")
    assert all(tuple(diag[key] for key in identity) == tuple(full[key] for key in identity) for diag in (bytes_full, peer, incremental))
    assert full["line"] == 2
    assert full["byte_offset"] == len(good)


def test_record_hash_boundaries_crlf_unterminated_and_decode_failure(tmp_path: Path) -> None:
    crlf = b'{"broken":}\r\n'
    unterminated = b'{"broken":}'
    undecodable = b'{"bad":"\xff"}\n'
    path = tmp_path / "boundaries.jsonl"
    path.write_bytes(crlf + unterminated + b"\n" + undecodable)

    diagnostics = wake_brief.read_jsonl(path)
    assert diagnostics[0]["raw_bytes_sha256"] == hashlib.sha256(crlf).hexdigest()
    assert diagnostics[0]["raw_text"] == crlf[:-2].decode()
    second_record = unterminated + b"\n"
    assert diagnostics[1]["raw_bytes_sha256"] == hashlib.sha256(second_record).hexdigest()
    assert diagnostics[2]["reason_code"] == "decode_failure"
    assert diagnostics[2]["raw_text"] is None

    last_path = tmp_path / "unterminated.jsonl"
    last_path.write_bytes(unterminated)
    last = wake_brief.read_jsonl(last_path)[0]
    assert last["raw_bytes_sha256"] == hashlib.sha256(unterminated).hexdigest()


def test_pathological_prefix_does_not_shift_incremental_line_or_offset(tmp_path: Path) -> None:
    for prefix in (b'{"note":"a\rb"}\n', '{"note":"a\u2028b"}\n'.encode("utf-8")):
        bad = b'{"broken":}\n'
        path = tmp_path / ("isolated-cr.jsonl" if b"\r" in prefix else "u2028.jsonl")
        path.write_bytes(prefix + bad)
        full = wake_brief.read_jsonl(path)[1]
        incremental = wake_brief._jsonl_from_bytes(
            path,
            bad,
            start_line=wake_brief._line_count(prefix),
            start_byte=len(prefix),
        )[0]
        assert wake_brief._line_count(prefix) == 1
        assert (incremental["line"], incremental["byte_offset"]) == (full["line"], full["byte_offset"])


def test_not_object_uses_shared_reason_code(tmp_path: Path) -> None:
    path = tmp_path / "not-object.jsonl"
    path.write_bytes(b"[]\n")
    wake = wake_brief.read_jsonl(path)[0]
    peer = _diagnostics_from_peer(path)[0]
    assert wake["reason_code"] == peer["reason_code"] == "not_object"
    assert wake == peer
