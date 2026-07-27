"""Read-only: does a peer wake run show the model actually ran, or only that cron fired?

`peer_health_wake.run_check` anchors codex liveness on `max(stamp)` over
`wake-codex-runs/*.jsonl`, and `_run_stamp_as_utc` derives that stamp from the
*filename alone* -- the file is never opened.  A wake whose turn died before the
model emitted anything still lands a fresh file, so it still resets the silence
clock.  This script opens the files the sentinel does not, and reports the two
anchors side by side.

Scans newest-first and stops at the first executed run, because that run *is* the
authentic anchor -- nothing older can beat it.  Cost is therefore one full read
per failed run plus one early-exiting read, not the whole 2.7 GB corpus.

Zero authority: reads only, appends nothing, changes nothing.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _encoding_of(path: Path) -> str:
    """These runs are written UTF-16LE with a BOM; decide from the bytes, not a guess."""
    with path.open("rb") as stream:
        prefix = stream.read(2)
    if prefix == b"\xff\xfe":
        return "utf-16"
    if prefix == b"\xfe\xff":
        return "utf-16"
    return "utf-8-sig"


def classify(path: Path) -> tuple[str, str]:
    """Return (verdict, evidence) for one run file.

    executed  -- the model produced at least one non-error completed item, or the
                 turn completed.  Cron fired *and* work was possible.
    failed    -- the turn failed, or nothing but errors was ever completed.  The
                 file exists because cron fired, not because codex worked.
    unreadable-- cannot be parsed; deliberately NOT counted as executed, so a
                 damaged run can never be mistaken for a live peer.
    """
    turn_failed = None
    try:
        with path.open(encoding=_encoding_of(path)) as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    return "unreadable", f"line parse: {exc}"
                if not isinstance(row, dict):
                    return "unreadable", "row is not an object"
                kind = row.get("type")
                if kind == "turn.completed":
                    return "executed", "turn.completed"
                if kind == "item.completed":
                    item = row.get("item") or {}
                    # An error item completing is the failure being reported, not work.
                    if isinstance(item, dict) and item.get("type") != "error":
                        return "executed", f"item.completed/{item.get('type')}"
                elif kind == "turn.failed":
                    err = row.get("error") or {}
                    turn_failed = str(err.get("message", ""))[:110]
    except (OSError, UnicodeError) as exc:
        return "unreadable", f"{type(exc).__name__}: {exc}"

    if turn_failed is not None:
        return "failed", f"turn.failed: {turn_failed}"
    return "failed", "no non-error item ever completed"


def stamp_of(path: Path, local_offset_hours: float) -> datetime:
    """Mirror peer_health_wake._run_stamp_as_utc: the filename IS the timestamp."""
    parsed = datetime.strptime(path.stem, "%Y-%m-%dT%H-%M-%S")
    tz = timezone(timedelta(hours=local_offset_hours))
    return parsed.replace(tzinfo=tz).astimezone(timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", type=Path, required=True)
    # Defaults to the host clock on purpose.  An earlier revision made --now required
    # "so there is no implicit clock", and the first real invocation hand-typed a
    # timestamp 13 minutes into the future -- the exact authored-stamp disease
    # ledger-timestamp-authority-v0.1 already pinned.  Demanding a human-typed clock
    # does not create rigour, it creates a guess.  Every printed figure now says
    # which clock produced it.
    ap.add_argument(
        "--now",
        help="ISO-8601 with offset; omit to read the host clock (override is for replay only)",
    )
    ap.add_argument("--threshold-hours", type=float, default=6.0)
    ap.add_argument("--local-offset-hours", type=float, default=9.0)
    ap.add_argument(
        "--max-scan",
        type=int,
        default=400,
        help="stop after opening this many runs; a truncated scan is reported, never silently capped",
    )
    args = ap.parse_args()

    if args.now:
        now = datetime.fromisoformat(args.now)
        if now.tzinfo is None:
            raise SystemExit("--now must carry an explicit offset")
        now_authority = "authored (--now, replay)"
    else:
        now = datetime.now(timezone.utc)
        now_authority = "clock (host)"
    now = now.astimezone(timezone.utc)

    runs = sorted(args.runs_dir.glob("*.jsonl"), key=lambda p: p.stem, reverse=True)
    if not runs:
        raise SystemExit(f"no run files under {args.runs_dir}")

    scanned: list[tuple[datetime, str, str, str]] = []
    authentic: tuple[datetime, str, str, str] | None = None
    truncated = False
    for path in runs:
        if len(scanned) >= args.max_scan:
            truncated = True
            break
        verdict, evidence = classify(path)
        row = (stamp_of(path, args.local_offset_hours), path.name, verdict, evidence)
        scanned.append(row)
        if verdict == "executed":
            authentic = row
            break

    for stamp, name, verdict, evidence in scanned:
        print(f"{name}  {verdict:<10} {evidence}")

    # As shipped the anchor is max(stamp) over every file, opened or not.
    newest = stamp_of(runs[0], args.local_offset_hours)
    cur_h = (now - newest).total_seconds() / 3600
    cur_raises = cur_h > args.threshold_hours

    print()
    print(f"now                  {now.isoformat()}   authority={now_authority}")
    failed_n = sum(1 for r in scanned if r[2] != "executed")
    print(f"runs on disk         {len(runs)}   opened={len(scanned)}   failed among opened={failed_n}")
    print(f"anchor AS SHIPPED    {runs[0].name}  (filename only, contents never read)")
    print(f"  silence            {cur_h:.2f}h    raises at >{args.threshold_hours}h -> {cur_raises}")

    if authentic is None:
        floor = (now - scanned[-1][0]).total_seconds() / 3600
        note = " (scan truncated -- true silence is at least this)" if truncated else ""
        print(f"anchor IF AUTHENTIC  none in the {len(scanned)} newest runs{note}")
        print(f"  silence            >= {floor:.2f}h   raises at >{args.threshold_hours}h -> True")
        auth_raises = True
    else:
        auth_h = (now - authentic[0]).total_seconds() / 3600
        auth_raises = auth_h > args.threshold_hours
        print(f"anchor IF AUTHENTIC  {authentic[1]}  ({authentic[3]})")
        print(f"  silence            {auth_h:.2f}h    raises at >{args.threshold_hours}h -> {auth_raises}")

    print()
    if auth_raises != cur_raises:
        print("DIVERGENCE  YES -- the sentinel reports a live peer that has not run a single turn.")
    else:
        print("DIVERGENCE  no -- both anchors agree at this threshold right now.")

    # The divergence is not the load-bearing claim; reachability is.  As shipped the
    # anchor is refreshed by cron, not by codex, so its silence is bounded above by
    # the cron gap.  If that bound is under the threshold the raise is unreachable --
    # the sentinel cannot report this outage however long it lasts.
    if len(scanned) >= 2:
        gaps = [
            (scanned[i][0] - scanned[i + 1][0]).total_seconds() / 3600
            for i in range(len(scanned) - 1)
        ]
        worst_gap = max(gaps)
        print()
        print(f"cron gap among opened runs   max={worst_gap:.2f}h  (n={len(gaps)})")
        print(f"shipped anchor silence is bounded by that gap -> <= {worst_gap:.2f}h")
        if worst_gap <= args.threshold_hours:
            print(
                f"REACHABILITY  the >{args.threshold_hours}h raise is UNREACHABLE while cron keeps firing:"
                "\n              each failed wake lands a fresh file and resets the clock,"
                "\n              so this outage can never be reported no matter how long it runs."
            )
        else:
            print("REACHABILITY  cron is slower than the threshold; the raise stays reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
