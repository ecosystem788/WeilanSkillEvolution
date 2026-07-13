from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(r"C:\Users\zy\.claude\skills\solve-with-weilan\scripts")
TRACE = SCRIPT_DIR / "weilan_trace.py"
sys.path.insert(0, str(SCRIPT_DIR))
import wake_brief  # noqa: E402


STAMP = "2026-07-11T14:00:00+00:00"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def seed_root(root: Path) -> None:
    write_jsonl(root / "peer-chat.jsonl", [{"from": "claude", "text": "proposal"}])
    write_jsonl(root / "codex-inbox-replies.jsonl", [])


def build(root: Path) -> dict:
    return wake_brief.build_brief(
        root=root,
        workspace=r"D:\WeilanSkillEvolution",
        scope="skill-evolution",
        updated_at_utc=STAMP,
        now_utc=STAMP,
        recall_fixture={"activation": {"state": "ACTIVE", "continuation_allowed": True}},
        prospective_fixture={"goals": []},
    )


def append_receipt(root: Path, wake_id: str = "wake-1", *extra: str) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(TRACE),
        "concurrent-receipt-append",
        "--root",
        str(root),
        "--wake-id",
        wake_id,
        "--time",
        "2026-07-11 23:59:00",
        "--attempted-relation",
        "continue",
        "--attempted-parent",
        "wf-parent",
        "--observed-head",
        "wf-open-head",
        "--open-error",
        "causal parent must be closed: wf-open-head",
        "--source",
        "wake_brief:fixture",
        *extra,
    ]
    env = os.environ.copy()
    env["CODEX_HOME"] = str(root / "codex-home")
    return subprocess.run(command, text=True, capture_output=True, env=env)


def test_no_concurrency_regular_brief_has_no_sidecar_rows(tmp_path: Path) -> None:
    seed_root(tmp_path)

    brief = build(tmp_path)

    assert brief["concurrent_receipts_new"] == []
    assert not (tmp_path / "concurrent-receipts.jsonl").exists()
    assert "concurrent-receipts.jsonl" not in wake_brief.REQUIRED_SOURCE_FILES


def test_open_failure_can_append_visibility_only_sidecar_row(tmp_path: Path) -> None:
    seed_root(tmp_path)

    result = append_receipt(tmp_path)
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line) for line in (tmp_path / "concurrent-receipts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {
            "schema_version": "weilan_concurrent_receipt_v0.1",
            "wake_id": "wake-1",
            "time": "2026-07-11 23:59:00",
            "attempted_relation": "continue",
            "attempted_parent": "wf-parent",
            "observed_head": "wf-open-head",
            "open_error": "causal parent must be closed: wf-open-head",
            "work_performed": False,
            "folded_by_frame_id": None,
            "source": "wake_brief:fixture",
        }
    ]
    assert not (tmp_path / ".lineage.lock").exists()

    brief = build(tmp_path)
    assert [row["wake_id"] for row in brief["concurrent_receipts_new"]] == ["wake-1"]


def test_work_performed_true_is_rejected_instead_of_downgraded(tmp_path: Path) -> None:
    seed_root(tmp_path)

    result = append_receipt(tmp_path, "wake-material", "--work-performed")

    assert result.returncode != 0
    assert "work_performed=false" in result.stderr
    assert not (tmp_path / "concurrent-receipts.jsonl").exists()


def test_fold_marker_hides_receipt_without_rewriting_history(tmp_path: Path) -> None:
    seed_root(tmp_path)
    assert append_receipt(tmp_path, "wake-fold").returncode == 0
    assert append_receipt(tmp_path, "wake-fold", "--folded-by-frame-id", "wf-folding-frame").returncode == 0

    rows = (tmp_path / "concurrent-receipts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 2
    brief = build(tmp_path)
    assert brief["concurrent_receipts_new"] == []
