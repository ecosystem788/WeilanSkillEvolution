"""Read-only probe: the 2026-08-02 recurrence of the frame deadlock.

Re-derives, from live logs and live orchestration sources, the five load-bearing
facts of the 08-02 outage:

  F1  how many cron firings died at frame_open, over what wall window
  F2  how many times the only automatic rescue trigger fired in that segment
  F3  the latch expression that makes it fire at most once per failure segment
  F4  what the rescue episode did (wake-agent.log row)
  F5  which episode created the orphan head, and whether the exit path can see
      "I am leaving an open head"
  F6  whether anything in the wake path calls the frame-abandon escape hatch
      that was co-signed and deployed on 2026-07-31

Writes nothing but its own .out.json next to this file. Touches no ledger.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

IMPL = Path(r"D:\WeilanSkillEvolution\proposals\bounded-scheduler-v0.1\impl")
OUT = Path(__file__).with_suffix(".out.json")
DAY = "2026-08-02"


def decode(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "utf-16-le"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cron_segment() -> dict:
    """F1 + F2: the failure segment on DAY, counted the way the log records it."""
    lines = [l for l in decode(IMPL / "wake-cron.log").splitlines() if l.strip()]
    day = [l for l in lines if l.startswith(DAY)]
    errors = [l for l in day if " ERROR " in l]
    alerts = [l for l in day if "ALERT sentinel_failure_streak=" in l]
    done = [l for l in day if "alert wake_agent done rc=" in l]
    diags = sorted({m.group(1) for l in errors
                    for m in [re.search(r"diag_sha256=([0-9a-f]{64})", l)] if m})
    stamps = [l.split("  ", 1)[0] for l in errors]
    # physical position of the "done" line tells us when the rescue child returned
    done_pos = [lines.index(l) for l in done]
    err_pos = [(lines.index(l), l.split("  ", 1)[0]) for l in errors]
    neighbours = []
    for dp in done_pos:
        before = [s for p, s in err_pos if p < dp]
        after = [s for p, s in err_pos if p > dp]
        neighbours.append({
            "done_line": done[done_pos.index(dp)].strip(),
            "preceding_error_stamp": before[-1] if before else None,
            "following_error_stamp": after[0] if after else None,
        })
    return {
        "error_count": len(errors),
        "first_error_stamp": stamps[0] if stamps else None,
        "last_error_stamp": stamps[-1] if stamps else None,
        "distinct_diag_sha256": diags,
        "alert_lines": [l.strip() for l in alerts],
        "alert_count": len(alerts),
        "rescue_return_lines": neighbours,
    }


def latch_expression() -> dict:
    """F3: the once-per-segment latch, quoted verbatim from the live source."""
    path = IMPL / "run_wake_cron.ps1"
    text = decode(path)
    lines = text.splitlines()
    hits = {}
    for i, l in enumerate(lines, 1):
        if "streak.alerted" in l or "alerted = @(" in l:
            hits[i] = l.strip()
    # the escalation call itself: does it pass a rescue context?
    call = {}
    for i, l in enumerate(lines, 1):
        if "$WakeAgentScript" in l and "&" in l:
            call[i] = l.strip()
    return {"source": str(path), "sha256": sha256_file(path),
            "latch_lines": hits, "escalation_call_lines": call}


def rescue_param() -> dict:
    """F3b: wake_agent's rescue-takeover proof requires a context the caller never sends."""
    path = IMPL / "wake_agent.ps1"
    lines = decode(path).splitlines()
    hits = {}
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if ("param([string]$RescueContext" in s
                or "IsNullOrWhiteSpace($RescueContext)" in s
                or "$rescueAllowed = Test-RescueTakeover" in s
                or "rescue proof failed" in s):
            hits[i] = s
    return {"source": str(path), "sha256": sha256_file(path), "lines": hits}


def exit_path_blindness() -> dict:
    """F5: Get-HeadAndOpenState exists; the exit path calls only Get-Head."""
    path = IMPL / "wake_agent.ps1"
    lines = decode(path).splitlines()
    defs, calls = {}, {}
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if s.startswith("function Get-Head"):
            defs[i] = s
        if "Get-HeadAndOpenState" in s and not s.startswith("function"):
            calls.setdefault("Get-HeadAndOpenState", []).append(i)
        if re.search(r"=\s*Get-Head\b", s):
            calls.setdefault("Get-Head", []).append(i)
        if "$moved = if ($headBefore -ne $headAfter)" in s:
            calls.setdefault("moved_expression", []).append(i)
    return {"source": str(path), "function_defs": defs, "call_sites": calls}


def agent_runs() -> dict:
    """F4 + F5: the wake-agent rows around the outage."""
    lines = [l.strip() for l in decode(IMPL / "wake-agent.log").splitlines() if l.strip()]
    window = [l for l in lines if l.startswith(("2026-08-02T00", "2026-08-02T09"))]
    parsed = []
    for l in window:
        m = re.match(r"(\S+)\s+rc=(\d+)\s+(\S+)\s+turns=(\S+)\s+cost=\$?(\S+)\s+(\S+)\s+head=(\S+)", l)
        parsed.append({"raw": l} if not m else {
            "stamp": m.group(1), "rc": int(m.group(2)), "subtype": m.group(3),
            "turns": m.group(4), "cost": m.group(5), "moved": m.group(6), "head": m.group(7),
        })
    return {"rows": parsed}


def abandon_callers() -> dict:
    """F6: does any orchestration file invoke the deployed escape hatch?"""
    targets = ["wake.py", "run_wake_cron.ps1", "wake_agent.ps1",
               "run_wake_cron_hidden.vbs", "wake_codex.ps1",
               "wake_prompt.md", "wake_prompt_codex.md"]
    out = {}
    for name in targets:
        p = IMPL / name
        if not p.exists():
            out[name] = "missing"
            continue
        text = decode(p)
        out[name] = {
            "abandon_occurrences": text.lower().count("abandon"),
            "sha256": sha256_file(p),
        }
    return out


def main() -> None:
    result = {
        "probe": Path(__file__).name,
        "day": DAY,
        "read_only": True,
        "F1_F2_cron_segment": cron_segment(),
        "F3_latch": latch_expression(),
        "F3b_rescue_context": rescue_param(),
        "F4_F5_agent_runs": agent_runs(),
        "F5_exit_path": exit_path_blindness(),
        "F6_abandon_callers": abandon_callers(),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"wrote": str(OUT),
                      "errors": result["F1_F2_cron_segment"]["error_count"],
                      "alerts": result["F1_F2_cron_segment"]["alert_count"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
