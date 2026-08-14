"""Comparability boundary for site_fingerprint A/B tests.

Reading a brief is not a read-only observation: build_brief commits the
incremental cursor, so the *next* run legitimately sees an empty delta.  Two
adjacent live runs therefore cannot be used as an A/B pair — a fingerprint
difference between them is the cursor advancing, NOT a regression.  Clock-drift
immunity may only be asserted after the cursor has gone quiet (warm-up run
first, then compare the two runs after it).

That boundary was learned by stepping on it (peer-chat 2026-07-28T20:43:34+09:00
and the narrower restatement at 20:51:18+09:00) and is not pinned by any other
test: test_wake_brief_open_agenda.py exercises the drift invariant with an
*empty* peer-chat and commit_cursor=False, so the consumption path never runs
there.  These tests run against a tmp_path root only; the live wake cursor is
never touched.
"""

from __future__ import annotations

import json
import types
from pathlib import Path


class FakeGit:
    # Canned git runner: each call pops the next response (stdout text or an
    # exception to raise).  Keeps unit tests off the real repository/network.

    def __init__(self, *responses: object) -> None:
        self._responses = list(responses)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> str:
        self.commands.append(command)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def fake_git_ok() -> FakeGit:
    return FakeGit(
        "",  # git fetch
        "codex/se-0.4-0.7-program",  # rev-parse --abbrev-ref HEAD
        "origin/codex/se-0.4-0.7-program",  # rev-parse <branch>@{upstream}
        "0\t5\n",  # rev-list --left-right --count <upstream>...HEAD
        "b86d857\n",  # rev-parse --short HEAD
    )


LIVE_WAKE_BRIEF = Path("C:/Users/zy/.claude/skills/solve-with-weilan/scripts/wake_brief.py")
STAMP = "2026-07-12T08:00:00+00:00"
CLOCK_GOAL = {
    "goal_ref": "goal:clock",
    "state": "ACTIVE",
    "condition": {
        "event_kind": "clock",
        "event_name": "tick",
        "not_before_utc": "2026-07-21T00:00:00+00:00",
    },
}


def load_live_module() -> types.ModuleType:
    module = types.ModuleType("live_wake_brief")
    module.__file__ = str(LIVE_WAKE_BRIEF)
    source = LIVE_WAKE_BRIEF.read_text(encoding="utf-8")
    exec(compile(source, str(LIVE_WAKE_BRIEF), "exec"), module.__dict__)
    return module


def seed_root(root: Path, peer_chat_rows: list[dict[str, object]]) -> None:
    for name in (
        "owner-inbox.jsonl",
        "owner-inbox-processed.jsonl",
        "codex-inbox-replies.jsonl",
        "concurrent-receipts.jsonl",
    ):
        (root / name).write_text("", encoding="utf-8")
    (root / "peer-chat.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in peer_chat_rows),
        encoding="utf-8",
    )


def build(module: types.ModuleType, root: Path, now_utc: str) -> dict[str, object]:
    return module.build_brief(
        root=root,
        workspace="D:\\WeilanSkillEvolution",
        scope="skill-evolution",
        updated_at_utc=STAMP,
        now_utc=now_utc,
        recall_fixture={"activation": {"state": "ACTIVE"}, "open_agenda": [CLOCK_GOAL]},
        prospective_fixture={"goals": []},
        git_runner=fake_git_ok(),
        commit_cursor=True,
    )


def normalized_hash(module: types.ModuleType, brief: dict[str, object], cursor_status: object) -> str:
    """Fingerprint with cursor_status held fixed, isolating the delta change."""
    return module.site_fingerprint_for({**brief, "cursor_status": cursor_status})["hash"]


def test_reading_a_brief_consumes_the_delta_so_run1_vs_run2_is_not_an_ab_pair(tmp_path: Path) -> None:
    module = load_live_module()
    rows = [
        {"from": "codex", "text": "first", "time": "2026-07-12T07:00:00+09:00"},
        {"from": "claude", "text": "second", "time": "2026-07-12T07:30:00+09:00"},
    ]
    seed_root(tmp_path, rows)
    cursor_path = tmp_path / "wake-cursor.json"
    assert not cursor_path.exists()

    first = build(module, tmp_path, STAMP)
    # commit_cursor=True must really have committed, or everything below is vacuous.
    assert cursor_path.exists()
    second = build(module, tmp_path, STAMP)

    assert [row["text"] for row in first["peer_chat_new"]] == ["first", "second"]
    assert second["peer_chat_new"] == []
    assert first["site_fingerprint"]["peer_chat_has_route_change"] is True
    assert second["site_fingerprint"]["peer_chat_has_route_change"] is False
    assert first["cursor_status"] == {"status": "full_rescan", "reason": "no_cursor"}
    assert second["cursor_status"] == {"status": "incremental"}

    # The two runs are identical in every input except the cursor's own state,
    # yet the fingerprints differ even with cursor_status held fixed: the delta
    # was consumed by the first read.  Reading is not free.
    held = second["cursor_status"]
    assert normalized_hash(module, first, held) != normalized_hash(module, second, held)


def test_clock_drift_immunity_holds_once_the_cursor_has_gone_quiet(tmp_path: Path) -> None:
    module = load_live_module()
    seed_root(tmp_path, [{"from": "codex", "text": "first", "time": "2026-07-12T07:00:00+09:00"}])

    build(module, tmp_path, "2026-07-20T23:59:00+00:00")  # warm-up: consumes the delta
    second = build(module, tmp_path, "2026-07-20T23:59:30+00:00")
    third = build(module, tmp_path, "2026-07-21T00:00:30+00:00")

    assert second["peer_chat_new"] == third["peer_chat_new"] == []
    assert second["cursor_status"] == third["cursor_status"] == {"status": "incremental"}

    # The clock really moved across the eligibility boundary...
    assert second["open_agenda"][0]["remaining_seconds"] == 30.0
    assert third["open_agenda"][0]["remaining_seconds"] == -30.0
    assert second["open_agenda"][0]["eligible_now"] is False
    assert third["open_agenda"][0]["eligible_now"] is True
    # ...and the fingerprint did not, which is the whole point of stripping the
    # clock display fields.  Assert this ONLY on a post-warm-up pair.
    assert second["site_fingerprint"]["hash"] == third["site_fingerprint"]["hash"]
