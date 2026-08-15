#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""peer_chat_receipt_lint.py 的 pytest 钉点（RECEIPT_CONVENTION v0.1 §五）。

运行：
  python -m pytest test_peer_chat_receipt_lint.py -v
或直接：
  python test_peer_chat_receipt_lint.py

用例覆盖（4024 edit ①-⑥ + 4020 验收口径）：
  [1] 非收据消息（提案/回信/闲聊）出范围，不约束；
  [2] 休息收据 ≤200 通过；
  [3] 干活收据 ≤600 + round-notes 可达 通过；
  [4] 干活收据 >600 挡门；
  [5] 休息收据 >200 挡门；
  [6] 缺必需字段挡门；
  [7] 帧号非法挡门；
  [8] round-notes/<帧号>.md 缺失挡门；
  [9] 自承「笔记 pending」不挡门（交挂账助手，2 醒规则）；
  [10] 字段软上限只报告不挡门（4024 edit ②）；
  [11] --adoption-after 把更早收据记 history_out_of_scope，不计失败；
  [12] CLI 端到端（temp 账本，exit code 与 JSON）。
"""

import json
import os
import subprocess
import sys

import pytest

import peer_chat_receipt_lint as lint

HERE = os.path.dirname(os.path.abspath(__file__))

FRAME = "wf-20260814-080000-abcdef"
PARENT = "wf-20260814-070752-6f0cfd"
NOTE = "round-notes/%s.md" % FRAME


def work_receipt(extra="", notes=None):
    tail = "" if notes is None else " | 笔记=%s" % notes
    return "【续帧收据】帧=%s | 父=%s | 结果=success | 做了什么=落地D1%s | 续点=Claude回核%s" % (FRAME, PARENT, extra, tail)


def rest_receipt(sentence="无真活诚实歇"):
    return "【续帧收据】帧=%s | 父=%s | 结果=success | %s" % (FRAME, PARENT, sentence)


def make_round_notes(tmp_path):
    d = tmp_path / "round-notes"
    d.mkdir()
    (d / (FRAME + ".md")).write_text("notes\n", encoding="utf-8")
    return str(d)


def test_scope_ignores_non_receipt():
    for t in [
        "【提案·收据瘦身 v0.1】改什么/为什么/怎么验证/怎么回滚",
        "【同意·带 edits】整体方向同意。",
        "闲聊一句。",
        "答观察员:是问题。",
    ]:
        assert lint.parse_receipt(t) is None
        assert lint.check_message(t) is None


def test_rest_receipt_ok(tmp_path):
    notes = make_round_notes(tmp_path)
    text = rest_receipt()
    res = lint.check_message(text, round_notes_dir=notes)
    assert res is not None
    assert res["kind"] == "rest"
    assert len(text) <= 200
    assert res["ok"] is True


def test_work_receipt_ok(tmp_path):
    notes = make_round_notes(tmp_path)
    text = work_receipt(notes=NOTE)
    res = lint.check_message(text, round_notes_dir=notes)
    assert res is not None
    assert res["kind"] == "work"
    assert len(text) <= 600
    assert res["ok"] is True


def test_work_too_long(tmp_path):
    notes = make_round_notes(tmp_path)
    text = work_receipt(extra="x" * 600, notes=NOTE)
    assert len(text) > 600
    res = lint.check_message(text, round_notes_dir=notes)
    assert res["ok"] is False
    assert any(i.startswith("too_long=") for i in res["issues"])


def test_rest_too_long(tmp_path):
    notes = make_round_notes(tmp_path)
    text = rest_receipt(sentence="字" * 250)
    assert len(text) > 200
    res = lint.check_message(text, round_notes_dir=notes)
    assert res["ok"] is False
    assert any(i.startswith("too_long=") for i in res["issues"])


def test_missing_field(tmp_path):
    notes = make_round_notes(tmp_path)
    text = "【续帧收据】帧=%s | 父=%s | 结果=success | 做了什么=x" % (FRAME, PARENT)
    res = lint.check_message(text, round_notes_dir=notes)
    assert res["ok"] is False
    assert any(i.startswith("missing_fields=") and "续点" in i for i in res["issues"])


def test_bad_frame(tmp_path):
    notes = make_round_notes(tmp_path)
    text = "【续帧收据】帧=not-a-frame | 父=%s | 结果=success | 做了什么=x | 续点=y" % PARENT
    res = lint.check_message(text, round_notes_dir=notes)
    assert res["ok"] is False
    assert any(i.startswith("bad_frame=") for i in res["issues"])


def test_round_notes_missing(tmp_path):
    d = tmp_path / "round-notes"
    d.mkdir()
    res = lint.check_message(work_receipt(notes=NOTE), round_notes_dir=str(d))
    assert res["ok"] is False
    assert any(i.startswith("round_notes_missing=") for i in res["issues"])


def test_notes_pending_not_gating(tmp_path):
    d = tmp_path / "round-notes"
    d.mkdir()
    text = work_receipt(notes="pending")
    res = lint.check_message(text, round_notes_dir=str(d))
    assert res["ok"] is True
    assert "notes_pending" in res["soft"]


def test_soft_caps_report_only(tmp_path):
    notes = make_round_notes(tmp_path)
    text = work_receipt(extra="x" * 400, notes=NOTE)
    res = lint.check_message(text, round_notes_dir=notes)
    assert len(text) < 600
    assert res["ok"] is True
    assert any(s.startswith("做了什么=") for s in res["soft"])


def test_adoption_after_scopes_history(tmp_path):
    notes = make_round_notes(tmp_path)
    ledger = tmp_path / "peer-chat.jsonl"
    rows = [
        {"from": "codex", "time": "2026-08-14T15:53:18+09:00", "text": work_receipt(notes=NOTE)},
        {"from": "codex", "time": "2026-08-14T18:00:00+09:00", "text": work_receipt(notes=NOTE)},
    ]
    ledger.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    summary = lint.scan_ledger(str(ledger), round_notes_dir=notes, adoption_after="2026-08-14T17:00:00+09:00")
    assert summary["counts"]["history_out_of_scope"] == 1
    assert summary["counts"]["failures"] == 0
    assert summary["ok"] is True


def test_cli_end_to_end(tmp_path):
    notes = make_round_notes(tmp_path)
    ledger = tmp_path / "peer-chat.jsonl"
    good = {"from": "codex", "time": "2026-08-14T18:00:00+09:00", "text": work_receipt(notes=NOTE)}
    bad = {"from": "codex", "time": "2026-08-14T18:01:00+09:00", "text": work_receipt(extra="y" * 700, notes=NOTE)}
    ledger.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in (good, bad)) + "\n", encoding="utf-8")
    script = os.path.join(HERE, "peer_chat_receipt_lint.py")
    p = subprocess.run(
        [sys.executable, script, "--ledger", str(ledger), "--round-notes", str(notes)],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert p.returncode == 1
    data = json.loads(p.stdout)
    assert data["counts"]["failures"] == 1
    assert data["ok"] is False


def test_parse_error_non_gating(tmp_path):
    notes = make_round_notes(tmp_path)
    ledger = tmp_path / "peer-chat.jsonl"
    good = {"from": "codex", "time": "2026-08-14T18:00:00+09:00", "text": work_receipt(notes=NOTE)}
    corrupt = '{"from": "claude", "time": "2026-07-13 18:22:40", "text": "D:\\CodexData\\home"}\n'
    ledger.write_text(json.dumps(good, ensure_ascii=False) + "\n" + corrupt, encoding="utf-8")
    summary = lint.scan_ledger(str(ledger), round_notes_dir=notes)
    assert summary["counts"]["ledger_parse_errors"] == 1
    assert summary["counts"]["failures"] == 0
    assert summary["ok"] is True

SUPERSEDE_BAD_FRAME = "wf-20260815-055000-claude01"
SUPERSEDE_GOOD_FRAME = "wf-20260815-055000-2c5e7d"
SUPERSEDE_GOOD_FRAME2 = "wf-20260815-013517-bc3384"


def _bad_frame_work_receipt(frame, notes="round-notes/missing.md"):
    return "【续帧收据】帧=%s | 父=%s | 结果=success | 做了什么=x | 续点=y | 笔记=%s" % (frame, PARENT, notes)


def _supersede_line_frame_ref(bad_frame, good_frame):
    return ("【勘误·frame id retro-fix】supersede 续帧收据 帧=%s(笔误,JST 戳)\n"
            "实际 weilan_trace.open L2 给出的真值是 %s(UTC 戳)。round-notes 已 git mv 至 %s.md。"
            % (bad_frame, good_frame, good_frame))


def _supersede_line_peer_chat_ref(line_no, bad_frame, good_frame):
    return ("【勘误·frame id retro-fix】supersede peer-chat:%d (bad_frame %s)。合规 frame id = %s; "
            "笔记已 git mv 至 round-notes/%s.md (commit ed5d498)。本条 supersede。"
            % (line_no, bad_frame, good_frame, good_frame))


def _write_ledger(tmp_path, rows):
    ledger = tmp_path / "peer-chat.jsonl"
    ledger.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return str(ledger)


def test_supersede_exemption_bad_frame(tmp_path):
    notes_dir = tmp_path / "round-notes"
    notes_dir.mkdir()
    (notes_dir / (SUPERSEDE_GOOD_FRAME + ".md")).write_text("n\n", encoding="utf-8")
    rows = [
        {"from": "claude", "time": "2026-08-15T05:51:00+09:00",
         "text": _bad_frame_work_receipt(SUPERSEDE_BAD_FRAME, "round-notes/" + SUPERSEDE_BAD_FRAME + ".md")},
        {"from": "claude", "time": "2026-08-15T05:52:00+09:00",
         "text": _supersede_line_peer_chat_ref(1, SUPERSEDE_BAD_FRAME, SUPERSEDE_GOOD_FRAME)},
    ]
    ledger = _write_ledger(tmp_path, rows)
    summary = lint.scan_ledger(ledger, round_notes_dir=str(notes_dir))
    assert summary["counts"]["failures"] == 0
    assert summary["counts"]["superseded"] == 1
    assert summary["ok"] is True
    soft = summary["superseded"][0]["soft"]
    assert any(s.startswith("superseded=" + SUPERSEDE_BAD_FRAME + "→") for s in soft)


def test_supersede_exemption_round_notes_missing(tmp_path):
    notes_dir = tmp_path / "round-notes"
    notes_dir.mkdir()
    (notes_dir / (SUPERSEDE_GOOD_FRAME2 + ".md")).write_text("n\n", encoding="utf-8")
    wrong = "wf-20260815-103348-d5b7a3"
    rows = [
        {"from": "claude", "time": "2026-08-15T10:34:00+09:00",
         "text": _bad_frame_work_receipt(wrong, "round-notes/" + wrong + ".md")},
        {"from": "claude", "time": "2026-08-15T10:36:00+09:00",
         "text": _supersede_line_frame_ref(wrong, SUPERSEDE_GOOD_FRAME2)},
    ]
    ledger = _write_ledger(tmp_path, rows)
    summary = lint.scan_ledger(ledger, round_notes_dir=str(notes_dir))
    assert summary["counts"]["failures"] == 0
    assert summary["counts"]["superseded"] == 1
    soft = summary["superseded"][0]["soft"]
    assert any(s.startswith("superseded=" + wrong + "→") for s in soft)


def test_no_supersede_still_blocks(tmp_path):
    notes_dir = tmp_path / "round-notes"
    notes_dir.mkdir()
    rows = [
        {"from": "claude", "time": "2026-08-15T05:51:00+09:00",
         "text": _bad_frame_work_receipt(SUPERSEDE_BAD_FRAME)},
    ]
    ledger = _write_ledger(tmp_path, rows)
    summary = lint.scan_ledger(ledger, round_notes_dir=str(notes_dir))
    assert summary["counts"]["failures"] == 1
    assert summary["counts"]["superseded"] == 0
    assert summary["ok"] is False


def test_no_cross_author_exemption(tmp_path):
    notes_dir = tmp_path / "round-notes"
    notes_dir.mkdir()
    (notes_dir / (SUPERSEDE_GOOD_FRAME + ".md")).write_text("n\n", encoding="utf-8")
    rows = [
        {"from": "claude", "time": "2026-08-15T05:51:00+09:00",
         "text": _bad_frame_work_receipt(SUPERSEDE_BAD_FRAME)},
        {"from": "codex", "time": "2026-08-15T05:52:00+09:00",
         "text": _supersede_line_peer_chat_ref(1, SUPERSEDE_BAD_FRAME, SUPERSEDE_GOOD_FRAME)},
    ]
    ledger = _write_ledger(tmp_path, rows)
    summary = lint.scan_ledger(ledger, round_notes_dir=str(notes_dir))
    assert summary["counts"]["failures"] == 1
    assert summary["counts"]["superseded"] == 0
    assert summary["ok"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
