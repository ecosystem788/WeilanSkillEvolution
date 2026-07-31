"""Regression tests for the process-local find_frame id -> path table.

The table is an optimisation only. These tests pin vanished-path fallback,
in-process invalidation, duplicate detection, and the full date-directory mtime
guard for observable foreign changes, plus the pre-existing empty/missing
behaviours. The remaining same-mtime-tick hole is bounded in the proposal.
"""

import os
import time
from pathlib import Path

import pytest

import weilan_trace


@pytest.fixture()
def frames(tmp_path, monkeypatch):
    """A method-state root with a frames/ tree, with the table reset around it."""
    method_state = tmp_path / "method-state"
    (method_state / "frames").mkdir(parents=True)
    monkeypatch.setenv("WEILAN_METHOD_HOME", str(method_state))
    monkeypatch.setattr(weilan_trace, "state_root", lambda: method_state)
    weilan_trace.invalidate_frame_index()
    yield method_state / "frames"
    weilan_trace.invalidate_frame_index()


def write_frame(frames_root, date_dir, frame_id, *, events=1):
    path = frames_root / date_dir / f"{frame_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(
        '{"schema_version": "x", "event_id": "e%d", "frame_id": "%s", '
        '"timestamp_utc": "2026-08-01T00:00:00+00:00", "event_type": "frame_opened", '
        '"level": "L2", "workspace": "W", "data": {}}\n' % (index, frame_id)
        for index in range(events)
    )
    path.write_text(body, encoding="utf-8")
    return path


def glob_find(frames_root, frame_id):
    """The pre-change implementation, used as the oracle."""
    candidates = list(frames_root.glob(f"*/{frame_id}.jsonl"))
    matches = [path for path in candidates if weilan_trace.read_events(path)]
    if not matches:
        raise FileNotFoundError(f"frame not found: {frame_id}")
    if len(matches) > 1:
        raise RuntimeError(f"multiple frame files found: {frame_id}")
    return matches[0]


def test_indexed_lookup_matches_glob_oracle(frames):
    for index in range(5):
        write_frame(frames, "2026-07-%02d" % (20 + index), "wf-fixture-%d" % index)
    for index in range(5):
        frame_id = "wf-fixture-%d" % index
        assert weilan_trace.find_frame(frame_id) == glob_find(frames, frame_id)


def test_table_is_actually_used_not_just_correct(frames):
    """Guard against a silent regression to per-id globbing.

    Without this, an implementation that ignored the table entirely would still
    pass every other test in this file.
    """
    write_frame(frames, "2026-07-20", "wf-cached")
    weilan_trace.find_frame("wf-cached")

    calls = []
    real_glob = Path.glob

    def counting_glob(self, pattern):
        calls.append(pattern)
        return real_glob(self, pattern)

    original = Path.glob
    Path.glob = counting_glob
    try:
        weilan_trace.find_frame("wf-cached")
    finally:
        Path.glob = original
    assert calls == [], f"second lookup still globbed: {calls}"


def test_a_vanished_indexed_path_falls_back_to_glob(frames):
    """Obligation (a): a deletion between build and lookup must not be served."""
    path = write_frame(frames, "2026-07-20", "wf-moved")
    assert weilan_trace.find_frame("wf-moved") == path

    # Move the frame to another date directory behind the table's back.
    moved = frames / "2026-07-21" / "wf-moved.jsonl"
    moved.parent.mkdir(parents=True, exist_ok=True)
    os.replace(path, moved)

    assert weilan_trace.find_frame("wf-moved") == moved
    assert weilan_trace.find_frame("wf-moved") == glob_find(frames, "wf-moved")


def test_a_vanished_indexed_path_with_no_replacement_raises(frames):
    path = write_frame(frames, "2026-07-20", "wf-deleted")
    assert weilan_trace.find_frame("wf-deleted") == path
    path.unlink()
    with pytest.raises(FileNotFoundError):
        weilan_trace.find_frame("wf-deleted")


