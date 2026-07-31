"""Read-only review probe: does the new fail-loud guard reclassify benign small skew?

Writes nothing outside a throwaway temp dir. Delete after use.
"""
import sys
import tempfile
from datetime import timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import test_peer_health_wake as T
from peer_health_wake import run_check

NOW = T.NOW
LOCAL = timezone(timedelta(hours=9))


def local(dt):
    return dt.astimezone(LOCAL).strftime("%Y-%m-%d %H:%M:%S")


def probe(label, activity_time):
    d = Path(tempfile.mkdtemp())
    T.fixture(d, activity_time=activity_time)
    r = run_check(root=d, now=NOW)
    kinds = [e.get("kind") or e.get("event") for e in r]
    print(f"{label}: appended={kinds} anomaly={bool(r.clock_anomaly)} anchor={r.activity_anchor['time_utc'] if r.activity_anchor else None}")
    return r


# A) the fixture that test_small_future_activity_is_fresh_end_to_end pins
probe("A 5-min-future  ", local(NOW + timedelta(minutes=5)))
# B) 1-second future skew
probe("B 1-sec-future  ", local(NOW + timedelta(seconds=1)))
# C) control: 25h-past anchor, the classic silent-pending raise case
probe("C 25h-past      ", local(NOW - timedelta(hours=25)))
# D) fresh past anchor
probe("D 1h-past       ", local(NOW - timedelta(hours=1)))
