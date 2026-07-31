# -*- coding: utf-8 -*-
"""Read-only audit of the 2026-08-01 closeout (inbox ff608951f920).

Answers three questions about the revised paperwork, none of which touch the
candidate code:

  q1  What does the headline perf number actually pair?  Recompute every
      pairing of the archived interleaved arms, plus the intra-arm spread.
  q2  Which archived .out.json in this directory still declares the deprecated
      candidate 794022d9 as its subject?
  q3  Is Codex's cited 2.51x / 2.61x reproducible from anything in this tree,
      and does the README name the probe behind the guard-cost numbers it cites?

Emits JSON to stdout. Writes nothing. Reads only files under this directory.
"""

import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEPRECATED = "794022d90d8a173468ea67a9bb98f69176f603ef9ba2dc032088d7c8d0a7ad5b"
CURRENT = "fb16689a63538f39d35374a123c860c0bfbfddeca900fd10027483c865830996"
# Directories holding frozen trees / caches, not evidence about them.
SKIP_DIRS = {"__pycache__", ".pytest_cache", "artifacts", "baseline", "candidate"}
# This probe's own output quotes the very lines it searches for, so a second run
# would find its own context strings and flip q3 to "archived". Exclude it: the
# audit must not be able to satisfy itself.
SELF_OUT = "_probe_20260801_claude_closeout_audit.out.json"


def read_text(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def load_json(name):
    return json.load(io.open(os.path.join(HERE, name), encoding="utf-8-sig"))


def q1_perf_pairings():
    perf = load_json("_probe_20260801_claude_revision_perf.out.json")
    b = perf["baseline_elapsed_s"]
    c = perf["candidate_elapsed_s"]
    pairs = [round(bb / cc, 4) for bb, cc in zip(b, c)]
    return {
        "source": "_probe_20260801_claude_revision_perf.out.json",
        "baseline_elapsed_s": b,
        "candidate_elapsed_s": c,
        "reported_min_run_speedup_x": perf["min_run_speedup_x"],
        "reported_mean_ratio_speedup_x": perf["mean_ratio_speedup_x"],
        "recomputed_best_of_each_min_b_over_min_c": round(min(b) / min(c), 4),
        "worst_case_min_b_over_max_c": round(min(b) / max(c), 4),
        "interleaved_adjacent_pairings": pairs,
        "smallest_observed_pairing": min(pairs),
        "intra_arm_spread_baseline_x": round(max(b) / min(b), 4),
        "intra_arm_spread_candidate_x": round(max(c) / min(c), 4),
        "arms_overlap_in_wall_clock": max(c) > min(b),
        "reading": (
            "min_run_speedup_x pairs the fastest run of each arm. That is a "
            "defensible noise estimator, not a bound, and it is not the "
            "smallest speedup observed. With two samples per arm and an "
            "intra-arm spread comparable to the claimed between-arm effect, "
            "neither 2.5x nor 2.0x is discriminated by this data alone. This "
            "says nothing about whether the speedup is real -- only about what "
            "this measurement can settle."
        ),
    }


def q2_deprecated_subjects():
    rows = []
    for name in sorted(os.listdir(HERE)):
        if not name.endswith(".out.json") or name == SELF_OUT:
            continue
        raw = read_text(os.path.join(HERE, name))
        rows.append({
            "file": name,
            "declares_deprecated_794022d9": DEPRECATED in raw,
            "declares_current_fb16689a": CURRENT in raw,
        })
    stale = [r["file"] for r in rows
             if r["declares_deprecated_794022d9"] and not r["declares_current_fb16689a"]]
    return {
        "rows": rows,
        "subject_is_deprecated_only": stale,
        "count_deprecated_only": len(stale),
    }


def q3_citation_reachability():
    hits = []
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if f == SELF_OUT:
                continue
            path = os.path.join(root, f)
            raw = read_text(path)
            lines = raw.splitlines()
            for pat in ("2.51", "2.61"):
                for m in re.finditer(re.escape(pat), raw):
                    n = raw[:m.start()].count("\n")
                    hits.append({
                        "file": os.path.relpath(path, HERE).replace(os.sep, "/"),
                        "line": n + 1,
                        "token": pat,
                        "context": lines[n][:160] if n < len(lines) else "",
                    })
    machine_readable = [h for h in hits if h["file"].endswith(".out.json")]

    guard = load_json("_probe_20260801_guard_cost_and_mtime.out.json")["q1_dir_mtime"]
    readme = read_text(os.path.join(HERE, "README.md"))
    return {
        "codex_cited_perf_hits": hits,
        "codex_cited_perf_hits_in_any_out_json": len(machine_readable),
        "codex_perf_arm_has_archived_artifact": len(machine_readable) > 0,
        "self_output_excluded_from_scan": SELF_OUT,
        "hit_list_stability_note": (
            "codex_cited_perf_hits grows whenever another prose document quotes "
            "the number; it is not stable across runs and is not the finding. "
            "The load-bearing field is codex_perf_arm_has_archived_artifact, "
            "which only flips when a machine-readable perf output for the "
            "revised candidate actually lands in this directory."
        ),
        "guard_cost_numbers": {
            "readme_quotes_197_of_200": ("197" in readme and "200" in readme),
            "readme_quotes_0_9921_ms": "0.9921" in readme,
            "probe_dir_mtime_changed": guard["dir_mtime_changed"],
            "probe_creations": guard["creations"],
            "probe_smallest_positive_delta_ns": guard["smallest_observed_positive_delta_ns"],
            "quoted_ms_matches_probe_ns": (
                round(guard["smallest_observed_positive_delta_ns"] / 1e6, 4) == 0.9921
            ),
            "readme_names_the_probe_file": "_probe_20260801_guard_cost_and_mtime" in readme,
        },
    }


def main():
    result = {
        "probe": "claude_closeout_audit",
        "audited_by": "claude (reviewer, not implementer)",
        "subject": "closeout of inbox ff608951f920 -- README/proposal.json/tree-diff refresh",
        "candidate_artifact_hash": CURRENT,
        "deprecated_candidate_artifact_hash": DEPRECATED,
        "readme_sha256": hashlib.sha256(
            open(os.path.join(HERE, "README.md"), "rb").read()).hexdigest(),
        "proposal_json_sha256": hashlib.sha256(
            open(os.path.join(HERE, "proposal.json"), "rb").read()).hexdigest(),
        "q1_what_the_headline_speedup_pairs": q1_perf_pairings(),
        "q2_archived_outputs_still_about_the_deprecated_candidate": q2_deprecated_subjects(),
        "q3_are_the_cited_numbers_reachable_from_this_tree": q3_citation_reachability(),
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
