"""Re-runnable, read-only probe for FINDING.md in this directory.

Question: in the append-only ledgers, is the `time` field read from the host
clock, or typed from a model's guess? And does the difference reach anything
load-bearing?

Writes nothing. Run:
    python proposals/ledger-timestamp-authority-v0.1/probe_timestamp_authority.py
"""
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IMPL = REPO / "proposals" / "bounded-scheduler-v0.1" / "impl"
MUTUAL_AID = REPO / "proposals" / "mutual-aid-v0.1"

FILES = ("peer-chat.jsonl", "owner-inbox.jsonl", "owner-inbox-replies.jsonl",
         "codex-inbox.jsonl", "codex-inbox-replies.jsonl")
IMPLIED_AUTHOR = {"owner-inbox.jsonl": "owner", "owner-inbox-replies.jsonl": "claude"}


def parse_t(s):
    try:
        return datetime.strptime((s or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def load():
    rows, unparseable = [], 0
    for name in FILES:
        path = IMPL / name
        if not path.exists():
            continue
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                unparseable += 1          # known escape damage, corrected out-of-band
                continue
            t = parse_t(obj.get("time"))
            if t:
                rows.append((name, line_no, obj.get("from") or IMPLIED_AUTHOR.get(name, "?"), t))
    return rows, unparseable


def section(title):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


rows, unparseable = load()
print(f"parsed {len(rows)} timestamped lines across {len(FILES)} ledgers "
      f"({unparseable} unparseable, known escape damage)")

# --- 1. append order vs claimed time ------------------------------------------
section("1. append-order vs claimed-time inversions")
print("A ledger is append-only and every author shares one host. If every stamp\n"
      "were read from that clock, a line could never claim a time earlier than\n"
      "the line already above it.")
inv_by_author, tot_by_author = defaultdict(int), defaultdict(int)
back_steps = []
for name in FILES:
    prev = None
    for r in [x for x in rows if x[0] == name]:
        tot_by_author[r[2]] += 1
        if prev and r[3] < prev[3]:
            inv_by_author[r[2]] += 1
            back_steps.append((prev[3] - r[3]).total_seconds() / 3600.0)
        prev = r

# --- 2. the :00-seconds fingerprint -------------------------------------------
zero_sec = defaultdict(int)
for _, _, who, t in rows:
    if t.second == 0:
        zero_sec[who] += 1

print("\nauthor   lines   inversions        seconds==:00 (chance 1/60 = 1.7%)")
for who in sorted(tot_by_author, key=lambda w: -tot_by_author[w]):
    n = tot_by_author[who]
    print(f"{who:>7} {n:>7} {inv_by_author[who]:>6} ({inv_by_author[who] / n:5.1%})"
          f"   {zero_sec[who]:>5} ({zero_sec[who] / n:5.1%})")
print("\nA clock read at arbitrary moments lands on :00 about 1.7% of the time.\n"
      "A materially higher rate is the fingerprint of a hand-typed stamp.")

section("2. distribution of back-steps")
buckets = Counter()
for h in back_steps:
    buckets["<1h" if h < 1 else "1-8h" if h < 8 else "8-10h (JST/UTC band)"
            if h < 10 else "10-18h" if h < 18 else ">=18h"] += 1
for k in ("<1h", "1-8h", "8-10h (JST/UTC band)", "10-18h", ">=18h"):
    n = buckets.get(k, 0)
    print(f"  {k:>22}: {n:>4} ({n / len(back_steps):5.1%})" if back_steps else "")
if back_steps:
    print(f"\n  median back-step: {sorted(back_steps)[len(back_steps) // 2]:.2f}h")
    print("  The <1h mass is drift/guessing; the 8-10h band is JST<->UTC confusion.")

# --- 3. does it reach anything load-bearing? ----------------------------------
section("3. live effect on the peer-liveness sentinel")
sys.path.insert(0, str(MUTUAL_AID))
try:
    import peer_health_wake as ph
except Exception as exc:                                    # pragma: no cover
    print(f"  skipped: cannot import peer_health_wake ({exc})")
    raise SystemExit(0)

parse_errors, known_corrected = [], []
corrections_path = IMPL / "peer-chat.corrections.jsonl"
corrections = ph._rows(corrections_path, parse_errors=parse_errors)
now = datetime.now(timezone.utc)
# `now_utc` became a required argument when the v0.1 fix landed (8114b1d): the
# anchor itself now needs to know "now" in order to drop future authored
# candidates.  This probe crashed with TypeError until 2026-07-26 because of it.
anchor = ph._claude_activity_anchor(
    IMPL, parse_errors, known_corrected, corrections, corrections_path, now
)
if anchor is None:
    print("  no anchor available")
    raise SystemExit(0)

last_activity, source_ref = anchor


def anchor_provenance(ref):
    """Who stamped the anchor?  Three classes, not two.

    A two-way `runs-or-not` split was wrong: it called every ledger anchor
    hand-written, including lines the append helper itself clock-stamped.
    `peer_health_wake` already layers `time_authority == "clock"` above
    authored/unknown (:206, :218) -- this reads the same layer rather than
    guessing from the filename.  Note `clock` attests *origin* (read off the
    host clock, not typed by a model), never accuracy.
    """
    if ph.CLAUDE_ACTIVITY_RUNS in ref:
        return "tool-generated run"
    name, _, line_no = ref.split("@", 1)[0].rpartition(":")
    if not name or not line_no.isdigit():
        return "authored/unknown ledger (source ref not recognised)"
    per_file = {"peer-chat.jsonl": dict(corrections=corrections,
                                        corrections_path=corrections_path)}
    row = dict(ph._rows(IMPL / name, parse_errors=[], known_corrected=[],
                        **per_file.get(name, {}))).get(int(line_no))
    if row is None:
        return "authored/unknown ledger (line not re-readable)"
    if row.get("time_authority") == "clock":
        return "clock-authority ledger"
    return "authored/unknown ledger"


print(f"  anchor chosen by max() : {last_activity.isoformat()}")
print(f"  anchor source          : {source_ref}")
print(f"  anchor provenance      : {anchor_provenance(source_ref)}")
print(f"  host clock (utc)       : {now.isoformat(timespec='seconds')}")
print(f"  anchor - now           : {(last_activity - now).total_seconds() / 3600:+.3f} h")

runs = [(ph._run_stamp_as_utc(p), p.name) for p in (IMPL / ph.CLAUDE_ACTIVITY_RUNS).glob("*.json")]
if runs:
    newest = max(runs)
    print(f"  newest tool-stamped run: {newest[0].isoformat()}  ({newest[1]})")

suppressed = last_activity > now
print(f"\n  clock_anomaly branch taken -> sentinel SUPPRESSED: {suppressed}")
print("  BEFORE the v0.1 fix (8114b1d) this section was the live wound: a hand-typed\n"
      "  future stamp outranked the tool-stamped run in max(), won the anchor, tripped\n"
      "  the future guard, and the liveness check returned without ever measuring\n"
      "  silence.  FINDING.md section 3 records that run verbatim.  AFTER the fix a\n"
      "  future *authored* candidate is dropped and the tool-stamped run anchor is used\n"
      "  instead, so this section can no longer reproduce the wound from the live\n"
      "  ledger -- it can only show which kind of stamp currently holds the anchor.\n"
      "  The injection-level regression witnesses live in the test suite:\n"
      "  test_reverse_latest_future_authored_append_falls_back_to_run_anchor and\n"
      "  test_reverse_backfilled_authored_append_cannot_displace_run_anchor\n"
      "  (proposals/mutual-aid-v0.1/test_peer_health_wake.py).")
