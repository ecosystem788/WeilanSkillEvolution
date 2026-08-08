from __future__ import annotations

import json
from pathlib import Path
import subprocess

import cited_artifact_receipt_check as gate


AUTHOR = "codex"
TIMESTAMP = "2026-08-01T00:00:00+09:00"


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _write_bucket(ledger_root: Path, text: str) -> None:
    record = {"from": AUTHOR, "time": TIMESTAMP, "text": text}
    (ledger_root / gate.LEDGER_NAME).write_text(
        json.dumps(record, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _repository(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    ledger_root = root / "proposals" / "bounded-scheduler-v0.1" / "impl"
    ledger_root.mkdir(parents=True)
    (root / "proposals" / "tracked.md").write_text("tracked\n", encoding="utf-8")
    (root / "proposals" / "history.md").write_text("history\n", encoding="utf-8")
    (root / ".gitignore").write_text("proposals/ignored.md\n", encoding="utf-8")
    (root / "proposals" / "ignored.md").write_text("ignored\n", encoding="utf-8")

    _git(root, "init")
    _git(root, "-c", "user.name=WeiLan Test", "-c", "user.email=test@example.invalid", "add", ".gitignore", "proposals/tracked.md", "proposals/history.md")
    _git(root, "-c", "user.name=WeiLan Test", "-c", "user.email=test@example.invalid", "commit", "-m", "seed")
    _git(root, "rm", "proposals/history.md")
    _git(root, "-c", "user.name=WeiLan Test", "-c", "user.email=test@example.invalid", "commit", "-m", "remove history-only file")
    return root, ledger_root


def _statuses(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    record = payload["records"][0]
    return {item["path"]: item for item in record["citations"]}


def test_cited_paths_obeys_signed_adversarial_boundary() -> None:
    text = "\n".join(
        (
            r"C:\Users\zy\proposals\windows-absolute.md",
            "D:proposals/drive-relative.py",
            "D:/WeilanSkillEvolution/proposals/workspace-absolute.md",
            "http://example.invalid/proposals/http.md",
            "https://example.invalid/docs/https.md",
            "git@host:proposals/remote.md",
            "全文:proposals/chinese-label.md",
            "【证据】:proposals/punctuation-label.md",
            "proposals/bare.md",
        )
    )

    assert gate.cited_paths(text) == [
        "proposals/chinese-label.md",
        "proposals/punctuation-label.md",
        "proposals/bare.md",
    ]


def test_ellipsis_is_warning_without_aborting_other_citations(tmp_path: Path) -> None:
    _root, ledger_root = _repository(tmp_path)
    _write_bucket(
        ledger_root,
        "proposals/.../ghost.md and proposals/tracked.md",
    )

    payload = gate.check_bucket(root=ledger_root, author=AUTHOR, timestamp=TIMESTAMP)
    statuses = _statuses(payload)

    assert statuses["proposals/.../ghost.md"]["status"] == "unresolvable_component"
    assert statuses["proposals/tracked.md"]["status"] == "tracked_head"
    assert payload["status_counts"] == {
        "tracked_head": 1,
        "unresolvable_component": 1,
    }
    assert payload["warning_count"] == 1
    assert payload["warning_statuses"] == ["unresolvable_component"]


def test_ignored_warns_but_history_only_does_not(tmp_path: Path) -> None:
    _root, ledger_root = _repository(tmp_path)
    _write_bucket(
        ledger_root,
        "proposals/ignored.md and proposals/history.md",
    )

    payload = gate.check_bucket(root=ledger_root, author=AUTHOR, timestamp=TIMESTAMP)
    statuses = _statuses(payload)

    assert statuses["proposals/ignored.md"]["status"] == "ignored"
    assert statuses["proposals/history.md"]["status"] == "history_only"
    assert payload["warning_count"] == 1


def test_one_classification_error_does_not_abort_bucket(
    tmp_path: Path, monkeypatch
) -> None:
    _root, ledger_root = _repository(tmp_path)
    _write_bucket(ledger_root, "proposals/bad.md and proposals/tracked.md")
    original = gate._classify

    def classify(**kwargs):
        if kwargs["path"] == "proposals/bad.md":
            raise gate.CheckError("git_failed", "synthetic per-citation failure")
        return original(**kwargs)

    monkeypatch.setattr(gate, "_classify", classify)
    payload = gate.check_bucket(root=ledger_root, author=AUTHOR, timestamp=TIMESTAMP)
    statuses = _statuses(payload)

    assert statuses["proposals/bad.md"]["status"] == "check_error:git_failed"
    assert statuses["proposals/bad.md"]["classification_error"] == {
        "reason": "git_failed",
        "detail": "synthetic per-citation failure",
    }
    assert statuses["proposals/tracked.md"]["status"] == "tracked_head"


def test_true_parent_escape_keeps_invalid_path_reason(tmp_path: Path) -> None:
    root, _ledger_root = _repository(tmp_path)

    try:
        gate._classify(root=root, path="../outside.md", tracked=set(), historical=set())
    except gate.CheckError as exc:
        assert exc.reason == "invalid_path"
        assert exc.detail == "path escapes root: ../outside.md"
    else:
        raise AssertionError("true parent escape was not rejected")


def test_message_not_found_remains_nonzero(tmp_path: Path, capsys) -> None:
    _root, ledger_root = _repository(tmp_path)
    _write_bucket(ledger_root, "proposals/tracked.md")

    status = gate.main(
        [
            "--root",
            str(ledger_root),
            "--from",
            AUTHOR,
            "--time",
            "missing-time",
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert status != 0
    assert output["ok"] is False
    assert output["reason"] == "message_not_found"


def test_dots_only_component_ge3_is_unresolvable(tmp_path: Path) -> None:
    _root, ledger_root = _repository(tmp_path)
    _write_bucket(
        ledger_root,
        "proposals/..../ghost.md and proposals/...../ghost.md and proposals/tracked.md",
    )

    payload = gate.check_bucket(root=ledger_root, author=AUTHOR, timestamp=TIMESTAMP)
    statuses = _statuses(payload)

    assert statuses["proposals/..../ghost.md"]["status"] == "unresolvable_component"
    assert statuses["proposals/...../ghost.md"]["status"] == "unresolvable_component"
    assert statuses["proposals/tracked.md"]["status"] == "tracked_head"
    assert payload["warning_count"] == 2
    assert payload["warning_statuses"] == ["unresolvable_component"]


def test_warning_flip_counts_only_non_clean_statuses(tmp_path: Path, monkeypatch) -> None:
    _root, ledger_root = _repository(tmp_path)
    _write_bucket(
        ledger_root,
        "proposals/tracked.md and proposals/history.md and proposals/bad.md",
    )
    original = gate._classify

    def classify(**kwargs):
        if kwargs["path"] == "proposals/bad.md":
            raise gate.CheckError("git_failed", "synthetic per-citation failure")
        return original(**kwargs)

    monkeypatch.setattr(gate, "_classify", classify)
    payload = gate.check_bucket(root=ledger_root, author=AUTHOR, timestamp=TIMESTAMP)
    statuses = _statuses(payload)

    assert statuses["proposals/tracked.md"]["status"] == "tracked_head"
    assert statuses["proposals/history.md"]["status"] == "history_only"
    assert statuses["proposals/bad.md"]["status"] == "check_error:git_failed"
    assert payload["warning_count"] == 1
    assert payload["warning_statuses"] == ["check_error:git_failed"]


def test_all_clean_statuses_give_zero_warning(tmp_path: Path) -> None:
    _root, ledger_root = _repository(tmp_path)
    _write_bucket(ledger_root, "proposals/tracked.md and proposals/history.md")

    payload = gate.check_bucket(root=ledger_root, author=AUTHOR, timestamp=TIMESTAMP)

    assert payload["warning_count"] == 0
    assert payload["warning_statuses"] == []


def test_rev_suffix_qualified_paths_blocked_but_cjk_labels_kept() -> None:
    text = "\n".join(
        (
            "全文:proposals/chinese-label.md",
            "【证据】:proposals/punct-label.md",
            "):proposals/paren-label.md",
            "HEAD^:proposals/rev1.md",
            "HEAD@{1}:proposals/rev2.md",
            "e830a26^:proposals/rev3.md",
        )
    )

    assert gate.cited_paths(text) == [
        "proposals/chinese-label.md",
        "proposals/punct-label.md",
        "proposals/paren-label.md",
    ]
