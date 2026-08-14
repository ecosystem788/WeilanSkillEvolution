from __future__ import annotations

from pathlib import Path

import wake_brief


STAMP = "2026-07-10T09:30:00+00:00"
UPSTREAM = "origin/codex/se-0.4-0.7-program"
WORKSPACE = "D:\\WeilanSkillEvolution"


class FakeGit:
    # Canned git runner: each call pops the next response (stdout text or
    # an exception to raise); records every command it was given.

    def __init__(self, *responses: object) -> None:
        self._responses = list(responses)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> str:
        self.commands.append(command)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def git_error(message: str) -> wake_brief._GitError:
    return wake_brief._GitError(message, ["git"])


def seed_root(root: Path) -> None:
    for name in (
        "owner-inbox.jsonl",
        "owner-inbox-processed.jsonl",
        "codex-inbox-replies.jsonl",
        "peer-chat.jsonl",
        "concurrent-receipts.jsonl",
    ):
        (root / name).write_text("", encoding="utf-8")


def build_brief(root: Path, git_runner: FakeGit) -> dict:
    return wake_brief.build_brief(
        root=root,
        workspace=WORKSPACE,
        scope="skill-evolution",
        updated_at_utc=STAMP,
        now_utc=STAMP,
        recall_fixture={"activation": {"state": "ACTIVE"}, "control": {}, "open_agenda": []},
        prospective_fixture={"goals": []},
        git_runner=git_runner,
    )


def test_success_reports_ahead_count_and_head_short(tmp_path: Path) -> None:
    seed_root(tmp_path)
    runner = FakeGit("", "codex/se-0.4-0.7-program", UPSTREAM, "0\t5\n", "b86d857\n")

    brief = build_brief(tmp_path, runner)

    assert brief["unpushed_commits"] == {
        "count": 5,
        "head_short": "b86d857",
        "suggestion": "本醒可推",
    }
    assert runner.commands[0] == ["fetch"]


def test_zero_ahead_says_nothing_to_push(tmp_path: Path) -> None:
    seed_root(tmp_path)
    runner = FakeGit("", "codex/se-0.4-0.7-program", UPSTREAM, "0\t0\n", "b86d857\n")

    brief = build_brief(tmp_path, runner)

    assert brief["unpushed_commits"]["count"] == 0
    assert brief["unpushed_commits"]["suggestion"] == "无可推"


def test_fetch_failure_falls_back_to_local_ref_and_flags_it(tmp_path: Path) -> None:
    seed_root(tmp_path)
    runner = FakeGit(
        git_error("fatal: unable to access 'https://example.invalid/': could not resolve host"),
        "codex/se-0.4-0.7-program",
        UPSTREAM,
        "0\t5\n",
        "b86d857\n",
    )

    brief = build_brief(tmp_path, runner)

    assert brief["unpushed_commits"]["count"] == 5
    assert brief["unpushed_commits"]["fetch_failed"] is True


def test_not_a_git_repository_is_fail_closed(tmp_path: Path) -> None:
    seed_root(tmp_path)
    runner = FakeGit(
        git_error("fatal: not a git repository (or any of the parent directories): .git"),
        git_error("fatal: not a git repository (or any of the parent directories): .git"),
    )

    brief = build_brief(tmp_path, runner)

    field = brief["unpushed_commits"]
    assert field["count"] is None
    assert field["error"] == "not a git repository"
    assert field["command"][0] == "git"


def test_detached_head_is_fail_closed(tmp_path: Path) -> None:
    seed_root(tmp_path)
    runner = FakeGit("", "HEAD")

    brief = build_brief(tmp_path, runner)

    assert brief["unpushed_commits"]["count"] is None
    assert brief["unpushed_commits"]["error"] == "no_upstream_or_detached"


def test_branch_without_upstream_is_fail_closed(tmp_path: Path) -> None:
    seed_root(tmp_path)
    runner = FakeGit(
        "",
        "orphan-branch",
        git_error("fatal: no upstream configured for branch 'orphan-branch'"),
    )

    brief = build_brief(tmp_path, runner)

    assert brief["unpushed_commits"]["count"] is None
    assert brief["unpushed_commits"]["error"] == "no_upstream_or_detached"


def test_git_command_failure_reports_detail_and_command(tmp_path: Path) -> None:
    seed_root(tmp_path)
    runner = FakeGit("", "codex/se-0.4-0.7-program", UPSTREAM, git_error("fatal: ambiguous argument"))

    brief = build_brief(tmp_path, runner)

    field = brief["unpushed_commits"]
    assert field["count"] is None
    assert field["error"] == "git_command_failed"
    assert field["error_detail"] == "fatal: ambiguous argument"
    assert field["command"] == ["git", "-C", WORKSPACE, "rev-list", "--left-right", "--count", f"{UPSTREAM}...HEAD"]


def test_garbage_rev_list_output_is_fail_closed(tmp_path: Path) -> None:
    seed_root(tmp_path)
    runner = FakeGit("", "codex/se-0.4-0.7-program", UPSTREAM, "not two numbers\n", "b86d857\n")

    brief = build_brief(tmp_path, runner)

    field = brief["unpushed_commits"]
    assert field["count"] is None
    assert field["error"] == "git_command_failed"
    assert "unexpected rev-list output" in field["error_detail"]


def test_fingerprint_does_not_absorb_unpushed_commits(tmp_path: Path) -> None:
    seed_root(tmp_path)
    # Warm up the incremental cursor first: build 1 is a full_rescan, and
    # the fingerprint tracks cursor_status (advance must not be read as a
    # regression).  Only after the cursor is quiet may the two runs be
    # compared.
    build_brief(tmp_path, FakeGit("", "codex/se-0.4-0.7-program", UPSTREAM, "0\t1\n", "b86d857\n"))
    quiet = build_brief(tmp_path, FakeGit("", "codex/se-0.4-0.7-program", UPSTREAM, "0\t0\n", "b86d857\n"))
    busy = build_brief(tmp_path, FakeGit("", "codex/se-0.4-0.7-program", UPSTREAM, "0\t9\n", "b86d857\n"))

    assert quiet["cursor_status"]["status"] == "incremental"
    assert busy["cursor_status"]["status"] == "incremental"
    assert quiet["unpushed_commits"]["count"] == 0
    assert busy["unpushed_commits"]["count"] == 9
    assert quiet["site_fingerprint"]["hash"] == busy["site_fingerprint"]["hash"]


def test_real_default_runner_is_fail_closed_for_non_repo(tmp_path: Path) -> None:
    # Real default runner (no fixture): a non-git workspace must report
    # fail-closed "not a git repository", never a silent zero.
    seed_root(tmp_path)
    brief = wake_brief.build_brief(
        root=tmp_path,
        workspace=str(tmp_path),
        scope="skill-evolution",
        updated_at_utc=STAMP,
        now_utc=STAMP,
        recall_fixture={"activation": {"state": "ACTIVE"}, "control": {}, "open_agenda": []},
        prospective_fixture={"goals": []},
    )

    field = brief["unpushed_commits"]
    assert field["count"] is None
    assert field["error"] == "not a git repository"
