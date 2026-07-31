from __future__ import annotations

import json
from pathlib import Path

import pytest

import wake_brief


STAMP = "2026-07-10T09:30:00+00:00"
SEAM_BAD_JSON = b'{"broken":}\n'
SEAM_NON_OBJECT = b'["not", "an", "object"]\n'
SEAM_VALID_ROW = b'{"tail":"ok"}\n'
SEAM_TAIL = SEAM_BAD_JSON + SEAM_NON_OBJECT + SEAM_VALID_ROW


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def fixture_recall() -> dict:
    return {
        "activation": {"state": "ACTIVE", "continuation_allowed": True},
        "control": {"state": "active", "sources": ["control:event-1"]},
        "freshness": {"fresh": True},
    }


def fixture_prospective() -> dict:
    return {
        "sources": ["prospective:ledger-1"],
        "goals": [
            {
                "goal_ref": "goal:due",
                "state": "ACTIVE",
                "not_before": "2026-07-10T09:00:00+00:00",
                "causal_events": [
                    {"event_id": "ready-1", "state": "READY"},
                    {"event_id": "done-1", "state": "OBSERVED"},
                ],
            },
            {
                "goal_ref": "goal:future",
                "state": "ACTIVE",
                "not_before": "2026-07-10T10:00:00+00:00",
                "causal_events": [{"event_id": "ready-2", "state": "READY"}],
            },
            {"goal_ref": "goal:closed", "state": "CLOSED", "causal_events": [{"event_id": "ready-3", "state": "READY"}]},
        ],
    }


def seed_root(root: Path) -> None:
    write_jsonl(
        root / "owner-inbox.jsonl",
        [
            {"id": "old-owner", "text": "already handled"},
            {"id": "new-owner", "text": "full owner text"},
        ],
    )
    write_jsonl(root / "owner-inbox-processed.jsonl", [{"id": "old-owner"}])
    write_jsonl(root / "codex-inbox-replies.jsonl", [{"reply_to": "a", "text": "reply A"}, {"reply_to": "b", "text": "reply B"}])
    write_jsonl(root / "peer-chat.jsonl", [{"from": "claude", "text": "chat A"}, {"from": "owner", "text": "chat B"}])


def build(root: Path, **kwargs):
    return wake_brief.build_brief(
        root=root,
        workspace="D:\\WeilanSkillEvolution",
        scope="skill-evolution",
        updated_at_utc=STAMP,
        now_utc=STAMP,
        recall_fixture=fixture_recall(),
        prospective_fixture=fixture_prospective(),
        **kwargs,
    )


def assert_tail_matches_full_scan(path: Path, prefix: bytes, tail: list[dict]) -> None:
    full_scan = wake_brief.read_jsonl(path)
    expected = full_scan[prefix.count(b"\n") :]

    assert tail == expected
    assert [row["reason_code"] for row in tail[:2]] == ["invalid_json", "not_object"]
    assert [row["line"] for row in tail[:2]] == [prefix.count(b"\n") + 1, prefix.count(b"\n") + 2]
    assert [row["byte_offset"] for row in tail[:2]] == [len(prefix), len(prefix) + len(SEAM_BAD_JSON)]
    assert tail[2] == {"tail": "ok"}


def test_lossless_aggregation_keeps_delta_text_and_sources(tmp_path: Path) -> None:
    seed_root(tmp_path)

    brief = build(tmp_path)

    assert brief["authority"]["activation"]["state"] == "ACTIVE"
    assert [row["id"] for row in brief["owner_inbox_delta"]] == ["new-owner"]
    assert brief["owner_inbox_delta"][0]["text"] == "full owner text"
    assert [row["reply_to"] for row in brief["codex_replies_unreviewed"]] == ["a", "b"]
    assert [row["text"] for row in brief["peer_chat_new"]] == ["chat A", "chat B"]
    assert [goal["goal_ref"] for goal in brief["prospective_due"]] == ["goal:due"]
    assert brief["prospective_due"][0]["causal_events"] == [{"event_id": "ready-1", "state": "READY"}]
    refs = {source["ref"] for source in brief["sources"]}
    assert (tmp_path / "owner-inbox.jsonl").as_posix() in refs
    assert (tmp_path / "codex-inbox-replies.jsonl").as_posix() in refs
    assert "control:event-1" in refs
    assert "prospective:ledger-1" in refs


