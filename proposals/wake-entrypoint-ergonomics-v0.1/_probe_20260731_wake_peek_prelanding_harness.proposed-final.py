"""Pre-landing harness for the wake-entrypoint patch: --peek (1) + cursor (2).

Every write happens under tempfile.  The live ledger, the live cursor and the
live skill directory are never touched: the module under test is imported by
path, and the trace subprocess is replaced by a stub script written into the
temp root.

Two modules are loaded side by side -- the current base and the proposed final --
so the negative controls are real observations of the gap, not narration.

FROZEN EVIDENCE, NOT A REGRESSION TEST.  It only means anything while base and
proposed hold different bytes, i.e. before this patch lands.  After landing the
two paths are byte-identical, both negative controls reverse, and running this
file reports 2 FAIL / rc=1 BY DESIGN -- that is the artifact still telling the
truth, not the artifact rotting.  Hence the _probe_ name: pytest must never
collect it.  Long-term coverage of the landed behaviour lives in the three new
cases in proposals/bounded-scheduler-v0.1/impl/test_wake_brief.py, which assert
the landed state only and never import the base module.

Run:  python _probe_20260731_wake_peek_prelanding_harness.py
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_PATH = HERE.parent / "bounded-scheduler-v0.1" / "impl" / "wake_brief.py"
PROPOSED_PATH = HERE / "wake_brief.proposed-final.py"

FAILURES: list[str] = []


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = _load("wake_brief_base", BASE_PATH)
proposed = _load("wake_brief_proposed", PROPOSED_PATH)

RECALL_FIXTURE = {
    "activation": {"state": "ACTIVE", "continuation_allowed": True},
    "control": {"state": "active"},
    "freshness": {"fresh": True},
    "open_agenda": [],
}
PROSPECTIVE_FIXTURE = {"goals": []}

STUB_TRACE = """import json, sys
print(json.dumps({"activation": {"state": "ACTIVE"}, "control": {"state": "active"},
                  "freshness": {"fresh": True}, "open_agenda": [], "goals": []},
                 ensure_ascii=False))
