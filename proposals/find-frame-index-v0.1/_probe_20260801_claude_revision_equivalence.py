"""Read-only: Claude's INDEPENDENT re-run of the load-bearing equivalence probe
against the REVISED candidate fb16689a...

Why this exists: _probe_20260801_find_frame_equivalence.py calls itself "the
load-bearing evidence for the change", and its archived .out.json still measures
the superseded candidate 794022d9... The revision was never put through it. The
scenario the revision exists to fix -- foreign_second_file_after_first_lookup --
is precisely the one that probe was built to isolate, so leaving it un-rerun
means the revision's central claim had no equivalence evidence at all.

This module imports the original probe rather than copying its scenarios, so
there is one definition of the nine scenarios, not two that can drift apart.
Only the candidate artifact id is overridden.

It also adds one thing the original could not ask. Scenario 9 creates the second
file immediately after the first lookup, with no sleep. The guard rests on
directory mtime, whose grain was measured at roughly 1 ms, so back-to-back
operations can land inside one tick and stay invisible. Whether the guard closes
scenario 9 *in practice* is therefore a frequency, not a yes/no -- so the
scenario is run REPEATS times against each tree and the outcomes are tallied.
A single green run of scenario 9 would not have been evidence of anything.

Emits JSON to stdout; writes only inside its own temp dirs.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAND = "fb16689a63538f39d35374a123c860c0bfbfddeca900fd10027483c865830996"
RACE = "foreign_second_file_after_first_lookup"
REPEATS = int(os.environ.get("WEILAN_PROBE_REPEATS", "25"))


def load_original():
    path = os.path.join(HERE, "_probe_20260801_find_frame_equivalence.py")
    spec = importlib.util.spec_from_file_location("ffi_equivalence_original", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    original = load_original()
    base_scripts = os.path.join(
        HERE, "artifacts", original.BASE, "solve-with-weilan", "scripts")
    cand_scripts = os.path.join(HERE, "artifacts", CAND, "solve-with-weilan", "scripts")

    rows, divergent = [], []
    for scenario in original.SCENARIOS:
        baseline = original.drive(base_scripts, scenario)
        candidate = original.drive(cand_scripts, scenario)
        same = baseline == candidate
        rows.append({"scenario": scenario, "baseline": baseline,
                     "candidate": candidate, "equivalent": same})
        if not same:
            divergent.append(scenario)

    repeated = []
    for _ in range(REPEATS):
        baseline = original.drive(base_scripts, RACE)
        candidate = original.drive(cand_scripts, RACE)
        repeated.append({"equivalent": baseline == candidate,
                         "candidate_second_lookup": (candidate or [{}])[-1]})
    agree = sum(1 for row in repeated if row["equivalent"])

    result = {
        "probe": "claude_revision_equivalence",
        "measured_by": "claude (reviewer, not implementer)",
        "base_artifact_hash": original.BASE,
        "candidate_artifact_hash": CAND,
        "scenario_count": len(original.SCENARIOS),
        "equivalent_count": sum(1 for row in rows if row["equivalent"]),
        "divergent_scenarios": divergent,
        "race_scenario_repeats": {
            "scenario": RACE,
            "repeats": REPEATS,
            "equivalent_to_baseline": agree,
            "divergent_from_baseline": REPEATS - agree,
            "note": (
                "Divergences here are not defects: they are the disclosed "
                "same-mtime-tick residual showing up at its natural rate under "
                "back-to-back writes. What would be a defect is the reverse -- "
                "the guard never firing."
            ),
            "outcomes": repeated,
        },
        "rows": rows,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