def test_b_append_event_under_frames_invalidates_the_table(frames):
    """Obligation (b): a frame this process writes is visible to the next lookup."""
    write_frame(frames, "2026-07-20", "wf-existing")
    weilan_trace.find_frame("wf-existing")  # builds the table without wf-new

    new_path = frames / "2026-07-21" / "wf-new.jsonl"
    weilan_trace.append_event(
        new_path,
        weilan_trace.make_event("wf-new", "frame_opened", "L2", "W", {}),
    )
    assert weilan_trace.find_frame("wf-new") == new_path


def test_b_append_outside_frames_keeps_the_table(frames, tmp_path):
    """Invalidation is narrow: an unrelated ledger append must not drop the table."""
    write_frame(frames, "2026-07-20", "wf-keep")
    weilan_trace.find_frame("wf-keep")
    assert weilan_trace._FRAME_INDEX is not None

    weilan_trace.append_event(
        tmp_path / "method-state" / "lineage" / "2026-07-20.jsonl",
        {"schema_version": "x", "note": "unrelated ledger"},
    )
    assert weilan_trace._FRAME_INDEX is not None


def test_c_multiple_live_matches_still_raise(frames):
    """Obligation (c): the duplicate-id error survives the table."""
    write_frame(frames, "2026-07-20", "wf-dup")
    write_frame(frames, "2026-07-21", "wf-dup")
    with pytest.raises(RuntimeError):
        weilan_trace.find_frame("wf-dup")
    with pytest.raises(RuntimeError):
        glob_find(frames, "wf-dup")


def test_empty_frame_files_are_still_filtered(frames):
    """read_events() filtering is unchanged: an empty file is not a match."""
    empty = write_frame(frames, "2026-07-20", "wf-empty", events=0)
    assert empty.read_bytes() == b""
    with pytest.raises(FileNotFoundError):
        weilan_trace.find_frame("wf-empty")

    live = write_frame(frames, "2026-07-21", "wf-empty")
    weilan_trace.invalidate_frame_index()
    assert weilan_trace.find_frame("wf-empty") == live


def test_missing_id_still_raises_file_not_found(frames):
    write_frame(frames, "2026-07-20", "wf-present")
    with pytest.raises(FileNotFoundError):
        weilan_trace.find_frame("wf-absent")


def test_foreign_second_file_rebuilds_after_observable_mtime_change(frames):
    """T2: an observable foreign directory-mtime change rebuilds the table."""
    first = write_frame(frames, "2026-07-20", "wf-race")
    write_frame(frames, "2026-07-21", "wf-anchor")
    assert weilan_trace.find_frame("wf-race") == first
    date_dir = frames / "2026-07-21"
    indexed_mtime = date_dir.stat().st_mtime_ns

    # Cross the measured roughly 1 ms timestamp grain before the foreign write,
    # then wait again before lookup. The explicit inequality pins T2's premise.
    time.sleep(0.005)
    write_frame(frames, date_dir.name, "wf-race")
    time.sleep(0.005)
    assert date_dir.stat().st_mtime_ns != indexed_mtime

    with pytest.raises(RuntimeError):
        weilan_trace.find_frame("wf-race")
    with pytest.raises(RuntimeError):
        glob_find(frames, "wf-race")


def test_same_mtime_tick_residual_is_pinned_not_hidden(frames, monkeypatch):
    """An unobservable same-tick foreign write remains an explicit boundary."""
    first = write_frame(frames, "2026-07-20", "wf-same-tick")
    write_frame(frames, "2026-07-21", "wf-anchor")
    assert weilan_trace.find_frame("wf-same-tick") == first
    guard_snapshot = dict(weilan_trace._FRAME_INDEX_DIR_MTIMES)

    write_frame(frames, "2026-07-21", "wf-same-tick")
    monkeypatch.setattr(
        weilan_trace,
        "_scan_frame_date_dirs",
        lambda _frames_root: ([], guard_snapshot),
    )

    assert weilan_trace.find_frame("wf-same-tick") == first
    with pytest.raises(RuntimeError):
        glob_find(frames, "wf-same-tick")