"""


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    if not condition:
        FAILURES.append(f"{label}: {detail}")
    print(f"[{status}] {label}" + (f"  -- {detail}" if detail and not condition else ""))


def make_root(tmp: Path, chat_lines: int = 1) -> Path:
    root = tmp / "root"
    root.mkdir(parents=True, exist_ok=True)
    rows = [
        json.dumps({"from": "codex", "text": f"line {i}", "time": f"2026-07-31T0{i}:00:00+09:00"},
                   ensure_ascii=False)
        for i in range(chat_lines)
    ]
    (root / "peer-chat.jsonl").write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    (root / "codex-inbox-replies.jsonl").write_text("", encoding="utf-8")
    (root / "concurrent-receipts.jsonl").write_text("", encoding="utf-8")
    return root


def brief(module, root: Path, stamp: str, *, commit_cursor: bool = True) -> dict:
    return module.build_brief(
        root=root,
        workspace=str(root),
        scope="test-scope",
        updated_at_utc=stamp,
        recall_fixture=RECALL_FIXTURE,
        prospective_fixture=PROSPECTIVE_FIXTURE,
        commit_cursor=commit_cursor,
    )


def cursor_source(b: dict) -> dict:
    for source in b["sources"]:
        if source.get("kind") == "cursor":
            return source
    raise AssertionError("no cursor source entry in brief")


# --- (1) --peek --------------------------------------------------------------

def test_peek_library_level_does_not_commit(tmp: Path) -> None:
    root = make_root(tmp / "t1", chat_lines=2)
    cursor = root / "wake-cursor.json"

    first = brief(proposed, root, "2026-07-31T10:00:00+00:00", commit_cursor=False)
    check("peek/first run sees the full delta", len(first["peer_chat_new"]) == 2,
          f"got {len(first['peer_chat_new'])}")
    check("peek/no cursor file is created", not cursor.exists())

    second = brief(proposed, root, "2026-07-31T10:00:01+00:00", commit_cursor=False)
    check("peek/the same delta is still visible on the next run",
          len(second["peer_chat_new"]) == 2, f"got {len(second['peer_chat_new'])}")


def test_peek_cli_reaches_the_library_switch(tmp: Path) -> None:
    root = make_root(tmp / "t2", chat_lines=2)
    stub = tmp / "t2" / "stub_trace.py"
    stub.write_text(STUB_TRACE, encoding="utf-8")
    previous = os.environ.get("WEILAN_TRACE_SCRIPT")
    os.environ["WEILAN_TRACE_SCRIPT"] = str(stub)
    try:
        argv = ["--workspace", str(root), "--scope", "test-scope", "--root", str(root),
                "--updated-at-utc", "2026-07-31T10:00:00+00:00"]
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = proposed.main(argv + ["--peek"])
        out = json.loads(buffer.getvalue())
        check("peek/CLI --peek exits 0", rc == 0, f"rc={rc}")
        check("peek/CLI --peek leaves no cursor behind", not (root / "wake-cursor.json").exists())
        check("peek/CLI --peek reports commit not performed",
              cursor_source(out)["cursor_commit"]["performed"] is False)

        # Boundary, stated in the proposal: the DEFAULT command still consumes.
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = proposed.main(argv)
        default_out = json.loads(buffer.getvalue())
        check("peek/default CLI still commits (unchanged behaviour)",
              rc == 0 and (root / "wake-cursor.json").exists()
              and cursor_source(default_out)["cursor_commit"]["performed"] is True)
    finally:
        if previous is None:
            os.environ.pop("WEILAN_TRACE_SCRIPT", None)
        else:
            os.environ["WEILAN_TRACE_SCRIPT"] = previous


def test_negative_control_base_cli_cannot_reach_it(tmp: Path) -> None:
    root = make_root(tmp / "t3", chat_lines=1)
    result = subprocess.run(
        [sys.executable, str(BASE_PATH), "--workspace", str(root), "--scope", "s",
         "--root", str(root), "--peek"],
        capture_output=True,
    )
    check("negative control/base CLI rejects --peek (the gap was real)",
          result.returncode == 2, f"rc={result.returncode}")
    check("negative control/base CLI wrote no cursor because it never ran",
          not (root / "wake-cursor.json").exists())


# --- (2) cursor observability -------------------------------------------------

def test_cursor_before_is_the_stamp_this_call_read(tmp: Path) -> None:
    root = make_root(tmp / "t4", chat_lines=1)
    brief(proposed, root, "2026-07-31T10:00:00+00:00")
    second = brief(proposed, root, "2026-07-31T11:00:00+00:00")
    source = cursor_source(second)
    check("observability/cursor_before is the PREVIOUS stamp, not this call's",
          source["cursor_before"]["updated_at_utc"] == "2026-07-31T10:00:00+00:00",
          json.dumps(source["cursor_before"], ensure_ascii=False))
    check("observability/cursor_commit carries this call's write stamp",
          source["cursor_commit"] == {"performed": True,
                                      "updated_at_utc": "2026-07-31T11:00:00+00:00"},
          json.dumps(source["cursor_commit"], ensure_ascii=False))
    check("observability/no fabricated consumed_this_wake verdict",
          "consumed_this_wake" not in json.dumps(source))


def test_quiet_wake_vs_already_burned_becomes_distinguishable(tmp: Path) -> None:
    """The load-bearing case from the finding.

    Situation A: an accidental second run moments after the delta was consumed.
    Situation B: a genuinely quiet wake a day later.
    Both are `incremental` with an empty delta.  Under the base module the two
    briefs' cursor evidence is byte-identical; under the proposal it is not.
    """
    root_a = make_root(tmp / "t5a", chat_lines=1)
    brief(proposed, root_a, "2026-07-31T10:00:00+00:00")          # the run that consumed
    burned = brief(proposed, root_a, "2026-07-31T10:00:05+00:00")  # the accidental re-run

    root_b = make_root(tmp / "t5b", chat_lines=1)
    brief(proposed, root_b, "2026-07-30T10:00:00+00:00")           # yesterday's wake
    quiet = brief(proposed, root_b, "2026-07-31T10:00:05+00:00")   # today, nothing new

    check("distinguishability/both really are empty incremental briefs",
          burned["peer_chat_new"] == [] and quiet["peer_chat_new"] == []
          and burned["cursor_status"] == quiet["cursor_status"] == {"status": "incremental"})
    check("distinguishability/cursor_before separates them",
          cursor_source(burned)["cursor_before"]["updated_at_utc"]
          != cursor_source(quiet)["cursor_before"]["updated_at_utc"],
          "the two stamps collided")

    base_a = make_root(tmp / "t5c", chat_lines=1)
    brief(base, base_a, "2026-07-31T10:00:00+00:00")
    base_burned = brief(base, base_a, "2026-07-31T10:00:05+00:00")
    base_b = make_root(tmp / "t5d", chat_lines=1)
    brief(base, base_b, "2026-07-30T10:00:00+00:00")
    base_quiet = brief(base, base_b, "2026-07-31T10:00:05+00:00")
    # `ref` is the cursor's own path and differs only because the two fixtures
    # live in different temp roots; the question is whether anything BESIDES the
    # path tells the two situations apart.  Under the base module: nothing does.
    strip_ref = lambda source: {k: v for k, v in source.items() if k != "ref"}
    check("negative control/base module cannot separate them in-band",
          strip_ref(cursor_source(base_burned)) == strip_ref(cursor_source(base_quiet))
          == {"kind": "cursor"}
          and base_burned["cursor_status"] == base_quiet["cursor_status"],
          json.dumps(cursor_source(base_burned), ensure_ascii=False))


def test_absent_and_unreadable_cursor_are_reported_honestly(tmp: Path) -> None:
    root = make_root(tmp / "t6", chat_lines=1)
    first = brief(proposed, root, "2026-07-31T10:00:00+00:00")
    before = cursor_source(first)["cursor_before"]
    check("observability/first ever wake says file_exists=False, loaded=False",
          before["file_exists"] is False and before["loaded"] is False
          and before["updated_at_utc"] is None and before["load_reason"] == "no_cursor",
          json.dumps(before, ensure_ascii=False))

    (root / "wake-cursor.json").write_text("{not json", encoding="utf-8")
    second = brief(proposed, root, "2026-07-31T11:00:00+00:00")
    before = cursor_source(second)["cursor_before"]
    check("observability/corrupt cursor is file_exists=True but not loaded",
          before["file_exists"] is True and before["loaded"] is False
          and before["load_reason"] == "unreadable_cursor",
          json.dumps(before, ensure_ascii=False))


def test_site_fingerprint_is_not_perturbed(tmp: Path) -> None:
    """Why the fields live on the source entry and not in cursor_status."""
    # ONE root for both modules -- the source refs embed the root path, so two
    # temp dirs would differ for a reason that has nothing to do with the patch.
    # Neither comparison run commits, so they observe identical cursor state.
    root = make_root(tmp / "t7", chat_lines=3)
    stamp = "2026-07-31T10:00:00+00:00"
    b_first = brief(base, root, stamp, commit_cursor=False)
    p_first = brief(proposed, root, stamp, commit_cursor=False)
    check("conservation/fingerprint hash identical on a first wake",
          b_first["site_fingerprint"]["hash"] == p_first["site_fingerprint"]["hash"],
          f"{b_first['site_fingerprint']['hash'][:16]} vs {p_first['site_fingerprint']['hash'][:16]}")

    brief(proposed, root, stamp)  # commit, so the next pair reads a real cursor
    later = "2026-07-31T12:00:00+00:00"
    b_second = brief(base, root, later, commit_cursor=False)
    p_second = brief(proposed, root, later, commit_cursor=False)
    check("conservation/fingerprint hash identical on a quiet second wake",
          b_second["site_fingerprint"]["hash"] == p_second["site_fingerprint"]["hash"],
          f"{b_second['site_fingerprint']['hash'][:16]} vs {p_second['site_fingerprint']['hash'][:16]}")
    check("conservation/the second pair really did read a live cursor",
          cursor_source(p_second)["cursor_before"]["updated_at_utc"] == stamp
          and b_second["cursor_status"] == {"status": "incremental"})
    check("conservation/everything except the cursor source entry is unchanged",
          json.dumps({k: v for k, v in b_second.items() if k != "sources"}, sort_keys=True,
                     ensure_ascii=False)
          == json.dumps({k: v for k, v in p_second.items() if k != "sources"}, sort_keys=True,
                        ensure_ascii=False))
    check("conservation/only the cursor source entry differs",
          [s for s in b_second["sources"] if s.get("kind") != "cursor"]
          == [s for s in p_second["sources"] if s.get("kind") != "cursor"])


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="wake-peek-"))
    try:
        test_peek_library_level_does_not_commit(tmp)
        test_peek_cli_reaches_the_library_switch(tmp)
        test_negative_control_base_cli_cannot_reach_it(tmp)
        test_cursor_before_is_the_stamp_this_call_read(tmp)
        test_quiet_wake_vs_already_burned_becomes_distinguishable(tmp)
        test_absent_and_unreadable_cursor_are_reported_honestly(tmp)
        test_site_fingerprint_is_not_perturbed(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if FAILURES:
        print(f"\n{len(FAILURES)} FAIL")
        for item in FAILURES:
            print("  -", item)
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
