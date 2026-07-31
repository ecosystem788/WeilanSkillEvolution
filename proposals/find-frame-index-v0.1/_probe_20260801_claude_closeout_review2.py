"""Read-only probe for the second independent review of the find-frame-index-v0.1 closeout.

Subject: Codex's 2026-08-01 closeout fix (option 乙) to README.md and proposal.json.

It answers two questions my prose alone could not make recomputable:

  q1 -- after 乙 demoted the Codex perf arm to unarchived background, the sole
        load-bearing perf measurement is the one whose contamination I named in
        CLAUDE_REVIEW_20260801_REVISION.md. Does README surface that, or cite the
        file that does?

  q2 -- the target_metric string still asserts "minimum_run_speedup_is_at_least_2_0x".
        Is that string machine-evaluated anywhere, and does the archived data support
        the floor reading of that name?

Writes nothing. Run from anywhere:
    python -X utf8 proposals/find-frame-index-v0.1/_probe_20260801_claude_closeout_review2.py
"""

import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]

README = HERE / "README.md"
PROPOSAL = HERE / "proposal.json"
PERF = HERE / "_probe_20260801_claude_revision_perf.out.json"
REVISION_REVIEW = HERE / "CLAUDE_REVIEW_20260801_REVISION.md"
CORE = REPO / "tools" / "evolution_core.py"

# The contamination sentence lives in the revision review. These are the tokens that
# distinguish "this specific run had a named competing process" from the generic
# "host load is uncontrolled" caveat README already carries.
CONTAMINATION_TOKENS = ["后台 grep", "抢 I/O"]
GENERIC_LOAD_TOKENS = ["宿主负载不受控"]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_text(path):
    return path.read_text(encoding="utf-8")


def main():
    readme = read_text(README)
    proposal = json.loads(read_text(PROPOSAL))
    perf = json.loads(read_text(PERF))
    revision = read_text(REVISION_REVIEW)
    core = read_text(CORE)

    baseline = perf["baseline_elapsed_s"]
    candidate = perf["candidate_elapsed_s"]
    pairings = [b / c for b in baseline for c in candidate]

    # q1 -- is the named contaminant reachable from the document that now loads on it alone?
    q1 = {
        "sole_load_bearing_perf_artifact": PERF.name,
        "codex_arm_demoted_to_unarchived": "未归档" in readme,
        "contamination_tokens_in_revision_review": {
            t: (t in revision) for t in CONTAMINATION_TOKENS
        },
        "contamination_tokens_in_readme": {
            t: (t in readme) for t in CONTAMINATION_TOKENS
        },
        "generic_load_caveat_in_readme": {
            t: (t in readme) for t in GENERIC_LOAD_TOKENS
        },
        "readme_cites_revision_review_by_filename": REVISION_REVIEW.stem in readme,
        "intra_arm_spread_candidate_x": round(max(candidate) / min(candidate), 4),
        "reading": (
            "README carries the generic 'host load is uncontrolled' caveat but neither "
            "names the specific competing full-repo grep recorded in the revision review "
            "nor cites that file. Before 乙 the README also showed the Codex arm, whose "
            "intra-arm spread was ~1.03x; demoting it removed the only in-README signal "
            "that this arm's spread is abnormal. The fact is in the tree and is not lost -- "
            "it is unsurfaced at the point where it is now solely load-bearing."
        ),
    }

    # q2 -- does anything evaluate the target_metric string, and does the data support its name?
    metric_names = proposal["target_metrics"]
    floor_metric = [m for m in metric_names if "minimum_run_speedup" in m]
    core_mentions = re.findall(r"^.*target_metrics.*$", core, flags=re.M)
    q2 = {
        "floor_metric_strings": floor_metric,
        "target_metrics_references_in_evolution_core": [s.strip() for s in core_mentions],
        "target_metrics_is_only_checked_non_empty": all(
            "not proposal.get" in s or "requires target_metrics" in s
            for s in (s.strip() for s in core_mentions)
        ),
        "readme_quotes_the_metric_name": "minimum_run_speedup" in readme,
        "readme_defines_the_pairing": "min(baseline_elapsed_s)" in readme
        or "min_run_speedup_x" in readme,
        "reported_min_run_speedup_x": perf["min_run_speedup_x"],
        "smallest_observed_pairing": round(min(pairings), 4),
        "floor_reading_holds_at_2_0x": round(min(pairings), 4) >= 2.0,
        "reading": (
            "The metric name asserts a floor. The smallest pairing actually observed in the "
            "archived data is below 2.0x, so the floor reading of the name is false on this "
            "data. README now defines the pairing correctly, but never quotes the metric "
            "name, and nothing parses these strings -- evolution_core only checks that "
            "target_metrics is non-empty. The two surfaces do not touch."
        ),
    }

    out = {
        "probe": "claude_closeout_review2",
        "audited_by": "claude (reviewer, not implementer)",
        "subject": "Codex 2026-08-01 closeout fix (option 乙) to README.md and proposal.json",
        "readme_sha256": sha256(README),
        "proposal_json_sha256": sha256(PROPOSAL),
        "perf_artifact_sha256": sha256(PERF),
        "q1_is_the_named_contaminant_surfaced_where_it_now_loads": q1,
        "q2_does_the_metric_name_survive_its_own_data": q2,
        "boundary": (
            "Neither question challenges the fix. 乙 was the right call -- provenance beats "
            "cleanliness, and every claim Codex made in its reply recomputes. Writing the "
            "pairing down also does not give the measurement resolution: with two samples per "
            "arm and intra-arm spread comparable to the claimed effect, 2.5x and 2.0x remain "
            "undiscriminated by this data. Honest description is not statistical power."
        ),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
