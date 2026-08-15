from __future__ import annotations

import json
import types
from pathlib import Path

IMPL_DIR = Path(__file__).resolve().parent
STAMP = "2026-08-15T01:00:00+00:00"


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


def load_repo_module():
    module = types.ModuleType("wake_brief_codex_lane")
    module.__file__ = str(IMPL_DIR / "wake_brief.py")
    source = (IMPL_DIR / "wake_brief.py").read_text(encoding="utf-8")
    exec(compile(source, str(IMPL_DIR / "wake_brief.py"), "exec"), module.__dict__)
    return module


def seed_root(root: Path) -> None:
    for name in (
        "owner-inbox.jsonl",
        "owner-inbox-processed.jsonl",
        "codex-inbox.jsonl",
        "codex-inbox-processed.jsonl",
        "codex-inbox-replies.jsonl",
        "peer-chat.jsonl",
        "concurrent-receipts.jsonl",
    ):
        (root / name).write_text("", encoding="utf-8")


def _recall() -> dict:
    return {
        "activation": {"state": "ACTIVE", "continuation_allowed": True},
        "control": {},
        "freshness": {"fresh": True},
    }


def build(module, root: Path) -> dict:
    return module.build_brief(
        root=root,
        workspace="D:\\WeilanSkillEvolution",
        scope="skill-evolution",
        updated_at_utc=STAMP,
        now_utc=STAMP,
        recall_fixture=_recall(),
        prospective_fixture={"goals": []},
        git_runner=fake_git_ok(),
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_build_brief_codex_inbox_delta_same_shape_as_owner(tmp_path: Path) -> None:
    module = load_repo_module()
    seed_root(tmp_path)

    owner_new = {"id": "owner-1", "from": "owner", "text": "owner task"}
    codex_new = {"id": "codex-1", "from": "claude", "text": "codex task"}
    _write_jsonl(tmp_path / "owner-inbox.jsonl", [owner_new, {"id": "owner-done", "from": "owner", "text": "x"}])
    _write_jsonl(tmp_path / "owner-inbox-processed.jsonl", [{"id": "owner-done"}])
    _write_jsonl(tmp_path / "codex-inbox.jsonl", [codex_new, {"id": "codex-done", "from": "claude", "text": "y"}])
    _write_jsonl(tmp_path / "codex-inbox-processed.jsonl", [{"id": "codex-done"}])

    brief = build(module, tmp_path)

    # (i) codex_inbox_delta 与 owner_inbox_delta 同形:list of dict
    assert isinstance(brief["owner_inbox_delta"], list)
    assert isinstance(brief["codex_inbox_delta"], list)
    assert brief["owner_inbox_delta"] == [owner_new]
    assert brief["codex_inbox_delta"] == [codex_new]
    assert all(isinstance(row, dict) for row in brief["codex_inbox_delta"])

    # sources 补两条 codex 车道源
    source_refs = [s["ref"] for s in brief["sources"]]
    assert any(ref.endswith("/codex-inbox.jsonl") for ref in source_refs)
    assert any(ref.endswith("/codex-inbox-processed.jsonl") for ref in source_refs)


def test_inbox_has_work_is_owner_or_codex() -> None:
    module = load_repo_module()

    def fp(owner, codex):
        return module.site_fingerprint_for(
            {"authority": {}, "owner_inbox_delta": owner, "codex_inbox_delta": codex, "sources": []}
        )

    # (ii) 任一 Δ 即 inbox_has_work=true
    assert fp([], [])["inbox_has_work"] is False
    assert fp([{"id": "o"}], [])["inbox_has_work"] is True
    assert fp([], [{"id": "c"}])["inbox_has_work"] is True

    # 指纹 hash 随 codex 车道变化(FINDING 甲:指纹半件;别让 hash 与 inbox_has_work 脱钩)
    assert fp([], [])["hash"] != fp([], [{"id": "c"}])["hash"]


def test_inbox_has_work_via_build_brief_fixtures(tmp_path: Path) -> None:
    module = load_repo_module()
    seed_root(tmp_path)

    # codex 车道 Δ 单独存在 → inbox_has_work=true
    _write_jsonl(tmp_path / "codex-inbox.jsonl", [{"id": "c1", "from": "claude", "text": "t"}])
    brief = build(module, tmp_path)
    assert brief["codex_inbox_delta"] == [{"id": "c1", "from": "claude", "text": "t"}]
    assert module.site_fingerprint_for(brief)["inbox_has_work"] is True

    # 只剩 owner 车道 Δ → 仍 true,codex 车道空
    _write_jsonl(tmp_path / "codex-inbox-processed.jsonl", [{"id": "c1"}])
    _write_jsonl(tmp_path / "owner-inbox.jsonl", [{"id": "o1", "from": "owner", "text": "t"}])
    brief = build(module, tmp_path)
    assert brief["codex_inbox_delta"] == []
    assert brief["owner_inbox_delta"] == [{"id": "o1", "from": "owner", "text": "t"}]
    assert module.site_fingerprint_for(brief)["inbox_has_work"] is True

    # 双车道都空 → false
    _write_jsonl(tmp_path / "owner-inbox-processed.jsonl", [{"id": "o1"}])
    brief = build(module, tmp_path)
    assert brief["owner_inbox_delta"] == []
    assert brief["codex_inbox_delta"] == []
    assert module.site_fingerprint_for(brief)["inbox_has_work"] is False


def test_prompt_step2_consumes_codex_inbox_delta() -> None:
    # (iii) 提示词消费半件:wake_prompt_codex.md 第 2 步含消费句
    prompt = (IMPL_DIR / "wake_prompt_codex.md").read_text(encoding="utf-8")
    assert "codex_inbox_delta" in prompt
    assert "逐条处理" in prompt
    assert "回源核验兜底" in prompt
