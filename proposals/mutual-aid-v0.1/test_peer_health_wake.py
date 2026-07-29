import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

COMPILE_VIEW_ROOT = Path(__file__).resolve().parents[1] / "lineage-log-append-only-correction-v0.1"
if str(COMPILE_VIEW_ROOT) not in sys.path:
    sys.path.insert(0, str(COMPILE_VIEW_ROOT))

import compile_view
import peer_health_wake
from peer_health_wake import main, run_check, run_reverse_check


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


def codex_runs(root: Path, *stamps: str, executed: bool = True, encoding: str = "utf-16") -> None:
    """Write either model-executed or fire-only Codex runs in the real JSONL shape."""
    runs = root / "wake-codex-runs"
    runs.mkdir(parents=True, exist_ok=True)
    rows = (
        [
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message"}},
            {"type": "turn.completed"},
        ]
        if executed
        else [
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"id": "item_0", "type": "error"}},
            {"type": "turn.failed", "error": {"message": "tls handshake eof"}},
        ]
    )
    payload = "".join(json.dumps(row) + "\n" for row in rows)
    for stamp in stamps:
        (runs / f"{stamp.replace(' ', 'T').replace(':', '-')}.jsonl").write_text(
            payload, encoding=encoding
        )


def alerts(root):
    path = root / "peer-health-alerts.jsonl"
    return [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def cron_line(stamp: str, parent: str) -> str:
    return (
        f'{stamp} ERROR rc=3 stage=native_exit stderr={{"frame_commit_failure":'
        f'{{"stage":"frame_open_stale_head","attempted_parent":"{parent}"}}}}'
    )


def write_cron(root: Path, lines: list[str]) -> None:
    (root / "wake-cron.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def reverse_fixture(root: Path, *, claude_time="2026-07-16 16:00:00", heartbeat_count=3):
    append(root / "peer-chat.jsonl", {"from": "claude", "time": "2026-07-16 15:00:00", "text": "here"})
    append(
        root / "concurrent-receipts.jsonl",
        {"wake_id": "claude-wake-test", "time": "2026-07-16 15:30:00", "work_performed": False},
    )
    runs = root / "wake-agent-runs"
    runs.mkdir(parents=True)
    run_name = claude_time.replace(" ", "T").replace(":", "-")
    (runs / f"{run_name}.json").write_text("{}", encoding="utf-8")
    codex_runs = root / "wake-codex-runs"
    codex_runs.mkdir(parents=True)
    for hour in range(17, 17 + heartbeat_count):
        (codex_runs / f"2026-07-16T{hour:02d}-00-00.jsonl").write_text("", encoding="utf-8")


def malformed_chat(root: Path, *, time="2026-07-13 18:22:40", suffix="") -> str:
    raw = f'{{"from":"claude","time":"{time}","text":"D:\\bad\\escape{suffix}"}}'
    with (root / "peer-chat.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(raw + "\n")
    return raw


def malformed_chat_bytes(
    root: Path,
    *,
    terminator: bytes,
    time: str = "2026-07-13 18:22:40",
) -> bytes:
    raw = f'{{"from":"claude","time":"{time}","text":"D:\\bad\\escape"}}'.encode()
    with (root / "peer-chat.jsonl").open("ab") as stream:
        stream.write(raw + terminator)
    return raw + terminator


def correction(root: Path, *, corrects: str, before_hash: str) -> None:
    append(
        root / "peer-chat.corrections.jsonl",
        {"corrects": corrects, "before_hash": before_hash, "corrected_json": {"time": corrects}},
    )


def test_terminal_same_parent_streak_raises_orphan_alert_with_evidence(tmp_path):
    fixture(tmp_path)
    write_cron(tmp_path, [cron_line(f"2026-07-16T18:{minute:02d}:58", "wf-parent-a") for minute in range(10)])

    result = run_check(root=tmp_path, now=NOW)

    assert len(result) == 1
    alert = result[0]
    assert alert["kind"] == "orphan_frame"
    assert alert["parent_frame_id"] == "wf-parent-a"
    assert alert["first_error_time"] == "2026-07-16T18:00:58"
    assert alert["last_error_time"] == "2026-07-16T18:09:58"
    assert alert["consecutive_count"] == 10
    assert alert["authority"] == "none"


def test_real_current_log_tail_does_not_raise_orphan_alert(tmp_path):
    fixture(tmp_path)
    real_log = Path(__file__).resolve().parents[1] / "bounded-scheduler-v0.1" / "impl" / "wake-cron.log"
    (tmp_path / "wake-cron.log").write_bytes(real_log.read_bytes())

    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_success_line_truncates_old_orphan_streak(tmp_path):
    fixture(tmp_path)
    lines = [cron_line(f"2026-07-16T18:{minute:02d}:58", "wf-parent-a") for minute in range(10)]
    lines.append("2026-07-16T18:10:58 wake ok stop=quiescent frame=wf-success")
    write_cron(tmp_path, lines)

    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_unresolved_same_parent_orphan_alert_is_deduplicated(tmp_path):
    fixture(tmp_path)
    write_cron(tmp_path, [cron_line(f"2026-07-16T18:{minute:02d}:58", "wf-parent-a") for minute in range(10)])

    assert len(run_check(root=tmp_path, now=NOW)) == 1
    assert run_check(root=tmp_path, now=NOW) == []
    assert len(alerts(tmp_path)) == 1


def test_real_shape_fresh_activity_does_not_raise(tmp_path):
    fixture(tmp_path)
    assert run_check(root=tmp_path, now=NOW) == []
    assert alerts(tmp_path) == []


def test_forward_future_authored_activity_falls_back_to_run_anchor_and_still_judges(tmp_path):
    # Rewrites test_small_future_activity_reports_clock_anomaly_end_to_end: that test pinned
    # "a future authored stamp aborts the whole round with a clock_anomaly", which let one
    # hand-typed number silence the sentinel. Under the cosigned v0.2 the authored candidate is
    # dropped and the tool anchor still carries the threshold + backlog judgement.
    future_local = (NOW + timedelta(minutes=5)).astimezone(
        timezone(timedelta(hours=9))
    ).strftime("%Y-%m-%d %H:%M:%S")
    fixture(tmp_path, activity_time=future_local)
    codex_runs(tmp_path, "2026-07-11 19:00:00")

    result = run_check(root=tmp_path, now=NOW)

    assert result.clock_anomaly is None
    assert result.skipped is None
    assert len(result) == 1 and result[0]["event"] == "raised"
    assert result.activity_anchor == {
        "time_utc": "2026-07-11T10:00:00+00:00",
        "source_ref": "wake-codex-runs/2026-07-11T19-00-00.jsonl (codex executed run)",
    }
    assert result[0]["silence"]["silence_hours"] == 16
    assert result[0]["backlog"]["items"] == ["job-a"]


def test_forward_future_authored_activity_without_run_anchor_measures_nothing(tmp_path):
    future_local = (NOW + timedelta(minutes=5)).astimezone(
        timezone(timedelta(hours=9))
    ).strftime("%Y-%m-%d %H:%M:%S")
    fixture(tmp_path, activity_time=future_local)

    result = run_check(root=tmp_path, now=NOW)

    assert result == []
    assert result.clock_anomaly is None
    assert result.activity_anchor is None
    assert alerts(tmp_path) == []


def test_forward_backfilled_authored_append_cannot_displace_run_anchor(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:55:00")  # backfilled nine hours
    codex_runs(tmp_path, "2026-07-12 10:55:00")

    result = run_check(root=tmp_path, now=NOW)

    assert result == []
    assert result.clock_anomaly is None
    assert result.activity_anchor == {
        "time_utc": "2026-07-12T01:55:00+00:00",
        "source_ref": "wake-codex-runs/2026-07-12T10-55-00.jsonl (codex executed run)",
    }
    assert alerts(tmp_path) == []


def test_forward_future_clock_authority_append_remains_a_visible_clock_anomaly(tmp_path):
    fixture(tmp_path)
    append(
        tmp_path / "peer-chat.jsonl",
        {
            "from": "codex",
            "time": "2026-07-12T13:30:00+09:00",
            "time_authority": "clock",
            "text": "trusted future append",
        },
    )

    result = run_check(root=tmp_path, now=NOW)

    assert result == []
    assert result.clock_anomaly == {
        "anchor_time_utc": "2026-07-12T04:30:00+00:00",
        "now_utc": "2026-07-12T02:00:00+00:00",
        "future_delta_hours": 2.5,
        "source_ref": "peer-chat.jsonl:2@2026-07-12T13:30:00+09:00 (codex activity)",
        "authority": "none",
    }
    assert alerts(tmp_path) == []


def test_forward_later_valid_append_displaces_earlier_future_timestamp_in_cli(
    tmp_path, monkeypatch, capsys
):
    fixture(tmp_path, activity_time="2026-07-12 20:30:00")
    append(
        tmp_path / "peer-chat.jsonl",
        {"from": "codex", "time": "2026-07-12 10:59:00", "text": "honest later append"},
    )

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(peer_health_wake, "datetime", FixedDatetime)
    assert main(["--root", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["check"] == "completed"
    # This fixture has no orphan streak; the sibling tests cover that independent signal.
    assert report["appended"] == []
    assert report["clock_anomaly"] is None
    assert report["activity_anchor"] == {
        "time_utc": "2026-07-12T01:59:00+00:00",
        "source_ref": "peer-chat.jsonl:2@2026-07-12 10:59:00 (codex activity)",
    }
    assert alerts(tmp_path) == []


def test_forward_last_past_append_raises_despite_earlier_future_timestamp(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 20:30:00")
    append(
        tmp_path / "peer-chat.jsonl",
        {"from": "codex", "time": "2026-07-12 01:00:00", "text": "past-coordinate append"},
    )

    result = run_check(root=tmp_path, now=NOW)

    assert result.clock_anomaly is None
    assert len(result) == 1 and result[0]["event"] == "raised"
    assert result.activity_anchor["source_ref"].startswith("peer-chat.jsonl:2@")


def test_forward_orphan_alert_is_independent_of_every_anchor_outcome(tmp_path):
    # Rewrites test_forward_future_anchor_preserves_independent_orphan_alert, which reached the
    # orphan branch only through the authored-stamp clock_anomaly that v0.2 removes. The
    # invariant under test is unchanged: orphan_frame never depends on the activity anchor.
    for index, extra in enumerate(
        (
            None,  # future authored codex stamp: candidate dropped, no anchor at all
            {
                "from": "codex",
                "time": "2026-07-12T13:30:00+09:00",
                "time_authority": "clock",
                "text": "trusted future append",
            },  # genuine host-clock anomaly: whole round returns early
        )
    ):
        root = tmp_path / str(index)
        fixture(root, activity_time="2026-07-12 20:30:00")
        if extra is not None:
            append(root / "peer-chat.jsonl", extra)
        write_cron(root, [cron_line(f"2026-07-16T18:{minute:02d}:58", "wf-parent-a") for minute in range(10)])

        result = run_check(root=root, now=NOW)

        assert (result.clock_anomaly is not None) is (extra is not None)
        assert [event["kind"] for event in result] == ["orphan_frame"]
        assert [event["kind"] for event in alerts(root)] == ["orphan_frame"]


def test_forward_future_clock_anchor_with_orphan_is_explicit_in_cli(tmp_path, monkeypatch, capsys):
    # Rewrites test_forward_future_anchor_with_orphan_is_explicit_in_cli: same CLI invariant
    # (both signals visible at once), now driven by a clock-authority stamp rather than an
    # authored one, because only a real host-clock anomaly still aborts the round.
    fixture(tmp_path)
    append(
        tmp_path / "peer-chat.jsonl",
        {
            "from": "codex",
            "time": "2026-07-12T13:30:00+09:00",
            "time_authority": "clock",
            "text": "trusted future append",
        },
    )
    write_cron(tmp_path, [cron_line(f"2026-07-16T18:{minute:02d}:58", "wf-parent-a") for minute in range(10)])

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(peer_health_wake, "datetime", FixedDatetime)
    assert main(["--root", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["check"] == "clock_anomaly"
    assert [event["kind"] for event in report["appended"]] == ["orphan_frame"]
    assert report["clock_anomaly"] is not None
    assert [event["kind"] for event in alerts(tmp_path)] == ["orphan_frame"]


def test_silent_pending_raises_once_and_is_idempotent(tmp_path):
    fixture(tmp_path, activity_time="2026-07-12 01:00:00")
    first = run_check(root=tmp_path, now=NOW)
    assert len(first) == 1 and first[0]["event"] == "raised"
    assert first[0]["raised_by"] == "claude" and first[0]["peer"] == "codex"
    assert first[0]["status"] == "suspected"
    assert first[0]["silence"]["source_ref"] and first[0]["backlog"]["source_ref"]
    assert run_check(root=tmp_path, now=NOW) == []
    assert len(alerts(tmp_path)) == 1


def test_failed_wake_files_do_not_make_six_hour_alert_unreachable(tmp_path):
    fixture(tmp_path, activity_time="2026-07-11 01:00:00")
    codex_runs(tmp_path, "2026-07-12 04:30:00")
    failed_stamps = [
        (NOW.astimezone(timezone(timedelta(hours=9))) - timedelta(minutes=9 * offset))
        .strftime("%Y-%m-%d %H:%M:%S")
        for offset in range(27)
    ]
    codex_runs(tmp_path, *failed_stamps, executed=False)

    result = run_check(root=tmp_path, now=NOW, threshold_hours=6)

    assert len(result) == 1 and result[0]["event"] == "raised"
    assert result.activity_anchor == {
        "time_utc": "2026-07-11T19:30:00+00:00",
        "source_ref": "wake-codex-runs/2026-07-12T04-30-00.jsonl (codex executed run)",
    }
    assert result[0]["silence"]["silence_hours"] == 6.5
    assert result[0]["backlog"]["items"] == ["job-a"]


def test_authentic_run_younger_than_threshold_does_not_raise(tmp_path):
    fixture(tmp_path, activity_time="2026-07-11 01:00:00")
    codex_runs(tmp_path, "2026-07-12 06:18:00", encoding="utf-16")
    codex_runs(tmp_path, "2026-07-12 10:55:00", executed=False)

    result = run_check(root=tmp_path, now=NOW, threshold_hours=6)

    assert result == []
    assert result.activity_anchor["time_utc"] == "2026-07-11T21:18:00+00:00"
    assert alerts(tmp_path) == []


def test_decode_codex_run_reads_utf16le_bom(tmp_path):
    path = tmp_path / "utf16le.jsonl"
    expected = '{"message":"微澜 utf16le"}\n'
    path.write_bytes(expected.encode("utf-16"))
    assert path.read_bytes().startswith(b"\xff\xfe")
    parse_errors = []

    assert peer_health_wake._decode_codex_run(path, parse_errors) == expected
    assert parse_errors == []


def test_decode_codex_run_reads_utf8_sig(tmp_path):
    path = tmp_path / "utf8-sig.jsonl"
    expected = '{"message":"微澜 utf8-sig"}\n'
    path.write_bytes(expected.encode("utf-8-sig"))
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    parse_errors = []

    assert peer_health_wake._decode_codex_run(path, parse_errors) == expected
    assert parse_errors == []


def test_decode_codex_run_reads_utf8_without_bom(tmp_path):
    path = tmp_path / "utf8.jsonl"
    expected = '{"message":"微澜 utf8"}\n'
    path.write_bytes(expected.encode("utf-8"))
    assert not path.read_bytes().startswith((b"\xff\xfe", b"\xef\xbb\xbf"))
    parse_errors = []

    assert peer_health_wake._decode_codex_run(path, parse_errors) == expected
    assert parse_errors == []


def test_decode_codex_run_invalid_bytes_return_none_once(tmp_path):
    path = tmp_path / "invalid.jsonl"
    path.write_bytes(b"\xffbroken")
    parse_errors = []

    assert peer_health_wake._decode_codex_run(path, parse_errors) is None
    assert len(parse_errors) == 1
    assert parse_errors[0]["reason_code"] == "decode_failure"


def test_unreadable_newer_run_is_visible_and_does_not_mask_authentic_anchor(tmp_path):
    fixture(tmp_path, activity_time="2026-07-11 01:00:00")
    codex_runs(tmp_path, "2026-07-12 04:30:00", encoding="utf-8")
    runs = tmp_path / "wake-codex-runs"
    (runs / "2026-07-12T10-55-00.jsonl").write_bytes(b"\xffbroken")

    result = run_check(root=tmp_path, now=NOW, threshold_hours=6)

    assert len(result) == 1 and result[0]["event"] == "raised"
    assert result.activity_anchor["source_ref"].endswith(
        "2026-07-12T04-30-00.jsonl (codex executed run)"
    )
    assert len(result.parse_errors) == 1
    assert result.parse_errors[0]["source"].endswith("2026-07-12T10-55-00.jsonl")
    assert result.parse_errors[0]["reason_code"] == "decode_failure"


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


def test_malformed_or_missing_non_anchor_time_is_ignored_after_valid_append(tmp_path):
    bad_rows = (
        {"from": "codex", "time": "not-a-time", "text": "older malformed coordinate"},
        {"from": "codex", "text": "older missing coordinate"},
    )
    for index, bad_row in enumerate(bad_rows):
        root = tmp_path / str(index)
        fixture(root, activity_time="2026-07-12 01:00:00")
        append(root / "peer-chat.jsonl", bad_row)
        append(
            root / "peer-chat.jsonl",
            {"from": "codex", "time": "2026-07-12 10:59:00", "text": "valid source-local anchor"},
        )

        result = run_check(root=root, now=NOW)

        assert result == []
        assert result.skipped is None
        assert result.clock_anomaly is None
        assert result.activity_anchor == {
            "time_utc": "2026-07-12T01:59:00+00:00",
            "source_ref": "peer-chat.jsonl:3@2026-07-12 10:59:00 (codex activity)",
        }
        assert alerts(root) == []


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
    assert result.parse_errors[0]["source"] == (tmp_path / "peer-chat.jsonl").as_posix()
    assert result.parse_errors[0]["line"] == 2
    assert result.parse_errors[0]["reason_code"] == "invalid_json"
    assert result.known_corrected == []


def test_exact_time_and_legacy_no_lf_hash_routes_to_known_corrected(tmp_path):
    fixture(tmp_path)
    raw = malformed_chat(tmp_path)
    correction(tmp_path, corrects="2026-07-13 18:22:40", before_hash=hashlib.sha256(raw.encode()).hexdigest())

    result = run_check(root=tmp_path, now=NOW)

    assert result.parse_errors == []
    assert len(result.known_corrected) == 1
    assert result.known_corrected[0]["line"] == 2
    assert result.known_corrected[0]["corrects"] == "2026-07-13 18:22:40"
    assert result.known_corrected[0]["matched_convention"] == (
        "remove exactly one trailing LF byte; stored CR preserved"
    )


def test_current_record_minus_lf_v1_covers_all_physical_record_endings(tmp_path):
    cases = (
        (b"\n", b""),
        (b"\r\n", b"\r"),
        (b"", b""),
        (b"\r", b"\r"),
    )
    for index, (terminator, retained_suffix) in enumerate(cases):
        root = tmp_path / str(index)
        fixture(root)
        record = malformed_chat_bytes(root, terminator=terminator)
        expected_preimage = record[: -len(terminator)] + retained_suffix if terminator else record
        correction(
            root,
            corrects="2026-07-13 18:22:40",
            before_hash=hashlib.sha256(expected_preimage).hexdigest(),
        )

        result = run_check(root=root, now=NOW)

        assert result.parse_errors == []
        assert len(result.known_corrected) == 1
        assert result.known_corrected[0]["matched_hash"] == hashlib.sha256(
            peer_health_wake._current_record_minus_lf_v1(record)
        ).hexdigest()


def test_crlf_fixture_matches_compile_view_and_peer_health_v1(tmp_path):
    fixture(tmp_path)
    record = malformed_chat_bytes(tmp_path, terminator=b"\r\n")
    assert record.endswith(b"\r\n")
    assert compile_view.line_without_lf(record).endswith(b"\r")
    assert (
        peer_health_wake._current_record_minus_lf_v1(record)
        == compile_view.line_without_lf(record)
    )
    before_hash = hashlib.sha256(compile_view.line_without_lf(record)).hexdigest()
    correction(
        tmp_path,
        corrects="2026-07-13 18:22:40",
        before_hash=before_hash,
    )

    result = run_check(root=tmp_path, now=NOW)

    assert result.parse_errors == []
    assert len(result.known_corrected) == 1
    assert result.known_corrected[0]["matched_hash"] == before_hash


def test_named_commit_blob_line_hash_is_independently_recomputable(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "WeiLan Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "weilan-test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repo, check=True)
    ledger = repo / "ledger.jsonl"
    ledger.write_bytes(b'{"id":1}\r\n{"id":2}\n')
    subprocess.run(["git", "add", "ledger.jsonl"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=repo, check=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip()
    blob_oid = subprocess.check_output(
        ["git", "rev-parse", f"{commit}:ledger.jsonl"], cwd=repo
    ).decode().strip()
    blob = subprocess.check_output(["git", "cat-file", "blob", blob_oid], cwd=repo)
    first_record = blob[: blob.index(b"\n") + 1]

    assert peer_health_wake._current_record_minus_lf_v1(first_record) == b'{"id":1}\r'
    assert hashlib.sha256(
        peer_health_wake._current_record_minus_lf_v1(first_record)
    ).hexdigest() == hashlib.sha256(b'{"id":1}\r').hexdigest()

    charter = (Path(__file__).resolve().parents[2] / "CHARTER.md").read_text(encoding="utf-8")
    assert "`current-record-minus-LF-v1`" in charter
    assert "具名 `<commit>:<账本路径>` 的 Git blob" in charter
    assert "三域并存且不得以\"统一口径\"互相偷换" in charter


def test_same_time_with_wrong_hash_remains_parse_error(tmp_path):
    fixture(tmp_path)
    malformed_chat(tmp_path)
    correction(tmp_path, corrects="2026-07-13 18:22:40", before_hash="0" * 64)

    result = run_check(root=tmp_path, now=NOW)

    assert len(result.parse_errors) == 1
    assert result.known_corrected == []


def test_known_correction_does_not_hide_a_second_bad_line(tmp_path):
    fixture(tmp_path)
    raw = malformed_chat(tmp_path)
    malformed_chat(tmp_path, time="2026-07-13 18:22:41", suffix="-new")
    correction(tmp_path, corrects="2026-07-13 18:22:40", before_hash=hashlib.sha256(raw.encode()).hexdigest())

    result = run_check(root=tmp_path, now=NOW)

    assert len(result.known_corrected) == 1
    assert len(result.parse_errors) == 1
    assert result.parse_errors[0]["line"] == 3


def test_malformed_correction_remains_visible_and_cannot_cover_bad_chat(tmp_path):
    fixture(tmp_path)
    malformed_chat(tmp_path)
    (tmp_path / "peer-chat.corrections.jsonl").write_text('{"corrects":"broken"\n', encoding="utf-8")

    result = run_check(root=tmp_path, now=NOW)

    assert result.known_corrected == []
    assert len(result.parse_errors) == 2
    assert {Path(error["source"]).name for error in result.parse_errors} == {
        "peer-chat.corrections.jsonl",
        "peer-chat.jsonl",
    }


def test_sentinel_equivalent_hash_routes_in_reverse_without_changing_anchor(tmp_path):
    reverse_fixture(tmp_path)
    raw = malformed_chat(tmp_path)
    append(
        tmp_path / "peer-chat.corrections.jsonl",
        {
            "corrects": "2026-07-13 18:22:40",
            "sentinel_equiv_hash": hashlib.sha256((raw + "\n").encode()).hexdigest(),
        },
    )

    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))

    assert result.parse_errors == []
    assert len(result.known_corrected) == 1
    assert result.activity_anchor["source_ref"].startswith("wake-agent-runs/")
    assert len(result) == 1


def test_explicit_offset_receipt_forms_reverse_activity_anchor(tmp_path):
    reverse_fixture(tmp_path)
    append(
        tmp_path / "concurrent-receipts.jsonl",
        {"wake_id": "claude-wake-offset", "time": "2026-07-16 16:30:00 +0900"},
    )

    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))

    assert result.skipped is None
    assert result.activity_anchor == {
        "time_utc": "2026-07-16T07:30:00+00:00",
        "source_ref": "concurrent-receipts.jsonl:2@2026-07-16 16:30:00 +0900 (claude wake)",
    }


def test_malformed_offset_skips_reverse_check_without_losing_known_correction(tmp_path):
    reverse_fixture(tmp_path)
    raw = malformed_chat(tmp_path)
    correction(tmp_path, corrects="2026-07-13 18:22:40", before_hash=hashlib.sha256(raw.encode()).hexdigest())
    append(
        tmp_path / "concurrent-receipts.jsonl",
        {"wake_id": "claude-wake-bad-offset", "time": "2026-07-16 16:30:00 +09:XX"},
    )

    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))

    assert result.activity_anchor is None
    assert result.skipped is not None
    assert "ValueError" in result.skipped["reason"]
    assert "+09:XX" in result.skipped["reason"]
    assert result.parse_errors == []
    assert len(result.known_corrected) == 1
    assert result.known_corrected[0]["corrects"] == "2026-07-13 18:22:40"


def test_whole_file_read_failure_is_visible_in_cli(tmp_path, monkeypatch, capsys):
    fixture(tmp_path)
    original = Path.read_bytes

    def unreadable(path, *args, **kwargs):
        if path.name == "peer-chat.jsonl":
            raise PermissionError("test unreadable file")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
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


def test_reverse_silence_with_three_codex_heartbeats_raises_complete_alert(tmp_path):
    reverse_fixture(tmp_path)
    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))
    assert len(result) == 1
    alert = result[0]
    assert alert["direction"] == "codex_to_claude"
    assert alert["peer"] == "claude" and alert["raised_by"] == "codex"
    assert alert["silence"]["threshold_hours"] == 4
    assert alert["silence"]["source_ref"].startswith("wake-agent-runs/")
    assert alert["observer_heartbeats"]["count"] == 3
    assert alert["authority"] == "none"


def test_reverse_fresh_claude_does_not_alert(tmp_path):
    reverse_fixture(tmp_path, claude_time="2026-07-16 20:00:00")
    assert run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc)) == []
    assert not (tmp_path / "peer-health-alerts.jsonl").exists()


def test_reverse_latest_future_authored_append_falls_back_to_run_anchor(tmp_path):
    reverse_fixture(tmp_path)
    append(
        tmp_path / "peer-chat.jsonl",
        {"from": "claude", "time": "2026-07-16 23:30:00", "text": "latest future append"},
    )

    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))

    assert result.clock_anomaly is None
    assert len(result) == 1 and result[0]["event"] == "raised"
    assert result.activity_anchor == {
        "time_utc": "2026-07-16T07:00:00+00:00",
        "source_ref": "wake-agent-runs/2026-07-16T16-00-00.json (claude wake run)",
    }


