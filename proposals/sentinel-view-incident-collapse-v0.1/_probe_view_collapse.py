import json, hashlib, sys
from pathlib import Path

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
ALERTS = IMPL / "peer-health-alerts.jsonl"
OPEN_EVENTS = {"raised", "reopened"}

rows = [json.loads(l) for l in ALERTS.read_text(encoding="utf-8").splitlines() if l.strip()]

# Current (buggy) derivation, mirroring peer_health.py:209
current_active = [r for r in rows if r.get("event") in OPEN_EVENTS]

# Proposed derivation: collapse by incident_key to LAST event (physical order), then filter OPEN_EVENTS
by_key = {}
for r in rows:
    by_key[r.get("incident_key", r.get("id", "?"))] = r
proposed_active = [r for r in by_key.values() if r.get("event") in OPEN_EVENTS]

# Proposed rendering for rows without silence
def render(a):
    key = a.get("incident_key", "?")
    evt = a.get("event", "?")
    aid = a.get("id", "?")
    if "silence" in a:
        sh = a["silence"].get("silence_hours", "?")
        extra = f"silence={sh}h"
    elif "consecutive_count" in a:
        extra = f"count={a.get('consecutive_count')}, last_error={a.get('last_error_time')}"
    else:
        extra = "silence=?h"
    return f"- **{key}** ({evt}): {extra}, id={aid}"

out = {
    "rows_total": len(rows),
    "current_active_count": len(current_active),
    "current_active_keys": [r.get("incident_key") for r in current_active],
    "proposed_active_count": len(proposed_active),
    "proposed_active_keys": [r.get("incident_key") for r in proposed_active],
    "proposed_view_lines": [render(a) for a in proposed_active],
}
print(json.dumps(out, ensure_ascii=False, indent=2))
