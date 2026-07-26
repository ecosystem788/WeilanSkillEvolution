"""Read-only probe: can one hand-written number still silence the forward sentinel?

Companion to probe_timestamp_authority.py.  It was written to *expose* the wound in
the forward (claude->codex) check -- the one Claude runs at every wake.  Before the
v0.2 fix (8114b1d), `run_check` anchored only on hand-written `time` in ACTIVITY_FILES
while the 1700+ tool-stamped `wake-codex-runs/*.jsonl` files sat unused in that path,
so appending a single invented future stamp cancelled an alert that was otherwise
raised.  FINDING.md section 4 records that output verbatim.

Since the fix it is a *regression witness* instead: the tool-stamped run names are
forward anchor candidates, future authored candidates are dropped rather than allowed
to return the whole check, and all three scenarios below therefore agree.  The final
line is the one to read -- it must stay False.

Nothing in the repository is mutated: every scenario runs against a throwaway copy in
the system temp directory.  Run:

    python proposals/ledger-timestamp-authority-v0.1/probe_forward_asymmetry.py
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IMPL = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl"
MUTUAL_AID = REPO / "proposals" / "mutual-aid-v0.1"

sys.path.insert(0, str(MUTUAL_AID))
import peer_health_wake as ph  # noqa: E402

LEDGERS = (
    "peer-chat.jsonl",
    "codex-inbox-replies.jsonl",
    "codex-inbox.jsonl",
    "peer-health-alerts.jsonl",
    "concurrent-receipts.jsonl",
    "peer-chat.corrections.jsonl",
)

# A silence long enough to cross run_check's 6h default, plus a genuinely pending
# delegation -- both are required before the forward check will raise at all.
NOW = datetime(2026, 7, 26, 14, 0, 0, tzinfo=timezone.utc)
PENDING = {"id": "probe00000001", "time": "2026-07-26 09:30:00", "from": "claude", "text": "probe"}
FUTURE_LINE = {"from": "codex", "time": "2026-07-27 09:00:00", "text": "probe: hand-written future stamp"}
BACKFILLED_LINE = {"from": "codex", "time": "2026-07-26 00:04:29", "text": "probe: hand-written 9h backfill"}


def _sandbox(*, extra_chat: dict | None = None, pending: bool = True) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="weilan-probe-"))
    for name in LEDGERS:
        source = IMPL / name
        if source.exists():
            shutil.copy2(source, tmp / name)
    runs = tmp / ph.CODEX_HEARTBEAT_RUNS
    runs.mkdir(exist_ok=True)
    for path in (IMPL / ph.CODEX_HEARTBEAT_RUNS).glob("*.jsonl"):
        shutil.copy2(path, runs / path.name)
    if pending:
        with (tmp / "codex-inbox.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(PENDING, ensure_ascii=False) + "\n")
    if extra_chat is not None:
        with (tmp / "peer-chat.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(extra_chat, ensure_ascii=False) + "\n")
    return tmp


def _forward(**kwargs) -> tuple[list[str], dict | None, dict | None]:
    tmp = _sandbox(**kwargs)
    try:
        result = ph.run_check(root=tmp, now=NOW)
        events = [f"{row.get('event')}/{row.get('kind')}" for row in result]
        return events, result.clock_anomaly, result.activity_anchor
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    tool_runs = len(list((IMPL / ph.CODEX_HEARTBEAT_RUNS).glob("*.jsonl")))
    print(f"host clock (utc)          : {datetime.now(timezone.utc).isoformat()}")
    print(f"simulated now (utc)       : {NOW.isoformat()}")
    print(f"tool-stamped codex runs   : {tool_runs} files in {ph.CODEX_HEARTBEAT_RUNS}/")
    print(f"forward anchor sources    : {', '.join(ph.ACTIVITY_FILES)}  <- hand-written `time`")
    print(f"                          : {ph.CODEX_HEARTBEAT_RUNS}/  <- tool-stamped file names")
    print()

    baseline, anomaly, anchor = _forward()
    print("1) baseline (no injected line)")
    print(f"   anchor    : {anchor and anchor['source_ref']}")
    print(f"   appended  : {baseline}   anomaly={bool(anomaly)}")

    suppressed, anomaly, anchor = _forward(extra_chat=FUTURE_LINE)
    print("2) one hand-written FUTURE codex stamp appended")
    print(f"   anchor    : {anchor and anchor['source_ref']}")
    print(f"   appended  : {suppressed}   anomaly={bool(anomaly)}")
    if anomaly:
        print(f"   delta_h   : {anomaly['future_delta_hours']}")

    backfilled, anomaly, anchor = _forward(extra_chat=BACKFILLED_LINE)
    print("3) one hand-written BACKFILLED codex stamp appended (control)")
    print(f"   anchor    : {anchor and anchor['source_ref']}")
    print(f"   appended  : {backfilled}   anomaly={bool(anomaly)}")

    print()
    print(f"forward sentinel silenced by a single hand-written number: {bool(baseline) and not suppressed}")
    print("  This printed True before the v0.2 fix (8114b1d) and must stay False.  The")
    print("  degraded mode that makes it False is visible in the anchors above: all three")
    print("  scenarios fall back to a tool-stamped wake-codex-runs/ file name, so neither")
    print("  the invented future stamp (2) nor the backfilled one (3) moves the anchor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
