from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("idle_run_linter.py")
SPEC = importlib.util.spec_from_file_location("idle_run_linter_v02", MODULE_PATH)
idle_run_linter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = idle_run_linter
SPEC.loader.exec_module(idle_run_linter)


def write_frame(root: Path, frame_id: str, ts: str, verdict: str) -> None:
    day = ts[:10].replace("-", "")
    path = root / day / f"{frame_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    events = [
        {"event_type": "frame_opened", "frame_id": frame_id, "timestamp_utc": ts},
        {"event_type": "frame_closed", "frame_id": frame_id, "data": {"verdict": verdict}},
    ]
    path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""), encoding="utf-8")


def make_known_empty_impl(root: Path) -> Path:
    impl = root / "impl"
    write_jsonl(impl / "peer-chat.jsonl", [])
    write_jsonl(impl / "owner-inbox-processed.jsonl", [])
    write_jsonl(impl / "codex-inbox-processed.jsonl", [])
    return impl


def test_layer2_flags_consecutive_work_frames_without_structural_delta(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    impl = make_known_empty_impl(tmp_path)
    write_frame(frames, "wf-a", "2026-07-11T00:00:00+00:00", "Answered a short tea-room note.")
    write_frame(frames, "wf-b", "2026-07-11T00:01:00+00:00", "Added a brief peer-chat thought.")
    write_frame(frames, "wf-c", "2026-07-11T00:02:00+00:00", "Replied with a bounded observation.")

    result = idle_run_linter.analyze(str(frames), str(impl), structural_window=3)

    suspects = result["layer2_structural_suspicions"]
    assert len(suspects) == 1
    assert suspects[0]["frame_ids"] == ["wf-a", "wf-b", "wf-c"]
    assert suspects[0]["classes"] == ["WORK", "WORK", "WORK"]
    assert suspects[0]["no_inbox_delta"] is True
    assert suspects[0]["no_proposal_or_test_ref"] is True
    assert suspects[0]["no_file_delta_ref"] is True


def test_layer2_window_is_independent_from_layer1_idle_streak(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    impl = make_known_empty_impl(tmp_path)
    write_frame(frames, "wf-a", "2026-07-11T00:00:00+00:00", "Brief peer-chat response.")
    write_frame(frames, "wf-b", "2026-07-11T00:01:00+00:00", "Another bounded observation.")
    write_frame(frames, "wf-c", "2026-07-11T00:02:00+00:00", "Short note without artifact.")
    write_frame(frames, "wf-d", "2026-07-11T00:03:00+00:00", "近空醒, 没有真结构, 歇着。")

    result = idle_run_linter.analyze(str(frames), str(impl), structural_window=3)

    assert result["layer1_idle_streak_window"]["suspected_idle_streak"] == 1
    assert result["layer1_idle_streak_window"]["frame_ids"] == ["wf-d"]
    assert result["layer2_structural_suspicions"][0]["frame_ids"] == ["wf-a", "wf-b", "wf-c"]


def test_inbox_delta_prevents_structural_suspected_window(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    impl = make_known_empty_impl(tmp_path)
    write_jsonl(impl / "codex-inbox-processed.jsonl", [{"id": "task-1", "time": "2026-07-11 09:01:00"}])
    write_frame(frames, "wf-a", "2026-07-11T00:00:00+00:00", "Brief response.")
    write_frame(frames, "wf-b", "2026-07-11T00:01:00+00:00", "Another response.")
    write_frame(frames, "wf-c", "2026-07-11T00:02:00+00:00", "Third response.")

    result = idle_run_linter.analyze(str(frames), str(impl), structural_window=3)

    assert result["layer2_structural_suspicions"] == []
    window = result["layer2_structural_windows"][0]
    assert window["status"] == "WORK_EVIDENCE_PRESENT"
    assert window["no_inbox_delta"] is False
    assert window["reasons"] == ["inbox_delta_present"]


def test_proposal_test_or_file_reference_prevents_structural_suspected_window(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    impl = make_known_empty_impl(tmp_path)
    write_frame(frames, "wf-a", "2026-07-11T00:00:00+00:00", "Brief response.")
    write_frame(frames, "wf-b", "2026-07-11T00:01:00+00:00", "Ran pytest for proposals/example/test_example.py.")
    write_frame(frames, "wf-c", "2026-07-11T00:02:00+00:00", "Third response.")

    result = idle_run_linter.analyze(str(frames), str(impl), structural_window=3)

    assert result["layer2_structural_suspicions"] == []
    window = result["layer2_structural_windows"][0]
    assert window["status"] == "WORK_EVIDENCE_PRESENT"
    assert "proposal_or_test_ref_present" in window["reasons"]
    assert "file_delta_ref_present" in window["reasons"]


def test_first_window_frame_activity_before_its_frame_opened_is_not_false_suspected(tmp_path: Path) -> None:
    # v0.2.1 regression: frame_opened is written at frame close, so a turn's own
    # activity is timestamped before its own frame_opened. The first frame of a
    # window must still have its own-turn inbox delta counted (via the prior
    # frame boundary), otherwise it is falsely flagged SUSPECTED.
    frames = tmp_path / "frames"
    impl = make_known_empty_impl(tmp_path)
    # codex-inbox processed during wf-a's turn: after wf-0 opened, before wf-a opened.
    write_jsonl(impl / "codex-inbox-processed.jsonl", [{"id": "task-x", "time": "2026-07-11T00:01:00+00:00"}])
    write_frame(frames, "wf-0", "2026-07-11T00:00:00+00:00", "Prior turn response.")
    write_frame(frames, "wf-a", "2026-07-11T00:02:00+00:00", "Brief response.")
    write_frame(frames, "wf-b", "2026-07-11T00:03:00+00:00", "Another response.")
    write_frame(frames, "wf-c", "2026-07-11T00:04:00+00:00", "Third response.")

    result = idle_run_linter.analyze(str(frames), str(impl), structural_window=3)

    windows = {tuple(w["frame_ids"]): w for w in result["layer2_structural_windows"]}
    target = windows[("wf-a", "wf-b", "wf-c")]
    assert target["no_inbox_delta"] is False
    assert target["status"] == "WORK_EVIDENCE_PRESENT"
    assert "inbox_delta_present" in target["reasons"]
    assert ("wf-a", "wf-b", "wf-c") not in {
        tuple(w["frame_ids"]) for w in result["layer2_structural_suspicions"]
    }


def test_unknown_activity_sources_do_not_become_suspected(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    write_frame(frames, "wf-a", "2026-07-11T00:00:00+00:00", "Brief response.")
    write_frame(frames, "wf-b", "2026-07-11T00:01:00+00:00", "Another response.")
    write_frame(frames, "wf-c", "2026-07-11T00:02:00+00:00", "Third response.")

    result = idle_run_linter.analyze(str(frames), None, structural_window=3)

    assert result["layer2_structural_suspicions"] == []
    assert result["layer2_structural_windows"][0]["status"] == "UNKNOWN"
    assert result["layer2_structural_windows"][0]["reasons"] == ["no_impl_root"]
