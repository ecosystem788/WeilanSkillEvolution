"""Read-only probe: does wake_brief.prospective_due() ever return anything on live shapes?

Claim under test (2026-07-31, organ-fusion direction):
  wake_brief's `prospective_due` is the wake procedure's second-highest-priority
  work selector (only the owner mic outranks it).  This probe measures whether it
  can structurally ever be non-empty against the shape `weilan_trace.py
  prospective-show` actually emits.

Everything here is read-only:
  - imports the live wake_brief module and calls its pure function directly
  - runs `prospective-show` (a read command) once, against the real scope
  - never writes to any ledger, never calls wake_brief.build_brief (which would
    burn the wake cursor delta -- see memory note wake-brief-cursor-burns-delta)

Usage:  python _probe_20260731_prospective_due_shape.py [--out FILE]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_SCRIPTS = Path(r"C:/Users/zy/.claude/skills/solve-with-weilan/scripts")
WAKE_BRIEF = SKILL_SCRIPTS / "wake_brief.py"
TRACE = SKILL_SCRIPTS / "weilan_trace.py"
WORKSPACE = r"D:\WeilanSkillEvolution"
SCOPE = "skill-evolution"
REPO_TEST = Path(
    r"D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl/test_wake_brief.py"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_prospective_show() -> dict:
    out = subprocess.check_output(
        [
            sys.executable,
            str(TRACE),
            "prospective-show",
            "--workspace",
            WORKSPACE,
            "--scope",
            SCOPE,
        ],
        text=True,
        encoding="utf-8",
    )
    return json.loads(out)


def describe_shape(raw: dict) -> dict:
    goals = raw.get("goals")
    causal = raw.get("causal_events")
    sample_goal = None
    if isinstance(goals, dict) and goals:
        sample_goal = next(iter(goals.values()))
    elif isinstance(goals, list) and goals:
        sample_goal = goals[0]
    sample_event = None
    if isinstance(causal, dict) and causal:
        sample_event = next(iter(causal.values()))
    elif isinstance(causal, list) and causal:
        sample_event = causal[0]
    return {
        "top_level_keys": sorted(raw.keys()),
        "goals_type": type(goals).__name__,
        "goals_count": len(goals) if hasattr(goals, "__len__") else None,
        "causal_events_type": type(causal).__name__,
        "causal_events_count": len(causal) if hasattr(causal, "__len__") else None,
        "goal_keys": sorted(sample_goal.keys()) if isinstance(sample_goal, dict) else None,
        "goal_has_causal_events_key": (
            "causal_events" in sample_goal if isinstance(sample_goal, dict) else None
        ),
        "goal_has_top_level_not_before": (
            ("not_before" in sample_goal or "not_before_utc" in sample_goal)
            if isinstance(sample_goal, dict)
            else None
        ),
        "goal_not_before_location": (
            "condition.not_before_utc"
            if isinstance(sample_goal, dict)
            and isinstance(sample_goal.get("condition"), dict)
            and "not_before_utc" in sample_goal["condition"]
            else "unknown"
        ),
        "causal_event_keys": (
            sorted(sample_event.keys()) if isinstance(sample_event, dict) else None
        ),
        "causal_event_has_state_or_status": (
            ("state" in sample_event or "status" in sample_event)
            if isinstance(sample_event, dict)
            else None
        ),
    }


def goals_as_list(raw: dict) -> list:
    goals = raw.get("goals")
    if isinstance(goals, dict):
        return [g for g in goals.values() if isinstance(g, dict)]
    if isinstance(goals, list):
        return [g for g in goals if isinstance(g, dict)]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    now = datetime.now(timezone.utc).isoformat()
    wb = load_module(WAKE_BRIEF, "wake_brief_probe")

    raw = run_prospective_show()
    shape = describe_shape(raw)

    result: dict = {
        "probe": "prospective_due_shape_drift",
        "generated_at_utc": now,
        "live_wake_brief_sha256": sha256_file(WAKE_BRIEF),
        "live_weilan_trace_sha256": sha256_file(TRACE),
        "workspace": WORKSPACE,
        "scope": SCOPE,
        "live_prospective_show_shape": shape,
    }

    # --- layer 0: the live path, exactly as the wake procedure runs it ---
    live_due = wb.prospective_due(raw, now)
    extracted = wb._prospective_goals(raw)
    result["layer0_live"] = {
        "prospective_due_len": len(live_due),
        "goals_extracted_by_wake_brief": len(extracted),
        "note": "_prospective_goals only accepts raw['goals'] when it is a list",
    }

    # --- census: what would a correct reader have surfaced? ---
    all_goals = goals_as_list(raw)
    active = [g for g in all_goals if str(g.get("state", "")).upper() == "ACTIVE"]
    now_dt = datetime.fromisoformat(now)
    ripe = []
    for g in active:
        nb = (g.get("condition") or {}).get("not_before_utc")
        if nb is None:
            ripe.append(g)
            continue
        try:
            nb_dt = datetime.fromisoformat(nb)
        except ValueError:
            continue
        if nb_dt.tzinfo is None:
            nb_dt = nb_dt.replace(tzinfo=timezone.utc)
        if nb_dt <= now_dt:
            ripe.append(g)
    # which ripe goals also have an observed causal event on their event_name?
    causal = raw.get("causal_events")
    observed_names = set()
    events = causal.values() if isinstance(causal, dict) else (causal or [])
    for e in events:
        if isinstance(e, dict) and e.get("event_name"):
            observed_names.add(e["event_name"])
    with_observed = [
        g
        for g in ripe
        if (g.get("condition") or {}).get("event_name") in observed_names
    ]
    result["census_dropped"] = {
        "goals_total": len(all_goals),
        "active": len(active),
        "active_and_not_before_reached": len(ripe),
        "active_ripe_with_observed_causal_event": len(with_observed),
        "ripe_goal_refs": [g.get("goal_ref") for g in ripe],
        "ripe_with_observed_goal_refs": [g.get("goal_ref") for g in with_observed],
    }

    # --- layer isolation: fix one mismatch at a time, see if output changes ---
    layers: dict = {}

    fix1 = dict(raw)
    fix1["goals"] = goals_as_list(raw)
    layers["fix1_goals_dict_to_list"] = len(wb.prospective_due(fix1, now))

    fix2 = dict(fix1)
    fix2["goals"] = [
        {**g, "not_before": (g.get("condition") or {}).get("not_before_utc")}
        for g in fix1["goals"]
    ]
    layers["fix2_plus_not_before_lifted"] = len(wb.prospective_due(fix2, now))

    fix3 = dict(fix2)
    fix3["goals"] = [
        {
            **g,
            "causal_events": [
                {**e, "state": "READY"}
                for e in events
                if isinstance(e, dict)
                and e.get("event_name") == (g.get("condition") or {}).get("event_name")
            ],
        }
        for g in fix2["goals"]
    ]
    fix3_due = wb.prospective_due(fix3, now)
    layers["fix3_plus_causal_events_attached_with_state"] = len(fix3_due)
    layers["fix3_due_with_ready_events"] = len(
        [g for g in fix3_due if g.get("causal_events")]
    )
    result["layer_isolation"] = layers

    # --- the fixture that keeps this green in CI ---
    fixture_shape = None
    if REPO_TEST.exists():
        src = REPO_TEST.read_text(encoding="utf-8")
        spec = importlib.util.spec_from_file_location("wb_test_probe", REPO_TEST)
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(REPO_TEST.parent))
        try:
            spec.loader.exec_module(mod)
            fx = mod.fixture_prospective()
            fixture_shape = describe_shape(fx)
            fixture_shape["prospective_due_len_on_fixture"] = len(
                wb.prospective_due(fx, "2026-07-10T09:30:00+00:00")
            )
        except Exception as exc:  # pragma: no cover - diagnostic only
            fixture_shape = {"error": repr(exc)}
        finally:
            sys.path.pop(0)
        result["repo_test_sha256"] = hashlib.sha256(
            REPO_TEST.read_bytes()
        ).hexdigest()
        result["repo_test_has_live_shape_case"] = ('"goals": {' in src)
    result["fixture_shape"] = fixture_shape

    # --- exposure: how many wakes ran with this selector in place? ---
    # wake_brief was deployed 2026-07-10 (wake_prompt.md step 1.5).
    exposure: dict = {"deployed_on": "2026-07-10", "run_dirs": {}}
    for label, d, run_suffix in (
        (
            "wake-agent-runs",
            Path(r"D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl/wake-agent-runs"),
            ".json",
        ),
        (
            "wake-codex-runs",
            Path(r"D:/WeilanSkillEvolution/proposals/bounded-scheduler-v0.1/impl/wake-codex-runs"),
            ".jsonl",
        ),
    ):
        if not d.is_dir():
            exposure["run_dirs"][label] = {"exists": False}
            continue
        names = [p.name for p in d.iterdir() if p.is_file()]
        # one run == one <timestamp><run_suffix>; agent runs also emit a sibling .err.txt
        runs = [n for n in names if n.endswith(run_suffix) and not n.endswith(".err.txt")]
        # run files are named by ISO-ish timestamp prefix, e.g. 2026-07-31T21-57-07.jsonl
        since = [n for n in runs if n[:10] >= "2026-07-10"]
        exposure["run_dirs"][label] = {
            "exists": True,
            "files_total": len(names),
            "runs_total": len(runs),
            "runs_named_on_or_after_2026_07_10": len(since),
            "earliest_run_name": min(runs) if runs else None,
            "naming_note": "prefix-lexical compare on the filename date; not a clock authority claim",
        }

    # every wake_brief.py copy on disk, to test 'born broken' vs 'drifted'
    copies: dict = {}
    walk_errors = 0

    def _on_error(_exc):  # long paths (>MAX_PATH) exist in this repo; skip, count
        nonlocal walk_errors
        walk_errors += 1

    found: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(
        r"D:/WeilanSkillEvolution", onerror=_on_error
    ):
        if "wake_brief.py" in filenames:
            found.append(Path(dirpath) / "wake_brief.py")
    for p in found:
        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue
        h = sha256_file(p)
        # isolate the _prospective_goals function body, not the whole file
        body = ""
        if "def _prospective_goals" in src:
            body = src.split("def _prospective_goals", 1)[1].split("\ndef ", 1)[0]
        entry = copies.setdefault(
            h,
            {
                "has_prospective_goals_fn": bool(body),
                "extractor_accepts_list": "isinstance(value, list)" in body,
                "extractor_accepts_dict": "isinstance(value, dict)" in body
                or ".values()" in body,
                "paths": 0,
            },
        )
        entry["paths"] += 1
    exposure["wake_brief_variants_on_disk"] = {
        "distinct_sha256": len(copies),
        "all_define_prospective_goals": all(v["has_prospective_goals_fn"] for v in copies.values()),
        "variants_whose_extractor_accepts_list": sum(
            1 for v in copies.values() if v["extractor_accepts_list"]
        ),
        "variants_whose_extractor_accepts_dict": sum(
            1 for v in copies.values() if v["extractor_accepts_dict"]
        ),
    }
    exposure["wake_brief_variants_on_disk"]["walk_errors_skipped"] = walk_errors
    exposure["wake_brief_variants_on_disk"]["copies_found"] = len(found)
    exposure["live_sha256_among_them"] = sha256_file(WAKE_BRIEF) in copies
    result["exposure"] = exposure

    # --- downstream consumer of the empty list ---
    result["downstream"] = {
        "prospective_has_due_line": "wake_brief.py:508",
        "note": "site_fingerprint reports prospective_has_due=bool(prospective_due)",
        "site_fingerprint_prospective_has_due": None,
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
