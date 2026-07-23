from __future__ import annotations

import json
import types
from pathlib import Path


LIVE_WAKE_BRIEF = Path("C:/Users/zy/.claude/skills/solve-with-weilan/scripts/wake_brief.py")
STAMP = "2026-07-12T08:00:00+00:00"


def load_live_module():
    module = types.ModuleType("live_wake_brief")
    module.__file__ = str(LIVE_WAKE_BRIEF)
    source = LIVE_WAKE_BRIEF.read_text(encoding="utf-8")
    exec(compile(source, str(LIVE_WAKE_BRIEF), "exec"), module.__dict__)
    return module


def seed_root(root: Path) -> None:
    for name in (
        "owner-inbox.jsonl",
        "owner-inbox-processed.jsonl",
        "codex-inbox-replies.jsonl",
        "peer-chat.jsonl",
        "concurrent-receipts.jsonl",
    ):
        (root / name).write_text("", encoding="utf-8")


def build(module, root: Path, recall):
    return module.build_brief(
        root=root,
        workspace="D:\\WeilanSkillEvolution",
        scope="skill-evolution",
        updated_at_utc=STAMP,
        now_utc=STAMP,
        recall_fixture=recall,
        prospective_fixture={"goals": []},
    )


def test_open_agenda_is_passed_through_and_guarded(tmp_path: Path) -> None:
    module = load_live_module()
    seed_root(tmp_path)
    active = [
        {"goal_ref": "goal:active-a", "state": "ACTIVE"},
        {"goal_ref": "goal:active-b", "state": "ACTIVE"},
    ]
    recall = {"activation": {"state": "ACTIVE"}, "open_agenda": active}
    assert build(module, tmp_path, recall)["open_agenda"] == active

    for malformed in ({"open_agenda": "not-a-list"}, [], None):
        other = tmp_path / str(len(list(tmp_path.iterdir())))
        other.mkdir()
        seed_root(other)
        assert build(module, other, malformed)["open_agenda"] == []


def test_fingerprint_tracks_agenda_without_reclassifying_work(tmp_path: Path) -> None:
    module = load_live_module()
    seed_root(tmp_path)
    agenda = [{"goal_ref": "goal:active-a", "state": "ACTIVE"}]
    first = build(module, tmp_path, {"open_agenda": agenda})
    second = build(module, tmp_path, {"open_agenda": agenda})
    changed = build(module, tmp_path, {"open_agenda": agenda + [{"goal_ref": "goal:active-b"}]})

    assert first["site_fingerprint"]["open_agenda_present"] is True
    assert first["site_fingerprint"]["inbox_has_work"] is False
    assert first["site_fingerprint"]["prospective_has_due"] is False
    assert second["cursor_status"] == {"status": "incremental"}
    assert first["site_fingerprint"]["hash"] != second["site_fingerprint"]["hash"]
    normalized_first = dict(first)
    normalized_second = dict(second)
    normalized_first["cursor_status"] = normalized_second["cursor_status"]
    assert module.site_fingerprint_for(normalized_first)["hash"] == module.site_fingerprint_for(normalized_second)["hash"]
    assert module.site_fingerprint_for(normalized_second)["hash"] != module.site_fingerprint_for(changed)["hash"]


def test_clock_display_changes_with_now_but_fingerprint_stays_stable(tmp_path: Path) -> None:
    module = load_live_module()
    seed_root(tmp_path)
    agenda = [
        {
            "goal_ref": "goal:clock",
            "state": "ACTIVE",
            "condition": {
                "event_kind": "clock",
                "event_name": "tick",
                "not_before_utc": "2026-07-21T00:00:00+00:00",
            },
        }
    ]
    kwargs = {
        "root": tmp_path,
        "workspace": "D:\\WeilanSkillEvolution",
        "scope": "skill-evolution",
        "updated_at_utc": STAMP,
        "recall_fixture": {"open_agenda": agenda},
        "prospective_fixture": {"goals": []},
        "commit_cursor": False,
    }

    before = module.build_brief(now_utc="2026-07-20T23:59:30+00:00", **kwargs)
    after = module.build_brief(now_utc="2026-07-21T00:00:30+00:00", **kwargs)

    before_item = before["open_agenda"][0]
    after_item = after["open_agenda"][0]
    assert before_item["eligible_after_utc"] == "2026-07-21T00:00:00+00:00"
    assert before_item["remaining_seconds"] == 30.0
    assert before_item["eligible_now"] is False
    assert after_item["remaining_seconds"] == -30.0
    assert after_item["eligible_now"] is True
    assert before["site_fingerprint"]["hash"] == after["site_fingerprint"]["hash"]
    assert before_item["condition"]["not_before_utc"] == after_item["condition"]["not_before_utc"]