def test_one_call_reproduces_hand_computed_steps_2_to_8_delta_sets(tmp_path: Path) -> None:
    seed_root(tmp_path)

    brief = build(tmp_path)

    expected = {
        "owner_inbox_delta": ["new-owner"],
        "prospective_due": ["goal:due"],
        "codex_replies_unreviewed": ["a", "b"],
        "peer_chat_new": ["chat A", "chat B"],
    }
    observed = {
        "owner_inbox_delta": [row["id"] for row in brief["owner_inbox_delta"]],
        "prospective_due": [row["goal_ref"] for row in brief["prospective_due"]],
        "codex_replies_unreviewed": [row["reply_to"] for row in brief["codex_replies_unreviewed"]],
        "peer_chat_new": [row["text"] for row in brief["peer_chat_new"]],
    }
    assert observed == expected
    assert set(["authority", "owner_inbox_delta", "prospective_due", "codex_replies_unreviewed", "peer_chat_new", "sources", "cursor_status"]) <= set(brief)


def test_incremental_tail_uses_valid_cursor(tmp_path: Path) -> None:
    seed_root(tmp_path)
    wake_brief.write_cursor(tmp_path, tmp_path / "wake-cursor.json", "skill-evolution", STAMP)
    with (tmp_path / "peer-chat.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"from": "codex", "text": "new chat"}) + "\n")
    with (tmp_path / "codex-inbox-replies.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"reply_to": "c", "text": "reply C"}) + "\n")

    brief = build(tmp_path)

    assert brief["cursor_status"] == {"status": "incremental"}
    assert [row["text"] for row in brief["peer_chat_new"]] == ["new chat"]
    assert [row["reply_to"] for row in brief["codex_replies_unreviewed"]] == ["c"]


def test_tail_jsonl_real_cursor_uses_absolute_diagnostic_coordinates(tmp_path: Path) -> None:
    chat_path = tmp_path / "peer-chat.jsonl"
    cursor_path = tmp_path / "wake-cursor.json"
    prefix = b'{"seed":1}\n{"seed":2}\n'
    chat_path.write_bytes(prefix)
    wake_brief.write_cursor(tmp_path, cursor_path, "skill-evolution", STAMP)
    with chat_path.open("ab") as handle:
        handle.write(SEAM_TAIL)

    cursor, load_reason = wake_brief.load_cursor(cursor_path)
    assert load_reason is None
    assert cursor is not None
    assert cursor["files"]["peer-chat.jsonl"]["line_count"] == prefix.count(b"\n")
    mode, reason, details = wake_brief.validate_cursor(tmp_path, cursor, load_reason)
    assert (mode, reason, details) == ("incremental", None, None)

    tail = wake_brief._tail_jsonl(tmp_path, "peer-chat.jsonl", mode, cursor)

    assert_tail_matches_full_scan(chat_path, prefix, tail)


def test_tail_jsonl_legacy_splitlines_cursor_rewrites_then_resumes_incrementally(tmp_path: Path) -> None:
    chat_path = tmp_path / "peer-chat.jsonl"
    cursor_path = tmp_path / "wake-cursor.json"
    legacy_prefix = b'{"seed":1}\r{"seed":2}\n'
    assert len(legacy_prefix.splitlines()) != legacy_prefix.count(b"\n")
    chat_path.write_bytes(legacy_prefix)
    legacy_cursor = wake_brief.write_cursor(tmp_path, cursor_path, "skill-evolution", STAMP)
    legacy_cursor["files"]["peer-chat.jsonl"]["line_count"] = len(legacy_prefix.splitlines())
    cursor_path.write_text(json.dumps(legacy_cursor), encoding="utf-8")
    with chat_path.open("ab") as handle:
        handle.write(SEAM_TAIL)

    cursor, load_reason = wake_brief.load_cursor(cursor_path)
    assert load_reason is None
    assert cursor is not None
    mode, reason, details = wake_brief.validate_cursor(tmp_path, cursor, load_reason)
    assert mode == "full_rescan"
    assert reason == "line_count_mismatch"
    assert details is not None
    assert details["tracked_file"] == "peer-chat.jsonl"
    assert wake_brief._tail_jsonl(tmp_path, "peer-chat.jsonl", mode, cursor) == wake_brief.read_jsonl(chat_path)

    wake_brief.write_cursor(tmp_path, cursor_path, "skill-evolution", STAMP, preserve_previous=True)
    rewritten, load_reason = wake_brief.load_cursor(cursor_path)
    assert load_reason is None
    assert rewritten is not None
    observed_prefix = chat_path.read_bytes()
    assert rewritten["files"]["peer-chat.jsonl"]["line_count"] == observed_prefix.count(b"\n")
    assert rewritten["files"]["peer-chat.jsonl"]["line_count"] != len(observed_prefix.splitlines())
    assert wake_brief.validate_cursor(tmp_path, rewritten, load_reason) == ("incremental", None, None)

    with chat_path.open("ab") as handle:
        handle.write(SEAM_TAIL)
    mode, reason, details = wake_brief.validate_cursor(tmp_path, rewritten, load_reason)
    assert (mode, reason, details) == ("incremental", None, None)
    tail = wake_brief._tail_jsonl(tmp_path, "peer-chat.jsonl", mode, rewritten)

    assert_tail_matches_full_scan(chat_path, observed_prefix, tail)


def test_eol_only_drift_keeps_new_tail_and_is_observable(tmp_path: Path) -> None:
    seed_root(tmp_path)
    cursor_path = tmp_path / "wake-cursor.json"
    wake_brief.write_cursor(tmp_path, cursor_path, "skill-evolution", STAMP)

    chat_path = tmp_path / "peer-chat.jsonl"
    original_lf = chat_path.read_bytes().replace(b"\r\n", b"\n")
    chat_path.write_bytes(original_lf)
    wake_brief.write_cursor(tmp_path, cursor_path, "skill-evolution", STAMP)
    chat_path.write_bytes(original_lf.replace(b"\n", b"\r\n") + b'{"from":"codex","text":"new tail"}\r\n')

    brief = build(tmp_path)

    assert brief["cursor_status"]["status"] == "representation_drift"
    assert brief["cursor_status"]["reason"] == "eol_only_prefix_change"
    assert [row["text"] for row in brief["peer_chat_new"]] == ["new tail"]


def test_same_length_content_rewrite_still_forces_full_rescan(tmp_path: Path) -> None:
    seed_root(tmp_path)
    wake_brief.write_cursor(tmp_path, tmp_path / "wake-cursor.json", "skill-evolution", STAMP)
    chat_path = tmp_path / "peer-chat.jsonl"
    original = chat_path.read_bytes()
    rewritten = original.replace(b"chat A", b"chat X")
    assert len(rewritten) == len(original)
    chat_path.write_bytes(rewritten)

    brief = build(tmp_path)

    assert brief["cursor_status"]["status"] == "full_rescan"
    assert brief["cursor_status"]["reason"] == "prefix_mismatch"


def test_normal_append_remains_incremental_with_dual_anchor_cursor(tmp_path: Path) -> None:
    seed_root(tmp_path)
    wake_brief.write_cursor(tmp_path, tmp_path / "wake-cursor.json", "skill-evolution", STAMP)
    with (tmp_path / "peer-chat.jsonl").open("ab") as handle:
        handle.write(b'{"from":"codex","text":"ordinary tail"}\n')

    brief = build(tmp_path)

    assert brief["cursor_status"] == {"status": "incremental"}
    assert [row["text"] for row in brief["peer_chat_new"]] == ["ordinary tail"]


def test_crlf_to_lf_shrink_can_still_resume_by_line_count(tmp_path: Path) -> None:
    seed_root(tmp_path)
    chat_path = tmp_path / "peer-chat.jsonl"
    original_lf = chat_path.read_bytes().replace(b"\r\n", b"\n")
    chat_path.write_bytes(original_lf.replace(b"\n", b"\r\n"))
    wake_brief.write_cursor(tmp_path, tmp_path / "wake-cursor.json", "skill-evolution", STAMP)

    chat_path.write_bytes(chat_path.read_bytes().replace(b"\r\n", b"\n") + b'{"from":"codex","text":"tail after shrink"}\n')
    brief = build(tmp_path)

    assert brief["cursor_status"]["status"] == "representation_drift"
    assert [row["text"] for row in brief["peer_chat_new"]] == ["tail after shrink"]


def test_missing_cursor_falls_back_to_full_rescan(tmp_path: Path) -> None:
    seed_root(tmp_path)

    brief = build(tmp_path)

    assert brief["cursor_status"] == {"status": "full_rescan", "reason": "no_cursor"}
    assert [row["text"] for row in brief["peer_chat_new"]] == ["chat A", "chat B"]
    assert [row["reply_to"] for row in brief["codex_replies_unreviewed"]] == ["a", "b"]


@pytest.mark.parametrize("reason", ["file_shrank", "offset_oob", "prefix_mismatch", "line_count_mismatch"])
def test_cursor_integrity_failure_falls_back_without_losing_tail(tmp_path: Path, reason: str) -> None:
    seed_root(tmp_path)
    cursor_path = tmp_path / "wake-cursor.json"
    cursor = wake_brief.write_cursor(tmp_path, cursor_path, "skill-evolution", STAMP)

    if reason == "file_shrank":
        (tmp_path / "peer-chat.jsonl").write_text("", encoding="utf-8")
    elif reason == "offset_oob":
        cursor["files"]["peer-chat.jsonl"]["byte_offset"] = 10_000
        cursor_path.write_text(json.dumps(cursor), encoding="utf-8")
    elif reason == "prefix_mismatch":
        data = (tmp_path / "peer-chat.jsonl").read_text(encoding="utf-8")
        (tmp_path / "peer-chat.jsonl").write_text(data.replace("chat A", "chat X"), encoding="utf-8")
    elif reason == "line_count_mismatch":
        cursor["files"]["peer-chat.jsonl"]["line_count"] += 1
        cursor_path.write_text(json.dumps(cursor), encoding="utf-8")

    prior_bytes = cursor_path.read_bytes()
    brief = build(tmp_path)

    assert brief["cursor_status"]["status"] == "full_rescan"
    assert brief["cursor_status"]["reason"] == reason
    details = brief["cursor_status"]["details"]
    assert details["tracked_file"] == "peer-chat.jsonl"
    assert set(details) == {"tracked_file", "stored", "actual"}
    assert set(details["stored"]) == {"file_size", "byte_offset", "line_count", "prefix_hash"}
    assert set(details["actual"]) == {"file_size", "byte_offset", "line_count", "prefix_hash"}
    assert (tmp_path / "wake-cursor.prev.json").read_bytes() == prior_bytes
    if reason == "file_shrank":
        assert brief["peer_chat_new"] == []
    else:
        assert brief["peer_chat_new"]
    assert [row["reply_to"] for row in brief["codex_replies_unreviewed"]] == ["a", "b"]


def test_incremental_does_not_create_or_rewrite_previous_cursor(tmp_path: Path) -> None:
    seed_root(tmp_path)
    cursor_path = tmp_path / "wake-cursor.json"
    wake_brief.write_cursor(tmp_path, cursor_path, "skill-evolution", STAMP)
    prev_path = tmp_path / "wake-cursor.prev.json"
    sentinel = b"previous mismatch evidence\n"
    prev_path.write_bytes(sentinel)

    brief = build(tmp_path)

    assert brief["cursor_status"] == {"status": "incremental"}
    assert prev_path.read_bytes() == sentinel


def test_missing_required_sources_surfaces_missing_sources(tmp_path: Path) -> None:
    # Empty root (simulates a deployed scripts dir holding only the script):
    # the live inbox/chat files are absent.  The brief must NOT present as a
    # healthy incremental/full_rescan empty result -- it must flag the false-zero.
    brief = build(tmp_path)

    assert brief["cursor_status"]["status"] == "missing_sources"
    assert set(brief["cursor_status"]["missing_sources"]) == {"peer-chat.jsonl", "codex-inbox-replies.jsonl"}
    assert brief["cursor_status"]["prior_status"] == {"status": "full_rescan", "reason": "no_cursor"}
    assert brief["peer_chat_new"] == []
    assert brief["owner_inbox_delta"] == []


def test_owner_inbox_absence_alone_is_not_missing_sources(tmp_path: Path) -> None:
    # peer-chat + codex-inbox-replies present; owner-inbox legitimately absent
    # (wake prompt treats its absence as normal).  Guard must not false-positive.
    write_jsonl(tmp_path / "codex-inbox-replies.jsonl", [{"reply_to": "a", "text": "reply A"}])
    write_jsonl(tmp_path / "peer-chat.jsonl", [{"from": "claude", "text": "chat A"}])

    brief = build(tmp_path)

    assert brief["cursor_status"]["status"] != "missing_sources"
    assert brief["owner_inbox_delta"] == []


def test_main_derives_root_from_workspace_when_root_absent(monkeypatch, tmp_path: Path) -> None:
    captured: dict = {}

    def fake_build_brief(*, root, workspace, scope, updated_at_utc, commit_cursor):
        captured["root"] = root
        captured["commit_cursor"] = commit_cursor
        return {"ok": True}

    monkeypatch.setattr(wake_brief, "build_brief", fake_build_brief)
    rc = wake_brief.main(["--workspace", str(tmp_path), "--scope", "skill-evolution", "--updated-at-utc", STAMP])

    assert rc == 0
    assert captured["root"] == tmp_path / "proposals" / "bounded-scheduler-v0.1" / "impl"
    # The default command must keep consuming the delta.  --peek is opt-in only.
    assert captured["commit_cursor"] is True


def test_main_uses_explicit_root_when_passed(monkeypatch, tmp_path: Path) -> None:
    captured: dict = {}

    def fake_build_brief(*, root, workspace, scope, updated_at_utc, commit_cursor):
        captured["root"] = root
        captured["commit_cursor"] = commit_cursor
        return {"ok": True}

    monkeypatch.setattr(wake_brief, "build_brief", fake_build_brief)
    explicit = tmp_path / "elsewhere" / "impl"
    argv = ["--workspace", str(tmp_path), "--scope", "s", "--root", str(explicit), "--updated-at-utc", STAMP]
    rc = wake_brief.main(argv)

    assert rc == 0
    assert captured["root"] == explicit
    assert captured["commit_cursor"] is True

    assert wake_brief.main(argv + ["--peek"]) == 0
    assert captured["commit_cursor"] is False
    assert wake_brief.main(argv + ["--no-commit-cursor"]) == 0
    assert captured["commit_cursor"] is False


def test_cursor_advances_and_second_call_is_empty_incremental(tmp_path: Path) -> None:
    seed_root(tmp_path)

    first = build(tmp_path)
    second = build(tmp_path)

    assert first["cursor_status"] == {"status": "full_rescan", "reason": "no_cursor"}
    assert second["cursor_status"] == {"status": "incremental"}
    assert second["peer_chat_new"] == []
    assert second["codex_replies_unreviewed"] == []
    cursor, reason = wake_brief.load_cursor(tmp_path / "wake-cursor.json")
    assert reason is None
    assert wake_brief.validate_cursor(tmp_path, cursor, None) == ("incremental", None, None)


def cursor_source(brief: dict) -> dict:
    return next(source for source in brief["sources"] if source.get("kind") == "cursor")


def test_cursor_source_reports_the_stamp_it_read_not_the_one_it_wrote(tmp_path: Path) -> None:
    seed_root(tmp_path)

    first = build(tmp_path)
    assert cursor_source(first)["cursor_before"] == {
        "file_exists": False,
        "loaded": False,
        "updated_at_utc": None,
        "load_reason": "no_cursor",
    }
    assert cursor_source(first)["cursor_commit"] == {"performed": True, "updated_at_utc": STAMP}

    later = "2026-07-11T09:30:00+00:00"
    second = wake_brief.build_brief(
        root=tmp_path,
        workspace="D:\\WeilanSkillEvolution",
        scope="skill-evolution",
        updated_at_utc=later,
        now_utc=later,
        recall_fixture=fixture_recall(),
        prospective_fixture=fixture_prospective(),
    )
    # The load-bearing field: what this call READ.  Printing only what it wrote
    # would show a fresh "just now" for a quiet wake and for an accidental
    # re-run alike -- the ambiguity these fields exist to remove.
    assert cursor_source(second)["cursor_before"] == {
        "file_exists": True,
        "loaded": True,
        "updated_at_utc": STAMP,
    }
    assert cursor_source(second)["cursor_commit"] == {"performed": True, "updated_at_utc": later}
    # No verdict is manufactured: without a stable wake-id contract the brief
    # cannot honestly decide whether that earlier commit belonged to this wake.
    assert "consumed_this_wake" not in json.dumps(cursor_source(second))


def test_peek_does_not_commit_and_keeps_the_delta_visible(tmp_path: Path) -> None:
    seed_root(tmp_path)

    first = build(tmp_path, commit_cursor=False)
    assert not (tmp_path / "wake-cursor.json").exists()
    assert cursor_source(first)["cursor_commit"] == {"performed": False, "updated_at_utc": None}
    assert len(first["peer_chat_new"]) == 2

    second = build(tmp_path, commit_cursor=False)
    assert len(second["peer_chat_new"]) == 2


def test_cursor_observability_does_not_perturb_the_site_fingerprint(tmp_path: Path) -> None:
    """Why these fields sit on the source entry and not inside cursor_status.

    site_fingerprint hashes cursor_status whole but takes only `ref` from each
    source.  A per-call timestamp inside cursor_status would change the
    fingerprint on every wake and destroy its same-situation signal.
    """
    seed_root(tmp_path)
    build(tmp_path)
    brief = build(tmp_path)

    baseline = brief["site_fingerprint"]["hash"]
    assert baseline == wake_brief.site_fingerprint_for(brief)["hash"]
    assert cursor_source(brief)["cursor_before"]["updated_at_utc"] == STAMP

    # Move both new timestamps as far as they can go; the fingerprint must not
    # notice.  Everything else about the site is untouched.
    cursor_source(brief)["cursor_before"]["updated_at_utc"] = "2099-01-01T00:00:00+00:00"
    cursor_source(brief)["cursor_commit"]["updated_at_utc"] = "2099-01-01T00:00:00+00:00"
    assert wake_brief.site_fingerprint_for(brief)["hash"] == baseline
    assert "updated_at_utc" not in json.dumps(brief["cursor_status"])