def test_reverse_future_clock_append_remains_a_visible_clock_anomaly(tmp_path):
    reverse_fixture(tmp_path)
    append(
        tmp_path / "peer-chat.jsonl",
        {
            "from": "claude",
            "time": "2026-07-16T23:30:00+09:00",
            "time_authority": "clock",
            "text": "trusted future append",
        },
    )

    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))

    assert result == []
    assert result.clock_anomaly == {
        "anchor_time_utc": "2026-07-16T14:30:00+00:00",
        "now_utc": "2026-07-16T12:00:00+00:00",
        "future_delta_hours": 2.5,
        "source_ref": "peer-chat.jsonl:2@2026-07-16T23:30:00+09:00 (claude activity)",
        "authority": "none",
    }
    assert not (tmp_path / "peer-health-alerts.jsonl").exists()


def test_reverse_backfilled_authored_append_cannot_displace_run_anchor(tmp_path):
    reverse_fixture(tmp_path)
    append(
        tmp_path / "peer-chat.jsonl",
        {"from": "claude", "time": "2026-07-16 07:00:00", "text": "backfilled by nine hours"},
    )

    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))

    assert result.clock_anomaly is None
    assert len(result) == 1 and result[0]["event"] == "raised"
    assert result.activity_anchor["source_ref"].startswith("wake-agent-runs/")


