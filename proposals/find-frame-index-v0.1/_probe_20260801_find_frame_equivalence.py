"""Read-only: behavioural equivalence between the frozen baseline's find_frame and
the frozen candidate's find_frame.

This is the load-bearing evidence for the change. The regression test file cannot
supply it: that file calls invalidate_frame_index(), which does not exist on the
baseline, so on the baseline every one of its tests ERRORs at fixture setup. An
all-ERROR run proves the API is absent, not that any behaviour differs. Here we
drive *identical* scenarios through both implementations and compare outcomes.

Each scenario runs in its own subprocess with its own temp method-state, so the
two implementations never share a process or a fixture. Emits JSON to stdout.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

BASE = "ae0537dab5c050c9c1fadf7d432eaa39fa34449ba4420dd879f13068d0b142ad"
CAND = "794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b"
HERE = os.path.dirname(os.path.abspath(__file__))

SCENARIOS = [
    "plain_hit",
    "missing_id",
    "duplicate_id",
    "empty_frame_file_only",
    "empty_and_live_same_id",
    "moved_after_first_lookup",
    "deleted_after_first_lookup",
    "appended_by_this_process_after_first_lookup",
    "foreign_second_file_after_first_lookup",
]


def write_frame(frames_root, date_dir, frame_id, events=1):
    directory = os.path.join(frames_root, date_dir)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, frame_id + ".jsonl")
    body = "".join(
        '{"schema_version": "x", "event_id": "e%d", "frame_id": "%s", '
        '"timestamp_utc": "2026-08-01T00:00:00+00:00", "event_type": "frame_opened", '
        '"level": "L2", "workspace": "W", "data": {}}\n' % (index, frame_id)
        for index in range(events)
    )
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(body)
    return path


def attempt(module, frames_root, frame_id):
    """Return a comparable outcome: exception class name, or the frames-relative path."""
    try:
        found = module.find_frame(frame_id)
    except Exception as exc:  # noqa: BLE001 -- the class name is the observation
        return {"outcome": type(exc).__name__}
    return {"outcome": "path", "path": os.path.relpath(str(found), frames_root).replace(os.sep, "/")}


def run_scenario(scenario, method_home):
    sys.path.insert(0, os.environ["WEILAN_PROBE_SCRIPTS"])
    os.environ["WEILAN_METHOD_HOME"] = method_home
    import weilan_trace  # noqa: E402 -- must follow the sys.path/env setup

    frames_root = os.path.join(method_home, "frames")
    os.makedirs(frames_root, exist_ok=True)
    steps = []

    if scenario == "plain_hit":
        write_frame(frames_root, "2026-07-20", "wf-a")
        write_frame(frames_root, "2026-07-21", "wf-b")
        steps.append(attempt(weilan_trace, frames_root, "wf-b"))
        steps.append(attempt(weilan_trace, frames_root, "wf-a"))
    elif scenario == "missing_id":
        write_frame(frames_root, "2026-07-20", "wf-a")
        steps.append(attempt(weilan_trace, frames_root, "wf-absent"))
        steps.append(attempt(weilan_trace, frames_root, "wf-absent"))
    elif scenario == "duplicate_id":
        write_frame(frames_root, "2026-07-20", "wf-dup")
        write_frame(frames_root, "2026-07-21", "wf-dup")
        steps.append(attempt(weilan_trace, frames_root, "wf-dup"))
    elif scenario == "empty_frame_file_only":
        write_frame(frames_root, "2026-07-20", "wf-empty", events=0)
        steps.append(attempt(weilan_trace, frames_root, "wf-empty"))
    elif scenario == "empty_and_live_same_id":
        write_frame(frames_root, "2026-07-20", "wf-mixed", events=0)
        write_frame(frames_root, "2026-07-21", "wf-mixed")
        steps.append(attempt(weilan_trace, frames_root, "wf-mixed"))
    elif scenario == "moved_after_first_lookup":
        path = write_frame(frames_root, "2026-07-20", "wf-moved")
        steps.append(attempt(weilan_trace, frames_root, "wf-moved"))
        target_dir = os.path.join(frames_root, "2026-07-21")
        os.makedirs(target_dir, exist_ok=True)
        os.replace(path, os.path.join(target_dir, "wf-moved.jsonl"))
        steps.append(attempt(weilan_trace, frames_root, "wf-moved"))
    elif scenario == "deleted_after_first_lookup":
        path = write_frame(frames_root, "2026-07-20", "wf-gone")
        steps.append(attempt(weilan_trace, frames_root, "wf-gone"))
        os.remove(path)
        steps.append(attempt(weilan_trace, frames_root, "wf-gone"))
    elif scenario == "appended_by_this_process_after_first_lookup":
        write_frame(frames_root, "2026-07-20", "wf-old")
        steps.append(attempt(weilan_trace, frames_root, "wf-old"))
        from pathlib import Path

        new_path = Path(frames_root) / "2026-07-21" / "wf-fresh.jsonl"
        weilan_trace.append_event(
            new_path,
            weilan_trace.make_event("wf-fresh", "frame_opened", "L2", "W", {}),
        )
        steps.append(attempt(weilan_trace, frames_root, "wf-fresh"))
    elif scenario == "foreign_second_file_after_first_lookup":
        write_frame(frames_root, "2026-07-20", "wf-race")
        steps.append(attempt(weilan_trace, frames_root, "wf-race"))
        write_frame(frames_root, "2026-07-21", "wf-race")
        steps.append(attempt(weilan_trace, frames_root, "wf-race"))
    else:
        raise SystemExit("unknown scenario: " + scenario)

    json.dump(steps, sys.stdout, ensure_ascii=False, sort_keys=True)


def drive(scripts_dir, scenario):
    with tempfile.TemporaryDirectory(prefix="ffi-equiv-") as tmp:
        environment = os.environ.copy()
        environment["WEILAN_PROBE_SCRIPTS"] = scripts_dir
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", os.path.abspath(__file__),
             "--child", scenario, "--method-home", os.path.join(tmp, "method-state")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=environment,
        )
    if proc.returncode != 0:
        return {"child_returncode": proc.returncode, "stderr_tail": proc.stderr.strip()[-400:]}
    return json.loads(proc.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child")
    parser.add_argument("--method-home")
    args = parser.parse_args()
    if args.child:
        os.makedirs(args.method_home, exist_ok=True)
        run_scenario(args.child, args.method_home)
        return

    base_scripts = os.path.join(HERE, "artifacts", BASE, "solve-with-weilan", "scripts")
    cand_scripts = os.path.join(HERE, "artifacts", CAND, "solve-with-weilan", "scripts")
    rows, divergent = [], []
    for scenario in SCENARIOS:
        baseline = drive(base_scripts, scenario)
        candidate = drive(cand_scripts, scenario)
        same = baseline == candidate
        rows.append({
            "scenario": scenario,
            "baseline": baseline,
            "candidate": candidate,
            "equivalent": same,
        })
        if not same:
            divergent.append(scenario)
    result = {
        "base_artifact_hash": BASE,
        "candidate_artifact_hash": CAND,
        "scenario_count": len(SCENARIOS),
        "equivalent_count": sum(1 for row in rows if row["equivalent"]),
        "divergent_scenarios": divergent,
        "expected_divergent_scenarios": ["foreign_second_file_after_first_lookup"],
        "divergence_is_exactly_the_disclosed_race":
            divergent == ["foreign_second_file_after_first_lookup"],
        "rows": rows,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
