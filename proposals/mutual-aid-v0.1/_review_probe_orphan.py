"""Read-only review probe: is an orphan_frame incident still appended on the clock_anomaly path?

Writes nothing outside a throwaway temp dir. Delete after use.
"""
import sys
import tempfile
from datetime import timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import test_peer_health_wake as T
from peer_health_wake import ORPHAN_STREAK_MINIMUM, run_check

NOW = T.NOW
LOCAL = timezone(timedelta(hours=9))
PARENT = "wf-20260712-000000-abcdef"


def local(dt):
    return dt.astimezone(LOCAL).strftime("%Y-%m-%d %H:%M:%S")


def probe(label, activity_time):
    d = Path(tempfile.mkdtemp())
    T.fixture(d, activity_time=activity_time)
    T.write_cron(d, [T.cron_line(f"2026-07-12T0{i}:00:00", PARENT) for i in range(ORPHAN_STREAK_MINIMUM)])
    r = run_check(root=d, now=NOW)
    print(f"{label}: appended={[e.get('kind') for e in r]} anomaly={bool(r.clock_anomaly)} "
          f"alerts_file_rows={len(T.alerts(d))}")


print(f"ORPHAN_STREAK_MINIMUM={ORPHAN_STREAK_MINIMUM}")
probe("future anchor + orphan streak", local(NOW + timedelta(hours=9)))
probe("past anchor   + orphan streak", local(NOW - timedelta(hours=1)))