def test_reverse_later_valid_append_displaces_earlier_future_timestamp(tmp_path):
    reverse_fixture(tmp_path, claude_time="2026-07-16 20:00:00")
    append(
        tmp_path / "peer-chat.jsonl",
        {"from": "claude", "time": "2026-07-16 23:30:00", "text": "future-coordinate append"},
    )
    append(
        tmp_path / "peer-chat.jsonl",
        {"from": "claude", "time": "2026-07-16 20:30:00", "text": "honest later append"},
    )

    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))

    assert result == []
    assert result.clock_anomaly is None
    assert result.activity_anchor == {
        "time_utc": "2026-07-16T11:30:00+00:00",
        "source_ref": "peer-chat.jsonl:3@2026-07-16 20:30:00 (claude activity)",
    }
    assert not (tmp_path / "peer-health-alerts.jsonl").exists()


def test_reverse_last_past_append_raises_despite_earlier_future_timestamp(tmp_path):
    reverse_fixture(tmp_path)
    append(
        tmp_path / "peer-chat.jsonl",
        {"from": "claude", "time": "2026-07-16 23:30:00", "text": "future-coordinate append"},
    )
    append(
        tmp_path / "peer-chat.jsonl",
        {"from": "claude", "time": "2026-07-16 16:30:00", "text": "past-coordinate append"},
    )

    result = run_reverse_check(root=tmp_path, now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))

    assert result.clock_anomaly is None
    assert len(result) == 1 and result[0]["event"] == "raised"
    assert result.activity_anchor["source_ref"].startswith("peer-chat.jsonl:3@")


def test_reverse_unresolved_same_anchor_is_reported_once(tmp_path):
    reverse_fixture(tmp_path)
    now = datetime(2026, 7, 16, 12, tzinfo=timezone.utc)
    assert len(run_reverse_check(root=tmp_path, now=now)) == 1
    assert run_reverse_check(root=tmp_path, now=now) == []
    assert len(alerts(tmp_path)) == 1
