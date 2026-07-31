"""Read-only census: are there real frame_abandoned TERMINAL events in the live ledger,
and would a v3 "unmet_obligations must equal re-derived" gate reject them?

Read-only. Touches nothing. Run:
  python _probe_20260731_abandoned_census.py
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(r"D:\CodexData\home\method-state\frames")

TERMINAL = {"frame_closed", "frame_abandoned", "frame_blocked"}


def derive_unmet(events):
    """Mirror of the two require_closed obligation rules in validate_events
    (weilan_trace.py:1150-1164), as a machine-shaped list."""
    types = [e.get("event_type") for e in events]
    unmet = []
    if "minimal_unit_collapsed" in types:
        ci = types.index("minimal_unit_collapsed")
        ti = [i for i, t in enumerate(types) if t == "trace_emitted"]
        if not ti or max(ti) < ci:
            unmet.append({"rule": "collapse_requires_following_trace",
                          "event_id": events[ci].get("event_id")})
    for pi, t in enumerate(types):
        if t != "holder_probation_started":
            continue
        res = {"discriminating_test_executed", "minimal_unit_collapsed", "frame_blocked"}
        if not any(c in res for c in types[pi + 1:]):
            unmet.append({"rule": "probation_requires_resolution",
                          "event_id": events[pi].get("event_id")})
    return unmet


def main():
    hits = []
    for path in sorted(ROOT.rglob("*.jsonl")):
        try:
            events = [json.loads(line) for line in
                      path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception as exc:
            print(f"UNPARSED {path.name}: {exc}")
            continue
        abandoned = [e for e in events if e.get("event_type") == "frame_abandoned"]
        if not abandoned:
            continue
        ev = abandoned[-1]
        pre = events[:events.index(ev)]
        hits.append({
            "frame_id": path.stem,
            "is_terminal_last": events[-1].get("event_type") == "frame_abandoned",
            "event_types": [e.get("event_type") for e in events],
            "data_keys": sorted(ev.get("data", {}).keys()),
            "has_unmet_obligations_field": "unmet_obligations" in ev.get("data", {}),
            "v3_would_derive": derive_unmet(pre + [ev]),
        })

    print(json.dumps({
        "frames_with_frame_abandoned_event": len(hits),
        "detail": hits,
    }, ensure_ascii=False, indent=2))

    # The load-bearing question for the v3 gate:
    rejected = [h for h in hits if not h["has_unmet_obligations_field"]]
    print("\n--- v3 byte-equality gate impact ---")
    print(f"v2-era abandoned frames lacking the field: {len(rejected)}")
    for h in rejected:
        print(f"  {h['frame_id']}: v3 would derive {h['v3_would_derive']!r} "
              f"but stored field is absent -> mismatch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
