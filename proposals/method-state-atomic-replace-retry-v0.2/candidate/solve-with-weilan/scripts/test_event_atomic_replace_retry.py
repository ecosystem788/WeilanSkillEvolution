"""Regression tests for event-file atomic replace retry behavior."""

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import runtime_core


def _event(frame_id):
    return {
        "schema_version": "weilan_method_event_v0.1",
        "event_id": f"event-{frame_id}",
        "frame_id": frame_id,
        "timestamp_utc": "2026-07-10T00:00:00+00:00",
        "event_type": "frame_opened",
        "level": "L2",
        "workspace": "D:\\WeilanSkillEvolution",
        "data": {"source": "isolated-candidate-test"},
    }


def _read_one_json_line(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


def test_event_atomic_replace_covers_reader_window_beyond_old_half_second_budget(
    tmp_path, monkeypatch
):
    target = tmp_path / "frames" / "wf-retry.jsonl"
    original_replace = os.replace
    calls = []
    elapsed = {"seconds": 0.0}

    def flaky_replace(temporary, path):
        calls.append((Path(temporary).name, Path(path).name))
        if elapsed["seconds"] < 0.75:
            raise PermissionError("simulated 0.75s reader conflict")
        original_replace(temporary, path)

    monkeypatch.setattr(runtime_core.os, "replace", flaky_replace)
    monkeypatch.setattr(time, "sleep", lambda delay: elapsed.__setitem__("seconds", elapsed["seconds"] + delay))

    runtime_core.write_event_file_atomic(target, _event("wf-retry"))

    assert len(calls) == 5
    assert elapsed["seconds"] == pytest.approx(0.75)
    assert _read_one_json_line(target)["frame_id"] == "wf-retry"
    assert not list(target.parent.glob(".wf-retry.jsonl.*.tmp"))


def test_event_atomic_replace_exhaustion_preserves_existing_frame_and_reports_error(
    tmp_path, monkeypatch, capsys
):
    target = tmp_path / "frames" / "wf-existing.jsonl"
    target.parent.mkdir(parents=True)
    existing = json.dumps({"frame_id": "wf-existing", "event_type": "frame_opened"}) + "\n"
    target.write_text(existing, encoding="utf-8")
    sleeps = []
    calls = []

    def blocked_replace(_temporary, _path):
        calls.append(1)
        raise PermissionError("simulated persistent reader conflict")

    monkeypatch.setattr(runtime_core.os, "replace", blocked_replace)
    monkeypatch.setattr(time, "sleep", lambda delay: sleeps.append(delay))

    with pytest.raises(PermissionError, match="persistent reader conflict"):
        runtime_core.write_event_file_atomic(target, _event("wf-new"))

    assert len(calls) == 8
    assert sleeps == pytest.approx([0.05, 0.1, 0.2, 0.4, 0.4, 0.4, 0.4, 0.4])
    assert target.read_text(encoding="utf-8") == existing
    assert not list(target.parent.glob(".wf-existing.jsonl.*.tmp"))
    record = json.loads(capsys.readouterr().err)
    assert record["event"] == "replace_with_retry_exhausted"
    assert record["attempts"] == 8
    assert record["permission_errors"] == 8
    assert record["total_wait_s"] == pytest.approx(2.35)
    assert record["exhausted"] is True
    assert record["target"] == str(target)


def test_concurrent_frame_writes_remain_complete_while_directory_is_scanned(tmp_path):
    frames_dir = tmp_path / "method-state" / "frames" / "2026-07-10"
    frames_dir.mkdir(parents=True)
    stop = threading.Event()
    scanner_errors = []

    def scan_directory():
        while not stop.is_set():
            try:
                for path in frames_dir.iterdir():
                    if path.is_file() and not path.name.startswith("."):
                        path.read_text(encoding="utf-8")
            except Exception as exc:  # pragma: no cover - failure details are asserted.
                scanner_errors.append(repr(exc))
                stop.set()

    scanner = threading.Thread(target=scan_directory)
    scanner.start()
    try:
        def write_frame(index):
            frame_id = f"wf-concurrent-{index:02d}"
            runtime_core.write_event_file_atomic(
                frames_dir / f"{frame_id}.jsonl",
                _event(frame_id),
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(write_frame, range(40)))
    finally:
        stop.set()
        scanner.join(timeout=5)

    assert scanner_errors == []
    frame_files = sorted(frames_dir.glob("wf-concurrent-*.jsonl"))
    assert len(frame_files) == 40
    for path in frame_files:
        assert _read_one_json_line(path)["frame_id"] == path.stem
    assert not list(frames_dir.glob(".*.tmp"))
